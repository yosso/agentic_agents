import copy
import unittest
from unittest.mock import patch
from preparation import assemble_inputs


class FakeReport:
    def __init__(self):self.issues=[]
    def to_dict(self):
        return {'piers':[], 'soil_profiles':[], 'issues':[dict(severity=i.severity,footing=i.footing,source=i.source,message=i.message) for i in self.issues]}


class PreparationTests(unittest.TestCase):
    def test_quantity_and_extraction_errors_are_preserved(self):
        mapping=dict(mark='A',model='chosen.rtd',group='G',expected=2,row=2,source='Excel mapping',quantity_cell='B2')
        extraction=dict(error='Reader failure',groups=[dict(mark='A',model='chosen.rtd',group='G',node_count=1,support_count=1,status='Quantity mismatch')],reactions=[],warnings=['Incomplete combinations'])
        original=copy.deepcopy(mapping)
        with patch('preparation.prepare_pier_designs',return_value=FakeReport()):
            document=assemble_inputs('inputs.xlsx',[mapping],extraction)
        self.assertEqual(document['mapping_snapshot'][0]['model'],'chosen.rtd')
        messages=[i['message'] for i in document['issues']]
        self.assertIn('Reader failure',messages)
        self.assertIn('Incomplete combinations',messages)
        self.assertTrue(any('2' in m and '1' in m for m in messages))
        self.assertEqual(mapping,original)

    def test_missing_extraction_group_blocks_preparation(self):
        mapping=dict(mark='A',model='chosen.rtd',group='G',expected=2)
        with patch('preparation.prepare_pier_designs',return_value=FakeReport()):
            document=assemble_inputs('inputs.xlsx',[mapping],dict(groups=[],reactions=[]))
        self.assertEqual(document['issues'][0]['severity'],'ERROR')


if __name__=='__main__':unittest.main()
