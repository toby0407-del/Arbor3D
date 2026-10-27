"""Extract a real single-tree section locally without modifying the original scan."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--scan-id", default="20260812070325")
    args = parser.parse_args()
    os.environ["ARBOR3D_DATA_ROOT"] = str(args.source_root)
    os.environ["ARBOR3D_SCAN_ID"] = args.scan_id
    os.environ.pop("ARBOR3D_SECTION_CLOUD_URL", None)
    from dbh_seg import pipeline
    from geo_utils.console import ensure_utf8_stdout
    ensure_utf8_stdout()
    old_root = args.source_root / "treee_VScode"
    view_doc = json.loads((old_root / "inventory_out/best_views.json").read_text(encoding="utf-8"))
    if view_doc.get("scan_id") != args.scan_id:
        raise ValueError("Stored masks belong to another scan")
    output = ROOT / ".runtime/free-geometry/real-section"
    output.mkdir(parents=True, exist_ok=True)
    original_estimate = pipeline.estimate_dbh
    payload_file = output / "input.json"
    captured = []
    for view in view_doc["best_views"]:
        mask = Path(view["mask_path"])
        if not mask.is_absolute():
            mask = old_root / mask
        if not mask.is_file():
            continue
        tree_id = view["tree_id"]
        def capture(points, camera_xy=None, quality_context=None, quality_model=None):
            payload = {"scan_id": args.scan_id, "tree_id": tree_id, "units": "m", "points": points.tolist(),
                       "camera_xy": camera_xy.tolist() if camera_xy is not None else None,
                       "context": quality_context or {}, "source": "observed"}
            payload_file.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
            captured.append(tree_id)
            return original_estimate(points, camera_xy=camera_xy, quality_context=quality_context, quality_model=quality_model)
        pipeline.estimate_dbh = capture
        pipeline.calculate_dbh_for_segmented_tree(show_viz=False, mask_path=mask,
            ply_path=args.source_root / "3D_treedata_Denoised_Trees" / f"{args.scan_id}.ply",
            calib_path=args.source_root / "3D_treedata" / args.scan_id / "calibration/calib.json",
            tree_id=tree_id, output_dir=output, source_photo_path=Path(view["photo_path"]))
        if captured:
            data = json.loads(payload_file.read_text())
            print(json.dumps({"real_section": True, "scan_id": args.scan_id, "tree_id": tree_id, "points": len(data["points"]), "output": str(payload_file)}, ensure_ascii=True))
            return
    raise RuntimeError("No valid section could be extracted from the original masks")


if __name__ == "__main__":
    main()
