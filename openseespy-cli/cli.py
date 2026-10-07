"""Validate prepared inputs and run a single-pier 2D OpenSeesPy analysis."""
import argparse
import csv
import copy
import json
import math
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rsa-reaction-viewer'))
from pile_analysis_inputs import prepare as prepare_common, number, choose, converted_positive, PCF_KNM3, LBF_FT_KNM
from springs import mesh_and_springs


def prepare(document, settings):
    plan = prepare_common(document, settings)
    options = dict(settings['opensees'])
    for key in ('load_steps',):
        number(options[key], key, 0, True)
        if not isinstance(options[key], int):
            raise ValueError(f'{key} must be an integer.')
    options['energy_tolerance_kn_m'] = converted_positive(
        options, 'energy_tolerance_lbf_ft', 'energy_tolerance_kn_m', LBF_FT_KNM, 'opensees')
    options['water_unit_weight_kn_m3'] = converted_positive(
        options, 'water_unit_weight_pcf', 'water_unit_weight_kn_m3', PCF_KNM3, 'opensees')
    number(options['drag_ratio'], 'drag_ratio', 0)
    if options['drag_ratio'] > 1:
        raise ValueError('drag_ratio must be between zero and one.')
    choose(options['transformation'], ('Linear', 'PDelta'), 'transformation')
    for layer in plan['layers']:
        if layer['parameters']['kind'] != 'static':
            raise ValueError('This CLI supports monotonic static loading only; cyclic curves/history are not implemented.')
        if -layer['bottom'] > -plan['water_elevation_m'] and layer['weight'] <= options['water_unit_weight_kn_m3']:
            raise ValueError('Submerged soil unit weight must exceed water unit weight.')
    plan['opensees'] = options
    plan['solver'] = 'OpenSeesPy / elasticBeamColumn / PySimple1'
    plan['warnings'] += ['PySimple1 is a backbone approximation; results need not equal OpenPile.',
                         'Elastic gross section; no cracking, reinforcement, self-weight loading or residual-deflection check.']
    plan['node_depths_m'], plan['springs'] = mesh_and_springs(plan)
    return plan


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


# Solver uses kN and m; exported results use kip, ft, in, and psi.
KN_PER_KIP = 4.4482216152605
M_PER_FT = 0.3048
M_PER_IN = 0.0254
KPA_PER_PSI = 6.894757293168


def imperial_spring(spring):
    conversions = {
        'sample_depth_m': ('sample_depth_ft', M_PER_FT),
        'tributary_length_m': ('tributary_length_ft', M_PER_FT),
        'effective_stress_kpa': ('effective_stress_psi', KPA_PER_PSI),
        'pult_kn': ('pult_kip', KN_PER_KIP),
        'y50_m': ('y50_in', M_PER_IN),
    }
    return {conversions[k][0] if k in conversions else k:
            v / conversions[k][1] if k in conversions else v
            for k, v in spring.items()}


def imperial_plan(plan):
    result = copy.deepcopy(plan)
    for key in ('diameter', 'embedment', 'water_elevation', 'mesh'):
        result[key + '_ft'] = result.pop(key + '_m') / M_PER_FT
    result['node_depths_ft'] = [v / M_PER_FT for v in result.pop('node_depths_m')]
    result['springs'] = [imperial_spring(s) for s in result['springs']]
    material = result['material']
    material['E_psi'] = material.pop('E_kpa') / KPA_PER_PSI
    material['unit_weight_pcf'] = material.pop('unit_weight_kn_m3') / PCF_KNM3
    options = result['opensees']
    options['water_unit_weight_pcf'] = options.pop('water_unit_weight_kn_m3') / PCF_KNM3
    options['energy_tolerance_lbf_ft'] = options.pop('energy_tolerance_kn_m') / LBF_FT_KNM
    for layer in result['layers']:
        layer['top_ft'] = layer.pop('top') / M_PER_FT
        layer['bottom_ft'] = layer.pop('bottom') / M_PER_FT
        layer['unit_weight_pcf'] = layer.pop('weight') / PCF_KNM3
        params = layer['parameters']
        if 'Su' in params:
            params['Su_psi'] = params.pop('Su') / KPA_PER_PSI
        if 'initial_subgrade_modulus' in params:
            params['initial_subgrade_modulus_pci'] = params.pop('initial_subgrade_modulus') / (KN_PER_KIP / 1000 / M_PER_IN**3)
    result['loads'] = {'lateral_kip': result['loads']['Py'] / KN_PER_KIP,
                       'axial_kip': result['loads']['Pz'] / KN_PER_KIP,
                       'moment_kip_ft': result['loads']['Mx'] / (KN_PER_KIP * M_PER_FT)}
    # Original RSA vectors are exported in imperial units as well.
    for key in ('FX', 'FY', 'FZ', 'MX', 'MY', 'MZ'):
        factor = 1000 * KN_PER_KIP * (M_PER_FT if key.startswith('M') else 1)
        result['reaction'][key + ('_kip_ft' if key.startswith('M') else '_kip')] = result['reaction'].pop(key) / factor
    result['output_units'] = dict(length='ft', displacement='in', force='kip', moment='kip-ft', stress='psi', rotation='rad')
    return result


def solve(plan, output):
    try:
        import openseespy.opensees as ops
        from importlib.metadata import version
    except ImportError as exc:
        raise RuntimeError('Install openseespy-cli/requirements.txt in the CLI environment.') from exc
    ops.wipe()
    try:
        ops.logFile(str((output / 'solver.log').resolve()), '-noEcho')
        ops.model('basic', '-ndm', 2, '-ndf', 3)
        depths = plan['node_depths_m']
        n = len(depths)
        for node, depth in enumerate(depths, 1):
            ops.node(node, 0.0, -depth)
        ops.fix(n, 0, 1, 0)
        ops.geomTransf(plan['opensees']['transformation'], 1)
        diameter = plan['diameter_m']
        area, inertia = math.pi * diameter**2 / 4, math.pi * diameter**4 / 64
        for tag in range(1, n):
            ops.element('elasticBeamColumn', tag, tag, tag + 1, area, plan['material']['E_kpa'], inertia, 1)
        for index, spring in enumerate(plan['springs'], 1):
            fixed = n + index
            ops.node(fixed, 0.0, -depths[spring['node'] - 1])
            ops.fix(fixed, 1, 1, 1)
            ops.uniaxialMaterial('PySimple1', index, spring['soil_type'], spring['pult_kn'], spring['y50_m'], spring['Cd'], 0.0)
            ops.element('zeroLength', n + index, fixed, spring['node'], '-mat', index, '-dir', 1)
        ops.timeSeries('Linear', 1)
        ops.pattern('Plain', 1, 1)
        # OpenPile (y,z,Mx) -> OpenSees global (x,y,Mz), preserving handedness.
        loads = plan['loads']
        ops.load(1, loads['Py'], loads['Pz'], loads['Mx'])
        ops.constraints('Plain')
        ops.numberer('RCM')
        ops.system('BandGeneral')
        ops.test('EnergyIncr', plan['opensees']['energy_tolerance_kn_m'], plan['max_iterations'], 0)
        ops.algorithm('Newton')
        steps = plan['opensees']['load_steps']
        ops.integrator('LoadControl', 1.0 / steps)
        ops.analysis('Static')
        history = []
        for step in range(1, steps + 1):
            code = ops.analyze(1)
            history.append(dict(step=step, return_code=code, load_factor=ops.getTime(), iterations=ops.testIter()))
            if code != 0:
                write_json(output / 'convergence.json', history)
                raise RuntimeError(f'OpenSees failed at load step {step}/{steps}, return code {code}.')
        if not math.isclose(ops.getTime(), 1.0, rel_tol=0, abs_tol=1e-8):
            raise RuntimeError('Full target load was not reached.')
        ops.reactions()
        displacements = [dict(node=node, **{'Elevation [ft]': -depth / M_PER_FT, 'Deflection [in]': ops.nodeDisp(node, 1) / M_PER_IN,
                           'Settlement [in]': ops.nodeDisp(node, 2) / M_PER_IN, 'Rotation [rad]': ops.nodeDisp(node, 3)})
                         for node, depth in enumerate(depths, 1)]
        forces = []
        for tag in range(1, n):
            values = ops.eleResponse(tag, 'localForce')
            for end, node, offset in (('i', tag, 0), ('j', tag + 1, 3)):
                forces.append(dict(element=tag, end=end, node=node, **{'Elevation [ft]': -depths[node-1] / M_PER_FT,
                                   'N_local [kip]': values[offset] / KN_PER_KIP, 'V_local [kip]': values[offset+1] / KN_PER_KIP,
                                   'M_local [kip-ft]': values[offset+2] / (KN_PER_KIP * M_PER_FT)}))
        supports = [n] + list(range(n + 1, n + len(plan['springs']) + 1))
        reactions = [dict(node=node, **{'Fx [kip]': ops.nodeReaction(node, 1) / KN_PER_KIP,
                          'Fy [kip]': ops.nodeReaction(node, 2) / KN_PER_KIP, 'Mz [kip-ft]': ops.nodeReaction(node, 3) / (KN_PER_KIP * M_PER_FT)}) for node in supports]
        for row in displacements + forces + reactions:
            if any(not math.isfinite(v) for v in row.values() if isinstance(v, (int, float))):
                raise RuntimeError('Solver returned a non-finite result.')
        for name, rows in [('displacements', displacements), ('forces', forces), ('reactions', reactions)]:
            write_csv(output / f'{name}.csv', rows)
        write_json(output / 'convergence.json', history)
        summary = dict(status='converged', openseespy_version=version('openseespy'), engine_version=ops.version(),
                       load_factor=ops.getTime(), steps=steps, design_pass=None, warnings=plan['warnings'],
                       output_units=dict(length='ft', displacement='in', force='kip', moment='kip-ft', rotation='rad'),
                       head_deflection_in=displacements[0]['Deflection [in]'],
                       max_abs_deflection_in=max(abs(r['Deflection [in]']) for r in displacements),
                       max_abs_shear_kip=max(abs(r['V_local [kip]']) for r in forces),
                       max_abs_moment_kip_ft=max(abs(r['M_local [kip-ft]']) for r in forces))
        write_json(output / 'summary.json', summary)
        return summary
    finally:
        ops.wipe()
        # wipe() leaves OpenSees' global log handle open on Windows.
        ops.logFile(os.devnull)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['validate', 'run'])
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--settings', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New output directory')
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.inputs.read_text(encoding='utf-8-sig'))
        settings = json.loads(args.settings.read_text(encoding='utf-8-sig'))
        args.output.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    try:
        plan = prepare(document, settings)
        write_json(args.output / 'analysis-inputs.json', imperial_plan(plan))
        write_csv(args.output / 'springs.csv', [imperial_spring(s) for s in plan['springs']])
        write_json(args.output / 'validation.json', dict(valid=True, warnings=plan['warnings']))
    except (ValueError, KeyError, TypeError, AttributeError, StopIteration, OverflowError) as exc:
        write_json(args.output / 'validation.json', dict(valid=False, error=str(exc)))
        print(f'INPUT ERROR: {exc}', file=sys.stderr)
        return 2
    if args.command == 'validate':
        print(f'Inputs validated: {args.output}')
        return 0
    try:
        solve(plan, args.output)
    except Exception as exc:
        write_json(args.output / 'summary.json', dict(status='failed', error=str(exc), design_pass=None))
        print(f'SOLVER ERROR: {exc}', file=sys.stderr)
        return 3
    print(f'Analysis converged: {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
