"""Bounded cloud archives and verified result installation (no ML dependencies)."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

MAX_EXPANDED = 6 * 1024**3
MAX_ENTRIES = 20000


def safe_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,99}", value) or value in {".", ".."}:
        raise ValueError("Invalid record identifier")
    return value


def safe_member(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if not name or "\\" in name or ":" in name or path.is_absolute() or ".." in path.parts:
        raise ValueError("Unsafe archive path")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unpack_zip(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        if len(entries) > MAX_ENTRIES or sum(e.file_size for e in entries) > MAX_EXPANDED:
            raise ValueError("Archive exceeds expanded size or file count limit")
        seen: set[str] = set()
        for entry in entries:
            safe_member(entry.filename)
            if entry.filename.casefold() in seen:
                raise ValueError("Duplicate archive member")
            seen.add(entry.filename.casefold())
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("Archive symlinks are not supported")
        destination.mkdir(parents=True, exist_ok=True)
        for entry in entries:
            target = destination.joinpath(*safe_member(entry.filename).parts)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(entry) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)


def pack_inbox(inbox: Path, archive: Path) -> None:
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as bundle:
        for folder in ("raw", "denoised", "gaussian", "metadata"):
            for file in sorted((inbox / folder).rglob("*")):
                if file.is_symlink():
                    raise ValueError("Input symlinks are not supported")
                if file.is_file():
                    bundle.write(file, file.relative_to(inbox).as_posix())


def build_result(scan_dir: Path, scan_id: str, archive: Path) -> dict:
    safe_id(scan_id)
    report = json.loads((scan_dir / "inventory.json").read_text(encoding="utf-8"))
    if report.get("scan_id") != scan_id or not isinstance(report.get("trees"), list) or not report["trees"]:
        raise ValueError("No valid full-pipeline inventory was produced")
    manifest = {"schema_version": 1, "pipeline": "arbor3d", "mode": "full", "scan_id": scan_id, "files": []}
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as bundle:
        for file in sorted(scan_dir.rglob("*")):
            if file.is_symlink():
                raise ValueError("Result symlinks are not supported")
            if file.is_file():
                name = file.relative_to(scan_dir).as_posix()
                safe_member(name)
                manifest["files"].append({"path": name, "bytes": file.stat().st_size, "sha256": sha256(file)})
                bundle.write(file, name)
        bundle.writestr("cloud-manifest.json", json.dumps(manifest, ensure_ascii=False))
    return manifest


def install_result(archive: Path, app_root: Path, scan_id: str, path_id: str = "") -> dict:
    safe_id(scan_id)
    destination = app_root / "public" / "scans" / scan_id
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".cloud-result-", dir=destination.parent) as temporary:
        staged = Path(temporary) / "unpacked"
        unpack_zip(archive, staged)
        manifest = json.loads((staged / "cloud-manifest.json").read_text(encoding="utf-8"))
        if (manifest.get("scan_id"), manifest.get("pipeline"), manifest.get("mode"), manifest.get("schema_version")) != (scan_id, "arbor3d", "full", 1):
            raise ValueError("Cloud result provenance does not match the requested scan")
        expected = set()
        for entry in manifest["files"]:
            rel = safe_member(entry["path"])
            file = staged.joinpath(*rel.parts)
            if not file.is_file() or file.stat().st_size != entry["bytes"] or sha256(file) != entry["sha256"]:
                raise ValueError("Cloud result checksum mismatch")
            expected.add(rel.as_posix())
        actual = {file.relative_to(staged).as_posix() for file in staged.rglob("*") if file.is_file()}
        if actual != expected | {"cloud-manifest.json"} or "inventory.json" not in expected:
            raise ValueError("Cloud result manifest is incomplete")
        report = json.loads((staged / "inventory.json").read_text(encoding="utf-8"))
        if report.get("scan_id") != scan_id or not isinstance(report.get("trees"), list) or not report["trees"]:
            raise ValueError("Cloud inventory is empty or belongs to another scan")
        # Import IDs are unique; never overwrite an existing observation batch.
        if destination.exists():
            raise FileExistsError("Scan already exists; import the result as a new batch")
        staged.rename(destination)
    if path_id:
        bindings_file = app_root / "public" / "scans" / "_bindings.json"
        bindings = json.loads(bindings_file.read_text(encoding="utf-8")) if bindings_file.exists() else {}
        bindings[path_id] = scan_id
        temporary = bindings_file.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(bindings, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(bindings_file)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pack = sub.add_parser("pack")
    pack.add_argument("--inbox", type=Path, required=True)
    pack.add_argument("--archive", type=Path, required=True)
    install = sub.add_parser("install")
    install.add_argument("--archive", type=Path, required=True)
    install.add_argument("--app-root", type=Path, required=True)
    install.add_argument("--scan-id", required=True)
    install.add_argument("--path-id", default="")
    args = parser.parse_args()
    if args.command == "pack":
        pack_inbox(args.inbox, args.archive)
    else:
        report = install_result(args.archive, args.app_root, args.scan_id, args.path_id)
        print(json.dumps({"scan_id": args.scan_id, "tree_count": len(report["trees"])}))
