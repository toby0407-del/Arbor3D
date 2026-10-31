"""Update only the named existing F1 service; never create or upgrade a resource."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / ".runtime/free-geometry"
GROUP = "arbor3d-competition-rg"
SITE = "arbor3d-dbh-1ec69a14"


def az(*args, json_result=True):
    command = [sys.executable, "-m", "azure.cli", *args, "-o", "json" if json_result else "none"]
    result = subprocess.run(command, cwd=Path.home(), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        # Azure responses may include app settings; do not print captured output.
        (WORK / "last-error.txt").write_text(result.stderr, encoding="utf-8")
        raise RuntimeError("Azure operation failed; diagnostics saved privately in .runtime/free-geometry")
    return json.loads(result.stdout) if json_result and result.stdout.strip() else None


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    app = az("webapp", "show", "-g", GROUP, "-n", SITE)
    plan = az("appservice", "plan", "show", "--ids", app["serverFarmId"])
    if plan["sku"]["name"] != "F1":
        raise RuntimeError("Expected the existing F1 plan; no resource changes were made")
    old = az("webapp", "config", "appsettings", "list", "-g", GROUP, "-n", SITE)
    (WORK / "previous-settings.json").write_text(json.dumps(old), encoding="utf-8")
    old_map = {x["name"]: x["value"] for x in old}
    settings_file = WORK / "settings.json"
    # Keep the same key across retries without exposing it in process arguments.
    key = old_map.get("ARBOR3D_CLOUD_DBH_API_KEY") or secrets.token_urlsafe(32)
    if settings_file.exists():
        key = json.loads(settings_file.read_text())["ARBOR3D_CLOUD_DBH_API_KEY"]
    settings = {"ARBOR3D_CLOUD_DBH_API_KEY": key, "ARBOR3D_CLOUD_PREPARE_ONLY": "true",
                "ARBOR3D_CLOUD_WORK_DIR": "/home/arbor3d-jobs", "ARBOR3D_CLOUD_MAX_UPLOAD_BYTES": "1048576",
                "SCM_DO_BUILD_DURING_DEPLOYMENT": "true"}
    settings_file.write_text(json.dumps(settings), encoding="utf-8")
    os.chmod(settings_file, 0o600)
    archive = WORK / "service.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for directory in ("cloud_dbh", "measurement_quality", "dbh_seg", "geo_utils"):
            for source in (ROOT / directory).rglob("*.py"):
                if "__pycache__" not in source.parts and not source.name.startswith("test_"):
                    bundle.write(source, source.relative_to(ROOT).as_posix())
        bundle.write(ROOT / "yolo_seg/config.py", "yolo_seg/config.py")
        bundle.write(ROOT / "cloud_dbh/requirements-free.txt", "requirements.txt")
    print("Confirmed existing F1 plan; deploying lightweight geometry only.", flush=True)
    az("webapp", "config", "appsettings", "set", "-g", GROUP, "-n", SITE, "--settings", "@" + str(settings_file), json_result=False)
    az("webapp", "config", "set", "-g", GROUP, "-n", SITE, "--startup-file",
       "python -m uvicorn cloud_dbh.app:app --host 0.0.0.0 --port 8000", json_result=False)
    print("Uploading source package to the existing service.", flush=True)
    deployment = az("webapp", "deploy", "-g", GROUP, "-n", SITE, "--src-path", str(archive),
                    "--type", "zip", "--async", "true", "--restart", "true", "--timeout", "600000")
    (WORK / "deployment.json").write_text(json.dumps(deployment), encoding="utf-8")
    print("Deployment submitted; readiness still needs verification. No new resource or SKU was created.", flush=True)


if __name__ == "__main__":
    main()
