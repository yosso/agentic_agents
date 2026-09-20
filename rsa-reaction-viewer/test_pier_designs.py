import tempfile
import unittest
from pathlib import Path
from openpyxl import Workbook
from openpyxl.worksheet.table import Table
from pier_designs import prepare_pier_designs, SOIL_FIELDS, ASSIGNMENT_FIELDS


class PreparationTests(unittest.TestCase):
    def run_fixture(self, boring='SB3', end=10, reactions=None, assignment='SB3'):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'inputs.xlsx'
            book = Workbook()
            soil = book.active
            soil.title = 'GEOTECH PARAMETERS'
            soil.append(['NUMBER', boring])
            soil.append(list(SOIL_FIELDS))
            soil.append([0, end, 'SOFT CLAY', 125, 1, 0.66, 0, 200, '-', 133, 1, 1.5])
            soil.add_table(Table(displayName='tblSOIL_BORING_03', ref='A2:L3'))
            sheet = book.create_sheet('INPUT TABLES')
            sheet.append(list(ASSIGNMENT_FIELDS))
            sheet.append(['A', assignment, 2.5, 5, 0, 0.3])
            sheet.add_table(Table(displayName='tblBoringAssignment', ref='A1:F2'))
            book.save(path)
            book.close()
            before = path.read_bytes()
            result = prepare_pier_designs(path, reactions or [], soil_units={})
            self.assertEqual(before, path.read_bytes())
            return result

    def test_id_comes_from_table_suffix(self):
        row = dict(mark='A', model='file', group='g', node=1, case=20, case_name='comb',
                   FX=1, FY=2, FZ=-3, MX=4, MY=5, MZ=6)
        result = self.run_fixture(reactions=[row])
        self.assertEqual(result.soil_profiles[0].boring_id, 'SB3')
        self.assertEqual(result.piers[0].soil_table, 'tblSOIL_BORING_03')
        self.assertEqual(result.piers[0].reactions[0]['FZ'], -3)
        self.assertEqual(result.piers[0].water_table_depth_ft, 0)
        self.assertIsNone(result.soil_profiles[0].layers[0].properties['k_cyclic'])
        self.assertFalse(result.input_valid)  # units still unconfirmed
        self.assertFalse(result.to_dict()['solver_ready'])

    def test_unknown_boring_and_invalid_layer_report_sources(self):
        result = self.run_fixture(boring='SB3', end=0, assignment='SB23')
        messages = [i.message for i in result.issues]
        self.assertTrue(any('no unique soil table' in m for m in messages))
        self.assertTrue(any('END must exceed START' in m for m in messages))
        self.assertTrue(any('No extracted load combinations' in m for m in messages))

    def test_label_mismatch_is_flagged_and_does_not_reassign_profile(self):
        result = self.run_fixture(boring='SB23')
        self.assertEqual(result.soil_profiles[0].boring_id, 'SB3')
        self.assertTrue(any('Boring ID mismatch' in i.message for i in result.issues))

    def test_numeric_label_and_zero_padded_assignment_match(self):
        result = self.run_fixture(boring=3, assignment='SB03')
        self.assertEqual(result.piers[0].soil_table, 'tblSOIL_BORING_03')
        self.assertFalse(any('Boring ID mismatch' in i.message or 'no unique soil table' in i.message for i in result.issues))


if __name__ == '__main__':
    unittest.main()
