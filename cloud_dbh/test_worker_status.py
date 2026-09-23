"""Lightweight status helpers for Cloud DBH (no FastAPI required)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cloud_dbh.worker import JobPaths, write_status, read_status


class WorkerStatusTest(unittest.TestCase):
    def test_status_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = JobPaths.create("job-test", Path(tmp))
            write_status(paths, "queued", "waiting", scan_id="s1")
            payload = read_status(paths)
            assert payload is not None
            self.assertEqual(payload["status"], "queued")
            self.assertEqual(payload["scan_id"], "s1")
            self.assertEqual(payload["job_id"], "job-test")


if __name__ == "__main__":
    unittest.main()
