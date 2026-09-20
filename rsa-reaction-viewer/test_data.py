import tempfile
import unittest
from pathlib import Path
from openpyxl import Workbook
from openpyxl.worksheet.table import Table
from data import read_mapping, parse_cases, display_reaction, assess_group, controlling_combinations


class MappingTests(unittest.TestCase):
    def test_controllers_preserve_coincident_loads_and_sources(self):
        a = dict(mark='A', model='one', group='g', node=1, case=20, case_name='first',
                 FX=3, FY=4, FZ=-9, MX=1, MY=0, MZ=0)
        b = dict(a, model='two', case=30, FX=-8, FY=0, FZ=2, MX=0, MY=6)
        c = dict(a, mark='B', FX=100)
        results = controlling_combinations([a, b, c])
        lookup = {(r['mark'], r['criterion']): r for r in results}
        self.assertEqual(len(results), 10)
        self.assertEqual(lookup['A', 'Maximum compression']['reaction'], b)
        self.assertEqual(lookup['A', 'Maximum uplift']['reaction'], a)
        self.assertEqual(lookup['A', 'Maximum uplift']['value'], -9)
        self.assertEqual(lookup['A', 'Maximum shear']['value'], 8)
        self.assertEqual(lookup['A', 'Maximum bending moment']['value'], 6)
        self.assertEqual(lookup['A', 'Maximum torsion']['ties'], 2)
        self.assertIsNone(lookup['B', 'Maximum compression']['reaction'])
        self.assertEqual(controlling_combinations([]), [])

    def test_negative_torsion_controls_and_no_uplift_is_explicit(self):
        base = dict(mark='A', model='one', group='g', node=1, case=20,
                    case_name='first', FX=0, FY=0, FZ=3, MX=0, MY=0, MZ=5)
        other = dict(base, case=21, MZ=-12)
        result = {r['criterion']: r for r in controlling_combinations([base, other])}
        self.assertEqual(result['Maximum torsion']['value'], 12)
        self.assertEqual(result['Maximum torsion']['reaction']['MZ'], -12)
        self.assertIsNone(result['Maximum uplift']['reaction'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.path = self.folder / 'inputs.xlsx'

    def workbook(self, rows):
        book = Workbook()
        sheet = book.active
        sheet.title = 'INPUT TABLES'
        sheet.append(['MARK', 'FOOTING QTY', 'GROUP NAME', 'ROBOT FILE NAME'])
        for row in rows:
            sheet.append(row)
        sheet.add_table(Table(displayName='RSA_GROUP_MAPPING', ref=f'A1:D{len(rows)+1}'))
        book.save(self.path)
        book.close()

    def read(self):
        return read_mapping(self.path, 'INPUT TABLES', 'RSA_GROUP_MAPPING')

    def test_relative_model_extension_and_workbook_unchanged(self):
        self.workbook([['A', 21, 'BUS SUPPORT', 'frame'], [None]*4])
        (self.folder / 'frame.rtd').touch()
        before = self.path.read_bytes()
        rows = self.read()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['expected'], 21)
        self.assertTrue(rows[0]['exists'])
        self.assertEqual(rows[0]['model'], str(self.folder / 'frame.rtd'))
        self.assertEqual(before, self.path.read_bytes())

    def test_duplicate_group_rejected_but_separate_models_allowed(self):
        self.workbook([['A', 2, 'BUS', 'one'], ['B', 2, 'BUS', 'two']])
        self.assertEqual(len(self.read()), 2)
        self.workbook([['A', 2, 'BUS', 'one'], ['B', 2, 'bus', 'one']])
        with self.assertRaisesRegex(ValueError, 'more than once'):
            self.read()

    def test_incomplete_and_fractional_quantity_rejected(self):
        for row in [['A', None, 'BUS', 'one'], ['A', 2.5, 'BUS', 'one']]:
            self.workbook([row])
            with self.assertRaises(ValueError):
                self.read()

    def test_case_filter(self):
        self.assertEqual(parse_cases('1,3-5 3'), [1, 3, 4, 5])
        self.assertEqual(parse_cases(''), [])
        for text in ['0', '5-2', '1 OR 3']:
            with self.assertRaises(ValueError):
                parse_cases(text)

    def test_mismatch_identifies_input_and_actual_count(self):
        mapping = dict(expected=8, row=38, source='INPUT TABLES', quantity_cell='C38')
        verdict, findings, _ = assess_group(dict(node_count=7, support_count=7, status='Quantity mismatch'), mapping)
        self.assertEqual(verdict, 'REVIEW')
        self.assertIn('C38', findings[0])
        self.assertIn('Excel 8, Robot group nodes 7', findings[0])
        self.assertIn('difference -1', findings[0])
        verdict, findings, _ = assess_group(dict(node_count=8, support_count=7, status='Node is not a support'), mapping)
        self.assertEqual(verdict, 'REVIEW')
        self.assertIn('Robot supports 7', findings[0])
        self.assertEqual(assess_group(dict(node_count=8, support_count=8, status='OK'), mapping)[0], 'MATCH')

    def test_failed_read_is_not_reported_as_zero_nodes(self):
        verdict, findings, _ = assess_group(dict(node_count=None, support_count=None, status='File unavailable'), dict(expected=8, row=38))
        self.assertEqual(verdict, 'REVIEW')
        self.assertEqual(findings, ['File unavailable'])

    def test_units_keep_force_moment_and_sign_distinct(self):
        row = dict(FX=-4448.2216152605, FY=0, FZ=4448.2216152605,
                   MX=1355.8179483314, MY=0, MZ=-1355.8179483314)
        self.assertEqual(display_reaction(row, 'kip / kip-ft'), [-1, 0, 1, 1, 0, -1])


if __name__ == '__main__':
    unittest.main()
