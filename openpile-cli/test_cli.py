import copy
import json
from pathlib import Path
import tempfile
import unittest

from cli import prepare, main, FT, KSF_KPA, PCI_KNM3


class InputTests(unittest.TestCase):
    def setUp(self):
        examples = Path(__file__).parent / 'examples'
        self.doc = json.loads((examples / 'prepared.json').read_text())
        self.settings = json.loads((examples / 'settings.json').read_text())

    def test_units_depths_and_coincident_vector(self):
        plan = prepare(self.doc, self.settings)
        self.assertAlmostEqual(plan['embedment_m'], 30 * FT)
        self.assertAlmostEqual(plan['layers'][0]['parameters']['Su'], KSF_KPA)
        self.assertEqual(plan['loads'], dict(Py=1, Mx=1, Pz=-1))
        self.assertEqual(plan['layers'][0]['parameters']['eps50'], .01)
        self.assertEqual(plan['reaction']['MZ'], 0)

    def test_ambiguity_and_upstream_errors_block(self):
        self.doc['piers'][0]['reactions'] *= 2
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            prepare(self.doc, self.settings)
        self.doc['issues'] = [dict(severity='ERROR', footing='DEMO', source='group', message='Mismatch')]
        with self.assertRaisesRegex(ValueError, 'Mismatch'):
            prepare(self.doc, self.settings)

    def test_unknown_model_missing_water_and_percent_strain_block(self):
        for field, value in [('model', 'ROCK'), ('e50', 5.38)]:
            doc = copy.deepcopy(self.doc)
            doc['soil_profiles'][0]['layers'][0]['properties'][field] = value
            with self.assertRaises(ValueError):
                prepare(doc, self.settings)
        self.doc['piers'][0]['water_table_depth_ft'] = None
        with self.assertRaisesRegex(ValueError, 'water_table_depth_ft'):
            prepare(self.doc, self.settings)

    def test_sand_uses_selected_modulus_and_y_plane(self):
        self.settings['soil_models']['DEMO CLAY'] = dict(model='API_sand', kind='static', modulus='k_static_factored')
        self.doc['soil_profiles'][0]['layers'][0]['properties']['friction_angle'] = 30
        self.settings['plane'] = 'Y'
        self.doc['piers'][0]['reactions'][0].update(FY=2000, MX=-3000)
        plan = prepare(self.doc, self.settings)
        self.assertEqual(plan['loads'], dict(Py=2, Mx=-3, Pz=-1))
        self.assertAlmostEqual(plan['layers'][0]['parameters']['initial_subgrade_modulus'], 67 * PCI_KNM3)

    def test_gap_and_insufficient_coverage_block(self):
        self.doc['soil_profiles'][0]['layers'][0]['properties']['start'] = 1
        with self.assertRaisesRegex(ValueError, 'share boundaries'):
            prepare(self.doc, self.settings)
        self.doc['soil_profiles'][0]['layers'][0]['properties'].update(start=0, end=20)
        with self.assertRaisesRegex(ValueError, 'full requested embedment'):
            prepare(self.doc, self.settings)

    def test_cli_writes_validation_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'input.json').write_text(json.dumps(self.doc))
            (root / 'settings.json').write_text(json.dumps(self.settings))
            args = ['validate', '--inputs', str(root / 'input.json'), '--settings', str(root / 'settings.json'), '--output', str(root / 'result')]
            self.assertEqual(main(args), 0)
            self.assertTrue(json.loads((root / 'result/validation.json').read_text())['valid'])
            self.assertEqual(main(args), 2)


if __name__ == '__main__':
    unittest.main()
