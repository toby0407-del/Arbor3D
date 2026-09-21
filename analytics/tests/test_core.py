import csv
import json
import math
import tempfile
import unittest
from pathlib import Path
from analytics.core import build, export


def report(scan='s1', date='2026-01-01', dbh=22, strict=True, method='circle'):
    return ('campus', 'fixture.json', {'scan_id': scan, 'created_at': date, 'num_trees': 1, 'trees': [dict(Tree_ID='Tree_001', DBH_cm=dbh, dbh_is_strict_breast_height=strict, DBH_method=method)]})

def manual(scan='s1', date='2026-01-01', dbh=20):
    return dict(site_id='campus', scan_id=scan, local_tree_id='Tree_001', manual_dbh_cm=dbh, measured_at=date, strict_13m=True)

def identity(scan='s1', persistent='TREE-A'):
    return dict(site_id='campus', scan_id=scan, local_tree_id='Tree_001', persistent_tree_id=persistent, confirmed=True)

class AnalyticsTests(unittest.TestCase):
    def test_error_metrics(self):
        t = build([report(), report('s2', dbh=18)], [manual(), manual('s2')])
        s = t['Summary'][0]
        self.assertEqual((s['mae_cm'], s['rmse_cm'], s['bias_cm'], s['mape_pct']), (2, 2, 0, 10))
    def test_missing_not_zero(self):
        t = build([report()]); self.assertIsNone(t['Summary'][0]['mae_cm'])
        self.assertEqual(t['FactObservation'][0]['comparison_status'], 'missing_manual')
    def test_nonstandard_and_dates_excluded(self):
        for r, m, expected in [(report(strict=False), manual(), 'nonstandard_height'), (report(), manual(date='2026-02-01'), 'date_mismatch')]:
            self.assertEqual(build([r], [m])['FactObservation'][0]['comparison_status'], expected)
    def test_zero_nan_negative_rejected(self):
        for n in [0, -1, float('nan'), float('inf'), True]:
            with self.assertRaises(ValueError): build([report()], [manual(dbh=n)])
    def test_identity_is_required(self):
        self.assertEqual(build([report(), report('s2', '2027-01-01')])['FactGrowth'], [])
    def test_growth_and_negative_change(self):
        t=build([report(), report('s2', '2027-01-01', 20)], identity_rows=[identity(), identity('s2')])
        g=t['FactGrowth'][0]; self.assertEqual(g['delta_dbh_cm'], -2); self.assertTrue(g['negative_change'])
        self.assertAlmostEqual(g['annualized_delta_cm'], -2/365*365.25)
    def test_no_method_or_height_mixing(self):
        for r in [report('s2', '2027-01-01', method='caliper'), report('s2', '2027-01-01', strict=False)]:
            self.assertEqual(build([report(), r], identity_rows=[identity(), identity('s2')])['FactGrowth'], [])
    def test_duplicate_and_orphan_rejected(self):
        for reports, m, ids in [([report(),report()],[],[]), ([report()],[manual(),manual()],[]), ([report()],[manual('bad')],[]), ([report()],[],[identity('bad')])]:
            with self.assertRaises(ValueError): build(reports,m,ids)
    def test_ambiguous_dates_rejected(self):
        with self.assertRaises(ValueError): build([report(),report('s2')],identity_rows=[identity(),identity('s2')])
    def test_estimate_provenance(self):
        r=build([report()])['FactEstimate'][0]
        self.assertEqual((r['source'],r['height_source'],r['dbh_input_source']), ('estimated','estimated','ai'))
    def test_csv_json_and_empty_headers(self):
        with tempfile.TemporaryDirectory() as d:
            t=build([report()]); export(t,d)
            with open(Path(d)/'FactObservation.csv',encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
            self.assertEqual(rows[0]['manual_dbh_cm'],'')
            self.assertEqual(json.loads((Path(d)/'analytics.json').read_text())['tables'],t)
            self.assertTrue((Path(d)/'FactGrowth.csv').read_text(encoding='utf-8-sig').startswith('tree_key,'))
    def test_formula_injection_escaped(self):
        from analytics.core import csv_safe
        self.assertEqual(csv_safe(' =1+1'), "' =1+1")
        self.assertEqual(csv_safe(-2), -2)

if __name__ == '__main__': unittest.main()
