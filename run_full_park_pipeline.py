"""
run_full_park_pipeline.py
=========================
人做好的部分（RayStudio，程式無法代勞）：
  1. 掃描匯出 3D_treedata/{scan_id}/（照片、calib、cameras.json）
  2. 去噪點雲放到 3D_treedata_Denoised_Trees/{scan_id}.ply
  3. 完整 3D 高斯放到 3DGS_Park_Model/完整場景/{scan_id}.ply

之後一條指令，程式自己跑完並出 HTML：
  python run_full_park_pipeline.py --scan_id 20260812070325
"""
import argparse
from pathlib import Path

from dbh_seg import config as dbh_config
from geo_utils.console import ensure_utf8_stdout
from park_inventory.best_view import bind_best_views
from park_inventory.discover import discover_trees
from park_inventory.master import run_park_inventory
from park_inventory.scan_context import apply_scan_id, check_scan_ready


def parse_args():
    p = argparse.ArgumentParser(
        description="公園盤點一條龍：檢查素材 → 分樹 → 遮罩 → DBH/瘦身 → HTML"
    )
    p.add_argument(
        "--scan_id",
        type=str,
        default=None,
        help="掃描資料夾名稱，例如 20260812070325（預設用 config 目前那趟）",
    )
    p.add_argument("--output_dir", type=Path, default=None)
    p.add_argument("--skip-discover", action="store_true")
    p.add_argument("--skip-bind", action="store_true")
    p.add_argument("--skip-prune", action="store_true")
    p.add_argument("--skip-dbh", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    ensure_utf8_stdout()
    args = parse_args()
    scan_id = args.scan_id or dbh_config.SCAN_ID
    apply_scan_id(scan_id)

    missing = check_scan_ready(scan_id, need_gaussian=not args.skip_prune)
    if missing:
        print("❌ 素材還沒齊，請先用 RayStudio / 掃描軟體準備好再跑：")
        for item in missing:
            print(f"   - {item}")
        raise SystemExit(2)

    output_dir = args.output_dir or Path(f"inventory_out_{scan_id}")
    print("=== 自動盤點開始 ===")
    print(f"scan_id:    {scan_id}")
    print(f"output_dir: {output_dir}")
    print("人已完成：去噪點雲 + 3D 高斯 + 照片/校正")
    print("程式接著做：分樹身分 → 遮罩 → 樹圍 → 單樹 3DGS → HTML")

    if not args.skip_discover:
        registry = discover_trees(output_dir=output_dir)
        if not registry.get("trees"):
            raise SystemExit("階段一沒找到樹木，中止。")

    if not args.skip_bind:
        views = bind_best_views(output_dir=output_dir)
        if not views.get("num_trees"):
            raise SystemExit("階段二沒綁到最佳視角，中止。")

    report = run_park_inventory(
        output_dir=output_dir,
        skip_prune=args.skip_prune,
        skip_dbh=args.skip_dbh,
    )
    html = Path(output_dir) / "park_inventory_report.html"
    print("\n=== 完成，請打開成果頁 ===")
    print(html.resolve())
    raise SystemExit(0 if report.get("num_trees", 0) > 0 else 1)
