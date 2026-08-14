"""
discover_trees.py
=================
Pipeline 2.0 階段一：從掃描軌跡找出所有樹木並賦予 Tree_ID。

流程:
  1. 讀 cameras.json + camera_left，依幀數/距離抽樣
  2. YOLO (你的 best.pt) 批次偵測 tree_trunk
  3. 遮罩中心 → 魚眼射線 → 與地面平面交點
  4. DBSCAN 分群 → Tree_001, Tree_002, ...
  5. 輸出 inventory_out/tree_registry.json

用法:
  python discover_trees.py
  python discover_trees.py --every_n 12 --eps 1.5 --output_dir inventory_out
"""
import argparse
from pathlib import Path

from geo_utils.console import ensure_utf8_stdout
from park_inventory.discover import discover_trees
from park_inventory.scan_context import apply_scan_id


def parse_args():
    p = argparse.ArgumentParser(description="階段一：多樹木分群與 Tree ID")
    p.add_argument("--cameras_json", type=Path, default=None)
    p.add_argument("--camera_left_dir", type=Path, default=None)
    p.add_argument("--calib", type=Path, default=None)
    p.add_argument("--ply", type=Path, default=None)
    p.add_argument("--output_dir", type=Path, default=None)
    p.add_argument("--every_n", type=int, default=None, help="每隔幾幀抽一張")
    p.add_argument("--min_distance", type=float, default=None, help="移動超過幾公尺強制抽樣")
    p.add_argument("--eps", type=float, default=None, help="Tree center DBSCAN eps (公尺)")
    p.add_argument("--min_points", type=int, default=None, help="DBSCAN 最少點數")
    p.add_argument("--conf", type=float, default=None, help="YOLO 信心門檻")
    p.add_argument("--scan_id", type=str, default=None, help="掃描 ID")
    return p.parse_args()


if __name__ == "__main__":
    ensure_utf8_stdout()
    args = parse_args()
    if args.scan_id:
        apply_scan_id(args.scan_id)
    registry = discover_trees(
        cameras_json=args.cameras_json,
        camera_left_dir=args.camera_left_dir,
        calib_path=args.calib,
        ply_path=args.ply,
        output_dir=args.output_dir,
        every_n=args.every_n,
        min_distance_m=args.min_distance,
        cluster_eps_m=args.eps,
        cluster_min_points=args.min_points,
        yolo_conf=args.conf,
    )
    raise SystemExit(0 if registry.get("trees") else 1)
