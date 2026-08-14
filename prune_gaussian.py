"""
prune_gaussian.py
==================
把整座公園場景的 3D 高斯模型用「物理刪減」瘦身成只剩目標那一棵樹。

使用方式:
    # 沿用 gaussian_prune/config.py 預設路徑
    python prune_gaussian.py

    # Pipeline 2.0：指定單棵樹參數
    python prune_gaussian.py \\
        --mask real_tree_mask_Tree_001.jpg \\
        --input_ply "..\\3DGS_Park_Model\\完整場景\\20260812070325.ply" \\
        --calib "..\\3D_treedata\\20260812070325\\calibration\\calib.json" \\
        --tree_id Tree_001 \\
        --output_dir inventory_out
"""
import argparse
from pathlib import Path

from geo_utils.console import ensure_utf8_stdout
from gaussian_prune import prune_gaussian_to_single_tree


def parse_args():
    p = argparse.ArgumentParser(
        description="高斯模型瘦身成單棵樹（可覆寫路徑，供批次管線呼叫）"
    )
    p.add_argument("--mask", type=Path, default=None, help="YOLO 二值遮罩路徑")
    p.add_argument(
        "--input_ply",
        type=Path,
        default=None,
        help="完整場景 3DGS .ply（3DGS_Park_Model/完整場景/{scan_id}.ply）",
    )
    p.add_argument("--calib", type=Path, default=None, help="相機參數 calib.json")
    p.add_argument("--tree_id", type=str, default=None, help="樹木識別碼，例 Tree_001")
    p.add_argument(
        "--output_dir",
        type=Path,
        default=None,
        help="輸出目錄（{tree_id}_single_tree.ply / _supersplat.ply）",
    )
    p.add_argument(
        "--ground_ply",
        type=Path,
        default=None,
        help="地面校正用的去噪點雲（預設跟 dbh 同一份）",
    )
    p.add_argument(
        "--source_photo",
        type=Path,
        default=None,
        help="對應原始照片（用來查 cameras.json 單幀姿態）",
    )
    p.add_argument(
        "--no-supersplat",
        action="store_true",
        help="不另外輸出 SuperSplat 相容檔",
    )
    return p.parse_args()


if __name__ == "__main__":
    ensure_utf8_stdout()
    args = parse_args()
    info = prune_gaussian_to_single_tree(
        input_ply=args.input_ply,
        mask_path=args.mask,
        calib_path=args.calib,
        tree_id=args.tree_id,
        output_dir=args.output_dir,
        ground_ply=args.ground_ply,
        make_supersplat=not args.no_supersplat,
        source_photo_path=args.source_photo,
    )
    raise SystemExit(0 if info is not None else 1)
