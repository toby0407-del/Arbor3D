"""Geometry diagnostics, calibrated acceptance and operator-only rescan suggestions.

Distances are metres, angles degrees, image widths pixels. The small numerical
guards below are identifiability checks, not empirically established accuracy bounds.
"""
import math
import numpy as np

FEATURES = ("effective_points", "occupied_fraction", "max_gap_deg", "residual_m", "condition_number", "trunk_width_px")


def section_features(points, center, radius, trunk_width_px=None, voxel_m=0.002):
    p = np.asarray(points, dtype=float)
    if p.ndim != 2 or p.shape[1] < 2 or not np.isfinite(p).all():
        raise ValueError("Section points must be finite Nx2 or Nx3 coordinates in metres")
    if not math.isfinite(voxel_m) or voxel_m <= 0:
        raise ValueError("voxel_m must be positive")
    # Repeated returns at the same location cannot inflate independent support.
    p = np.unique(np.floor(p[:, :2] / voxel_m).astype(np.int64), axis=0) * voxel_m
    result = {"effective_points": len(p), "voxel_m": voxel_m,
              "trunk_width_px": trunk_width_px, "occupied_fraction": None,
              "max_gap_deg": None, "residual_m": None, "condition_number": None,
              "missing_azimuth_deg": None}
    if len(p) < 3 or center is None or radius is None or not np.isfinite([*center, radius]).all() or radius <= 0:
        return result
    v = p - np.asarray(center)
    d = np.linalg.norm(v, axis=1)
    theta = np.mod(np.degrees(np.arctan2(v[:, 1], v[:, 0])), 360)
    bins = np.unique((theta / 5).astype(int))
    angles = np.sort(theta)
    gaps = np.diff(np.r_[angles, angles[0] + 360])
    idx = int(np.argmax(gaps))
    # Local circle parameter Jacobian; low residual alone is insufficient.
    jac = np.column_stack((-v / np.maximum(d[:, None], 1e-12), -np.ones(len(p))))
    condition = float(np.linalg.cond(jac))
    result.update(occupied_fraction=len(bins) / 72, max_gap_deg=float(gaps[idx]),
                  residual_m=float(np.sqrt(np.mean((d - radius) ** 2))),
                  condition_number=condition if math.isfinite(condition) else None,
                  missing_azimuth_deg=float((angles[idx] + gaps[idx] / 2) % 360))
    return result


def _probability(features, model, method):
    """Fail closed on missing, out-of-domain or unverified model artifacts."""
    if not isinstance(model, dict) or model.get("schema_version") != "arbor3d-quality-1":
        return None, "missing_calibration"
    if not isinstance(model.get("model_id"), str) or not model["model_id"].strip():
        return None, "invalid_calibration"
    epsilon = model.get("tolerance_cm")
    if isinstance(epsilon, bool) or not isinstance(epsilon, (int, float)) or not math.isfinite(epsilon) or epsilon <= 0:
        return None, "invalid_calibration"
    if not isinstance(model.get("methods"), dict):
        return None, "invalid_calibration"
    m = model.get("methods", {}).get(method)
    if not isinstance(m, dict) or m.get("validation", {}).get("passed") is not True or model.get("policy_validation", {}).get("passed") is not True:
        return None, "independent_validation_required"
    try:
        if model["feature_names"] != list(FEATURES):
            return None, "feature_schema_mismatch"
        x = np.asarray([features[k] for k in FEATURES], dtype=float)
        bounds = np.asarray(m["bounds"], dtype=float)
        if not np.isfinite(x).all() or bounds.shape != (len(FEATURES), 2):
            return None, "missing_features"
        if np.any(x < bounds[:, 0]) or np.any(x > bounds[:, 1]):
            return None, "outside_calibration_domain"
        mean, scale = np.asarray(m["mean"]), np.asarray(m["scale"])
        weights = np.asarray(m["weights"])
        if mean.shape != x.shape or scale.shape != x.shape or weights.shape != (len(x) + 1,) or np.any(scale <= 0):
            return None, "invalid_calibration"
        z = float(np.r_[1, (x - mean) / scale] @ weights)
        a, b = m["sigmoid"]
        logit = float(a * z + b)
        if not math.isfinite(logit):
            return None, "invalid_calibration"
        return 1 / (1 + math.exp(-max(-700, min(700, logit)))), None
    except (KeyError, TypeError, ValueError, OverflowError):
        return None, "invalid_calibration"


def assess(features, method, context=None, model=None):
    context = context if isinstance(context, dict) else {}
    model = model if isinstance(model, dict) else None
    reasons = []
    if model and (not isinstance(model.get("scope"), dict) or not model["scope"] or any(context.get(k) != v for k, v in model["scope"].items())):
        reasons.append("calibration_scope_mismatch")
    for flag in ("scale_verified", "pose_verified", "breast_height_verified"):
        if context.get(flag) is not True:
            reasons.append(flag + "_required")
    n, condition = features.get("effective_points", 0), features.get("condition_number")
    if n < 3:
        reasons.append("insufficient_geometry")
    if method == "circle":
        if condition is None or not math.isfinite(condition) or condition > 1e4:
            reasons.append("unstable_circle_geometry")
    elif method == "caliper":
        for flag in ("view_direction_verified", "left_boundary_visible", "right_boundary_visible", "near_circular_verified"):
            if context.get(flag) is not True:
                reasons.append(flag + "_required")
        if context.get("cropped") is not False:
            reasons.append("uncropped_boundaries_required")
    else:
        reasons.append("unsupported_method")
    probability, calibration_reason = _probability(features, model, method)
    if calibration_reason:
        reasons.append(calibration_reason)
    # Precision is a target selected before validation, never YOLO confidence.
    target = model.get("target_probability", 0.95) if model else 0.95
    if not isinstance(target, (int, float)) or not 0 < target < 1:
        reasons.append("invalid_target")
        target = 0.95
    if probability is not None and probability < target:
        reasons.append("precision_target_not_met")
    return {"schema_version": "arbor3d-quality-1", "method": method,
            "decision": "accepted" if not reasons else "review",
            "identifiable": not any(r not in ("missing_calibration", "independent_validation_required", "precision_target_not_met", "outside_calibration_domain", "missing_features") for r in reasons),
            "probability": probability, "target_probability": target,
            "tolerance_cm": model.get("tolerance_cm") if model else None,
            "model_id": model.get("model_id") if model else None,
            "reasons": reasons, "features": features, "context": context}


def suggest_views(candidates, current_probability=None):
    """Only explicitly verified reachable candidates may be ranked. No flight commands."""
    safe = []
    for c in candidates:
        if c.get("safe") is not True or c.get("reachable") is not True:
            continue
        angle, gain, seconds = c.get("azimuth_deg"), c.get("new_coverage_deg"), c.get("time_s")
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in (angle, gain, seconds)):
            continue
        if not 0 <= angle < 360 or not 0 < gain <= 360 or seconds <= 0:
            continue
        safe.append({**c, "score": gain / seconds, "score_kind": "coverage_proxy", "precision_gain": None})
    safe.sort(key=lambda c: (-c["score"], c["azimuth_deg"]))
    return {"decision": "suggest" if safe else "manual_review", "candidates": safe,
            "advisory_only": True, "notice": "Coverage proxy only; no calibrated precision gain or autonomous flight."}
