import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from cloud_dbh import app as api
from cloud_dbh.worker import JobPaths, write_status


class CloudApiTests(unittest.TestCase):
    def test_jobs_and_results_require_authentication(self):
        with patch.object(api, "API_KEY", "test-only-key"), TestClient(api.app) as client:
            self.assertEqual(client.get("/health").status_code, 200)
            self.assertEqual(client.get("/v1/capabilities").status_code, 401)
            self.assertEqual(client.get("/v1/jobs/" + "a" * 32).status_code, 401)
            self.assertEqual(client.get("/v1/capabilities", headers={"X-API-Key": "test-only-key"}).status_code, 200)

    def test_full_job_is_rejected_before_upload_if_dependencies_are_missing(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(api, "WORK_DIR", Path(temporary)), \
             patch.object(api, "API_KEY", "test-only-key"), patch.object(api, "PREPARE_ONLY_DEFAULT", False), \
             patch.object(api, "capabilities", return_value={"full_pipeline_ready": False}), TestClient(api.app) as client:
            response = client.post("/v1/jobs", headers={"X-API-Key": "test-only-key"},
                data={"scan_id": "cloud-test"}, files={"archive": ("input.zip", io.BytesIO(b"test fixture"), "application/zip")})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_prepared_status_cannot_download_as_full_result(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(api, "WORK_DIR", Path(temporary)), \
             patch.object(api, "API_KEY", "test-only-key"), TestClient(api.app) as client:
            job_id = "a" * 32
            paths = JobPaths.create(job_id, Path(temporary))
            (paths.root / "result.zip").write_bytes(b"test fixture")
            write_status(paths, "prepared", "prepared only", prepare_only=True)
            headers = {"X-API-Key": "test-only-key"}
            self.assertEqual(client.get(f"/v1/jobs/{job_id}/result", headers=headers).status_code, 409)
            self.assertEqual(client.get("/v1/jobs/invalid-id", headers=headers).status_code, 404)


if __name__ == "__main__":
    unittest.main()
