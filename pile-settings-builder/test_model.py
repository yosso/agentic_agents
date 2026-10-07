import copy
import json
from pathlib import Path
import tempfile
import unittest

from model import ROOT, build_settings, check_prepared, concrete_modulus, defaults, read_source, save_settings, soil_labels, soil_layer_details, suggested_soil_model


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.document, self.piers, self.prepared = read_source(ROOT / 'openseespy-cli/examples/prepared.json')
        example = defaults()
        self.fields = {k: str(v) for k, v in {**example, **example['material'], **example['opensees'], **example['load_signs']}.items()}
        self.soils = {'DEMO CLAY': dict(model='API_clay', cohesion='cohesion_ultimate', strain='e50', J='0.5', modulus='k_static')}

    def build(self):
        return build_settings(self.piers[0], self.piers[0]['reactions'][0], self.fields, self.soils)

    def test_concrete_modulus_is_saved_and_validated(self):
        self.assertEqual(concrete_modulus('10000'), 5_700_000)
        modulus = concrete_modulus('4000')
        self.assertAlmostEqual(modulus, 3_604_996.5325919525)
        self.fields['E_psi'] = str(modulus)
        settings = self.build()
        self.assertEqual(settings['material']['E_psi'], modulus)
        check_prepared(self.document, settings)
        for value in ('', 'abc', '0', '-4000', 'nan', 'inf'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                concrete_modulus(value)

    def test_generated_settings_pass_real_cli_validation(self):
        self.assertTrue(self.prepared)
        self.assertEqual(soil_labels(self.document, self.piers[0]), ['DEMO CLAY'])
        settings = self.build()
        self.assertEqual(settings, defaults())
        original = copy.deepcopy(self.document)
        plan = check_prepared(self.document, settings)
        self.assertAlmostEqual(plan['material']['E_kpa'], 30_000_000)
        self.assertEqual(original, self.document)
        self.assertNotIn('E_kpa', settings['material'])

    def test_sand_settings_pass_cli_and_omit_clay_fields(self):
        self.document['soil_profiles'][0]['layers'][0]['properties']['friction_angle'] = 35
        self.soils['DEMO CLAY']['model'] = 'API_sand'
        settings = self.build()
        self.assertEqual(settings['soil_models']['DEMO CLAY'], dict(model='API_sand', kind='static', modulus='k_static'))
        check_prepared(self.document, settings)

    def test_soil_label_suggestions_are_conservative(self):
        self.assertEqual(suggested_soil_model('SOFT CLAY'), 'API_clay')
        self.assertEqual(suggested_soil_model('SAND/GRAVEL'), 'API_sand')
        self.assertEqual(suggested_soil_model('SANDY CLAY'), '')
        self.assertEqual(suggested_soil_model('PORUS LIMESTONE'), '')

    def test_layer_details_display_missing_values(self):
        layer = self.document['soil_profiles'][0]['layers'][0]
        layer['properties']['start'] = None
        layer['properties']['cohesion_ultimate'] = None
        details = soil_layer_details(self.document, self.piers[0], 'DEMO CLAY')
        self.assertIn('Missing-40 ft', details[0])
        self.assertIn('Su ultimate/factored Missing/', details[0])

    def test_unmapped_soil_can_be_saved_as_validation_draft(self):
        self.soils['PORUS LIMESTONE'] = dict(model='', cohesion='cohesion_ultimate',
                                             strain='e50', J='0.5', modulus='k_static')
        settings = self.build()
        self.assertNotIn('PORUS LIMESTONE', settings['soil_models'])

    def test_customary_units_convert_without_changing_saved_settings(self):
        self.fields.update(unit_weight_pcf='150', water_unit_weight_pcf='62.4', energy_tolerance_lbf_ft='0.001')
        settings = self.build()
        original = copy.deepcopy(settings)
        plan = check_prepared(self.document, settings)
        self.assertAlmostEqual(plan['material']['unit_weight_kn_m3'], 23.5631195769)
        self.assertAlmostEqual(plan['opensees']['water_unit_weight_kn_m3'], 9.8022577440)
        self.assertAlmostEqual(plan['opensees']['energy_tolerance_kn_m'], 0.0000013558179483314, places=16)
        self.assertEqual(settings, original)
        for group, customary, metric in [
            ('material', 'unit_weight_pcf', 'unit_weight_kn_m3'),
            ('opensees', 'water_unit_weight_pcf', 'water_unit_weight_kn_m3'),
            ('opensees', 'energy_tolerance_lbf_ft', 'energy_tolerance_kn_m'),
        ]:
            with self.subTest(field=customary):
                legacy = copy.deepcopy(settings)
                del legacy[group][customary]
                legacy[group][metric] = plan[group][metric]
                self.assertEqual(check_prepared(self.document, legacy)[group][metric], plan[group][metric])
                legacy[group][customary] = settings[group][customary]
                with self.assertRaisesRegex(ValueError, 'exactly one'):
                    check_prepared(self.document, legacy)
                for value in (0, -1, float('inf')):
                    invalid = copy.deepcopy(settings)
                    invalid[group][customary] = value
                    with self.assertRaises(ValueError):
                        check_prepared(self.document, invalid)

    def test_converted_defaults_preserve_original_physical_values(self):
        plan = check_prepared(self.document, self.build())
        self.assertAlmostEqual(plan['material']['unit_weight_kn_m3'], 24)
        self.assertAlmostEqual(plan['opensees']['water_unit_weight_kn_m3'], 9.81)
        self.assertAlmostEqual(plan['opensees']['energy_tolerance_kn_m'], 1e-10, places=20)

    def test_invalid_values_and_unselected_soil(self):
        for key, value in [('E_psi', 'nan'), ('load_steps', '1.5'), ('poisson_ratio', '0.5'), ('drag_ratio', '2'), ('axial', '0')]:
            with self.subTest(key=key):
                old = self.fields[key]
                self.fields[key] = value
                with self.assertRaises(ValueError):
                    self.build()
                self.fields[key] = old
        self.soils['DEMO CLAY']['model'] = ''
        self.assertNotIn('DEMO CLAY', self.build()['soil_models'])

    def test_ambiguous_reaction_is_rejected(self):
        self.piers[0]['reactions'] *= 2
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.build()

    def test_missing_water_is_preserved_and_blocks_validation(self):
        self.document['piers'][0]['water_table_depth_ft'] = None
        with self.assertRaisesRegex(ValueError, 'water_table_depth_ft'):
            check_prepared(self.document, self.build())
        self.assertIsNone(self.document['piers'][0]['water_table_depth_ft'])

    def test_raw_results_group_by_footing_and_preserve_selector(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'results.json'
            row = self.piers[0]['reactions'][0]
            source.write_text(json.dumps(dict(error=None, reactions=[row, dict(row, mark='SECOND', node=2)])), encoding='utf-8-sig')
            document, piers, prepared = read_source(source)
            self.assertFalse(prepared)
            self.assertEqual([p['footing'] for p in piers], ['DEMO', 'SECOND'])
            result = build_settings(piers[1], piers[1]['reactions'][0], self.fields, self.soils)
            self.assertEqual(result['reaction']['node'], 2)
            self.assertEqual(result['reaction']['model'], row['model'])

    def test_save_round_trip_and_source_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'results.json'
            source.write_text('original', encoding='utf-8')
            output = Path(folder) / 'settings.json'
            settings = self.build()
            save_settings(output, settings, source)
            self.assertEqual(json.loads(output.read_text()), settings)
            with self.assertRaises(ValueError):
                save_settings(source, settings, source)
            self.assertEqual(source.read_text(), 'original')


if __name__ == '__main__':
    unittest.main()
