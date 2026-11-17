"""Evidence based rescan regions. Local XY degrees are not compass bearings.

Minimisation is over missing 5-degree surface bins, not a claimed precision gain
or a flight path. Actual measurements must be assessed again after acquisition.
"""
import base64
import html
import json
import math
import sqlite3
from contextlib import closing
from pathlib import Path

import numpy as np


def build_rescan_plan(points, center, radius, quality, strict_breast_height=True):
    quality = quality or {}
    reasons = list(quality.get("reasons") or [])
    plan = dict(schema_version="arbor3d-rescan-2", required=True,
                status="manual_review", reasons=reasons, sectors=[],
                coordinate_frame="local_xy_ccw_from_positive_x",
                bin_deg=5, minimum_scope_deg=None, next_view_local_deg=None,
                precision_guaranteed=False, safety_status="unverified",
                policy="missing_surface_bins", overlay_available=False)
    probability, target = quality.get("probability"), quality.get("target_probability")
    accepted = (quality.get("schema_version") == "arbor3d-quality-1"
                and quality.get("decision") == "accepted" and quality.get("identifiable") is True
                and quality.get("method") in ("circle", "caliper") and not reasons
                and bool(quality.get("model_id"))
                and isinstance(probability, (int, float)) and math.isfinite(probability)
                and isinstance(target, (int, float)) and 0 < target < 1 and target <= probability <= 1
                and isinstance(quality.get("tolerance_cm"), (int, float)) and quality["tolerance_cm"] > 0)
    if accepted and strict_breast_height:
        return {**plan, "required": False, "status": "complete"}
    if not strict_breast_height:
        plan["reasons"] = list(dict.fromkeys(reasons + ["breast_height_verified_required"]))
        return plan
    p = np.asarray(points, dtype=float)
    # An unstable centre must never be converted into a confident angular region.
    if (quality.get("identifiable") is not True or center is None or radius is None
            or not np.isfinite([*center, radius]).all() or radius <= 0
            or p.ndim != 2 or p.shape[1] < 2 or len(p) < 3 or not np.isfinite(p).all()):
        return plan
    d = np.linalg.norm(p[:, :2] - np.asarray(center), axis=1)
    # Exclude off-surface objects; this tolerance is a fitting support diagnostic.
    support = p[np.abs(d - radius) <= max(.01, radius * .05), :2]
    if len(support) < 3:
        return plan
    a = np.mod(np.degrees(np.arctan2(support[:, 1]-center[1], support[:, 0]-center[0])), 360)
    occupied = set(np.minimum((a / 5).astype(int), 71).tolist())
    missing = set(range(72)) - occupied
    plan.update(occupied_bins=sorted(occupied), center_xy_m=list(map(float, center)), radius_m=float(radius))
    if not missing:
        # Calibration, scale, density or 2D issues cannot be cured by inventing a gap.
        return plan
    sectors = []
    starts = [i for i in sorted(missing) if (i-1) % 72 not in missing]
    for start in starts:
        n = 1
        while (start+n) % 72 in missing and n < 72:
            n += 1
        sectors.append(dict(start_deg=start*5, span_deg=n*5,
                            end_deg=((start+n)*5) % 360,
                            view_local_deg=(start*5+n*2.5) % 360))
    sectors.sort(key=lambda s: (-s["span_deg"], s["start_deg"]))
    plan.update(status="pending_safety_check", sectors=sectors,
                minimum_scope_deg=len(missing)*5, next_view_local_deg=sectors[0]["view_local_deg"],
                target="complete_surface_coverage_at_5deg_resolution")
    return plan


def write_overlay(image_path, plan):
    """Embed the unchanged original image and register sectors through plot axes."""
    image_path = Path(image_path)
    metadata = image_path.with_suffix(".plot.json")
    if not plan.get("sectors") or not image_path.is_file() or not metadata.is_file():
        return None
    m = json.loads(metadata.read_text(encoding="utf-8"))
    width, height = m["size_px"]
    left, top, w, h = m["axes_px"]
    xmin, xmax = m["xlim"]
    ymin, ymax = m["ylim"]
    def pixel(x, y):
        return left+(x-xmin)/(xmax-xmin)*w, top+(ymax-y)/(ymax-ymin)*h
    cx, cy = plan["center_xy_m"]
    r = plan["radius_m"]
    paths = []
    for index, sector in enumerate(plan["sectors"]):
        angles = np.radians(np.linspace(sector["start_deg"], sector["start_deg"]+sector["span_deg"], max(3, int(sector["span_deg"])+1)))
        xy = [pixel(cx+r*factor*math.cos(t), cy+r*factor*math.sin(t))
              for factor, seq in ((.88, angles), (.98, angles[::-1])) for t in seq]
        path = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in xy) + " Z"
        paths.append(f'<path d="{path}" fill="#f59e0b" fill-opacity=".48" stroke="#b45309" stroke-width="2"><title>Region {index+1}: {sector["start_deg"]} deg + {sector["span_deg"]} deg</title></path>')
    raw = base64.b64encode(image_path.read_bytes()).decode("ascii")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">'
           f'<title>{html.escape(image_path.stem)} rescan regions, local XY</title>'
           f'<image width="{width}" height="{height}" href="data:image/png;base64,{raw}"/>'
           f'<defs><clipPath id="plot"><rect x="{left}" y="{top}" width="{w}" height="{h}"/></clipPath></defs>'
           f'<g clip-path="url(#plot)">{"".join(paths)}</g></svg>')
    target = image_path.with_name(image_path.stem + "_rescan.svg")
    target.write_text(svg, encoding="utf-8")
    plan["overlay_available"] = True
    return str(target)


def save_task(db_path, scan_id, tree_id, plan, timestamp):
    """One current task per scan/tree; reruns replace, never inflate counts."""
    with closing(sqlite3.connect(db_path)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS rescan_tasks (scan_id TEXT, tree_id TEXT, required INTEGER, status TEXT, updated_at TEXT, plan_json TEXT, PRIMARY KEY(scan_id, tree_id))")
        db.execute("INSERT OR REPLACE INTO rescan_tasks VALUES (?, ?, ?, ?, ?, ?)",
                   (scan_id, tree_id or "single-tree", int(plan["required"]), plan["status"], timestamp,
                    json.dumps(plan, ensure_ascii=False, allow_nan=False)))
