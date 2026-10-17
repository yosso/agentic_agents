import sys
import tempfile
import unittest
from pathlib import Path
from capacity import capacity_search
from model import ROOT, read_json


class CapacityTests(unittest.TestCase):
    def run_search(self, folder, **kwargs):
        return capacity_search(ROOT/'openseespy-cli/examples/prepared.json',
                               read_json(ROOT/'openseespy-cli/examples/settings.json'),
                               Path(folder)/'results', python=sys.executable, **kwargs)

    def fake(self, inputs, settings, output, python):
        document=read_json(inputs)
        cfg=read_json(settings)
        row=document['piers'][0]['reactions'][0]
        self.assertEqual(cfg['embedment_ft'],10)
        self.assertAlmostEqual(row['FX'],row['MY'])
        self.assertAlmostEqual(row['FZ'],row['FX'])
        output.mkdir()
        (output/'forces.csv').write_text('element,end,node,Elevation [ft],V_local [kip],M_local [kip-ft]\n1,i,1,0,2,3\n1,j,2,-10,-2,-3\n')
        return {'head_deflection_in': row['FX']/1000*.1 if cfg['plane']=='X' else row['FX']/1000*.1}

    def test_combined_check_brackets_limit_and_preserves_load_ratio(self):
        with tempfile.TemporaryDirectory() as folder:
            result=self.run_search(folder,runner=self.fake)['searches'][0]
            self.assertEqual(result['status'],'bracketed')
            self.assertLessEqual(result['passing_deflection_in'],.3564)
            self.assertGreater(result['upper_deflection_in'],.3564)
            expected=.3564/(.1*2**.5)
            self.assertLessEqual(result['lower_passing_factor'],expected)
            self.assertGreater(result['upper_failing_factor'],expected)
            self.assertLessEqual(result['upper_failing_factor']-result['lower_passing_factor'],.01*result['upper_failing_factor'])

    def test_no_false_capacity_when_search_limit_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            result=self.run_search(folder,runner=self.fake,max_factor=1)['searches'][0]
            self.assertEqual(result['status'],'load_limit')

    def test_solver_failure_and_cancellation_are_unresolved(self):
        def fail(*args):
            raise RuntimeError('nonconvergence')
        with tempfile.TemporaryDirectory() as folder:
            result=self.run_search(folder,runner=fail)['searches'][0]
            self.assertEqual(result['status'],'unresolved')
            self.assertIsNone(result['lower_passing_factor'])
        with tempfile.TemporaryDirectory() as folder:
            result=self.run_search(folder,runner=self.fake,cancelled=lambda:True)['searches'][0]
            self.assertEqual(result['status'],'cancelled')


if __name__=='__main__':
    unittest.main()
