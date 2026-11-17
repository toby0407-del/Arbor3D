"""Authenticated asynchronous API for the real Arbor3D pipeline."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import uuid
from threading import BoundedSemaphore

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from cloud_dbh.archives import safe_id
from cloud_dbh.worker import DEFAULT_WORK, REPO_ROOT, JobPaths, execute_job, read_status, write_status

API_KEY = os.environ.get("ARBOR3D_CLOUD_DBH_API_KEY", "").strip()
WORK_DIR = Path(os.environ.get("ARBOR3D_CLOUD_WORK_DIR", str(DEFAULT_WORK)))
PREPARE_ONLY_DEFAULT = os.environ.get("ARBOR3D_CLOUD_PREPARE_ONLY", "").lower() in {"1", "true", "yes"}
MAX_UPLOAD_BYTES = int(os.environ.get("ARBOR3D_CLOUD_MAX_UPLOAD_BYTES", str(2 * 1024**3)))
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="arbor3d-worker")
queue_slots = BoundedSemaphore(2)
section_slot = BoundedSemaphore(1)
app = FastAPI(title="Arbor3D Cloud DBH", version="2.0.0")


def require_api_key(key: str | None, request: Request) -> None:
    if API_KEY:
        if not key or not secrets.compare_digest(key, API_KEY):
            raise HTTPException(401, "Invalid API key")
    elif request.client is None or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(503, "Cloud authentication is not configured")


def capabilities() -> dict:
    dependencies = {name: importlib.util.find_spec(name) is not None for name in ("torch", "open3d", "ultralytics", "cv2", "numpy")}
    weights = REPO_ROOT / "yolo_seg/runs/v3/weights/best.pt"
    model_ready = weights.is_file() and weights.stat().st_size > 1024
    return {"pipeline": "arbor3d", "full_pipeline_ready": not PREPARE_ONLY_DEFAULT and all(dependencies.values()) and model_ready,
            "prepare_only": PREPARE_ONLY_DEFAULT, "dependencies": dependencies, "model_ready": model_ready,
            "result_download": True, "max_upload_bytes": MAX_UPLOAD_BYTES,
            "section_geometry_ready": dependencies["numpy"], "section_max_points": 5000}


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "arbor3d-cloud-dbh", "api_version": 2, "auth_required": bool(API_KEY),
            "prepare_only_default": PREPARE_ONLY_DEFAULT}


@app.get("/v1/capabilities")
def get_capabilities(request: Request, x_api_key: str | None = Header(None)) -> dict:
    require_api_key(x_api_key, request)
    return capabilities()


@app.post("/v1/sections")
async def calculate_section(request: Request, x_api_key: str | None = Header(None)) -> dict:
    require_api_key(x_api_key, request)
    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > 2 * 1024 * 1024:
            raise HTTPException(413, "Section input exceeds 2 MB")
        chunks.append(chunk)
    raw = b"".join(chunks)
    if not section_slot.acquire(blocking=False):
        raise HTTPException(429, "Section worker is busy; retry shortly")
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Section input must be an object")
        from cloud_dbh.section_compute import compute_section
        return await run_in_threadpool(compute_section, payload, raw)
    except (ValueError, TypeError, KeyError) as error:
        raise HTTPException(400, str(error)) from error
    finally:
        section_slot.release()


@app.post("/v1/jobs")
async def create_job(request: Request, scan_id: str = Form(...), path_id: str = Form(""),
                     prepare_only: bool = Form(False), archive: UploadFile = File(...),
                     x_api_key: str | None = Header(None)) -> JSONResponse:
    require_api_key(x_api_key, request)
    try:
        safe_id(scan_id)
        if path_id and (len(path_id) > 200 or any(c in path_id for c in "\r\n\x00")):
            raise ValueError("Invalid path identifier")
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    use_prepare = prepare_only or PREPARE_ONLY_DEFAULT
    if not use_prepare and not capabilities()["full_pipeline_ready"]:
        raise HTTPException(503, "Full measurement dependencies or model are not ready")
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    active = sum(1 for f in WORK_DIR.glob("*/status.json") if '"status": "queued"' in f.read_text(encoding="utf-8") or '"status": "running"' in f.read_text(encoding="utf-8"))
    if active >= 2:
        raise HTTPException(429, "Worker queue is full; retry after the current jobs finish")
    if not queue_slots.acquire(blocking=False):
        raise HTTPException(429, "Worker queue is full")
    job_id = uuid.uuid4().hex
    paths = JobPaths.create(job_id, WORK_DIR)
    upload = paths.root / "upload.zip"
    size = 0
    try:
        with upload.open("wb") as target:
            while chunk := await archive.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Archive exceeds upload limit")
                target.write(chunk)
        if size == 0:
            raise HTTPException(400, "Empty archive")
    except Exception:
        upload.unlink(missing_ok=True)
        queue_slots.release()
        raise
    finally:
        await archive.close()
    write_status(paths, "queued", "Waiting for Azure worker", scan_id=scan_id, prepare_only=use_prepare)
    try:
        future = executor.submit(execute_job, job_id=job_id, scan_id=scan_id, path_id=path_id,
                                 zip_path=upload, prepare_only=use_prepare, work_root=WORK_DIR)
        future.add_done_callback(lambda _: queue_slots.release())
    except Exception:
        queue_slots.release()
        write_status(paths, "failed", "Worker could not start", scan_id=scan_id, prepare_only=use_prepare)
        raise
    return JSONResponse(status_code=202, content={"job_id": job_id, "status": "queued", "poll_url": f"/v1/jobs/{job_id}"})


def existing_job(job_id: str) -> tuple[JobPaths, dict]:
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise HTTPException(404, "Job not found")
    paths = WORK_DIR / job_id
    if not (paths / "status.json").is_file():
        raise HTTPException(404, "Job not found")
    job = JobPaths.create(job_id, WORK_DIR)
    return job, read_status(job) or {}


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str, request: Request, x_api_key: str | None = Header(None)) -> dict:
    require_api_key(x_api_key, request)
    return existing_job(job_id)[1]


@app.get("/v1/jobs/{job_id}/result")
def get_result(job_id: str, request: Request, x_api_key: str | None = Header(None)) -> FileResponse:
    require_api_key(x_api_key, request)
    paths, status = existing_job(job_id)
    result = paths.root / "result.zip"
    if status.get("status") != "succeeded" or status.get("prepare_only") or not result.is_file():
        raise HTTPException(409, "Full measurement result is not ready")
    return FileResponse(result, media_type="application/zip", filename=f"arbor3d-{job_id}.zip")
