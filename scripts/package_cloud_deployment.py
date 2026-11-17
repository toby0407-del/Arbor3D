"""Build a private, minimal Docker source bundle without credentials or scan data."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / ".runtime/cloud-deploy"
PACKAGES = ("cloud_dbh", "dbh_seg", "geo_utils", "gaussian_prune", "park_inventory", "measurement_quality", "yolo_seg", "semantic_seg")


def main():
    context = OUTPUT / "context"
    context.mkdir(parents=True, exist_ok=True)
    sources = [p for package in PACKAGES for p in (ROOT / package).rglob("*.py") if "__pycache__" not in p.parts]
    sources += [ROOT / "run_full_park_pipeline.py", ROOT / "scripts/postprocess_from_inbox.py", ROOT / "cloud_dbh/Dockerfile",
                ROOT / "cloud_dbh/requirements.txt", ROOT / "cloud_dbh/requirements-full.txt", ROOT / ".dockerignore",
                ROOT / "yolo_seg/runs/v3/weights/best.pt"]
    records = []
    with zipfile.ZipFile(OUTPUT / "source.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=1) as bundle:
        for source in sorted(set(sources)):
            relative = source.relative_to(ROOT)
            destination = context / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            bundle.write(source, relative.as_posix())
            records.append({"path": relative.as_posix(), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    manifest = {"contains_credentials": False, "contains_scan_inputs": False, "files": records,
                "source_sha256": hashlib.sha256((OUTPUT / "source.zip").read_bytes()).hexdigest()}
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(records), "archive_bytes": (OUTPUT / "source.zip").stat().st_size,
                      "source_sha256": manifest["source_sha256"]}))


if __name__ == "__main__":
    main()
