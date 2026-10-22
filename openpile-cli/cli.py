"""Validate prepared pier inputs and run one explicit 2D OpenPile analysis."""
import argparse
from contextlib import redirect_stdout
import io
import json
import math
import os
import re
from pathlib import Path
import sys

# Reuse the project's typed soil schema without importing the desktop application.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rsa-reaction-viewer'))

from pile_analysis_inputs import prepare as prepare_common, number, choose, FT, PSF_KPA, PCI_KNM3


def prepare(document, settings):
    plan = prepare_common(document, settings)
    plan['projection_height_m'] = number(settings.get('projection_height_ft', 1), 'projection_height_ft', 0) * FT
    return plan


def solve(plan, output):
    os.environ.setdefault('MPLBACKEND', 'Agg')
    os.environ.setdefault('MPLCONFIGDIR', str((output / 'matplotlib-cache').resolve()))
    try:
        from openpile.construct import Pile, CircularPileSection, Layer, SoilProfile, Model
        from openpile.materials import PileMaterial
        from openpile.soilmodels import API_clay, API_sand
        from openpile.winkler import winkler
        from importlib.metadata import version
    except ImportError as exc:
        raise RuntimeError('Install dependencies with: python -m pip install -r openpile-cli/requirements.txt') from exc
    mat = plan['material']
    pile = Pile(name=plan['footing'], material=PileMaterial(name='User material',
                E=mat['E_kpa'], nu=mat['poisson_ratio'], uw=mat['unit_weight_kn_m3']),
                sections=[CircularPileSection(top=plan['projection_height_m'], bottom=-plan['embedment_m'], diameter=plan['diameter_m'])])
    models = {'API_clay': API_clay, 'API_sand': API_sand}
    layers = [Layer(name=l['name'], top=l['top'], bottom=l['bottom'], weight=l['weight'],
                    lateral_model=models[l['model']](**l['parameters'])) for l in plan['layers']]
    soil = SoilProfile(name=plan['footing'], top_elevation=0, water_line=plan['water_elevation_m'], layers=layers)
    model = Model(name=plan['footing'], pile=pile, soil=soil, coarseness=plan['mesh_m'],
                  element_type='EulerBernoulli', distributed_moment=False, distributed_axial=False,
                  base_shear=False, base_moment=False, base_axial=False)
    model.set_support(elevation=-plan['embedment_m'], Tz=True)
    model.set_pointload(elevation=plan['projection_height_m'], **plan['loads'])
    solver_log = io.StringIO()
    try:
        with redirect_stdout(solver_log):
            result = winkler(model, max_iter=plan['max_iterations'])
    finally:
        (output / 'solver.log').write_text(solver_log.getvalue(), encoding='utf-8')
    # 1.0.3 labels the final iteration as converged even on iteration exhaustion.
    # Its residual/tolerance summary is rounded, so require its actual success branch.
    success = re.search(r'^Converged at iteration no\. (\d+)\s*$', solver_log.getvalue(), re.MULTILINE)
    if not success or int(success[1]) > plan['max_iterations']:
        raise RuntimeError('Solver did not converge within the iteration limit; see solver.log.')
    details = result.details()
    frames = dict(displacements=result.displacements, forces=result.forces, reactions=result.reactions)
    for name, frame in frames.items():
        if frame is None or (frame.empty and name != 'reactions'):
            raise RuntimeError(f'Solver returned no {name}.')
        if not all(math.isfinite(float(v)) for v in frame.select_dtypes(include='number').to_numpy().flat):
            raise RuntimeError(f'Solver returned non-finite {name}.')
    if not details.get('converged @ iter no.'):
        raise RuntimeError(f'Solver did not converge: {details}')
    for name, frame in frames.items():
        frame.to_csv(output / f'{name}.csv', index=False)
    summary = dict(status='converged', openpile_version=version('openpile'),
                   details=details, design_pass=None, warnings=plan['warnings'],
                   head_deflection_m=float(result.displacements.iloc[0]['Deflection [m]']),
                   head_deflection_in=float(result.displacements.iloc[0]['Deflection [m]']) / 0.0254,
                   max_abs_deflection_m=float(result.displacements['Deflection [m]'].abs().max()),
                   max_abs_shear_kn=float(result.forces['V [kN]'].abs().max()),
                   max_abs_moment_kn_m=float(result.forces['M [kNm]'].abs().max()))
    write_json(output / 'summary.json', summary)
    return summary


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['validate', 'run'])
    parser.add_argument('--inputs', required=True, type=Path, help='Prepared pier JSON from pier_designs.py')
    parser.add_argument('--settings', required=True, type=Path, help='Single-pier analysis settings JSON')
    parser.add_argument('--output', required=True, type=Path, help='New output directory (must not exist)')
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
        write_json(args.output / 'analysis-inputs.json', plan)
        write_json(args.output / 'validation.json', dict(valid=True, warnings=plan['warnings']))
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        write_json(args.output / 'validation.json', dict(valid=False, error=str(exc)))
        print(f'INPUT ERROR: {exc}', file=sys.stderr)
        return 2
    if args.command == 'validate':
        print(f'Inputs validated. Review {args.output / "analysis-inputs.json"}')
        return 0
    try:
        solve(plan, args.output)
    except Exception as exc:
        write_json(args.output / 'summary.json', dict(status='failed', error=str(exc), design_pass=None))
        print(f'SOLVER ERROR: {exc}', file=sys.stderr)
        return 3
    print(f'Analysis converged. Results: {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
