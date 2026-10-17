"""Fixed-depth load search against the combined head-displacement limit."""
import copy
import math
from pathlib import Path
from model import ROOT, SELECTOR, read_json, write_json, run_cli, summarize_forces


def capacity_search(inputs, template, output, depth_source='minimum', loading='case',
                    max_factor=1024, tolerance=.01, python=None,
                    progress=lambda message: None, cancelled=lambda: False, runner=run_cli):
    if loading not in ('case', 'pure') or depth_source not in ('minimum', 'settings'):
        raise ValueError('Unknown loading path or depth source.')
    if not math.isfinite(max_factor) or max_factor <= 0 or not 0 < tolerance < 1:
        raise ValueError('Maximum multiplier must be positive; relative tolerance must be between 0 and 1.')
    document = read_json(inputs)
    base = copy.deepcopy(template)
    matches = [p for p in document['piers'] if p['footing'] == base['footing']]
    if len(matches) != 1:
        raise ValueError('Choose one footing in the settings editor.')
    pier = matches[0]
    rows = [r for r in pier['reactions'] if all(r[k] == base['reaction'][k] for k in SELECTOR)]
    if len(rows) != 1:
        raise ValueError('Choose a unique coincident reaction in the settings editor.')
    source = rows[0]
    depth = float(pier['minimum_embedment_ft'] if depth_source == 'minimum' else base['embedment_ft'])
    allowable = float(pier['allowable_deflection_in'])
    if not math.isfinite(depth) or depth <= 0 or not math.isfinite(allowable) or allowable <= 0:
        raise ValueError('Depth and allowable must be positive finite numbers.')
    if loading == 'case' and not any(source[k] for k in ('FX','FY','MX','MY')):
        raise ValueError('The selected case has no lateral load or bending moment to scale.')
    python = python or ROOT/'openseespy-cli/.venv/Scripts/python.exe'
    if not Path(python).is_file():
        raise ValueError('Select a Python interpreter with OpenSeesPy installed.')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/'original-inputs.json', document)
    write_json(output/'template-settings.json', base)
    report = dict(footing=pier['footing'], depth_ft=depth, allowable_in=allowable,
                  check='sqrt(delta_X^2 + delta_Y^2)', loading=loading, searches=[],
                  limitations=['Displacement-limited load along the chosen path, not structural shear/moment strength or complete design acceptance.',
                               'Independent 2D planes; loaded elastic displacement, not residual displacement.',
                               'Bracket search assumes a continuous monotonic displacement response along each path; no global maximum is established.'])
    paths = ['case'] if loading == 'case' else ['shear-X','shear-Y','moment-X','moment-Y']
    for path in paths:
        search = dict(path=path, status='running', trials=[], lower_passing_factor=None, upper_failing_factor=None)
        report['searches'].append(search)
        def persist():
            write_json(output/'capacity-summary.json', report)
        def evaluate(factor):
            if cancelled():
                raise InterruptedError('Cancelled between solver runs.')
            trial_index = len(search['trials'])+1
            reaction = copy.deepcopy(source)
            if path == 'case':
                for key in ('FX','FY','FZ','MX','MY','MZ'):
                    reaction[key] = source[key]*factor
            else:
                for key in ('FX','FY','MX','MY','MZ'):
                    reaction[key] = 0.
                component = {'shear-X':'FX','shear-Y':'FY','moment-X':'MY','moment-Y':'MX'}[path]
                reaction[component] = factor * (4448.2216152605 if path.startswith('shear') else 1355.8179483314)
            modified = copy.deepcopy(document)
            target = next(p for p in modified['piers'] if p['footing']==pier['footing'])
            for row in target['reactions']:
                if all(row[k]==base['reaction'][k] for k in SELECTOR):
                    row.update(reaction)
            trial = dict(factor=factor, cases=[])
            search['trials'].append(trial)
            relative = Path(path)/f'trial-{trial_index:03d}'
            root = output/relative
            root.mkdir(parents=True)
            write_json(root/'inputs.json',modified)
            displacements=[]
            for plane in ('X','Y'):
                if cancelled():
                    raise InterruptedError('Cancelled between solver runs.')
                settings=copy.deepcopy(base)
                settings.update(plane=plane,embedment_ft=depth)
                settings_file=root/f'{plane}-settings.json'
                write_json(settings_file,settings)
                progress(f'{path} | factor {factor:.6g} | {depth:g} ft | plane {plane}')
                summary=runner(root/'inputs.json',settings_file,root/plane,python)
                displacement=float(summary['head_deflection_in'])
                if not math.isfinite(displacement):
                    raise ValueError('Non-finite displacement.')
                displacements.append(displacement)
                trial['cases'].append(dict(plane=plane,reaction=base['reaction'],head_deflection_in=displacement,results_folder=str(relative/plane)))
            trial.update(deflection_in=math.hypot(*displacements), applied_shear_kip=math.hypot(reaction['FX'],reaction['FY'])/4448.2216152605,
                         applied_moment_kip_ft=math.hypot(reaction['MX'],reaction['MY'])/1355.8179483314)
            trial['passed']=trial['deflection_in']<=allowable
            persist()
            return trial
        try:
            lower=evaluate(0.)
            if not lower['passed']:
                search.update(status='baseline_exceeds_allowable', message='Zero lateral scaling exceeds the allowable; no passing lower bound.')
                persist()
                continue
            upper=None
            factor=min(1.,max_factor)
            while True:
                trial=evaluate(factor)
                if not trial['passed']:
                    upper=trial
                    break
                lower=trial
                if factor >= max_factor:
                    break
                factor=min(factor*2,max_factor)
            if upper is None:
                search.update(status='load_limit',message='Maximum search multiplier passed; limit has not been found.')
            else:
                for _ in range(80):
                    if upper['factor']-lower['factor'] <= tolerance*max(upper['factor'],1e-12):
                        break
                    trial=evaluate((lower['factor']+upper['factor'])/2)
                    if trial['passed']:
                        lower=trial
                    else:
                        upper=trial
                search.update(status='bracketed',upper_failing_factor=upper['factor'],upper_deflection_in=upper['deflection_in'])
            search.update(lower_passing_factor=lower['factor'], passing_deflection_in=lower['deflection_in'],
                          applied_shear_kip=lower['applied_shear_kip'],applied_moment_kip_ft=lower['applied_moment_kip_ft'],
                          passing_results=lower['cases'],internal_force_envelopes=summarize_forces(lower['cases'],output))
        except InterruptedError as exc:
            search.update(status='cancelled',message=str(exc))
        except Exception as exc:
            search.update(status='unresolved',message=str(exc))
        persist()
        if cancelled():
            break
    return report
