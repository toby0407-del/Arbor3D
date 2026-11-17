import json
import tempfile
import unittest
from pathlib import Path
from analytics.tests.test_core import report
from analytics.core import build, export
from powerbi.local_app import publish


class DesktopPublishTests(unittest.TestCase):
    def test_reconciles_engine_results_and_rejects_stale_model(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            source=report()
            tables=build([source])
            export(tables,root/'analytics')
            scan=source[2]['scan_id']
            (root/'sources.json').write_text(json.dumps([dict(scan_id=scan,fingerprint='a'*64,dataset_kind='observed')]))
            summary=tables['Summary'][0]
            metrics={k:summary[k] for k in ('observations','paired_count','mae_cm','rmse_cm','bias_cm','mape_pct','review_count')}
            metrics.update(average_dbh_cm=22,co2_ton=tables['FactEstimate'][0]['co2_equivalent_ton'],demo_pairs=None,demo_mae_cm=None)
            # CSV empty text is imported as Tabular null; both mean no review reason.
            for row in tables['FactObservation']:
                if row['review_reason']=='': row['review_reason']=None
            evidence=dict(engine='Power BI Desktop / Analysis Services',queried_at='2026-10-28T00:00:00Z',
                tables={k:tables[k] for k in ('DimScan','FactObservation','FactEstimate','FactGrowth')},metrics=[dict(metrics,scan_id=scan)])
            results=root/'desktop.json'
            results.write_text(json.dumps(evidence))
            self.assertEqual(publish(root,results,root/'public'),[scan])
            self.assertIsNone(json.loads((root/f'public/analysis/{scan}.json').read_text())['metrics']['mae_cm'])
            evidence['tables']['FactObservation'][0]['auto_dbh_cm']=999
            results.write_text(json.dumps(evidence))
            with self.assertRaisesRegex(ValueError,'Desktop data differs'):
                publish(root,results,root/'public')

    def test_rejects_invented_dax_accuracy(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); source=report(); tables=build([source]); export(tables,root/'analytics')
            scan=source[2]['scan_id']
            (root/'sources.json').write_text(json.dumps([dict(scan_id=scan,fingerprint='a'*64,dataset_kind='observed')]))
            metrics={k:tables['Summary'][0][k] for k in ('observations','paired_count','mae_cm','rmse_cm','bias_cm','mape_pct','review_count')}
            metrics['mae_cm']=0
            evidence=dict(engine='Power BI Desktop / Analysis Services',queried_at='2026-10-28T00:00:00Z',tables=tables,metrics=[dict(metrics,scan_id=scan)])
            results=root/'desktop.json'; results.write_text(json.dumps(evidence))
            with self.assertRaisesRegex(ValueError,'DAX reconciliation failed'):
                publish(root,results,root/'public')
