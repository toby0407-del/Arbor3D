"""階段四：對每棵 Tree_ID 以獨立 subprocess 呼叫 DBH 與 Prune，避免記憶體累積。"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dbh_seg import config as dbh_config
from gaussian_prune import config as gs_config

from . import config
from .report import build_park_inventory_report, write_park_inventory_report

ROOT = Path(__file__).resolve().parent.parent


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str], label: str) -> bool:
    print(f"\n----- {label} -----")
    print(" ".join(str(c) for c in cmd))
    completed = subprocess.run(cmd, cwd=str(ROOT))
    ok = completed.returncode == 0
    if not ok:
        print(f"⚠️ {label} 失敗 (exit={completed.returncode})")
    return ok


def run_park_inventory(
    output_dir: Path | None = None,
    registry_path: Path | None = None,
    best_views_path: Path | None = None,
    skip_prune: bool = False,
    skip_dbh: bool = False,
    tree_ids: list[str] | None = None,
) -> dict:
    output_dir = Path(output_dir or config.DEFAULT_OUTPUT_DIR)
    registry_path = Path(registry_path or (output_dir / "tree_registry.json"))
    best_views_path = Path(best_views_path or (output_dir / "best_views.json"))
    dbh_dir = output_dir / "dbh"
    model_dir = output_dir / "models"
    dbh_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    registry = _load_json(registry_path)
    views_doc = _load_json(best_views_path)
    views = views_doc.get("best_views") or []
    if tree_ids:
        want = set(tree_ids)
        views = [v for v in views if v["tree_id"] in want]

    python = sys.executable
    dbh_script = ROOT / "dbh_from_segmentation.py"
    prune_script = ROOT / "prune_gaussian.py"
    ply = dbh_config.PLY_PATH
    calib = dbh_config.CALIB_PATH
    gaussian_ply = gs_config.GAUSSIAN_PLY_PATH
    dbh_json = dbh_dir / "dbh_results.json"
    if not skip_dbh and not tree_ids and dbh_json.exists():
        dbh_json.unlink()

    print("=== 階段四：公園批次盤點 ===")
    print(f"scan_id: {registry.get('scan_id')}")
    print(f"trees:   {len(views)}")
    print(f"PLY:     {ply}")
    print(f"3DGS:    {gaussian_ply}")

    run_log = []
    for i, view in enumerate(views, start=1):
        tree_id = view["tree_id"]
        mask = Path(view["mask_path"])
        if not mask.is_absolute():
            mask = (ROOT / mask).resolve()
        photo = view.get("photo_path")
        print(f"\n========== [{i}/{len(views)}] {tree_id} ==========")
        print(f"mask: {mask}")

        entry = {"tree_id": tree_id, "dbh_ok": None, "prune_ok": None}
        if not skip_dbh:
            entry["dbh_ok"] = _run(
                [
                    python, str(dbh_script),
                    "--no-viz",
                    "--mask", str(mask),
                    "--ply", str(ply),
                    "--calib", str(calib),
                    "--tree_id", tree_id,
                    "--output_dir", str(dbh_dir),
                    "--results_json", str(dbh_json),
                    "--source_photo", str(photo),
                ],
                f"{tree_id} DBH",
            )
        if not skip_prune:
            entry["prune_ok"] = _run(
                [
                    python, str(prune_script),
                    "--mask", str(mask),
                    "--input_ply", str(gaussian_ply),
                    "--calib", str(calib),
                    "--tree_id", tree_id,
                    "--output_dir", str(model_dir),
                    "--ground_ply", str(ply),
                    "--source_photo", str(photo),
                ],
                f"{tree_id} Prune",
            )
        run_log.append(entry)

    dbh_history = []
    if dbh_json.exists():
        dbh_history = _load_json(dbh_json)
        if not isinstance(dbh_history, list):
            dbh_history = []

    report = build_park_inventory_report(
        output_dir=output_dir,
        scan_id=registry.get("scan_id") or config.SCAN_ID,
        registry=registry,
        best_views=views,
        dbh_history=dbh_history,
    )
    report["run_log"] = run_log
    report["created_at"] = datetime.now().isoformat(timespec="seconds")
    json_path, csv_path = write_park_inventory_report(report, output_dir)

    n_ok_dbh = sum(1 for x in run_log if x.get("dbh_ok") is True)
    n_ok_prune = sum(1 for x in run_log if x.get("prune_ok") is True)
    print("\n=== 批次完成 ===")
    if skip_dbh:
        print("DBH: 略過")
    else:
        print(f"DBH 成功:   {n_ok_dbh}/{len(views)}")
    if skip_prune:
        print("Prune: 略過（沿用既有 models/）")
    else:
        print(f"Prune 成功: {n_ok_prune}/{len(views)}")
    print(f"總表: {json_path}")
    return report
