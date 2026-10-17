import csv
import json
from pathlib import Path
import tempfile
import unittest
from model import load_results


class ResultTests(unittest.TestCase):
    def test_project_end_signs_and_source_preservation(self):
        folder = Path(__file__).resolve().parents[1] / 'openseespy-cli/results/20261002-run-02'
        before = (folder / 'forces.csv').read_bytes()
        result = load_results(folder)
        with (folder / 'forces.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        moment = result['curves']['Moment [kip-ft]'][0]
        self.assertEqual(moment[0][0], float(rows[0]['M_local [kip-ft]']))
        self.assertEqual(moment[1][0], -float(rows[1]['M_local [kip-ft]']))
        self.assertAlmostEqual(result['curves']['Deflection [in]'][0][0][0], result['summary']['head_deflection_in'])
        self.assertEqual(before, (folder / 'forces.csv').read_bytes())

    def test_legacy_si_conversion(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            for name, data in [('analysis-inputs', {'layers': []}), ('summary', {'status': 'converged'}), ('validation', {'valid': True})]:
                (p / (name+'.json')).write_text(json.dumps(data))
            (p/'displacements.csv').write_text('node,Elevation [m],Deflection [m]\n1,0,0.0254\n2,-0.3048,0\n')
            (p/'forces.csv').write_text('element,end,node,Elevation [m],V_local [kN],M_local [kNm]\n1,i,1,0,4.4482216152605,1.3558179483314\n1,j,2,-0.3048,-4.4482216152605,-1.3558179483314\n')
            result = load_results(p)
            self.assertAlmostEqual(result['curves']['Deflection [in]'][0][0][0], 1)
            self.assertAlmostEqual(result['curves']['Shear [kip]'][0][1][0], 1)
            self.assertAlmostEqual(result['curves']['Moment [kip-ft]'][0][1][0], 1)
            self.assertAlmostEqual(result['curves']['Moment [kip-ft]'][0][1][1], 1)
            (p/'summary.json').write_text('{"status":"failed"}')
            with self.assertRaises(ValueError):
                load_results(p)


if __name__ == '__main__':
    unittest.main()
