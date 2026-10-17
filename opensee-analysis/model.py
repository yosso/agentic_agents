"""Batch depth sizing through the existing OpenSeesPy CLI."""
import copy
import csv
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SELECTOR = ('model', 'group', 'node', 'case')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')


def select_cases(pier):
    rows = pier['reactions']
    if not rows:
        raise ValueError('No reaction rows for this footing.')
    criteria = [(f'Maximum |{key}|', lambda r, key=key: abs(r[key])) for key in ('FX', 'FY', 'MX', 'MY', 'MZ')]
    criteria += [('Maximum resultant shear', lambda r: math.hypot(r['FX'], r['FY'])),
                 ('Maximum resultant bending', lambda r: math.hypot(r['MX'], r['MY'])),
                 ('Maximum compression', lambda r: r['FZ'] if r['FZ'] > 0 else None),
                 ('Maximum uplift', lambda r: -r['FZ'] if r['FZ'] < 0 else None)]
    selected = {}
    identities = [tuple(r[k] for k in SELECTOR) for r in rows]
    if len(set(identities)) != len(identities):
        raise ValueError('Reaction selectors are not unique.')
    for label, measure in criteria:
        values = [measure(r) for r in rows]
        if any(v is not None and not math.isfinite(v) for v in values):
            raise ValueError('Non-finite reaction value.')
        eligible = [v for v in values if v is not None]
        if not eligible:
            continue
        extreme = max(eligible)
        for row, value in zip(rows, values):
            if value != extreme:
                continue
            identity = tuple(row[k] for k in SELECTOR)
            selected.setdefault(identity, dict(reaction={k: row[k] for k in SELECTOR}, criteria=[]))['criteria'].append(label)
    return sorted(selected.values(), key=lambda item: str(tuple(item['reaction'][k] for k in SELECTOR)))


def starting_depth(pier, requested):
    """Respect the requested trial depth without going below the workbook minimum."""
    minimum = float(pier['minimum_embedment_ft'])
    trial = float(requested)
    if not all(math.isfinite(v) and v > 0 for v in (minimum, trial)):
        raise ValueError('Trial embedment and workbook minimum must be positive finite values.')
    return max(minimum, trial)


def run_cli(inputs, settings, output, python):
    completed = subprocess.run([str(python), str(ROOT/'openseespy-cli/cli.py'), 'run',
                               '--inputs', str(inputs), '--settings', str(settings), '--output', str(output)],
                              capture_output=True, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout).strip())
    summary = read_json(output/'summary.json')
    if summary.get('status') != 'converged' or not math.isclose(summary.get('load_factor', 0), 1, abs_tol=1e-8):
        raise RuntimeError('Solver did not converge to full load.')
    return summary


def summarize_forces(records, root):
    maxima = {}
    for quantity, column, unit in [('shear', 'V_local [kip]', 'kip'), ('moment', 'M_local [kip-ft]', 'kip-ft')]:
        best = None
        for record in records:
            with (root/record['results_folder']/'forces.csv').open(newline='', encoding='utf-8-sig') as stream:
                for row in csv.DictReader(stream):
                    value = float(row[column])
                    if not math.isfinite(value):
                        raise ValueError('Non-finite force result.')
                    if best is None or abs(value) > best['absolute_value']:
                        best = dict(absolute_value=abs(value), signed_local_end_value=value, unit=unit,
                                    depth_ft=-float(row['Elevation [ft]']), element=int(row['element']), end=row['end'],
                                    plane=record['plane'], reaction=record['reaction'], results_folder=record['results_folder'])
        maxima[quantity] = best
    return maxima


def batch(inputs, template, output, increment=1, max_depth=60, mode='resultant', python=None,
          footings=None, progress=lambda message: None, cancelled=lambda: False, runner=run_cli):
    if not math.isfinite(increment) or increment <= 0 or not math.isfinite(max_depth) or max_depth <= 0:
        raise ValueError('Depth increment and maximum depth must be positive finite numbers.')
    if mode not in ('directional', 'resultant'):
        raise ValueError('Unknown deflection check mode.')
    document = read_json(inputs)
    base = copy.deepcopy(template) if isinstance(template, dict) else read_json(template)
    piers = document['piers']
    if footings:
        piers = [p for p in piers if p['footing'] in footings]
    if not piers:
        raise ValueError('No footings selected.')
    if len({p['footing'] for p in piers}) != len(piers):
        raise ValueError('Footing marks must be unique.')
    python = python or ROOT/'openseespy-cli/.venv/Scripts/python.exe'
    if not Path(python).is_file():
        raise ValueError('Select a Python interpreter with OpenSeesPy installed.')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    # Snapshots make every case reproducible if source files are later edited.
    write_json(output/'prepared-inputs.json', document)
    write_json(output/'template-settings.json', base)
    report = dict(check_mode=mode, depth_increment_ft=increment, maximum_depth_ft=max_depth,
                  case_selection='All ties for component/resultant lateral and bending extremes, torsion, compression and uplift; coincident vectors retained.',
                  limitations=['Load extremes do not guarantee the governing deflection over every combination.',
                               'Loaded elastic displacement is compared to the workbook allowable; residual/non-recoverable behavior is not evaluated.',
                               'Two independent 2D planes; resultant mode combines their head displacements. No torsional or axial soil capacity check.',
                               'Passing status means the configured deflection screen only, not complete design acceptance.'], footings=[])
    def persist():
        write_json(output/'batch-summary.json', report)
        if report['footings']:
            with (output/'footings.csv').open('w', newline='', encoding='utf-8') as stream:
                fields = ['footing', 'status', 'accepted_depth_ft', 'allowable_in', 'checked_deflection_in', 'max_shear_kip', 'max_moment_kip_ft', 'message']
                writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(report['footings'])
    for index, pier in enumerate(piers, 1):
        result = dict(footing=pier['footing'], status='running', accepted_depth_ft=None, trials=[])
        report['footings'].append(result)
        try:
            cases = select_cases(pier)
            result['selected_cases'] = cases
            allowable = float(pier['allowable_deflection_in'])
            start = starting_depth(pier, base['embedment_ft'])
            result.update(starting_depth_ft=start, minimum_embedment_ft=pier['minimum_embedment_ft'], requested_embedment_ft=base['embedment_ft'])
            if not math.isfinite(allowable) or allowable <= 0 or not math.isfinite(start) or start <= 0:
                raise ValueError('Minimum embedment and allowable deflection must be positive finite values.')
            profiles = [s for s in document['soil_profiles'] if s['table_name'] == pier['soil_table']]
            if len(profiles) != 1:
                raise ValueError('Soil profile is missing or ambiguous.')
            coverage = float(profiles[0]['layers'][-1]['properties']['end'])
            limit = min(max_depth, coverage)
            result.update(allowable_in=allowable, soil_coverage_ft=coverage)
            if start > limit:
                raise ValueError('Starting embedment exceeds maximum depth or soil coverage.')
            trial_index = 0
            depth = start
            while True:
                if cancelled():
                    result.update(status='cancelled', message='Cancelled before next analysis.')
                    break
                trial_index += 1
                trial = dict(depth_ft=depth, cases=[])
                result['trials'].append(trial)
                for case_index, case in enumerate(cases, 1):
                    responses = {}
                    for plane in ('X', 'Y'):
                        if cancelled():
                            raise InterruptedError('Cancelled between solver runs.')
                        progress(f"Footing {pier['footing']} | {depth:g} ft | case {case_index}/{len(cases)} | plane {plane}")
                        relative = Path(f'footing-{index:03d}')/f'depth-{trial_index:03d}'/f'case-{case_index:03d}-{plane}'
                        folder = output/relative
                        folder.parent.mkdir(parents=True, exist_ok=True)
                        settings = copy.deepcopy(base)
                        settings.update(footing=pier['footing'], reaction=case['reaction'], plane=plane, embedment_ft=depth)
                        settings_file = folder.parent/f'case-{case_index:03d}-{plane}-settings.json'
                        write_json(settings_file, settings)
                        summary = runner(output/'prepared-inputs.json', settings_file, folder, python)
                        displacement = float(summary['head_deflection_in'])
                        if not math.isfinite(displacement):
                            raise ValueError('Non-finite head displacement.')
                        responses[plane] = displacement
                        trial['cases'].append(dict(reaction=case['reaction'], criteria=case['criteria'], plane=plane,
                                                   head_deflection_in=displacement, results_folder=str(relative)))
                    value = math.hypot(responses['X'], responses['Y']) if mode == 'resultant' else max(abs(v) for v in responses.values())
                    for record in trial['cases'][-2:]:
                        record['checked_deflection_in'] = value if mode == 'resultant' else abs(record['head_deflection_in'])
                governing = max(trial['cases'], key=lambda r: r['checked_deflection_in'])
                trial['checked_deflection_in'] = governing['checked_deflection_in']
                trial['passed'] = trial['checked_deflection_in'] <= allowable
                result['checked_deflection_in'] = trial['checked_deflection_in']
                if trial['passed']:
                    envelopes = summarize_forces(trial['cases'], output)
                    result.update(status='deflection_pass', accepted_depth_ft=depth, governing_deflection=governing,
                                  force_envelopes=envelopes, max_shear_kip=envelopes['shear']['absolute_value'],
                                  max_moment_kip_ft=envelopes['moment']['absolute_value'], message='First passing trial depth for selected extreme cases.')
                    break
                persist()
                if depth >= limit-1e-9:
                    result.update(status='depth_limit', message='Allowable exceeded at maximum depth or end of soil coverage.')
                    break
                depth = min(start+trial_index*increment, limit)
        except InterruptedError as exc:
            result.update(status='cancelled', message=str(exc))
        except Exception as exc:
            result.update(status='error', message=str(exc))
        persist()
        progress(f"Footing {pier['footing']}: {result['status']}")
        if cancelled():
            break
    report['cancelled'] = cancelled()
    persist()
    return report
