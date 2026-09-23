"""Invoke the existing Arbor3D postprocess pipeline for a cloud job."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
POSTPROCESS = REPO_ROOT / "scripts" / "postprocess_from_inbox.py"
DEFAULT_WORK = Path(os.environ.get("ARBOR3D_CLOUD_WORK_DIR", "/tmp/arbor3d-cloud-jobs"))


@dataclass
class JobPaths:
    job_id: str
    root: Path
    inbox: Path
    status_file: Path

    @classmethod
    def create(cls, job_id: str, work_root: Path | None = None) -> "JobPaths":
        root = (work_root or DEFAULT_WORK) / job_id
        inbox = root / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        return cls(job_id=job_id, root=root, inbox=inbox, status_file=root / "status.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(paths: JobPaths, status: str, message: str, **extra: Any) -> dict[str, Any]:
    payload = {
        "job_id": paths.job_id,
        "status": status,
        "message": message,
        "updated_at": utc_now(),
        **extra,
    }
    paths.status_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def read_status(paths: JobPaths) -> dict[str, Any] | None:
    if not paths.status_file.exists():
        return None
    return json.loads(paths.status_file.read_text(encoding="utf-8"))


def unpack_zip(zip_path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)


def ensure_inbox_layout(inbox: Path) -> None:
    """Accept either flat zip (raw/denoised/gaussian) or nested single top folder."""
    required = {"raw", "denoised", "gaussian"}
    present = {p.name for p in inbox.iterdir() if p.is_dir()}
    if required.issubset(present):
        return
    children = [p for p in inbox.iterdir() if p.is_dir()]
    if len(children) == 1:
        nested = children[0]
        nested_names = {p.name for p in nested.iterdir() if p.is_dir()}
        if required.issubset(nested_names):
            for name in required:
                src = nested / name
                dst = inbox / name
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.move(str(src), str(dst))
            return
    missing = sorted(required - present)
    raise FileNotFoundError(
        f"inbox 缺少資料夾：{', '.join(missing)}（需要 raw / denoised / gaussian）"
    )


def run_postprocess(
    *,
    job_dir: Path,
    scan_id: str,
    path_id: str = "",
    prepare_only: bool = False,
    python: str | None = None,
) -> None:
    if not POSTPROCESS.exists():
        raise FileNotFoundError(f"找不到管線腳本：{POSTPROCESS}")
    py = python or sys.executable
    cmd = [
        py,
        str(POSTPROCESS),
        "--job-dir",
        str(job_dir),
        "--scan-id",
        scan_id,
        "--repo-root",
        str(REPO_ROOT),
    ]
    if path_id:
        cmd.extend(["--path-id", path_id])
    if prepare_only:
        cmd.append("--prepare-only")
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    log_path = job_dir.parent / "worker.log"
    log_path.write_text(
        (completed.stdout or "") + "\n" + (completed.stderr or ""),
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"postprocess 失敗 (exit {completed.returncode})：見 {log_path}"
        )


def execute_job(
    *,
    job_id: str,
    scan_id: str,
    path_id: str = "",
    zip_path: Path | None = None,
    prepare_only: bool = False,
    work_root: Path | None = None,
) -> dict[str, Any]:
    paths = JobPaths.create(job_id, work_root)
    write_status(
        paths,
        "running",
        "雲端 DBH 管線執行中",
        scan_id=scan_id,
        path_id=path_id,
        prepare_only=prepare_only,
    )
    try:
        if zip_path is not None:
            unpack_zip(zip_path, paths.inbox)
        ensure_inbox_layout(paths.inbox)
        run_postprocess(
            job_dir=paths.inbox,
            scan_id=scan_id,
            path_id=path_id,
            prepare_only=prepare_only,
        )
        inventory = REPO_ROOT / "app" / "src" / "data" / "inventories" / f"{scan_id}.json"
        return write_status(
            paths,
            "succeeded",
            "雲端 DBH 管線完成" if not prepare_only else "已整理 inbox（prepare-only）",
            scan_id=scan_id,
            path_id=path_id,
            prepare_only=prepare_only,
            inventory_path=str(inventory) if inventory.exists() else None,
            pipeline_status=str(paths.inbox / "pipeline-status.json"),
        )
    except Exception as exc:  # noqa: BLE001 — surface to status JSON for API clients
        return write_status(
            paths,
            "failed",
            str(exc),
            scan_id=scan_id,
            path_id=path_id,
            prepare_only=prepare_only,
        )
