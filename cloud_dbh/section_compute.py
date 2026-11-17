"""Small NumPy-only geometry work suitable for the existing Azure free service."""
import contextlib
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import io
import json
import os
import uuid

import numpy as np
from dbh_seg.dbh_estimate import estimate_dbh
from cloud_dbh.archives import safe_id


def compute_section(payload: dict, raw: bytes) -> dict:
    scan_id = safe_id(payload.get("scan_id", ""))
    tree_id = safe_id(payload.get("tree_id", ""))
    if payload.get("units") != "m":
        raise ValueError("Section coordinates must use metres")
    points = np.asarray(payload.get("points"), dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not 3 <= len(points) <= 5000 or not np.isfinite(points).all():
        raise ValueError("Expected 3 to 5000 finite XYZ section points")
    camera = payload.get("camera_xy")
    if camera is not None:
        camera = np.asarray(camera, dtype=float)
        if camera.shape != (2,) or not np.isfinite(camera).all():
            raise ValueError("Camera position must be a finite XY pair")
    context = payload.get("context") or {}
    if not isinstance(context, dict) or len(json.dumps(context)) > 8192:
        raise ValueError("Invalid quality context")
    model = None
    if os.environ.get("ARBOR3D_QUALITY_MODEL"):
        with open(os.environ["ARBOR3D_QUALITY_MODEL"], encoding="utf-8") as source:
            model = json.load(source)
    # Use the same circle/caliper implementation as the local pipeline.
    with contextlib.redirect_stdout(io.StringIO()):
        result = estimate_dbh(points, camera_xy=camera, quality_context=context, quality_model=model)
    def primitive(value):
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(type(value).__name__)
    encoded = json.dumps(asdict(result), default=primitive, allow_nan=False)
    return {"scan_id": scan_id, "tree_id": tree_id, "result": json.loads(encoded),
            "execution": {"id": uuid.uuid4().hex, "platform": "azure-app-service" if os.getenv("WEBSITE_SITE_NAME") else "local-api",
                          "stage": "section_geometry", "point_count": len(points), "input_sha256": hashlib.sha256(raw).hexdigest(),
                          "completed_at": datetime.now(timezone.utc).isoformat()}}
