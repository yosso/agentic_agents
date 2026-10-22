"""Common prepared-input validation and unit conversion for pile solver CLIs.

Only standard-library modules and the typed workbook soil schema are required.
"""
from dataclasses import asdict
import math
from soil_parameters import SoilParameters

FT = 0.3048
LBF_KN = 0.0044482216152605
PSI_KPA = LBF_KN / 0.0254**2
PSF_KPA = LBF_KN / FT**2
PCF_KNM3 = LBF_KN / FT**3
PCI_KNM3 = LBF_KN / 0.0254**3
LBF_FT_KNM = LBF_KN * FT
UNITS = dict(depth='ft', density='lb/ft^3', cohesion='lb/ft^2',
             friction_angle='degrees', subgrade_modulus='lb/in^3', strain='unitless')


def number(value, label, minimum=None, strictly=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label}: finite numeric value required.')
    if minimum is not None and (value <= minimum if strictly else value < minimum):
        raise ValueError(f'{label}: must be {">" if strictly else ">="} {minimum}.')
    return float(value)


def converted_positive(values, customary, metric, factor, label):
    keys = [key for key in (customary, metric) if key in values]
    if len(keys) != 1:
        raise ValueError(f'{label}: supply exactly one of {customary} or {metric}.')
    key = keys[0]
    value = number(values[key], f'{label}.{key}', 0, True)
    return number(value * factor if key == customary else value, f'{label}.{metric}', 0, True)


def choose(value, allowed, label):
    if value not in allowed:
        raise ValueError(f'{label}: choose one of {allowed}.')
    return value


def unique(rows, label):
    if len(rows) != 1:
        raise ValueError(f'{label}: expected exactly one match; found {len(rows)}.')
    return rows[0]


def prepare(document, settings):
    """Validate and convert inputs without importing or running OpenPile."""
    mark = settings['footing']
    pier = unique([p for p in document['piers'] if p['footing'] == mark], 'Footing')
    profile = unique([p for p in document['soil_profiles'] if p['table_name'] == pier['soil_table']], 'Soil table')
    # Block global and selected-footing errors, preserving findings for other piers.
    blockers = [i for i in document.get('issues', []) if i['severity'] == 'ERROR'
                and i.get('footing', '') in ('', mark)]
    if blockers:
        raise ValueError('Prepared-input errors:\n' + '\n'.join(
            f"{i['source']}: {i['message']}" for i in blockers))
    if profile['units'] != UNITS:
        raise ValueError(f'Soil units must be {UNITS}; no unrecognized units are converted.')
    if document.get('reaction_units') != {'force': 'N', 'moment': 'N-m'}:
        raise ValueError('Prepared reaction units must be N and N-m.')
    selector = settings['reaction']
    load = unique([r for r in pier['reactions'] if all(
        r.get(k) == selector[k] for k in ('model', 'group', 'node', 'case'))], 'Reaction')
    for key in ('FX', 'FY', 'FZ', 'MX', 'MY', 'MZ'):
        number(load[key], key)
    plane = choose(settings['plane'], ('X', 'Y'), 'plane')
    force_key, moment_key = ('FX', 'MY') if plane == 'X' else ('FY', 'MX')
    signs = settings['load_signs']
    for key in ('lateral', 'moment', 'axial'):
        number(signs[key], f'load_signs.{key}')
        choose(signs[key], (-1, 1), f'load_signs.{key}')
    depth = number(settings['embedment_ft'], 'embedment_ft', 0, True)
    minimum = number(pier['minimum_embedment_ft'], 'minimum_embedment_ft', 0, True)
    if depth < minimum:
        raise ValueError('Requested embedment is below the workbook minimum.')
    diameter = number(pier['diameter_ft'], 'diameter_ft', 0, True)
    water = number(pier['water_table_depth_ft'], 'water_table_depth_ft', 0)
    number(pier['allowable_deflection_in'], 'allowable_deflection_in', 0, True)
    material = dict(settings['material'])
    modulus_fields = [key for key in ('E_psi', 'E_kpa') if key in material]
    if len(modulus_fields) != 1:
        raise ValueError('material: supply exactly one of E_psi or E_kpa.')
    modulus_field = modulus_fields[0]
    elastic_modulus = number(material[modulus_field], f'material.{modulus_field}', 0, True)
    material['E_kpa'] = number(
        elastic_modulus * PSI_KPA if modulus_field == 'E_psi' else elastic_modulus,
        'converted material.E_kpa', 0, True)
    material['unit_weight_kn_m3'] = converted_positive(
        material, 'unit_weight_pcf', 'unit_weight_kn_m3', PCF_KNM3, 'material')
    nu = number(material['poisson_ratio'], 'material.poisson_ratio', 0)
    if nu >= 0.5:
        raise ValueError('Poisson ratio must be less than 0.5.')
    choose(settings['boundary'], ('free_head_axially_fixed_tip',), 'boundary')
    mesh = number(settings['mesh_size_ft'], 'mesh_size_ft', 0, True)
    iterations = settings['max_iterations']
    number(iterations, 'max_iterations', 0, True)
    if not isinstance(iterations, int):
        raise ValueError('max_iterations must be an integer.')
    layers = []
    previous = 0.0
    for layer in profile['layers']:
        soil = SoilParameters(**layer['properties'])
        source = f"{profile['table_name']} row {layer['source_row']}"
        for field, value in asdict(soil).items():
            if field != 'model' and not (field == 'k_cyclic' and value is None):
                number(value, source + ' ' + field, 0)
        start = number(soil.start, source + ' START', 0)
        end = number(soil.end, source + ' END', start, True)
        if not math.isclose(start, previous, rel_tol=0, abs_tol=1e-8):
            raise ValueError(source + ': layers must start at zero and share boundaries.')
        previous = end
        if start >= depth:
            continue
        mapping = settings['soil_models'].get(soil.model)
        if mapping is None:
            raise ValueError(f'{source}: no explicit soil model mapping for {soil.model!r}.')
        model = choose(mapping['model'], ('API_clay', 'API_sand'), source + ' model')
        kind = choose(mapping['kind'], ('static', 'cyclic'), source + ' kind')
        kwargs = {'kind': kind}
        used = ['start', 'end', 'model', 'density']
        if model == 'API_clay':
            cohesion = choose(mapping['cohesion'], ('cohesion_ultimate', 'cohesion_factored'), source)
            strain = choose(mapping['strain'], ('e50', 'e50_factored'), source)
            kwargs['Su'] = number(getattr(soil, cohesion), source + ' ' + cohesion, 0, True) * PSF_KPA
            kwargs['eps50'] = number(getattr(soil, strain), source + ' ' + strain, 0, True)
            if kwargs['eps50'] >= 1:
                raise ValueError(source + ': epsilon50 must be a unitless fraction below 1; no percent conversion is assumed.')
            kwargs['J'] = number(mapping['J'], source + ' J', 0.25)
            if kwargs['J'] > 0.5:
                raise ValueError(source + ': J must be between 0.25 and 0.5.')
            used += [cohesion, strain]
        else:
            kwargs['phi'] = number(soil.friction_angle, source + ' friction_angle', 0, True)
            if kwargs['phi'] >= 90:
                raise ValueError(source + ': friction angle must be below 90 degrees.')
            modulus = choose(mapping['modulus'], ('k_static', 'k_static_factored') if kind == 'static' else ('k_cyclic',), source)
            kwargs['initial_subgrade_modulus'] = number(getattr(soil, modulus), source + ' ' + modulus, 0, True) * PCI_KNM3
            used += ['friction_angle', modulus]
        weight = number(soil.density, source + ' density', 0, True) * PCF_KNM3
        if weight < 10:
            raise ValueError(source + ': OpenPile requires total unit weight of at least 10 kN/m^3.')
        layers.append(dict(name=soil.model, top=-start * FT, bottom=-min(end, depth) * FT,
                           weight=weight, model=model, parameters=kwargs,
                           used_fields=used, source_cells=layer['cells'], raw_properties=layer.get('raw_properties', {})))
    if not layers or previous < depth:
        raise ValueError('Soil profile must cover the full requested embedment.')
    return dict(footing=mark, workbook=document.get('workbook'), soil_table=profile['table_name'],
                source_units=profile['units'], diameter_m=diameter * FT, embedment_m=depth * FT,
                water_elevation_m=-water * FT, mesh_m=mesh * FT, material=material,
                layers=layers, reaction=load, plane=plane,
                loads=dict(Py=load[force_key] * signs['lateral'] / 1000,
                           Mx=load[moment_key] * signs['moment'] / 1000,
                           Pz=load['FZ'] * signs['axial'] / 1000),
                max_iterations=iterations, settings=settings,
                allowable_deflection_in=pier['allowable_deflection_in'],
                warnings=['One 2D plane only; torsion and the other plane are not analyzed.',
                          'Axial tip restraint is prescribed; no axial soil capacity or settlement check.',
                          'Computed displacement is not residual/non-recoverable deflection; no design pass/fail is issued.'],
                preparation_findings=document.get('issues', []))

