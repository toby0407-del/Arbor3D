"""Seeded quarterly DEMO data, kept separate from real inventory evidence."""
import argparse
import csv
import hashlib
import json
import math
import random
from datetime import date
from pathlib import Path

from .core import build, export


def generate(template, output, *, quarters=16, end="2026-06-30", seed=42):
    if not 2 <= quarters <= 80:
        raise ValueError("quarters must be between 2 and 80")
    end_date = date.fromisoformat(end)
    if (end_date.month, end_date.day) not in ((3, 31), (6, 30), (9, 30), (12, 31)):
        raise ValueError("end must be a calendar quarter-end")
    template, output = Path(template), Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose a new empty output folder; never overwrite field data or reports")
    original = json.loads(template.read_text(encoding="utf-8"))
    trees = original["trees"]
    if not trees:
        raise ValueError("Template has no trees")
    quarter_index = end_date.year * 4 + (end_date.month // 3 - 1)
    dates = []
    for index in range(quarter_index - quarters + 1, quarter_index + 1):
        year, quarter = divmod(index, 4)
        dates.append(date(year, (quarter + 1) * 3, (31, 30, 30, 31)[quarter]))
    rng = random.Random(seed)
    profiles = []
    for i, tree in enumerate(trees):
        # Existing nonstandard DBH is only a size anchor, never a calibrated truth.
        anchor = tree.get("DBH_cm") or 20.0 + i
        annual = rng.uniform(0.35, 1.15)
        profiles.append((float(anchor), annual, ("steady", "slow", "stalled", "negative_review")[i % 4]))
    output.mkdir(parents=True, exist_ok=True)
    reports, manuals, identities, scenarios, quarterly = [], [], [], [], []
    for q, when in enumerate(dates):
        scan = f"SIM-{when.year}Q{(when.month - 1) // 3 + 1}"
        report = {"scan_id": scan, "created_at": when.isoformat(), "dataset_kind": "simulated",
                  "num_trees": len(trees), "gps_available": False, "trees": []}
        for i, tree in enumerate(trees):
            anchor, annual, scenario = profiles[i]
            base = max(5.0, anchor - annual * (quarters - 1) / 4)
            effective_q = min(q, quarters // 2) if scenario == "stalled" else q
            gain = annual * effective_q / 4 * (0.25 if scenario == "slow" else 1)
            drop = 1.5 if scenario == "negative_review" and q >= quarters - 3 else 0
            truth = max(3.0, base + gain - drop)
            manual = round(truth + rng.gauss(0, 0.04), 2)
            auto = round(truth + 0.12 + rng.gauss(0, 0.32), 2)
            local = f"SIM-Tree_{i + 1:03d}"
            report["trees"].append({"Tree_ID": local, "DBH_cm": auto, "DBH_method": "simulated_circle",
                "DBH_note": "negative_change_scenario" if drop else "ok", "dbh_is_strict_breast_height": True,
                "Height_m": round(1.3 + 1.8 * math.sqrt(truth), 2)})
            natural = dict(site_id="DEMO-fengchia", scan_id=scan, local_tree_id=local)
            manuals.append(dict(natural, manual_dbh_cm=manual, measured_at=when.isoformat(), strict_13m=True))
            identities.append(dict(natural, persistent_tree_id=f"SIM-PERSISTENT-{i + 1:03d}", confirmed=True))
            scenarios.append(dict(natural, scenario=scenario, latent_dbh_cm=round(truth, 4), dataset_kind="simulated"))
            quarterly.append(dict(dataset_kind="simulated", quarter=scan.removeprefix("SIM-"), date=when.isoformat(),
                persistent_tree_id=f"SIM-PERSISTENT-{i + 1:03d}", scenario=scenario,
                simulated_manual_dbh_cm=manual, simulated_ai_dbh_cm=auto, seed=seed))
        path = output / "reports" / f"{scan}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        reports.append(("DEMO-fengchia", str(path.resolve()), report))
    for name, rows in (("manual-SIMULATED", manuals), ("identities-SIMULATED", identities), ("scenarios-SIMULATED", scenarios), ("quarterly-SIMULATED", quarterly)):
        with (output / f"{name}.csv").open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    tables = build(reports, manuals, identities, allow_simulated=True)
    export(tables, output / "analytics")
    metadata = {"dataset_kind": "simulated", "seed": seed, "quarters": quarters, "trees": len(trees),
        "start": dates[0].isoformat(), "end": dates[-1].isoformat(), "observations": len(tables["FactObservation"]),
        "template_sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
        "assumptions": ["Quarter-end synthetic dates; no real historical scans or manual measurements.",
            "Seeded Gaussian manual noise SD=0.04 cm; algorithm noise bias=0.12 cm, SD=0.32 cm.",
            "Annual growth 0.35-1.15 cm is a demo parameter, not a validated biological model.",
            "Slow, stalled and negative-review scenarios are scripted; not health diagnoses."]}
    (output / "simulation.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (output / "README.md").write_text("# 模擬季度資料 / SIMULATED DEMO ONLY\n\n"
        "所有歷史日期、固定樹號、人工欄位、AI 欄位與增量均為模擬。不可用於實測精度、真實生長或碳權宣稱。\n"
        f"\n{dates[0]} 至 {dates[-1]}，{quarters} 季，每季 {len(trees)} 棵樹。假設與種子見 simulation.json。\n",
        encoding="utf-8")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", default="app/src/data/inventories/20260818092855.json")
    parser.add_argument("--out", required=True)
    parser.add_argument("--quarters", type=int, default=16)
    parser.add_argument("--end", default="2026-06-30", help="Last completed quarter-end")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(generate(args.template, args.out, quarters=args.quarters, end=args.end, seed=args.seed), indent=2))
