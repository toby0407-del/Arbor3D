"""把整條管線切到指定掃描 ID（去噪點雲、calib、照片、3DGS 都跟同一個 ID）。"""
from __future__ import annotations

from pathlib import Path


def scan_input_paths(scan_id: str) -> dict[str, Path]:
    """人要準備好的輸入檔（RayStudio / 掃描匯出）；程式不會幫你做這段。"""
    from dbh_seg import config as dbh_config

    root = dbh_config.PROJECT_ROOT
    from gaussian_prune.layout import DIR_FULL, resolve_full_scene_ply

    gaussian = resolve_full_scene_ply(scan_id)
    return {
        "denoised_ply": root / "3D_treedata_Denoised_Trees" / f"{scan_id}.ply",
        "calib": root / "3D_treedata" / scan_id / "calibration" / "calib.json",
        "cameras_json": root / "3D_treedata" / scan_id / "ray_gaussian" / "cameras.json",
        "camera_left": root / "3D_treedata" / scan_id / "gaussian" / "camera_left",
        "gaussian_ply": gaussian,
        "gaussian_default": DIR_FULL / f"{scan_id}.ply",
    }


def check_scan_ready(scan_id: str, need_gaussian: bool = True) -> list[str]:
    """回傳缺少的項目說明；空 list = 可以開跑。"""
    p = scan_input_paths(scan_id)
    missing = []
    if not p["denoised_ply"].exists():
        missing.append(f"去噪點雲：{p['denoised_ply']}")
    if not p["calib"].exists():
        missing.append(f"相機校正：{p['calib']}")
    if not p["cameras_json"].exists():
        missing.append(f"相機軌跡：{p['cameras_json']}")
    cam = p["camera_left"]
    if not cam.exists() or not any(cam.glob("*.jpg")):
        missing.append(f"左相機照片：{cam}\\*.jpg")
    if need_gaussian and not p["gaussian_ply"].exists():
        missing.append(f"3D 高斯：{p['gaussian_default']}")
    return missing


def apply_scan_id(scan_id: str) -> None:
    """執行期覆寫 dbh_seg / gaussian_prune / park_inventory 的路徑設定。"""
    from dbh_seg import config as dbh_config
    from gaussian_prune import config as gs_config
    from gaussian_prune.layout import resolve_full_scene_ply, single_tree_ply, supersplat_ply
    from park_inventory import config as inv_config

    root = dbh_config.PROJECT_ROOT
    dbh_config.SCAN_ID = scan_id
    dbh_config.PLY_PATH = root / "3D_treedata_Denoised_Trees" / f"{scan_id}.ply"
    dbh_config.CALIB_PATH = root / "3D_treedata" / scan_id / "calibration" / "calib.json"
    cam_dir = root / "3D_treedata" / scan_id / "gaussian" / "camera_left"
    dbh_config.SOURCE_PHOTO_PATH = cam_dir

    gs_config.GAUSSIAN_PLY_PATH = resolve_full_scene_ply(scan_id)
    gs_config.OUTPUT_PLY_PATH = single_tree_ply(scan_id)
    gs_config.SUPERSPLAT_PLY_PATH = supersplat_ply(scan_id)
    gs_config.GROUND_PLY_PATH = dbh_config.PLY_PATH
    gs_config.CALIB_PATH = dbh_config.CALIB_PATH
    gs_config.MASK_PATH = dbh_config.MASK_PATH

    inv_config.SCAN_ID = scan_id
    inv_config.CALIB_PATH = dbh_config.CALIB_PATH
    inv_config.DENOISED_PLY_PATH = dbh_config.PLY_PATH
    inv_config.CAMERA_LEFT_DIR = cam_dir
    inv_config.CAMERAS_JSON = (
        root / "3D_treedata" / scan_id / "ray_gaussian" / "cameras.json"
    )

    missing = []
    if not dbh_config.PLY_PATH.exists():
        missing.append(str(dbh_config.PLY_PATH))
    if not dbh_config.CALIB_PATH.exists():
        missing.append(str(dbh_config.CALIB_PATH))
    if missing:
        print("⚠️ 此掃描缺少檔案（可先做主掃描 20260812070325）：")
        for m in missing:
            print(f"   {m}")
    print(f"已切換掃描: {scan_id}")
    print(f"  點雲: {dbh_config.PLY_PATH}")
    print(f"  3DGS: {gs_config.GAUSSIAN_PLY_PATH}")
