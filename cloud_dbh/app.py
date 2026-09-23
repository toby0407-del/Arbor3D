"""Cloud DBH HTTP API — wraps the existing Arbor3D postprocess pipeline."""
from __future__ import annotations

import os
import secrets
import threading
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

try:
    from cloud_dbh.worker import (  # type: ignore[import-not-found]
        DEFAULT_WORK,
        JobPaths,
        execute_job,
        read_status,
        write_status,
    )
except ImportError:  # local `uvicorn app:app` from inside cloud_dbh/
    from worker import (  # type: ignore[no-redef]
        DEFAULT_WORK,
        JobPaths,
        execute_job,
        read_status,
        write_status,
    )

API_KEY = os.environ.get("ARBOR3D_CLOUD_DBH_API_KEY", "").strip()
WORK_DIR = Path(os.environ.get("ARBOR3D_CLOUD_WORK_DIR", str(DEFAULT_WORK)))
PREPARE_ONLY_DEFAULT = os.environ.get("ARBOR3D_CLOUD_PREPARE_ONLY", "").lower() in {
    "1",
    "true",
    "yes",
}

app = FastAPI(
    title="Arbor3D Cloud DBH",
    description="把既有胸徑／盤點管線接到 Microsoft Azure（Container Apps）執行",
    version="1.0.0",
)


def require_api_key(x_api_key: str | None) -> None:
    if not API_KEY:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="invalid API key")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "arbor3d-cloud-dbh",
        "work_dir": str(WORK_DIR),
        "prepare_only_default": PREPARE_ONLY_DEFAULT,
        "auth_required": bool(API_KEY),
    }


@app.post("/v1/jobs")
async def create_job(
    background: BackgroundTasks,
    scan_id: str = Form(...),
    path_id: str = Form(""),
    prepare_only: bool = Form(False),
    archive: UploadFile = File(...),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> JSONResponse:
    require_api_key(x_api_key)
    if not scan_id.strip():
        raise HTTPException(status_code=400, detail="scan_id required")
    job_id = uuid.uuid4().hex
    paths = JobPaths.create(job_id, WORK_DIR)
    zip_path = paths.root / "upload.zip"
    data = await archive.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty archive")
    zip_path.write_bytes(data)
    use_prepare = prepare_only or PREPARE_ONLY_DEFAULT
    write_status(
        paths,
        "queued",
        "已排隊，等待雲端 worker",
        scan_id=scan_id.strip(),
        path_id=path_id.strip(),
        prepare_only=use_prepare,
    )

    def _run() -> None:
        execute_job(
            job_id=job_id,
            scan_id=scan_id.strip(),
            path_id=path_id.strip(),
            zip_path=zip_path,
            prepare_only=use_prepare,
            work_root=WORK_DIR,
        )

    # Prefer FastAPI BackgroundTasks; fall back to thread if the runtime
    # already closed the request context in some ASGI servers.
    try:
        background.add_task(_run)
    except Exception:  # noqa: BLE001
        threading.Thread(target=_run, daemon=True).start()

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "queued",
            "poll_url": f"/v1/jobs/{job_id}",
        },
    )


@app.get("/v1/jobs/{job_id}")
def get_job(
    job_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    require_api_key(x_api_key)
    paths = JobPaths.create(job_id, WORK_DIR)
    status = read_status(paths)
    if status is None:
        raise HTTPException(status_code=404, detail="job not found")
    return status
