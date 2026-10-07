"""Run with the app's virtual environment to exercise the real OpenPile solver."""
import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile
import unittest

from cli import prepare, solve


@unittest.skipUnless(importlib.util.find_spec('openpile'), 'OpenPile not installed in this interpreter')
class SolverTests(unittest.TestCase):
    def setUp(self):
        examples = Path(__file__).parent / 'examples'
        self.doc = json.loads((examples / 'prepared.json').read_text())
        self.settings = json.loads((examples / 'settings.json').read_text())

    def test_clay_and_sand_results_and_iteration_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for model in ('clay', 'sand'):
                if model == 'sand':
                    self.doc['soil_profiles'][0]['layers'][0]['properties']['friction_angle'] = 35
                    self.settings['soil_models']['DEMO CLAY'] = dict(model='API_sand', kind='static', modulus='k_static')
                output = root / model
                output.mkdir()
                summary = solve(prepare(self.doc, self.settings), output)
                self.assertEqual(summary['status'], 'converged')
                self.assertIsNone(summary['design_pass'])
                self.assertGreater(abs(summary['head_deflection_m']), 0)
                for name in ('forces.csv', 'reactions.csv', 'displacements.csv', 'solver.log'):
                    self.assertTrue((output / name).is_file())
            self.settings['max_iterations'] = 1
            output = root / 'nonconverged'
            output.mkdir()
            with self.assertRaisesRegex(RuntimeError, 'iteration limit'):
                solve(prepare(self.doc, self.settings), output)
            self.assertFalse((output / 'forces.csv').exists())

    def test_elastic_cantilever_against_closed_form(self):
        os.environ.setdefault('MPLBACKEND', 'Agg')
        from openpile.construct import Pile, CircularPileSection, Model
        from openpile.materials import PileMaterial
        with tempfile.TemporaryDirectory() as folder:
            os.environ['MPLCONFIGDIR'] = folder
            E, diameter, length, force = 30e6, 1, 10, 1
            pile = Pile(name='benchmark', material=PileMaterial(name='test', E=E, nu=.2, uw=24),
                        sections=[CircularPileSection(top=0, bottom=-length, diameter=diameter)])
            model = Model(name='cantilever', pile=pile, coarseness=.5, element_type='EulerBernoulli')
            model.set_support(elevation=-length, Tz=True, Ty=True, Rx=True)
            model.set_pointload(elevation=0, Py=force)
            response = model.solve()
            expected = force * length**3 / (3 * E * math.pi * diameter**4 / 64)
            actual = abs(float(response.displacements.iloc[0]['Deflection [m]']))
            self.assertAlmostEqual(actual / expected, 1, places=6)


if __name__ == '__main__':
    unittest.main()
