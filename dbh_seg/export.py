"""把每次計算的 DBH 結果累積記錄成 JSON，方便回溯歷史、整理成果報告。"""
import json
from datetime import datetime
from pathlib import Path

from . import config


def export_result(
    result,
    slice_pts,
    out_path=None,
    source_photo_path=None,
    tree_id=None,
    mask_path=None,
    cross_section_image=None,
    slice_z_min=None,
    slice_z_max=None,
):
    """把這次的 DBH 結果 append 進 dbh_results.json，回傳存檔路徑字串。"""
    out_path = Path(out_path or (config.BASE_DIR / "dbh_results.json"))

    if slice_z_min is None and len(slice_pts):
        slice_z_min = float(slice_pts[:, 2].min())
    if slice_z_max is None and len(slice_pts):
        slice_z_max = float(slice_pts[:, 2].max())
    strict_breast = (
        slice_z_min is not None
        and slice_z_max is not None
        and slice_z_min >= config.SLICE_Z_MIN - 0.05
        and slice_z_max <= config.SLICE_Z_MAX + 0.05
    )

    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "scan_id": config.SCAN_ID,
        "tree_id": tree_id,
        "source_photo_path": str(source_photo_path) if source_photo_path else None,
        "mask_path": str(mask_path or config.MASK_PATH),
        "method": result.method,
        "dbh_cm": round(result.dbh_m * 100, 1),
        "arc_coverage_deg": round(result.arc_deg, 1),
        "num_slice_points": len(slice_pts),
        "slice_z_min_m": round(slice_z_min, 3) if slice_z_min is not None else None,
        "slice_z_max_m": round(slice_z_max, 3) if slice_z_max is not None else None,
        "dbh_is_strict_breast_height": strict_breast,
        "center_xy_m": [round(result.xc, 3), round(result.yc, 3)],
        "inlier_ratio": round(result.inlier_ratio, 3) if result.inlier_ratio is not None else None,
        "gap_detected": result.gap_detected,
        "gap_cm": round(result.gap_m * 100, 1) if result.gap_detected else None,
        "cross_section_image": str(cross_section_image) if cross_section_image else None,
    }

    try:
        with open(out_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []

    history.append(record)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"📝 已將本次結果記錄到：{out_path} (累計 {len(history)} 筆)")
    return str(out_path)
