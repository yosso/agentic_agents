"""Bridge tests without launching Robot or modifying a project workbook."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import extract_inputs as bridge


class ExtractionTests(unittest.TestCase):
    def test_extract_passes_combinations_and_preserves_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / 'test.rtd'
            model.touch()
            mappings = [dict(mark='A', row=2, expected=3, group='Supports', model=str(model), exists=True)]
            reactions = dict(groups=[], reactions=[], warnings=['Example warning'])
            document = dict(piers=[], soil_profiles=[], issues=[dict(severity='ERROR', message='Missing group')])
            request = dict(command='extract', workbook=str(Path(directory)/'input.xlsm'),
                           sheet='INPUT TABLES', table='RSA_GROUP_MAPPING', snapshot=mappings,
                           cases='101, 105-106', api='robot.dll')
            with patch.object(bridge, 'read_mapping', return_value=mappings), \
                 patch.object(bridge, 'extract_reactions', return_value=reactions) as extract, \
                 patch.object(bridge, 'assemble_inputs', return_value=document) as assemble:
                result = bridge.process(request)
                extract.assert_called_once_with(mappings, 'robot.dll', [101, 105, 106])
                assemble.assert_called_once_with(Path(request['workbook']), mappings, reactions)
                self.assertEqual(result['document'], document)
                self.assertEqual(result['extraction'], reactions)

    def test_stale_mapping_blocks_robot(self):
        with patch.object(bridge, 'read_mapping', return_value=[{'row': 2}]), \
             patch.object(bridge, 'extract_reactions') as extract:
            with self.assertRaisesRegex(ValueError, 'mapping changed'):
                bridge.process(dict(command='extract', workbook='input.xlsm', sheet='INPUT TABLES',
                                    table='RSA_GROUP_MAPPING', snapshot=[]))
            extract.assert_not_called()


if __name__ == '__main__':
    unittest.main()
