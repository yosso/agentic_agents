"""Read CLI results without changing the solver's exported files."""
import csv
import json
import math
from pathlib import Path


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def numeric(row, key):
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f'{key}: non-finite result.')
    return value


def load_results(folder):
    folder = Path(folder)
    plan = read_json(folder / 'analysis-inputs.json')
    summary = read_json(folder / 'summary.json')
    validation = read_json(folder / 'validation.json')
    if summary.get('status') != 'converged' or not validation.get('valid'):
        raise ValueError('This folder does not contain a validated, converged analysis.')
    with (folder / 'displacements.csv').open(encoding='utf-8-sig', newline='') as stream:
        displacements = list(csv.DictReader(stream))
    with (folder / 'forces.csv').open(encoding='utf-8-sig', newline='') as stream:
        forces = list(csv.DictReader(stream))
    if not displacements or not forces:
        raise ValueError('Result tables are empty.')
    imperial = 'Elevation [ft]' in displacements[0]
    elevation = 'Elevation [ft]' if imperial else 'Elevation [m]'
    deflection = 'Deflection [in]' if imperial else 'Deflection [m]'
    curves = {'Deflection [in]': [[(numeric(r, deflection) / (1 if imperial else .0254),
                                  -numeric(r, elevation) / (1 if imperial else .3048)) for r in displacements]],
              'Shear [kip]': [], 'Moment [kip-ft]': []}
    elements = {}
    for row in forces:
        if row['end'] not in ('i', 'j'):
            raise ValueError('Unknown element end in force table.')
        elements.setdefault(int(row['element']), {})[row['end']] = row
    for tag in sorted(elements):
        ends = elements[tag]
        if set(ends) != {'i', 'j'}:
            raise ValueError(f'Element {tag} is missing an end force.')
        for title, column, factor in [('Shear [kip]', 'V_local [kip]' if imperial else 'V_local [kN]', 1 if imperial else 4.4482216152605),
                                      ('Moment [kip-ft]', 'M_local [kip-ft]' if imperial else 'M_local [kNm]', 1 if imperial else 4.4482216152605*.3048)]:
            curves[title].append([(numeric(ends[end], column) * (1 if end == 'i' else -1) / factor,
                                   -numeric(ends[end], elevation) / (1 if imperial else .3048)) for end in ('i', 'j')])
    boundaries = []
    for layer in plan.get('layers', []):
        boundaries.append((-layer.get('bottom_ft', layer.get('bottom', 0)/.3048), layer['name']))
    return dict(folder=folder, plan=plan, summary=summary, validation=validation,
                curves=curves, boundaries=boundaries)
