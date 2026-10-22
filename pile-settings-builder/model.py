"""Settings generation without GUI or third-party dependencies."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SELECTOR = ('model', 'group', 'node', 'case')


def read_source(path):
    document = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(document, dict):
        raise ValueError('Expected a JSON object containing piers or reactions.')
    if 'piers' in document and 'soil_profiles' in document:
        piers = document['piers']
        prepared = True
    elif 'reactions' in document:
        if document.get('error'):
            raise ValueError(f"Reaction extraction failed: {document['error']}")
        prepared = False
        grouped = {}
        for row in document['reactions']:
            mark = row.get('mark')
            if not mark:
                raise ValueError('Each reaction must contain a footing mark. Export prepared inputs from the viewer.')
            grouped.setdefault(mark, []).append(row)
        piers = [dict(footing=mark, reactions=rows) for mark, rows in grouped.items()]
    else:
        raise ValueError('Open prepared pier inputs or viewer reaction results, not a settings/solver-summary file.')
    if not piers:
        raise ValueError('No footings found in this file.')
    marks = [p['footing'] for p in piers]
    if len(set(marks)) != len(marks):
        raise ValueError('Footing labels must be unique.')
    for pier in piers:
        for row in pier['reactions']:
            if any(key not in row for key in SELECTOR):
                raise ValueError('A reaction is missing its model, group, node, or case.')
    return document, piers, prepared


def defaults():
    return json.loads((ROOT / 'openseespy-cli/examples/settings.json').read_text(encoding='utf-8-sig'))


def soil_labels(document, pier):
    return list(dict.fromkeys(
        layer['properties']['model']
        for profile in document.get('soil_profiles', [])
        if profile['table_name'] == pier.get('soil_table')
        for layer in profile['layers']))


def suggested_soil_model(label):
    tokens = set(label.upper().replace('/', ' ').replace('-', ' ').split())
    has_clay = bool(tokens & {'CLAY', 'CLAYEY'})
    has_granular = bool(tokens & {'SAND', 'SANDY', 'GRAVEL'})
    if has_clay and not has_granular:
        return 'API_clay'
    if has_granular and not has_clay:
        return 'API_sand'
    return ''


def soil_layer_details(document, pier, label):
    def display(value):
        if value is None:
            return 'Missing'
        return f'{value:g}' if isinstance(value, (int, float)) else str(value)

    layers = [(index, layer) for profile in document.get('soil_profiles', [])
              if profile['table_name'] == pier.get('soil_table')
              for index, layer in enumerate(profile['layers'], 1) if layer['properties']['model'] == label]
    details = []
    for index, layer in layers:
        values = layer['properties']
        details.append(
            f"Layer {index} | Excel row {layer['source_row']} | {display(values['start'])}-{display(values['end'])} ft | label: {label}\n"
            f"Su ultimate/factored {display(values['cohesion_ultimate'])}/{display(values['cohesion_factored'])} lb/ft^2; "
            f"e50/factored {display(values['e50'])}/{display(values['e50_factored'])}; "
            f"phi {display(values['friction_angle'])} deg; k-static/factored "
            f"{display(values['k_static'])}/{display(values['k_static_factored'])} lb/in^3")
    return details


def positive(value, label, integer=False, zero=False):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{label}: enter a number.') from None
    if not math.isfinite(result) or result < 0 or (not zero and result == 0):
        raise ValueError(f'{label}: enter a finite {"nonnegative" if zero else "positive"} number.')
    if integer and not result.is_integer():
        raise ValueError(f'{label}: enter a whole number.')
    return int(result) if integer else result


def concrete_modulus(fc_psi):
    """Normal-weight relation requested by the user, with both values in psi."""
    return 57000 * math.sqrt(positive(fc_psi, "Concrete f'c (psi)"))


def build_settings(pier, reaction, fields, soils):
    selector = {key: reaction[key] for key in SELECTOR}
    matches = [r for r in pier['reactions'] if all(r[k] == selector[k] for k in SELECTOR)]
    if len(matches) != 1:
        raise ValueError('The selected reaction must identify exactly one source row.')
    result = defaults()
    result.update(footing=pier['footing'], reaction=selector)
    if fields['plane'] not in ('X', 'Y'):
        raise ValueError('Choose plane X or Y.')
    result['plane'] = fields['plane']
    for key in ('embedment_ft', 'mesh_size_ft', 'max_iterations'):
        result[key] = positive(fields[key], key, integer=key == 'max_iterations')
    result['projection_height_ft'] = positive(fields.get('projection_height_ft', 1), 'Projection above ground (ft)', zero=True)
    result['material'] = {key: positive(fields[key], key, zero=key == 'poisson_ratio')
                          for key in ('E_psi', 'unit_weight_pcf', 'poisson_ratio')}
    if result['material']['poisson_ratio'] >= .5:
        raise ValueError('Poisson ratio must be less than 0.5.')
    for key in ('lateral', 'moment', 'axial'):
        if str(fields[key]) not in ('1', '-1'):
            raise ValueError(f'{key}: choose +1 or -1.')
        result['load_signs'][key] = int(fields[key])
    for key in ('load_steps', 'energy_tolerance_lbf_ft', 'water_unit_weight_pcf', 'drag_ratio'):
        result['opensees'][key] = positive(fields[key], key, integer=key == 'load_steps', zero=key == 'drag_ratio')
    if result['opensees']['drag_ratio'] > 1:
        raise ValueError('Drag ratio must be between 0 and 1.')
    if fields['transformation'] not in ('Linear', 'PDelta'):
        raise ValueError('Choose Linear or PDelta transformation.')
    result['opensees']['transformation'] = fields['transformation']
    result['soil_models'] = {}
    for label, choice in soils.items():
        model = choice['model']
        if not model:
            continue
        if model not in ('API_clay', 'API_sand'):
            raise ValueError(f'{label}: choose a soil model.')
        item = dict(model=model, kind='static')
        if model == 'API_clay':
            if choice['cohesion'] not in ('cohesion_ultimate', 'cohesion_factored') or choice['strain'] not in ('e50', 'e50_factored'):
                raise ValueError(f'{label}: choose cohesion and strain fields.')
            item.update(cohesion=choice['cohesion'], strain=choice['strain'], J=positive(choice['J'], f'{label} J'))
            if not .25 <= item['J'] <= .5:
                raise ValueError(f'{label}: J must be between 0.25 and 0.5.')
        else:
            if choice['modulus'] not in ('k_static', 'k_static_factored'):
                raise ValueError(f'{label}: choose the sand modulus field.')
            item['modulus'] = choice['modulus']
        result['soil_models'][label] = item
    return result


def check_prepared(document, settings):
    """Run the existing CLI validator without importing the OpenSeesPy solver."""
    folder = ROOT / 'openseespy-cli'
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location('_settings_builder_opensees', folder / 'cli.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.prepare(copy.deepcopy(document), copy.deepcopy(settings))


def save_settings(path, settings, source_path):
    target = Path(path).resolve()
    if target == Path(source_path).resolve():
        raise ValueError('Choose a different filename; the source results cannot be overwritten.')
    target.write_text(json.dumps(settings, indent=2, allow_nan=False) + '\n', encoding='utf-8')
