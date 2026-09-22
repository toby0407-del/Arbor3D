#!/usr/bin/env python3
"""Prepare an App import job, run Arbor3D, and publish its inventory."""
from __future__ import annotations

import argparse
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SAFE_SCAN_ID = re.compile(r"^[\w.-]{1,100}$", re.UNICODE)
ASSET_FIELDS = {
    "Best_Photo": "photos",
    "Mask_Path": "masks",
    "Cross_Section_Image": "dbh",
    "3D_Model_Path": "models",
    "Single_Tree_Ply": "models",
}


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="把 Arbor3D App inbox 整理成正式管線輸入並發佈盤點結果"
    )
    parser.add_argument("--job-dir", type=Path, required=True)
    parser.add_argument("--scan-id", required=True)
    parser.add_argument("--path-id", default="")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="3D_treedata 等資料夾的上層；預設沿用既有設定（倉庫上一層）",
    )
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--python", default=sys.executable)
    return parser.parse_args()


def write_status(job_dir: Path, status: str, message: str, **extra: Any) -> None:
    payload = {"status": status, "message": message, **extra}
    target = job_dir / "pipeline-status.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(target)


def find_one(root: Path, name_or_suffix: str) -> Path:
    if not root.exists():
        raise FileNotFoundError(f"找不到資料夾：{root}")
    lowered = name_or_suffix.lower()
    if lowered.startswith("."):
        matches = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == lowered)
    else:
        matches = sorted(p for p in root.rglob("*") if p.is_file() and p.name.lower() == lowered)
    if not matches:
        raise FileNotFoundError(f"{root} 內找不到 {name_or_suffix}")
    if len(matches) > 1:
        print(f"⚠️ 找到多個 {name_or_suffix}，使用：{matches[0]}")
    return matches[0]


def link_or_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        try:
            if source.samefile(destination):
                return
        except OSError:
            pass
        if filecmp.cmp(source, destination, shallow=False):
            return
        raise FileExistsError(f"目的檔已存在且內容不同，為避免覆寫已中止：{destination}")
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def load_json(path: Path, label: str) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} 不是有效 JSON：{path}（{exc}）") from exc
    if not isinstance(value, (dict, list)) or not value:
        raise ValueError(f"{label} 必須是非空白的 JSON 物件或陣列：{path}")
    return value


def prepare_inputs(job_dir: Path, scan_id: str, data_root: Path) -> dict[str, Any]:
    denoised = find_one(job_dir / "denoised", ".ply")
    gaussian = find_one(job_dir / "gaussian", ".ply")
    metadata_roots = [job_dir / "metadata", job_dir / "raw"]

    def find_metadata(name: str) -> Path:
        for root in metadata_roots:
            try:
                return find_one(root, name)
            except FileNotFoundError:
                continue
        raise FileNotFoundError(f"缺少 {name}；請上傳相機校正／姿態資料夾")

    calib = find_metadata("calib.json")
    cameras = find_metadata("cameras.json")
    load_json(calib, "calib.json")
    load_json(cameras, "cameras.json")

    photo_root = job_dir / "raw" / "go"
    photos = sorted(p for p in photo_root.rglob("*.jpg") if p.is_file())
    if not photos:
        raise FileNotFoundError(
            f"{photo_root} 沒有 .jpg；正式管線目前需要 RayStudio 左相機 JPG"
        )

    denoised_dest = data_root / "3D_treedata_Denoised_Trees" / f"{scan_id}.ply"
    gaussian_dest = data_root / "3DGS_Park_Model" / "完整場景" / f"{scan_id}.ply"
    scan_root = data_root / "3D_treedata" / scan_id
    calib_dest = scan_root / "calibration" / "calib.json"
    cameras_dest = scan_root / "ray_gaussian" / "cameras.json"
    photos_dest = scan_root / "gaussian" / "camera_left"

    link_or_copy(denoised, denoised_dest)
    link_or_copy(gaussian, gaussian_dest)
    link_or_copy(calib, calib_dest)
    link_or_copy(cameras, cameras_dest)
    for photo in photos:
        link_or_copy(photo, photos_dest / photo.name)

    return {
        "denoised": str(denoised_dest),
        "gaussian": str(gaussian_dest),
        "calib": str(calib_dest),
        "cameras": str(cameras_dest),
        "photos_dir": str(photos_dest),
        "photo_count": len(photos),
    }


def resolve_asset(source_value: str, output_dir: Path, data_root: Path) -> Path | None:
    source = Path(source_value)
    candidates = [source] if source.is_absolute() else [output_dir / source, data_root / source]
    return next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)


def publish_report(
    report_path: Path,
    output_dir: Path,
    repo_root: Path,
    data_root: Path,
    scan_id: str,
    path_id: str,
) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or not isinstance(report.get("trees"), list):
        raise ValueError(f"正式管線報告格式不正確：{report_path}")

    public_dir = repo_root / "app" / "public" / "scans" / scan_id
    inventory_dir = repo_root / "app" / "src" / "data" / "inventories"
    public_dir.mkdir(parents=True, exist_ok=True)
    inventory_dir.mkdir(parents=True, exist_ok=True)

    for index, tree in enumerate(report["trees"]):
        if not isinstance(tree, dict):
            continue
        tree_id = re.sub(r"[^\w.-]+", "_", str(tree.get("Tree_ID") or f"tree_{index + 1}"))
        for field, folder in ASSET_FIELDS.items():
            value = tree.get(field)
            if not isinstance(value, str) or not value:
                continue
            source = resolve_asset(value, output_dir, data_root)
            if source is None:
                print(f"⚠️ 報告附件不存在，保留空值：{field}={value}")
                tree[field] = None
                continue
            destination = public_dir / folder / f"{tree_id}_{source.name}"
            link_or_copy(source, destination)
            tree[field] = destination.relative_to(public_dir).as_posix()

    report["scan_id"] = scan_id
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    (public_dir / "inventory.json").write_text(rendered, encoding="utf-8")
    (inventory_dir / f"{scan_id}.json").write_text(rendered, encoding="utf-8")

    for name in (
        "park_inventory_report.csv",
        "park_inventory_report.html",
        "tree_id_map_dbh.png",
        "dbh_markers.ply",
    ):
        source = output_dir / name
        if source.is_file():
            link_or_copy(source, public_dir / "reports" / name)

    if path_id:
        bindings_path = repo_root / "app" / "public" / "scans" / "_bindings.json"
        try:
            bindings = json.loads(bindings_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            bindings = {}
        if not isinstance(bindings, dict):
            raise ValueError(f"路徑綁定檔不是 JSON 物件：{bindings_path}")
        bindings[path_id] = scan_id
        bindings_path.parent.mkdir(parents=True, exist_ok=True)
        bindings_path.write_text(
            json.dumps(bindings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return report


def main() -> int:
    args = parse_args()
    job_dir = args.job_dir.resolve()
    repo_root = args.repo_root.resolve()
    data_root = (args.data_root or repo_root.parent).resolve()
    scan_id = args.scan_id.strip()
    if not SAFE_SCAN_ID.fullmatch(scan_id) or scan_id in {".", ".."}:
        raise ValueError("scan-id 只能包含文字、數字、底線、連字號與句點")

    prepared = prepare_inputs(job_dir, scan_id, data_root)
    if args.prepare_only:
        message = f"正式管線輸入已備妥（{prepared['photo_count']} 張 JPG）"
        write_status(job_dir, "prepared", message, prepared=prepared)
        print(message)
        return 0

    runner = repo_root / "run_full_park_pipeline.py"
    if not runner.is_file():
        raise FileNotFoundError(f"找不到正式管線：{runner}")
    output_dir = job_dir / "official-output"
    command = [
        args.python,
        str(runner),
        "--scan_id",
        scan_id,
        "--output_dir",
        str(output_dir),
    ]
    print("正式 Arbor3D 管線開始")
    subprocess.run(command, cwd=repo_root, check=True)
    report_path = output_dir / "park_inventory_report.json"
    if not report_path.is_file():
        raise FileNotFoundError(f"管線完成但找不到報告：{report_path}")
    report = publish_report(
        report_path, output_dir, repo_root, data_root, scan_id, args.path_id.strip()
    )
    count = int(report.get("num_trees") or len(report.get("trees") or []))
    message = f"正式 Arbor3D 盤點與發佈完成：{count} 棵"
    write_status(
        job_dir,
        "done",
        message,
        prepared=prepared,
        inventory=str(repo_root / "app" / "public" / "scans" / scan_id / "inventory.json"),
    )
    print(message)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        raw_job = next(
            (sys.argv[i + 1] for i, value in enumerate(sys.argv[:-1]) if value == "--job-dir"),
            "",
        )
        if raw_job:
            write_status(Path(raw_job).resolve(), "error", str(exc))
        print(f"❌ {exc}", file=sys.stderr)
        raise SystemExit(1)
