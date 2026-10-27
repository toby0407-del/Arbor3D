"""Method-specific quality gates; diagnostic candidates are never formal DBH by default."""
import numpy as np
import geo_utils as utils

from measurement_quality import assess, section_features
from . import config
from .caliper import build_caliper_result
from .fitting import fit_dbh
from .result import DBHResult

__all__ = ["DBHResult", "estimate_dbh"]


def estimate_dbh(slice_pts, camera_xy=None, quality_context=None, quality_model=None) -> DBHResult:
    context = dict(quality_context or {})
    if camera_xy is None:
        context["view_direction_verified"] = False
    xc, yc, r, inlier_count = fit_dbh(slice_pts)
    circle = None
    if r is not None and np.isfinite([xc, yc, r]).all() and r > 0:
        pts = slice_pts[:, :2]
        mask = utils.circle_inlier_mask(pts, xc, yc, r, tolerance=config.RANSAC_DIST_THRESHOLD)
        arc = utils.arc_coverage_deg(pts[mask], xc, yc) if mask.sum() >= 3 else 0
        circle = DBHResult(method="circle", dbh_m=2*r, arc_deg=arc,
                           xc=xc, yc=yc, r=r, inlier_count=inlier_count,
                           inlier_ratio=float(mask.sum()) / len(pts))
    caliper = build_caliper_result(slice_pts, circle.arc_deg if circle else None,
                                   ref_xc=xc if circle else None, ref_yc=yc if circle else None,
                                   ref_r=r if circle else None, camera_xy=camera_xy)
    features = section_features(slice_pts, (xc, yc) if circle else None, r if circle else None,
                                trunk_width_px=context.get("trunk_width_px"))
    candidates = [c for c in (circle, caliper) if c is not None]
    for c in candidates:
        c.quality = assess(features, c.method, context, quality_model)
        if not config.DBH_MIN_M <= c.dbh_m <= config.DBH_MAX_M:
            c.quality["reasons"].append("candidate_outside_size_range")
        if c.gap_detected:
            c.quality["reasons"].append("disconnected_section")
        if c.quality["reasons"]:
            c.quality["decision"] = "review"
        if "candidate_outside_size_range" in c.quality["reasons"] or c.gap_detected:
            c.quality["identifiable"] = False
    accepted = [c for c in candidates if c.quality["decision"] == "accepted"]
    # Select only among eligible methods; confidence/angle cannot bypass the gate.
    if accepted:
        result = max(accepted, key=lambda c: c.quality["probability"])
    else:
        result = circle if circle and circle.quality["identifiable"] else caliper
    result.quality_candidates = [{"method": c.method, "candidate_dbh_cm": round(c.dbh_m*100, 3), **c.quality} for c in candidates]
    print("   品質決策：", result.quality["decision"], ", ".join(result.quality["reasons"]))
    return result
