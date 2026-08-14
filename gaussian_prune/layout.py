"""3DGS_Park_Model 資料夾分類：完整場景 / 單棵樹 / SuperSplat。"""
from pathlib import Path

from dbh_seg import config as dbh_config

MODEL_DIR = dbh_config.PROJECT_ROOT / "3DGS_Park_Model"
DIR_FULL = MODEL_DIR / "完整場景"
DIR_SINGLE = MODEL_DIR / "單棵樹"
DIR_SPLAT = MODEL_DIR / "SuperSplat"

# 小於這個大小就當成「已經瘦身過」，不當完整公園輸入
_FULL_SCENE_MIN_BYTES = 50 * 1024 * 1024


def resolve_full_scene_ply(scan_id: str) -> Path:
    """找出這趟掃描的完整 3D 高斯。標準檔名是 {scan_id}.ply，舊的 backup_ 當備援。"""
    names = [f"{scan_id}.ply", f"backup_{scan_id}.ply"]
    folders = [DIR_FULL, MODEL_DIR]
    large, any_hit = [], []
    for folder in folders:
        for name in names:
            path = folder / name
            if not path.exists():
                continue
            any_hit.append(path)
            if path.stat().st_size >= _FULL_SCENE_MIN_BYTES:
                large.append(path)
    if large:
        return large[0]
    if any_hit:
        return any_hit[0]
    return DIR_FULL / f"{scan_id}.ply"


def single_tree_ply(scan_id: str) -> Path:
    return DIR_SINGLE / f"{scan_id}_single_tree.ply"


def supersplat_ply(scan_id: str) -> Path:
    return DIR_SPLAT / f"{scan_id}_supersplat.ply"
