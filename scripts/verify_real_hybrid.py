"""Verify one original tree through local extraction, Azure geometry and local export."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    for line in (ROOT / "app/.env.local").read_text(encoding="utf-8-sig").splitlines():
        name, sep, value = line.partition("=")
        if sep and name in {"ARBOR3D_SECTION_CLOUD_URL", "ARBOR3D_CLOUD_DBH_API_KEY"}:
            os.environ[name] = value.strip()
    if not os.environ.get("ARBOR3D_SECTION_CLOUD_URL"):
        raise RuntimeError("Hybrid section service is not configured")
    doc = json.loads((args.source_root / "treee_VScode/inventory_out/best_views.json").read_text(encoding="utf-8"))
    scan_id = doc["scan_id"]
    os.environ["ARBOR3D_DATA_ROOT"] = str(args.source_root)
    os.environ["ARBOR3D_SCAN_ID"] = scan_id
    from dbh_seg import calculate_dbh_for_segmented_tree
    from geo_utils.console import ensure_utf8_stdout
    ensure_utf8_stdout()
    out = ROOT / ".runtime/free-geometry/hybrid-pipeline"
    out.mkdir(parents=True, exist_ok=True)
    view = doc["best_views"][0]
    mask = Path(view["mask_path"])
    if not mask.is_absolute():
        mask = args.source_root / "treee_VScode" / mask
    start = time.monotonic()
    result = calculate_dbh_for_segmented_tree(show_viz=False, mask_path=mask,
        ply_path=args.source_root / "3D_treedata_Denoised_Trees" / f"{scan_id}.ply",
        calib_path=args.source_root / "3D_treedata" / scan_id / "calibration/calib.json",
        source_photo_path=Path(view["photo_path"]), tree_id=view["tree_id"], output_dir=out)
    if result is None or not result.execution or result.execution.get("platform") != "azure-app-service":
        raise RuntimeError("The real hybrid pipeline did not return an Azure execution record")
    records = json.loads((out / "dbh_results.json").read_text(encoding="utf-8"))
    record = records[-1]
    assert record["execution"]["id"] == result.execution["id"]
    assert record["scan_id"] == scan_id
    assert record["dbh_cm"] is None and record["measurement_quality"]["decision"] == "review"
    proof = {"source": "observed", "scan_id": scan_id, "tree_id": view["tree_id"],
             "local_stages": ["existing_YOLO_mask", "point_projection", "depth_filter", "ground_alignment", "section_extraction", "plot_and_export"],
             "azure_stage": result.execution, "candidate_dbh_cm": record["candidate_dbh_cm"], "formal_dbh_cm": record["dbh_cm"],
             "strict_breast_height": record["dbh_is_strict_breast_height"], "elapsed_seconds": round(time.monotonic()-start, 3),
             "azure_sku": "F1", "new_paid_resources_created": False, "original_scan_modified": False}
    (out / "verification.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print(json.dumps(proof, ensure_ascii=True))


if __name__ == "__main__":
    main()
