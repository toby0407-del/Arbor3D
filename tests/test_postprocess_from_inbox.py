from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.postprocess_from_inbox import publish_report


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "postprocess_from_inbox.py"
PLY = b"ply\nformat ascii 1.0\nelement vertex 0\nend_header\n"


class PostprocessFromInboxTests(unittest.TestCase):
    def make_job(self, root: Path, with_metadata: bool = True) -> Path:
        job = root / "job"
        (job / "denoised").mkdir(parents=True)
        (job / "gaussian").mkdir()
        (job / "raw" / "go").mkdir(parents=True)
        (job / "denoised" / "tree.ply").write_bytes(PLY)
        (job / "gaussian" / "scene.ply").write_bytes(PLY)
        (job / "raw" / "go" / "frame.jpg").write_bytes(b"jpeg-test")
        if with_metadata:
            (job / "metadata" / "calibration").mkdir(parents=True)
            (job / "metadata" / "poses").mkdir()
            (job / "metadata" / "calibration" / "calib.json").write_text(
                json.dumps({"camera": "test"}), encoding="utf-8"
            )
            (job / "metadata" / "poses" / "cameras.json").write_text(
                json.dumps([{"id": 1}]), encoding="utf-8"
            )
        return job

    def run_adapter(self, job: Path, data_root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--job-dir",
                str(job),
                "--scan-id",
                "test-scan",
                "--repo-root",
                str(REPO_ROOT),
                "--data-root",
                str(data_root),
                "--prepare-only",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_prepare_only_stages_all_required_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            job = self.make_job(root)
            data = root / "data"
            result = self.run_adapter(job, data)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((data / "3D_treedata_Denoised_Trees/test-scan.ply").is_file())
            self.assertTrue((data / "3DGS_Park_Model/完整場景/test-scan.ply").is_file())
            scan = data / "3D_treedata/test-scan"
            self.assertTrue((scan / "calibration/calib.json").is_file())
            self.assertTrue((scan / "ray_gaussian/cameras.json").is_file())
            self.assertTrue((scan / "gaussian/camera_left/frame.jpg").is_file())
            status = json.loads((job / "pipeline-status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "prepared")
            self.assertEqual(status["prepared"]["photo_count"], 1)

    def test_missing_metadata_fails_with_actionable_status(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            job = self.make_job(root, with_metadata=False)
            result = self.run_adapter(job, root / "data")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("calib.json", result.stderr)
            status = json.loads((job / "pipeline-status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "error")
            self.assertIn("calib.json", status["message"])

    def test_full_adapter_publishes_report_assets_and_binding(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            job = self.make_job(root)
            fake_repo = root / "repo"
            fake_repo.mkdir()
            runner = fake_repo / "run_full_park_pipeline.py"
            runner.write_text(
                textwrap.dedent(
                    """
                    import argparse, json
                    from pathlib import Path
                    p = argparse.ArgumentParser()
                    p.add_argument("--scan_id")
                    p.add_argument("--output_dir", type=Path)
                    a = p.parse_args()
                    a.output_dir.mkdir(parents=True)
                    photo = a.output_dir / "best.jpg"
                    photo.write_bytes(b"photo")
                    report = {
                        "created_at": "2026-09-22T00:00:00",
                        "scan_id": a.scan_id,
                        "gps_available": False,
                        "num_trees": 1,
                        "trees": [{"Tree_ID": "Tree_001", "Best_Photo": str(photo)}],
                    }
                    (a.output_dir / "park_inventory_report.json").write_text(
                        json.dumps(report), encoding="utf-8"
                    )
                    """
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--job-dir",
                    str(job),
                    "--scan-id",
                    "test-scan",
                    "--path-id",
                    "site:path",
                    "--repo-root",
                    str(fake_repo),
                    "--data-root",
                    str(root / "data"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            public = fake_repo / "app/public/scans/test-scan"
            report = json.loads((public / "inventory.json").read_text(encoding="utf-8"))
            relative_photo = report["trees"][0]["Best_Photo"]
            self.assertEqual(relative_photo, "photos/Tree_001_best.jpg")
            self.assertTrue((public / relative_photo).is_file())
            bindings = json.loads(
                (fake_repo / "app/public/scans/_bindings.json").read_text(encoding="utf-8")
            )
            self.assertEqual(bindings["site:path"], "test-scan")
            source_inventory = fake_repo / "app/src/data/inventories/test-scan.json"
            self.assertTrue(source_inventory.is_file())

    def test_publish_rejects_partial_cross_section_set(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            output = root / "output"
            output.mkdir()
            cross_section = output / "Tree_001.png"
            cross_section.write_bytes(b"png-test")
            report_path = output / "park_inventory_report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "trees": [
                            {
                                "Tree_ID": "Tree_001",
                                "Cross_Section_Image": str(cross_section),
                            },
                            {"Tree_ID": "Tree_002", "Cross_Section_Image": None},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Tree_002"):
                publish_report(
                    report_path,
                    output,
                    root / "repo",
                    root / "data",
                    "test-scan",
                    "",
                )


if __name__ == "__main__":
    unittest.main()
