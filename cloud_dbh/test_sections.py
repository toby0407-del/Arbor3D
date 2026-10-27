import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient
from cloud_dbh import app as api
from cloud_dbh.section_compute import compute_section


class SectionTests(unittest.TestCase):
    def sample(self):
        a = np.linspace(0, 2*np.pi, 80, endpoint=False)
        return {"scan_id": "unit-test", "tree_id": "test-only", "units": "m",
                "context": {"scale_verified": True, "pose_verified": True, "breast_height_verified": True},
                "points": np.column_stack([.2*np.cos(a), .2*np.sin(a), np.full(80,1.3)]).tolist()}

    def test_actual_geometry_runs_but_does_not_invent_calibration(self):
        payload = self.sample()
        raw = json.dumps(payload).encode()
        result = compute_section(payload, raw)
        self.assertAlmostEqual(result["result"]["dbh_m"], .4, places=3)
        self.assertEqual(result["result"]["quality"]["decision"], "review")
        self.assertIsNone(result["result"]["quality"]["probability"])
        self.assertEqual(result["execution"]["input_sha256"], hashlib.sha256(raw).hexdigest())

    def test_api_requires_key_and_rejects_wrong_units(self):
        with patch.object(api, "API_KEY", "test-only-key"), TestClient(api.app) as client:
            payload = self.sample()
            self.assertEqual(client.post("/v1/sections", json=payload).status_code, 401)
            payload["units"] = "cm"
            self.assertEqual(client.post("/v1/sections", json=payload, headers={"X-API-Key":"test-only-key"}).status_code,400)


if __name__ == "__main__":
    unittest.main()
