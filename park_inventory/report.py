"""階段五：把每棵樹的 DBH、座標、剖面圖、3D 模型整成總表。"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path


def _latest_dbh_record(dbh_history: list, tree_id: str) -> dict | None:
    matches = [r for r in dbh_history if r.get("tree_id") == tree_id]
    return matches[-1] if matches else None


def _resolve(path_str: str | None, base: Path) -> str | None:
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_absolute():
        p = (base / p).resolve()
    return str(p)


def _dbh_note(dbh: dict) -> str:
    """沒有現場量測時，用演算法狀態標註可信度（不是真實樹圍）。"""
    if not dbh.get("dbh_cm"):
        return "no_measurement"
    notes = []
    if not dbh.get("dbh_is_strict_breast_height"):
        notes.append("not_1.3m")
    if dbh.get("gap_detected"):
        notes.append("gap")
    method = dbh.get("method")
    cm = float(dbh.get("dbh_cm") or 0)
    if method == "caliper" and cm >= 45:
        notes.append("wide_caliper")
    return ",".join(notes) if notes else "ok"


def build_park_inventory_report(
    output_dir: Path,
    scan_id: str,
    registry: dict,
    best_views: list[dict],
    dbh_history: list,
) -> dict:
    """組出 park_inventory_report.json 結構（不寫檔）。"""
    trees_by_id = {t["tree_id"]: t for t in registry.get("trees") or []}
    views_by_id = {v["tree_id"]: v for v in best_views}
    rows = []

    for tree_id, view in views_by_id.items():
        tree = trees_by_id.get(tree_id) or {}
        dbh = _latest_dbh_record(dbh_history, tree_id) or {}
        slice_png = output_dir / "dbh" / f"dbh_slice_top_down_{tree_id}.png"
        model_dir = output_dir / "models"
        supersplat = model_dir / f"{tree_id}_supersplat.ply"
        single_tree = model_dir / f"{tree_id}_single_tree.ply"

        center = tree.get("center_xyz")
        rows.append(
            {
                "Tree_ID": tree_id,
                "DBH_cm": dbh.get("dbh_cm"),
                "DBH_method": dbh.get("method"),
                "DBH_note": _dbh_note(dbh),
                "arc_coverage_deg": dbh.get("arc_coverage_deg"),
                "num_slice_points": dbh.get("num_slice_points"),
                "slice_z_min_m": dbh.get("slice_z_min_m"),
                "slice_z_max_m": dbh.get("slice_z_max_m"),
                "dbh_is_strict_breast_height": dbh.get("dbh_is_strict_breast_height"),
                "GPS_Location": None,  # 此掃描 calib 無 GPS / RTK
                "Local_XYZ_m": center,
                "Best_Photo": view.get("photo_path"),
                "Mask_Path": _resolve(view.get("mask_path"), output_dir.parent),
                "Cross_Section_Image": str(slice_png) if slice_png.exists() else None,
                "3D_Model_Path": str(supersplat) if supersplat.exists() else (
                    str(single_tree) if single_tree.exists() else None
                ),
                "Single_Tree_Ply": str(single_tree) if single_tree.exists() else None,
                "YOLO_confidence": view.get("confidence"),
                "num_detections": tree.get("num_detections"),
            }
        )

    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "scan_id": scan_id,
        "gps_available": False,
        "num_trees": len(rows),
        "trees": rows,
    }


def write_park_inventory_report(report: dict, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "park_inventory_report.json"
    csv_path = output_dir / "park_inventory_report.csv"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = [
        "Tree_ID",
        "DBH_cm",
        "DBH_method",
        "DBH_note",
        "arc_coverage_deg",
        "num_slice_points",
        "slice_z_min_m",
        "slice_z_max_m",
        "dbh_is_strict_breast_height",
        "GPS_Location",
        "Local_XYZ_m",
        "Best_Photo",
        "Mask_Path",
        "Cross_Section_Image",
        "3D_Model_Path",
        "Single_Tree_Ply",
        "YOLO_confidence",
        "num_detections",
    ]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["trees"]:
            flat = dict(row)
            xyz = flat.get("Local_XYZ_m")
            if isinstance(xyz, list):
                flat["Local_XYZ_m"] = ",".join(str(x) for x in xyz)
            writer.writerow(flat)

    print(f"公園總表 JSON: {json_path}")
    print(f"公園總表 CSV:  {csv_path}")

    from .html_report import write_html_report
    from .overlay import save_dbh_marker_ply, save_inventory_map

    save_inventory_map(report, output_dir / "tree_id_map_dbh.png")
    save_dbh_marker_ply(report, output_dir / "dbh_markers.ply")
    html_path = write_html_report(report, output_dir)
    print(f"成果頁: {html_path}")
    return json_path, csv_path
