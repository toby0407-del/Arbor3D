"""
run_park_inventory.py
=====================
Pipeline 2.0 總控制器（階段四 + 五）。

對 tree_registry / best_views 裡的每一棵樹：
  1. subprocess 呼叫 dbh_from_segmentation.py（算 DBH + 剖面圖）
  2. subprocess 呼叫 prune_gaussian.py（瘦身高斯 + SuperSplat）
  3. 整成 park_inventory_report.json / .csv

每棵樹用獨立行程，結束即釋放點雲記憶體。

用法:
  python run_park_inventory.py
  python run_park_inventory.py --output_dir inventory_out
  python run_park_inventory.py --skip-prune          # 只算 DBH（較快，方便驗收）
  python run_park_inventory.py --tree_id Tree_001    # 只跑指定樹
"""
import argparse
from pathlib import Path

from geo_utils.console import ensure_utf8_stdout
from park_inventory.master import run_park_inventory
from park_inventory.scan_context import apply_scan_id


def parse_args():
    p = argparse.ArgumentParser(description="公園多樹木批次盤點（DBH + 高斯瘦身 + 總表）")
    p.add_argument("--output_dir", type=Path, default=None)
    p.add_argument("--scan_id", type=str, default=None, help="掃描 ID，例如 20260812070325")
    p.add_argument("--registry", type=Path, default=None)
    p.add_argument("--best_views", type=Path, default=None)
    p.add_argument("--skip-prune", action="store_true", help="略過高斯瘦身（較快）")
    p.add_argument("--skip-dbh", action="store_true", help="略過 DBH")
    p.add_argument(
        "--tree_id",
        action="append",
        default=None,
        help="只跑指定 Tree_ID，可重複，例如 --tree_id Tree_001 --tree_id Tree_002",
    )
    return p.parse_args()


if __name__ == "__main__":
    ensure_utf8_stdout()
    args = parse_args()
    if args.scan_id:
        apply_scan_id(args.scan_id)
    report = run_park_inventory(
        output_dir=args.output_dir,
        registry_path=args.registry,
        best_views_path=args.best_views,
        skip_prune=args.skip_prune,
        skip_dbh=args.skip_dbh,
        tree_ids=args.tree_id,
    )
    n = report.get("num_trees", 0)
    raise SystemExit(0 if n > 0 else 1)
