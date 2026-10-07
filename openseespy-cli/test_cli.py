import csv
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cli import prepare, solve, main, imperial_plan, KN_PER_KIP
from springs import effective_stress, backbone


class InputTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).parent / 'examples'
        self.document = json.loads((root / 'prepared.json').read_text())
        self.settings = json.loads((root / 'settings.json').read_text())

    def test_tributaries_cover_pile_and_clay_parameters(self):
        plan = prepare(self.document, self.settings)
        self.assertAlmostEqual(sum(s['tributary_length_m'] for s in plan['springs']), plan['embedment_m'])
        self.assertTrue(all(s['sample_depth_m'] > 0 for s in plan['springs']))
        layer = plan['layers'][0]
        soil_type, p, y = backbone(layer, 1, 18, 1)
        su = layer['parameters']['Su']
        self.assertEqual(soil_type, 1)
        self.assertAlmostEqual(p, min(9*su, 3*su+18+.5*su))
        self.assertAlmostEqual(y, .025)
        water = -plan['water_elevation_m']
        self.assertAlmostEqual(effective_stress(plan, water + 1), layer['weight'] * (water+1) - 9.81)

    def test_imperial_export_preserves_solver_plan(self):
        import copy
        plan = prepare(self.document, self.settings)
        original = copy.deepcopy(plan)
        exported = imperial_plan(plan)
        self.assertEqual(plan, original)
        self.assertAlmostEqual(exported['embedment_ft'], self.settings['embedment_ft'])
        self.assertAlmostEqual(exported['springs'][0]['pult_kip'] * KN_PER_KIP, plan['springs'][0]['pult_kn'])
        self.assertAlmostEqual(exported['springs'][0]['y50_in'] * .0254, plan['springs'][0]['y50_m'])
        self.settings['soil_models']['DEMO CLAY'] = dict(model='API_sand', kind='static', modulus='k_static')
        self.document['soil_profiles'][0]['layers'][0]['properties']['friction_angle'] = 35
        exported = imperial_plan(prepare(self.document, self.settings))
        self.assertAlmostEqual(exported['layers'][0]['parameters']['initial_subgrade_modulus_pci'],
                               self.document['soil_profiles'][0]['layers'][0]['properties']['k_static'])

    def test_modulus_psi_conversion_and_legacy_kpa(self):
        material = self.settings['material']
        material['E_psi'] = 1_000_000
        plan = prepare(self.document, self.settings)
        self.assertAlmostEqual(plan['material']['E_kpa'], 6_894_757.293168, places=5)
        self.assertNotIn('E_kpa', material)
        self.assertEqual(plan['settings']['material']['E_psi'], 1_000_000)
        del material['E_psi']
        material['E_kpa'] = 30_000_000
        self.assertEqual(prepare(self.document, self.settings)['material']['E_kpa'], 30_000_000)

    def test_invalid_or_ambiguous_modulus_rejected(self):
        material = self.settings['material']
        for value in (0, -1, True, '4000000', float('nan'), float('inf')):
            with self.subTest(value=value):
                material['E_psi'] = value
                with self.assertRaises(ValueError):
                    prepare(self.document, self.settings)
        material.update(E_psi=4_000_000, E_kpa=30_000_000)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            prepare(self.document, self.settings)
        del material['E_psi']
        del material['E_kpa']
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            prepare(self.document, self.settings)

    def test_layer_boundary_keeps_separate_soils(self):
        import copy
        layers = self.document['soil_profiles'][0]['layers']
        lower = copy.deepcopy(layers[0])
        layers[0]['properties']['end'] = 10
        lower['properties']['start'] = 10
        layers.append(lower)
        plan = prepare(self.document, self.settings)
        node = next(i+1 for i, z in enumerate(plan['node_depths_m']) if math.isclose(z, 3.048))
        self.assertEqual({s['layer_index'] for s in plan['springs'] if s['node'] == node}, {0, 1})

    def test_cyclic_and_bad_settings_rejected(self):
        self.settings['soil_models']['DEMO CLAY']['kind'] = 'cyclic'
        with self.assertRaisesRegex(ValueError, 'monotonic'):
            prepare(self.document, self.settings)
        self.settings['soil_models']['DEMO CLAY']['kind'] = 'static'
        self.settings['opensees']['load_steps'] = 0
        with self.assertRaises(ValueError):
            prepare(self.document, self.settings)

    def test_cli_validation_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, value in [('prepared', self.document), ('settings', self.settings)]:
                (root / f'{name}.json').write_text(json.dumps(value))
            args = ['validate', '--inputs', str(root/'prepared.json'), '--settings', str(root/'settings.json'), '--output', str(root/'result')]
            self.assertEqual(main(args), 0)
            self.assertTrue((root/'result/springs.csv').exists())
            self.assertEqual(main(args), 2)


@unittest.skipUnless(importlib.util.find_spec('openseespy'), 'OpenSeesPy not installed')
class SolverTests(unittest.TestCase):
    setUp = InputTests.setUp

    def test_clay_sand_and_global_equilibrium(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('clay', 'sand'):
                if name == 'sand':
                    self.settings['soil_models']['DEMO CLAY'] = dict(model='API_sand', kind='static', modulus='k_static')
                    self.document['soil_profiles'][0]['layers'][0]['properties']['friction_angle'] = 35
                plan = prepare(self.document, self.settings)
                output = Path(folder)/name
                output.mkdir()
                summary = solve(plan, output)
                self.assertEqual(summary['status'], 'converged')
                self.assertGreater(abs(summary['head_deflection_in']), 0)
                self.assertIsNone(summary['design_pass'])
                with (output/'reactions.csv').open() as stream:
                    reactions = list(csv.DictReader(stream))
                self.assertAlmostEqual(sum(float(r['Fx [kip]']) for r in reactions), -plan['loads']['Py'] / KN_PER_KIP, places=5)
                self.assertAlmostEqual(sum(float(r['Fy [kip]']) for r in reactions), -plan['loads']['Pz'] / KN_PER_KIP, places=5)

    def test_failed_step_does_not_export_success(self):
        import openseespy.opensees as ops
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(ops, 'analyze', return_value=-3):
                with self.assertRaisesRegex(RuntimeError, 'failed at load step'):
                    solve(prepare(self.document, self.settings), Path(folder))
            self.assertFalse((Path(folder)/'summary.json').exists())
            self.assertFalse((Path(folder)/'forces.csv').exists())

    def test_cantilever_matches_closed_form(self):
        import openseespy.opensees as ops
        ops.wipe()
        try:
            ops.model('basic', '-ndm', 2, '-ndf', 3)
            ops.node(1, 0, 0)
            ops.node(2, 0, -10)
            ops.fix(2, 1, 1, 1)
            ops.geomTransf('Linear', 1)
            E, A, I = 30e6, math.pi/4, math.pi/64
            ops.element('elasticBeamColumn', 1, 1, 2, A, E, I, 1)
            ops.timeSeries('Linear', 1)
            ops.pattern('Plain', 1, 1)
            ops.load(1, 1, 0, 0)
            ops.constraints('Plain')
            ops.numberer('RCM')
            ops.system('BandGeneral')
            ops.test('NormDispIncr', 1e-12, 10)
            ops.algorithm('Linear')
            ops.integrator('LoadControl', 1)
            ops.analysis('Static')
            self.assertEqual(ops.analyze(1), 0)
            self.assertAlmostEqual(ops.nodeDisp(1, 1)/(10**3/(3*E*I)), 1, places=8)
        finally:
            ops.wipe()


if __name__ == '__main__':
    unittest.main()
