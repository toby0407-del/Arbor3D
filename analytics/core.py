"""Versioned analytics contract. Never infers persistent identity from local Tree_ID."""
from __future__ import annotations
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

VERSION = "1.1"
FIELDS = {
    "DimTree": ["tree_key", "site_id", "persistent_tree_id", "identity_status"],
    "DimScan": ["scan_key", "site_id", "scan_id", "observed_at", "source_file", "source_sha256"],
    "FactObservation": ["observation_key", "tree_key", "scan_key", "local_tree_id", "observed_at", "auto_dbh_cm", "auto_source", "auto_method", "strict_13m", "manual_dbh_cm", "manual_source", "manual_measured_at", "manual_height_m", "manual_strict_13m", "comparison_status", "error_cm", "absolute_error_cm", "squared_error_cm2", "ape_pct", "yolo_confidence", "arc_coverage_deg", "review_required", "review_reason"],
    "FactEstimate": ["observation_key", "tree_key", "scan_key", "dbh_input_cm", "dbh_input_source", "height_m", "height_source", "coefficient", "carbon_d", "co2_equivalent_ton", "source", "formula_version"],
    "FactGrowth": ["tree_key", "from_scan_key", "to_scan_key", "from_observation_key", "to_observation_key", "from_date", "to_date", "source", "method", "days", "delta_dbh_cm", "annualized_delta_cm", "negative_change"],
    "Summary": ["scope", "observations", "paired_count", "mae_cm", "rmse_cm", "bias_cm", "mape_pct", "review_count"],
}
for _fields in FIELDS.values():
    _fields.append("dataset_kind")

def key(*parts):
    return json.dumps(parts, ensure_ascii=False, separators=(",", ":"))

def number(value, name, minimum=0, maximum=None, allow_zero=False):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{name}: boolean is not a measurement")
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name}: expected a number") from None
    if not math.isfinite(n) or n < minimum or (not allow_zero and n == minimum) or (maximum is not None and n > maximum):
        raise ValueError(f"{name}: invalid value {value!r}")
    return n

def identifier(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: nonempty string required")
    return value.strip()

def day(value):
    # Existing reports use local ISO without an offset. Preserve the recorded calendar day.
    if not isinstance(value, str) or not value.strip():
        raise ValueError("measurement date required")
    return datetime.fromisoformat(value.replace("Z", "+00:00").replace("/", "-")).date().isoformat()

def boolean(value):
    if value is True or value == "true":
        return True
    if value is False or value == "false" or value is None or value == "":
        return False
    raise ValueError(f"expected true/false, got {value!r}")

def load_csv(path):
    if path is None:
        return []
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def index_rows(rows, label):
    result = {}
    for row in rows:
        k = tuple(identifier(row.get(n), n) for n in ("site_id", "scan_id", "local_tree_id"))
        if k in result:
            raise ValueError(f"duplicate {label}: {k}")
        result[k] = row
    return result

def build(reports, manual_rows=(), identity_rows=(), max_pair_days=0, *, allow_simulated=False):
    """reports: [(site_id, source_path, report_dict)]. Default pairs only same-day strict DBH."""
    if max_pair_days < 0:
        raise ValueError("max_pair_days must be nonnegative")
    reports = list(reports)
    kinds = {r.get("dataset_kind", "observed") for _, _, r in reports}
    if not kinds or not kinds <= {"observed", "simulated"} or len(kinds) != 1:
        raise ValueError("Use one dataset kind per snapshot; never mix observed and simulated reports")
    dataset_kind = kinds.pop()
    if dataset_kind == "simulated" and not allow_simulated:
        raise ValueError("Simulated reports require explicit allow_simulated; not field evidence")
    manual = index_rows(manual_rows, "manual observation")
    identities = index_rows(identity_rows, "identity mapping")
    tables = {name: [] for name in FIELDS}
    trees, seen_scans, seen_obs, persistent_scan = {}, set(), set(), set()
    for site, path, report in reports:
        site = identifier(site, "site_id")
        scan = identifier(report.get("scan_id"), "scan_id")
        date = day(report.get("created_at"))
        sk = key(site, scan)
        if sk in seen_scans:
            raise ValueError(f"duplicate scan: {sk}")
        seen_scans.add(sk)
        records = report.get("trees")
        if not isinstance(records, list) or report.get("num_trees", len(records)) != len(records):
            raise ValueError("trees must be a list matching num_trees")
        source_bytes = Path(path).read_bytes() if Path(path).is_file() else json.dumps(report, sort_keys=True).encode()
        tables["DimScan"].append(dict(zip(FIELDS["DimScan"], [sk, site, scan, date, str(path), hashlib.sha256(source_bytes).hexdigest()])))
        for tree in records:
            local = identifier(tree.get("Tree_ID"), "Tree_ID")
            natural = (site, scan, local)
            if natural in seen_obs:
                raise ValueError(f"duplicate tree in scan: {natural}")
            seen_obs.add(natural)
            identity = identities.get(natural)
            persistent = identifier(identity.get("persistent_tree_id"), "persistent_tree_id") if identity else None
            if identity and not boolean(identity.get("confirmed")):
                raise ValueError(f"identity not confirmed: {natural}")
            tk = key(site, "persistent", persistent) if persistent else key(site, "unresolved", scan, local)
            if (sk, tk) in persistent_scan:
                raise ValueError("two local trees map to one persistent tree in a scan")
            persistent_scan.add((sk, tk))
            trees[tk] = dict(zip(FIELDS["DimTree"], [tk, site, persistent, "confirmed" if persistent else "unresolved"]))
            auto = number(tree.get("DBH_cm"), "DBH_cm")
            strict = boolean(tree.get("dbh_is_strict_breast_height"))
            m = manual.get(natural, {})
            md = number(m.get("manual_dbh_cm"), "manual_dbh_cm")
            mh = number(m.get("manual_height_m"), "manual_height_m")
            mdate = day(m.get("measured_at")) if md is not None or mh is not None else None
            ms = boolean(m.get("strict_13m"))
            if md is None:
                status = "missing_manual"
            elif auto is None:
                status = "missing_auto"
            elif not strict or not ms:
                status = "nonstandard_height"
            elif abs((datetime.fromisoformat(date) - datetime.fromisoformat(mdate)).days) > max_pair_days:
                status = "date_mismatch"
            else:
                status = "paired"
            err = auto - md if status == "paired" else None
            reason = [r for r in (tree.get("DBH_note") or "").split(",") if r and r != "ok"]
            if not strict:
                reason.append("not_1.3m")
            if auto is None:
                reason.append("no_measurement")
            if tree.get("DBH_method") == "caliper" and auto is not None and auto >= 45:
                reason.append("wide_caliper")
            row = dict(zip(FIELDS["FactObservation"], [key(*natural), tk, sk, local, date, auto, "ai" if auto is not None else "missing", tree.get("DBH_method") or "unknown", strict, md, "measured" if md is not None else "missing", mdate, mh, ms, status, err, abs(err) if err is not None else None, err**2 if err is not None else None, abs(err)/md*100 if err is not None else None, number(tree.get("YOLO_confidence"), "confidence", maximum=1, allow_zero=True), number(tree.get("arc_coverage_deg"), "arc", maximum=360, allow_zero=True), bool(reason), ",".join(sorted(set(reason)))]))
            tables["FactObservation"].append(row)
            dbh = md if md is not None else auto
            height_auto = number(tree.get("Height_m"), "Height_m")
            height = mh if mh is not None else height_auto
            height_source = "measured" if mh is not None else "ai" if height_auto is not None else "estimated"
            if height is None and dbh is not None:
                height = max(3.5, min(22, 1.3 + 1.8 * math.sqrt(dbh)))
            coefficient = number(m.get("carbon_coefficient"), "carbon_coefficient") or 0.0159
            carbon = (math.pi * dbh / 100)**2 * height * coefficient if dbh is not None and height is not None else None
            tables["FactEstimate"].append(dict(zip(FIELDS["FactEstimate"], [row["observation_key"], tk, sk, dbh, "measured" if md is not None else "ai" if auto is not None else "missing", height, height_source if height is not None else "missing", coefficient, carbon, carbon * 3.667 if carbon is not None else None, "estimated", "arbor-worksheet-v1"])))
    for label, supplied in (("manual", manual), ("identity", identities)):
        if set(supplied) - seen_obs:
            raise ValueError(f"unmatched {label} rows: {sorted(set(supplied) - seen_obs)}")
    tables["DimTree"] = list(trees.values())
    # Same-source, same-method, strict-height, confirmed identities only. No interpolation.
    groups = defaultdict(list)
    for row in tables["FactObservation"]:
        if trees[row["tree_key"]]["identity_status"] != "confirmed":
            continue
        if row["auto_dbh_cm"] is not None and row["strict_13m"]:
            groups[(row["tree_key"], "ai", row["auto_method"])].append((row["observed_at"], row["auto_dbh_cm"], row))
        if row["manual_dbh_cm"] is not None and row["manual_strict_13m"]:
            groups[(row["tree_key"], "measured", "manual")].append((row["manual_measured_at"], row["manual_dbh_cm"], row))
    for (tk, source, method), obs in sorted(groups.items()):
        obs.sort(key=lambda x: (x[0], x[2]["scan_key"]))
        dates = [o[0] for o in obs]
        if len(dates) != len(set(dates)):
            raise ValueError(f"ambiguous same-day temporal records: {tk}, {source}")
        for a, b in zip(obs, obs[1:]):
            days = (datetime.fromisoformat(b[0]) - datetime.fromisoformat(a[0])).days
            delta = b[1] - a[1]
            tables["FactGrowth"].append(dict(zip(FIELDS["FactGrowth"], [tk, a[2]["scan_key"], b[2]["scan_key"], a[2]["observation_key"], b[2]["observation_key"], a[0], b[0], source, method, days, delta, delta / days * 365.25, delta < 0])))
    for scope, rows in [("all", tables["FactObservation"])] + [(sk, [r for r in tables["FactObservation"] if r["scan_key"] == sk]) for sk in sorted(seen_scans)]:
        pairs = [r for r in rows if r["comparison_status"] == "paired"]
        n = len(pairs)
        avg = lambda field: sum(r[field] for r in pairs)/n if n else None
        tables["Summary"].append(dict(zip(FIELDS["Summary"], [scope, len(rows), n, avg("absolute_error_cm"), math.sqrt(avg("squared_error_cm2")) if n else None, avg("error_cm"), avg("ape_pct"), sum(r["review_required"] for r in rows)])))
    for rows in tables.values():
        for row in rows:
            row["dataset_kind"] = dataset_kind
            if dataset_kind == "simulated":
                for field in ("auto_source", "manual_source", "dbh_input_source", "height_source", "source"):
                    if row.get(field) in ("ai", "measured", "estimated"):
                        row[field] = "simulated_" + row[field]
                if row.get("identity_status") == "confirmed":
                    row["identity_status"] = "simulated"
    return tables

def csv_safe(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value

def export(tables, out, max_pair_days=0):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for name, fields in FIELDS.items():
        with (out / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fields)
            writer.writeheader()
            writer.writerows({k: csv_safe(v) for k, v in row.items()} for row in tables[name])
    (out / "analytics.json").write_text(json.dumps({"schema_version": VERSION, "tables": tables}, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    manifest = {"schema_version": VERSION, "pair_max_days": max_pair_days, "counts": {k: len(v) for k, v in tables.items()}, "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*.csv"))}, "notes": ["No manual values are fabricated.", "No inferred identity or simulated growth enters FactGrowth.", "CSV formula-like text escaped with apostrophe; JSON retains original identifiers."]}
    manifest["dataset_kind"] = tables["Summary"][0]["dataset_kind"]
    if manifest["dataset_kind"] == "simulated":
        manifest["notes"] = ["SIMULATED DEMO ONLY: all dates, identities, measurements and growth are synthetic.", "Error metrics measure injected simulation noise, not real model accuracy.", "Do not combine with observed snapshots or claim field validation."]
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
