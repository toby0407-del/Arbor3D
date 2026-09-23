import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from analytics.tests.test_core import report, manual
from analytics.core import FIELDS

class IntegrationTests(unittest.TestCase):
    def test_app_bundle_cli(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d,'input.json'); output=Path(d,'out')
            row=manual(); row.pop('site_id')
            path.write_text(json.dumps({'schema_version':'1.0','report':report()[2],'manual_measurements':[row]}))
            result=subprocess.run([sys.executable,'-m','analytics','--bundle',str(path),'--site-id','campus','--out',str(output)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            summary=json.loads(result.stdout)
            self.assertEqual(summary['paired_count'],1)
            self.assertEqual(summary['mae_cm'],2)
            self.assertEqual(set(json.loads((output/'analytics.json').read_text())['tables']),set(FIELDS))
    def test_invalid_bundle_has_no_output(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d,'input.json'); output=Path(d,'out')
            row=manual(); row['measured_at']=''
            path.write_text(json.dumps({'report':report()[2],'manual_measurements':[row]}))
            result=subprocess.run([sys.executable,'-m','analytics','--bundle',str(path),'--site-id','campus','--out',str(output)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2); self.assertFalse(output.exists())
    def test_model_contract_endpoints(self):
        model=json.loads(Path('powerbi/model.bim').read_text())['model']
        columns={t['name']:{c['name'] for c in t['columns']} for t in model['tables']}
        for name,fields in columns.items(): self.assertEqual(fields,set(FIELDS[name]))
        for rel in model['relationships']:
            self.assertIn(rel['fromColumn'],columns[rel['fromTable']]); self.assertIn(rel['toColumn'],columns[rel['toTable']])

    def test_one_command_powerbi_delivery(self):
        from powerbi.delivery import deliver
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); bundle=root/'input.json'; output=root/'delivery'
            row=manual(); row.pop('site_id')
            bundle.write_text(json.dumps({'schema_version':'1.0','report':report()[2],'manual_measurements':[row]}))
            result=deliver(bundle,'campus',output)
            self.assertEqual(result['pages'],5)
            self.assertEqual(result['dataset_kind'],'observed')
            self.assertFalse(result['desktop_validated'])
            self.assertTrue((output/'analytics/analytics.json').is_file())
            self.assertTrue((output/'powerbi/Arbor3D.pbip').is_file())
            self.assertTrue((output/'delivery-report.json').is_file())
            with self.assertRaises(ValueError): deliver(bundle,'campus',output)

    def test_onelake_package_and_hash_guard(self):
        from analytics.core import build, export
        from fabric.package_snapshot import package
        from zipfile import ZipFile
        with tempfile.TemporaryDirectory() as d:
            source=Path(d,'source.json'); source.write_text(json.dumps(report()[2]))
            out=Path(d,'out'); export(build([('campus',str(source),report()[2])]),out)
            zip_path=Path(d,'lake.zip'); result=package(out,zip_path)
            self.assertFalse(result['uploaded'])
            with ZipFile(zip_path) as z:
                self.assertTrue(any('/bronze/' in n for n in z.namelist()))
                self.assertTrue(any('/gold/' in n for n in z.namelist()))
            (out/'FactObservation.csv').write_text('changed')
            with self.assertRaises(ValueError): package(out,zip_path)
