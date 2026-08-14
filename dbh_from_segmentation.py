"""
dbh_from_segmentation.py
=========================
用 YOLO 遮罩剝離單棵樹幹點雲，套用地面校正 + RANSAC / 卡尺法，計算 DBH。

使用方式:
    # 沿用 dbh_seg/config.py 預設路徑
    python dbh_from_segmentation.py --no-viz

    # Pipeline 2.0：指定單棵樹參數
    python dbh_from_segmentation.py --no-viz \\
        --mask real_tree_mask_Tree_001.jpg \\
        --ply "..\\3D_treedata_Denoised_Trees\\20260812070325.ply" \\
        --calib "..\\3D_treedata\\20260812070325\\calibration\\calib.json" \\
        --tree_id Tree_001 \\
        --output_dir inventory_out
"""
import argparse
from pathlib import Path

from geo_utils.console import ensure_utf8_stdout
from dbh_seg import calculate_dbh_for_segmented_tree


def parse_args():
    p = argparse.ArgumentParser(
        description="計算單棵樹 DBH（可覆寫 config.py 路徑，供批次管線呼叫）"
    )
    p.add_argument("--mask", type=Path, default=None, help="YOLO 二值遮罩路徑")
    p.add_argument("--ply", type=Path, default=None, help="去噪點雲 .ply 路徑")
    p.add_argument("--calib", type=Path, default=None, help="相機參數 calib.json")
    p.add_argument("--tree_id", type=str, default=None, help="樹木識別碼，例 Tree_001")
    p.add_argument(
        "--output_dir",
        type=Path,
        default=None,
        help="輸出目錄（俯視圖、dbh_results.json）",
    )
    p.add_argument(
        "--results_json",
        type=Path,
        default=None,
        help="DBH 結果 JSON 路徑（預設 output_dir/dbh_results.json）",
    )
    p.add_argument(
        "--source_photo",
        type=Path,
        default=None,
        help="對應原始照片路徑（寫入結果紀錄）",
    )
    p.add_argument("--no-viz", action="store_true", help="不開 Open3D 視窗")
    return p.parse_args()


if __name__ == "__main__":
    ensure_utf8_stdout()
    args = parse_args()
    result = calculate_dbh_for_segmented_tree(
        show_viz=not args.no_viz,
        mask_path=args.mask,
        ply_path=args.ply,
        calib_path=args.calib,
        tree_id=args.tree_id,
        output_dir=args.output_dir,
        source_photo_path=args.source_photo,
        results_json=args.results_json,
    )
    raise SystemExit(0 if result is not None else 1)
