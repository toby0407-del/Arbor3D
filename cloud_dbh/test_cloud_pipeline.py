import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from cloud_dbh.archives import build_result, install_result, pack_inbox, safe_member, unpack_zip
from cloud_dbh.worker import execute_job


class CloudArchiveTests(unittest.TestCase):
    def test_archive_rejects_traversal_and_duplicate_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("../escape.txt", "/absolute.txt", "folder\\escape.txt", "C:/escape.txt"):
                with self.assertRaises(ValueError):
                    safe_member(name)
                if "\\" in name:  # ZipInfo normalizes Windows separators when creating a fixture.
                    continue
                with zipfile.ZipFile(root / "bad.zip", "w") as archive:
                    archive.writestr(name, "bad")
                with self.assertRaises(ValueError):
                    unpack_zip(root / "bad.zip", root / "out")
            self.assertFalse((root / "escape.txt").exists())

    def test_full_result_installs_assets_and_bindings_without_overwriting_observations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "result"
            source.mkdir()
            report = {"scan_id": "cloud-test", "num_trees": 1, "trees": [{"Tree_ID": "test-only", "DBH_cm": None}]}
            (source / "inventory.json").write_text(json.dumps(report), encoding="utf-8")
            (source / "evidence.txt").write_text("unit-test fixture", encoding="utf-8")
            build_result(source, "cloud-test", root / "result.zip")
            actual = install_result(root / "result.zip", root / "app", "cloud-test", "path-1")
            self.assertEqual(actual, report)
            self.assertEqual(json.loads((root / "app/public/scans/_bindings.json").read_text())["path-1"], "cloud-test")
            self.assertTrue((root / "app/public/scans/cloud-test/evidence.txt").exists())
            with self.assertRaises(FileExistsError):
                install_result(root / "result.zip", root / "app", "cloud-test")
            with self.assertRaises(ValueError):
                install_result(root / "result.zip", root / "app", "different-scan")

    def test_checksums_and_prepare_mode_cannot_be_published_as_real_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with zipfile.ZipFile(root / "bad.zip", "w") as archive:
                archive.writestr("cloud-manifest.json", json.dumps({"schema_version": 1, "pipeline": "arbor3d", "mode": "full", "scan_id": "cloud-test", "files": [{"path": "inventory.json", "bytes": 2, "sha256": "0" * 64}]}))
                archive.writestr("inventory.json", "{}")
            with self.assertRaisesRegex(ValueError, "checksum"):
                install_result(root / "bad.zip", root / "app", "cloud-test")
            self.assertFalse((root / "app/public/scans/cloud-test").exists())

    def test_input_archive_includes_metadata_but_not_logs_or_generated_archives(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "metadata").mkdir()
            (root / "metadata/calib.json").write_text("{}")
            (root / "job.json").write_text("private task metadata")
            pack_inbox(root, root / "upload.zip")
            with zipfile.ZipFile(root / "upload.zip") as archive:
                self.assertEqual(archive.namelist(), ["metadata/calib.json"])

    def test_prepare_job_has_distinct_status_and_no_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job = root / "job-test"
            for folder in ("raw", "denoised", "gaussian"):
                (job / "inbox" / folder).mkdir(parents=True)
            with patch("cloud_dbh.worker.run_postprocess"):
                result = execute_job(job_id="job-test", scan_id="cloud-test", prepare_only=True, work_root=root)
            self.assertEqual(result["status"], "prepared")
            self.assertIsNone(result["result"])

    def test_full_job_without_inventory_fails_instead_of_reusing_an_old_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job = root / "job-test"
            for folder in ("raw", "denoised", "gaussian"):
                (job / "inbox" / folder).mkdir(parents=True)
            with patch("cloud_dbh.worker.run_postprocess"):
                result = execute_job(job_id="job-test", scan_id="cloud-test", work_root=root)
            self.assertEqual(result["status"], "failed")


if __name__ == "__main__":
    unittest.main()
