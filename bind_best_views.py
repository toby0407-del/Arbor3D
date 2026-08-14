"""
bind_best_views.py
==================
Pipeline 2.0 階段二：為 tree_registry.json 裡的每棵樹選最佳照片，
並產出專屬遮罩 real_tree_mask_Tree_XXX.jpg。

用法:
  python bind_best_views.py
  python bind_best_views.py --registry inventory_out/tree_registry.json --output_dir inventory_out
"""
import argparse
from pathlib import Path

from geo_utils.console import ensure_utf8_stdout
from park_inventory.best_view import bind_best_views


def parse_args():
    p = argparse.ArgumentParser(description="階段二：最佳觀測視角綁定 + 專屬遮罩")
    p.add_argument("--registry", type=Path, default=None, help="tree_registry.json")
    p.add_argument("--output_dir", type=Path, default=None)
    p.add_argument("--conf", type=float, default=None, help="YOLO 信心門檻")
    return p.parse_args()


if __name__ == "__main__":
    ensure_utf8_stdout()
    args = parse_args()
    out = bind_best_views(
        registry_path=args.registry,
        output_dir=args.output_dir,
        yolo_conf=args.conf,
    )
    raise SystemExit(0 if out.get("num_trees", 0) > 0 else 1)
