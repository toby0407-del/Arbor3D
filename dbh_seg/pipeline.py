"""整合流程：讀檔 -> 剝離樹幹 -> 清潔 -> 地面校正+切片 -> 圓形擬合 -> 視覺化。"""
import json
from pathlib import Path

import numpy as np
import open3d as o3d

import geo_utils as utils

from . import config
from .cleanup import clean_tree_points
from .dbh_estimate import estimate_dbh
from .export import export_result
from .isolate import isolate_tree_points
from .plot2d import save_slice_plot
from .report import report_dbh
from .slicing import extract_breast_height_slice, ground_align_points
from .viz import visualize


def _resolve_paths(ply_path=None, calib_path=None, mask_path=None, output_dir=None):
    ply = Path(ply_path) if ply_path else config.PLY_PATH
    calib = Path(calib_path) if calib_path else config.CALIB_PATH
    mask = Path(mask_path) if mask_path else config.MASK_PATH
    out_dir = Path(output_dir) if output_dir else config.BASE_DIR
    return ply, calib, mask, out_dir


def _load_inputs(ply_path, calib_path, mask_path):
    for label, path in [
        ("點雲", ply_path),
        ("相機參數", calib_path),
        ("YOLO 遮罩", mask_path),
    ]:
        if not path.exists():
            print(f"❌ 找不到{label}檔案: {path}")
            return None, None

    print(f"正在讀取點雲檔案 (檔案較大，請耐心稍候): {ply_path}")
    pcd = o3d.io.read_point_cloud(str(ply_path))
    print(f"原始點數: {len(pcd.points):,}")
    if len(pcd.points) == 0:
        print("錯誤：讀取到的點雲是空的，請確認檔案是否正確。")
        return None, None

    with open(calib_path, "r", encoding="utf-8") as f:
        calib_data = json.load(f)
    return pcd, calib_data


def calculate_dbh_for_segmented_tree(
    show_viz: bool = True,
    mask_path=None,
    ply_path=None,
    calib_path=None,
    tree_id=None,
    output_dir=None,
    export: bool = True,
    source_photo_path=None,
    results_json=None,
):
    ply, calib, mask, out_dir = _resolve_paths(
        ply_path, calib_path, mask_path, output_dir
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    pcd, calib_data = _load_inputs(ply, calib, mask)
    if pcd is None:
        return None

    if tree_id:
        print(f"\n🌳 Tree ID: {tree_id}")

    print("\n🎯 步驟 1/4：用 YOLO 遮罩剝離樹幹弧面點雲...")
    camera_pose = None
    if source_photo_path:
        from park_inventory.cameras import find_frame_for_photo

        frame = find_frame_for_photo(source_photo_path)
        if frame is None:
            print(f"   ⚠️ 找不到照片對應的 cameras.json 幀，改用 calib.json 固定外參: {source_photo_path}")
        else:
            camera_pose = (frame.position, frame.rotation_c2w)
            print(f"   對應幀: {frame.img_name}  相機位置={np.round(frame.position, 3).tolist()}")

    tree_points, tree_colors = isolate_tree_points(
        pcd, calib_data, mask, camera_pose=camera_pose
    )
    print(f"   從 {len(pcd.points):,} 個點中，剝離出 {len(tree_points):,} 個樹幹點。")
    if len(tree_points) < config.MIN_SLICE_POINTS:
        print("❌ 剝離出的樹幹點太少，無法繼續計算，請確認遮罩與點雲是否對應正確。")
        return None

    _, tree_points = clean_tree_points(tree_points, tree_colors)

    print("\n🎯 步驟 2/4：對完整場景做 RANSAC 地面偵測，取得水平校正矩陣...")
    aligned_tree_points, rotation_matrix, z_offset = ground_align_points(pcd, tree_points)

    print("\n🎯 步驟 3/4：把地面校正套用到樹幹點雲，並切出胸高切片 (Z = 1.2m~1.4m)...")
    slice_pts = extract_breast_height_slice(aligned_tree_points)
    if len(slice_pts) < config.MIN_SLICE_POINTS:
        print(f"❌ 胸高切片內點數不足 ({len(slice_pts)} < {config.MIN_SLICE_POINTS})，")
        print("   可能是這次掃描沒有涵蓋到 1.2m~1.4m 的高度，請確認上面印出的高度範圍是否合理，")
        print("   或調整 dbh_seg/config.py 裡的 SLICE_Z_MIN / SLICE_Z_MAX 再試一次。")
        return None

    camera_xy = None
    if camera_pose is not None:
        cam_world = np.asarray(camera_pose[0], dtype=float).reshape(1, 3)
        cam_aligned = utils.apply_ground_transform(cam_world, rotation_matrix, z_offset)[0]
        camera_xy = cam_aligned[:2]

    print("\n🎯 步驟 4/4：評估涵蓋角度，用圓形擬合或可見寬度法計算 DBH...")
    result = estimate_dbh(slice_pts, camera_xy=camera_xy)

    report_dbh(result)

    plot_name = (
        f"dbh_slice_top_down_{tree_id}.png" if tree_id else "dbh_slice_top_down.png"
    )
    plot_path = out_dir / plot_name
    save_slice_plot(slice_pts, result, out_path=plot_path)

    if export:
        json_path = results_json or (out_dir / "dbh_results.json")
        export_result(
            result,
            slice_pts,
            out_path=json_path,
            source_photo_path=source_photo_path or config.SOURCE_PHOTO_PATH,
            tree_id=tree_id,
            mask_path=mask,
            cross_section_image=plot_path,
            slice_z_min=float(slice_pts[:, 2].min()),
            slice_z_max=float(slice_pts[:, 2].max()),
        )

    if show_viz:
        visualize(aligned_tree_points, slice_pts, result)
    return result
