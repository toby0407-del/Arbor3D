"""Send only the extracted section to Azure; raw scans and YOLO stay local."""
import hashlib
import json
import os
import urllib.request
from urllib.parse import urlsplit

import numpy as np
from .result import DBHResult


def estimate_section_cloud(points, *, scan_id, tree_id, camera_xy=None, context=None, model=None):
    endpoint = os.environ["ARBOR3D_SECTION_CLOUD_URL"].rstrip("/")
    url = urlsplit(endpoint)
    local = url.hostname in {"localhost", "127.0.0.1", "::1"}
    key = os.environ.get("ARBOR3D_CLOUD_DBH_API_KEY", "")
    if url.username or url.password or url.query or url.fragment or (not local and (url.scheme != "https" or not key)):
        raise ValueError("Section cloud endpoint requires HTTPS and server-side authentication")
    body = {"scan_id": scan_id, "tree_id": tree_id, "units": "m", "points": np.asarray(points).tolist(),
            "camera_xy": np.asarray(camera_xy).tolist() if camera_xy is not None else None, "context": context or {}}
    raw = json.dumps(body, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(endpoint + "/v1/sections", data=raw, method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": key})
    with urllib.request.urlopen(request, timeout=60) as response:
        reply = json.loads(response.read(2 * 1024 * 1024))
    execution = reply.get("execution", {})
    if reply.get("scan_id") != scan_id or reply.get("tree_id") != tree_id or execution.get("input_sha256") != hashlib.sha256(raw).hexdigest() or execution.get("stage") != "section_geometry":
        raise ValueError("Cloud section result does not match the submitted evidence")
    if not local and execution.get("platform") != "azure-app-service":
        raise ValueError("Remote service did not identify an Azure executor")
    values = reply["result"]
    if model and values.get("quality", {}).get("model_id") != model.get("model_id"):
        raise ValueError("Cloud calibration model does not match the local model")
    for name in ("caliper_p1", "caliper_p2", "caliper_kept_mask"):
        if values.get(name) is not None:
            values[name] = np.asarray(values[name])
    result = DBHResult(**values)
    result.execution = execution
    return result
