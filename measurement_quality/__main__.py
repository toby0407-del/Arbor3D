"""Offline calibration from observed, manually paired and explicitly grouped data.

Usage: python -m measurement_quality calibrate evidence.json --out quality-model.json
The output remains disabled until independent accepted-set validation passes.
"""
import argparse
import hashlib
import json
import math
from datetime import date
from pathlib import Path

import numpy as np

from .core import FEATURES, _probability, assess


def sigmoid(x):
    return 1 / (1 + np.exp(-np.clip(x, -40, 40)))


def logistic(x, y):
    w = np.zeros(x.shape[1])
    penalty = np.eye(len(w)) * 0.1
    penalty[0, 0] = 0
    for _ in range(80):
        p = sigmoid(x @ w)
        step = np.linalg.solve(x.T @ ((p * (1 - p))[:, None] * x) + penalty + np.eye(len(w)) * 1e-8,
                               x.T @ (p - y) + penalty @ w)
        w -= step
        if np.max(np.abs(step)) < 1e-7:
            break
    return w


def wilson_lower(successes, total):
    if not total:
        return 0.0
    z = 1.959963984540054
    p = successes / total
    return (p + z*z/(2*total) - z*math.sqrt(p*(1-p)/total + z*z/(4*total*total))) / (1 + z*z/total)


def calibrate(bundle, tolerance_cm=1.0, target=0.95):
    if not 0 < target < 1 or not math.isfinite(tolerance_cm) or tolerance_cm <= 0:
        raise ValueError("Precision target and tolerance must be positive, with target < 1")
    rows = bundle.get("rows", [])
    if not rows:
        raise ValueError("No paired observations. Export quality evidence after recording manual measurements.")
    scope = bundle.get("scope", {})
    if not all(isinstance(scope.get(k), str) and scope[k].strip() for k in ("sensor_id", "protocol_id")):
        raise ValueError("Declare sensor_id and protocol_id in scope; thresholds cannot be universal across equipment")
    groups, observations = {}, set()
    for row in rows:
        if row.get("source") != "observed":
            raise ValueError("Calibration accepts observed data only; simulated data cannot establish accuracy")
        group = row.get("persistent_tree_id")
        split = row.get("split")
        if not group or split not in ("train", "calibration", "test"):
            raise ValueError("Assign a confirmed persistent_tree_id and train/calibration/test split to every row")
        if groups.setdefault(group, split) != split:
            raise ValueError("The same persistent tree crosses dataset splits")
        identity = (row.get("scan_id"), row.get("tree_id"), row.get("method"))
        if identity in observations:
            raise ValueError("Duplicate scan/tree/method observation")
        observations.add(identity)
        if not row.get("scan_date") or row.get("scan_date") != row.get("manual_date") or row.get("strict_13m") is not True:
            raise ValueError("Manual reference must have a matching observation date and verified 1.3 m height")
        date.fromisoformat(row["scan_date"])
        if row.get("method") not in ("circle", "caliper"):
            raise ValueError("Unsupported measurement method")
        for key in ("candidate_dbh_cm", "manual_dbh_cm"):
            val = row.get(key)
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or val <= 0:
                raise ValueError(f"{key} must be a positive finite number")
        f = row.get("features", {})
        if not all(isinstance(f.get(k), (int, float)) and not isinstance(f[k], bool) and math.isfinite(f[k]) for k in FEATURES):
            raise ValueError("All quality features, including actual image width in pixels, are required")
        if not assess(f, row["method"], row.get("context"))["identifiable"]:
            raise ValueError("Only geometrically identifiable, verified observations may train a method model")
        if any(row.get("context", {}).get(k) != v for k, v in scope.items()):
            raise ValueError("Observation context must match the declared sensor/protocol scope")
    test_keys = [(r["persistent_tree_id"], r["method"]) for r in rows if r["split"] == "test"]
    if len(test_keys) != len(set(test_keys)):
        raise ValueError("Independent test requires one preselected observation per tree/method; repeated scans are correlated")
    model = {"schema_version": "arbor3d-quality-1", "feature_names": list(FEATURES),
             "target_probability": target, "tolerance_cm": tolerance_cm,
             "scope": scope,
             "model_id": hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest()[:16],
             "policy_validation": {"passed": True}, "methods": {}}
    for method in ("circle", "caliper"):
        partitions = {s: [r for r in rows if r["method"] == method and r["split"] == s] for s in ("train", "calibration", "test")}
        if not any(partitions.values()):
            continue
        if any(not v for v in partitions.values()):
            raise ValueError(f"{method}: all three independent partitions are required")
        arrays = {s: np.asarray([[r["features"][k] for k in FEATURES] for r in rr]) for s, rr in partitions.items()}
        labels = {s: np.asarray([float(abs(r["candidate_dbh_cm"] - r["manual_dbh_cm"]) <= tolerance_cm) for r in rr]) for s, rr in partitions.items()}
        if any(len(set(labels[s])) < 2 for s in ("train", "calibration")):
            raise ValueError(f"{method}: train and calibration each require both successes and failures")
        mean, scale = arrays["train"].mean(axis=0), arrays["train"].std(axis=0)
        scale[scale < 1e-10] = 1
        design = {s: np.column_stack((np.ones(len(a)), (a - mean) / scale)) for s, a in arrays.items()}
        weights = logistic(design["train"], labels["train"])
        cw = logistic(np.column_stack((np.ones(len(design["calibration"])), design["calibration"] @ weights)), labels["calibration"])
        m = {"mean": mean.tolist(), "scale": scale.tolist(), "weights": weights.tolist(),
             "sigmoid": [float(cw[1]), float(cw[0])],
             "bounds": np.column_stack((arrays["train"].min(axis=0), arrays["train"].max(axis=0))).tolist(),
             "validation": {"passed": True}}
        model["methods"][method] = m
        probabilities = [_probability(r["features"], model, method)[0] for r in partitions["test"]]
        accepted = [i for i, p in enumerate(probabilities) if p is not None and p >= target]
        successes = int(sum(labels["test"][accepted]))
        lower = wilson_lower(successes, len(accepted))
        p_in = [(p, y) for p, y in zip(probabilities, labels["test"]) if p is not None]
        m["validation"] = {"passed": lower >= target, "test_count": len(probabilities),
                           "accepted_count": len(accepted), "successes": successes,
                           "accepted_coverage": len(accepted) / len(probabilities),
                           "wilson_95_lower": lower,
                           "brier_score_in_domain": float(np.mean([(p-y)**2 for p,y in p_in])) if p_in else None,
                           "note": "Locked train/calibration rules; untouched test set. Bounds are data support, not universal minima."}
    # Validate the actual max-probability selection policy, not only each model.
    test_groups = {}
    for row in rows:
        if row["split"] == "test":
            test_groups.setdefault(row["persistent_tree_id"], []).append(row)
    chosen = []
    for group in test_groups.values():
        eligible = []
        for row in group:
            p, _ = _probability(row["features"], model, row["method"])
            if p is not None and p >= target:
                eligible.append((p, row))
        if eligible:
            chosen.append(max(eligible, key=lambda item:item[0])[1])
    successes = sum(abs(r["candidate_dbh_cm"]-r["manual_dbh_cm"]) <= tolerance_cm for r in chosen)
    lower = wilson_lower(successes, len(chosen))
    model["policy_validation"] = {"passed": lower >= target, "test_trees": len(test_groups),
        "accepted_trees": len(chosen), "successes": successes, "wilson_95_lower": lower,
        "coverage": len(chosen)/len(test_groups) if test_groups else 0,
        "selection_rule": "maximum calibrated probability among identifiable eligible methods"}
    return model


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["calibrate"])
    p.add_argument("input", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--tolerance-cm", type=float, default=1)
    p.add_argument("--target", type=float, default=0.95)
    args = p.parse_args()
    try:
        model = calibrate(json.loads(args.input.read_text(encoding="utf-8-sig")), args.tolerance_cm, args.target)
    except (ValueError, TypeError, KeyError) as exc:
        p.error(str(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(model, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({k: m["validation"] for k, m in model["methods"].items()}, indent=2))


if __name__ == "__main__":
    main()
