import json
import tempfile
import unittest
from pathlib import Path

from analytics.core import build, export
from analytics.simulate import generate
from analytics.tests.test_core import report
from powerbi.build_project import generate as project


class SimulationTests(unittest.TestCase):
    def test_quarterly_history_and_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            template = root / 'template.json'
            template.write_text(json.dumps(report()[2]), encoding='utf-8')
            metadata = generate(template, root / 'demo')
            self.assertEqual((metadata['start'], metadata['end']), ('2022-09-30', '2026-06-30'))
            self.assertEqual(metadata['observations'], 16)
            data = json.loads((root / 'demo/analytics/analytics.json').read_text(encoding='utf-8'))['tables']
            self.assertEqual(len(data['FactGrowth']), 30)
            self.assertEqual({r['source'] for r in data['FactGrowth']}, {'simulated_ai', 'simulated_measured'})
            self.assertTrue(all(r['dataset_kind'] == 'simulated' for rows in data.values() for r in rows))
            self.assertEqual(data['DimTree'][0]['identity_status'], 'simulated')
            generate(template, root / 'repeat')
            self.assertEqual((root / 'demo/reports/SIM-2022Q3.json').read_bytes(), (root / 'repeat/reports/SIM-2022Q3.json').read_bytes())
            with self.assertRaises(ValueError): generate(template, root / 'demo')

    def test_real_and_simulated_must_not_mix(self):
        real = report()
        fake = report('sim')
        fake[2]['dataset_kind'] = 'simulated'
        with self.assertRaises(ValueError): build([fake])
        with self.assertRaises(ValueError): build([real, fake], allow_simulated=True)
        self.assertEqual(build([real])['Summary'][0]['dataset_kind'], 'observed')

    def test_invalid_quarter_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'absent'
            for kwargs in ({'end': '2026-08-18'}, {'quarters': 1}):
                with self.assertRaises(ValueError): generate('unused.json', out, **kwargs)
            self.assertFalse(out.exists())

    def test_pbip_links_fields_and_protected_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'data'
            export(build([report()]), source)
            result = project(source, root / 'project')
            self.assertFalse(result['desktop_validated'])
            self.assertEqual(result['pages'], 5)
            model = json.loads((root / 'project/Arbor3D.SemanticModel/model.bim').read_text(encoding='utf-8'))['model']
            columns = {t['name']: {c['name'] for c in t['columns']} for t in model['tables']}
            measures = {t['name']: {m['name'] for m in t.get('measures', [])} for t in model['tables']}
            for path in (root / 'project').rglob('visual.json'):
                visual = json.loads(path.read_text(encoding='utf-8'))
                for role in visual['visual']['query']['queryState'].values():
                    for projection in role['projections']:
                        kind, expr = next(iter(projection['field'].items()))
                        entity = expr['Expression']['SourceRef']['Entity']
                        self.assertIn(expr['Property'], (measures if kind == 'Measure' else columns)[entity])
            with self.assertRaises(ValueError): project(source, root / 'project')
            (source / 'FactGrowth.csv').write_text('corrupted', encoding='utf-8')
            with self.assertRaises(ValueError): project(source, root / 'bad')
            self.assertFalse((root / 'bad').exists())

    def test_real_accuracy_measures_exclude_simulation(self):
        from powerbi.build_model import MEASURES
        for name in ('Valid Pairs', 'MAE cm', 'RMSE cm', 'Bias cm', 'MAPE percent'):
            self.assertIn('KEEPFILTERS(FactObservation[dataset_kind] = "observed")', MEASURES[name])
