import copy
import json
from pathlib import Path
import tempfile
import unittest
from model import ROOT, batch, select_cases, write_json, starting_depth


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((ROOT/'openseespy-cli/examples/prepared.json').read_text())
        self.settings = json.loads((ROOT/'openseespy-cli/examples/settings.json').read_text())
        self.settings['embedment_ft'] = 10
        self.doc['piers'][0]['minimum_embedment_ft'] = 10
        self.doc['piers'][0]['allowable_deflection_in'] = .1

    def fake(self, inputs, settings, output, python):
        cfg = json.loads(settings.read_text())
        output.mkdir()
        (output/'forces.csv').write_text('element,end,node,Elevation [ft],V_local [kip],M_local [kip-ft]\n1,i,1,0,2,3\n1,j,2,-10,-2,-3\n')
        return dict(status='converged', load_factor=1, head_deflection_in=.2 if cfg['embedment_ft'] < 12 else .08)

    def execute(self, folder, **kwargs):
        source = Path(folder)/'inputs.json'
        write_json(source, self.doc)
        return batch(source, self.settings, Path(folder)/'results', max_depth=13, python=__import__('sys').executable, runner=self.fake, **kwargs)

    def test_increase_depth_and_recheck_all_planes(self):
        with tempfile.TemporaryDirectory() as folder:
            report = self.execute(folder, mode='directional')
            result = report['footings'][0]
            self.assertEqual(result['accepted_depth_ft'], 12)
            self.assertEqual([t['depth_ft'] for t in result['trials']], [10, 11, 12])
            self.assertEqual({r['plane'] for r in result['trials'][-1]['cases']}, {'X', 'Y'})
            self.assertEqual(result['max_moment_kip_ft'], 3)
            self.assertTrue((Path(folder)/'results/footings.csv').exists())

    def test_resultant_exceeds_allowable_when_each_plane_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.execute(folder)['footings'][0]
            self.assertEqual(result['status'], 'depth_limit')
            self.assertAlmostEqual(result['checked_deflection_in'], (0.08**2 + 0.08**2)**0.5)
            self.assertEqual(result['status'], 'depth_limit')
            self.assertIsNone(result['accepted_depth_ft'])

    def test_solver_failure_does_not_become_pass_or_trigger_depth_increase(self):
        def fail(*args):
            raise RuntimeError('nonconvergence')
        with tempfile.TemporaryDirectory() as folder:
            self.fake = fail
            result = self.execute(folder)['footings'][0]
            self.assertEqual(result['status'], 'error')
            self.assertEqual(len(result['trials']), 1)
            self.assertIn('nonconvergence', result['message'])

    def test_requested_depth_reaches_solver_and_report(self):
        self.settings['embedment_ft'] = 12
        with tempfile.TemporaryDirectory() as folder:
            result = self.execute(folder, mode='directional')['footings'][0]
            self.assertEqual(result['starting_depth_ft'], 12)
            self.assertEqual([t['depth_ft'] for t in result['trials']], [12])
            settings = next((Path(folder)/'results').rglob('*-settings.json'))
            self.assertEqual(json.loads(settings.read_text())['embedment_ft'], 12)

    def test_minimum_remains_floor_and_invalid_depth_is_rejected(self):
        pier = self.doc['piers'][0]
        self.assertEqual(starting_depth(pier, 8), 10)
        for value in (0, -1, float('nan'), float('inf'), 'invalid'):
            with self.assertRaises(ValueError):
                starting_depth(pier, value)
        self.settings['embedment_ft'] = 14
        with tempfile.TemporaryDirectory() as folder:
            result = self.execute(folder)['footings'][0]
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['trials'], [])
            self.assertIn('Starting embedment', result['message'])

    def test_all_ties_keep_coincident_vectors(self):
        row = self.doc['piers'][0]['reactions'][0]
        self.doc['piers'][0]['reactions'].append(dict(row, node=99))
        cases = select_cases(self.doc['piers'][0])
        self.assertEqual({c['reaction']['node'] for c in cases}, {row['node'], 99})

    def test_soil_coverage_and_cancellation(self):
        with tempfile.TemporaryDirectory() as folder:
            self.doc['soil_profiles'][0]['layers'][-1]['properties']['end'] = 11.5
            result = self.execute(folder)['footings'][0]
            self.assertEqual(result['status'], 'depth_limit')
            self.assertEqual(result['trials'][-1]['depth_ft'], 11.5)
        with tempfile.TemporaryDirectory() as folder:
            result = self.execute(folder, cancelled=lambda: True)['footings'][0]
            self.assertEqual(result['status'], 'cancelled')
            self.assertFalse(result['trials'])


if __name__ == '__main__':
    unittest.main()
