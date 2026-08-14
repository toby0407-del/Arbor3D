"""把整座公園場景的 3D 高斯模型，依照 YOLO(+可選 SegFormer) 遮罩
「物理刪減」成只剩目標那一棵樹，大幅縮小檔案、聚焦成果展示。
"""
import json
import os
from pathlib import Path

import numpy as np
import open3d as o3d

import geo_utils as utils
from dbh_seg.mask_fusion import fuse_masks, load_binary_mask

from . import config
from .convert_for_supersplat import convert_ply_for_supersplat
from .ground_cutoff import ground_cutoff_mask
from .ply_io import load_ply_vertices, save_ply_vertices


def prune_gaussian_to_single_tree(
    input_ply=None,
    mask_path=None,
    calib_path=None,
    tree_id=None,
    output_dir=None,
    ground_ply=None,
    secondary_mask_path=None,
    make_supersplat=True,
    source_photo_path=None,
):
    """可覆寫路徑的高斯瘦身。未指定參數時沿用 gaussian_prune/config.py。"""
    input_ply = Path(input_ply) if input_ply else config.GAUSSIAN_PLY_PATH
    mask_path = Path(mask_path) if mask_path else config.MASK_PATH
    calib_path = Path(calib_path) if calib_path else config.CALIB_PATH
    ground_ply = Path(ground_ply) if ground_ply else config.GROUND_PLY_PATH
    secondary = (
        Path(secondary_mask_path)
        if secondary_mask_path is not None
        else config.SECONDARY_MASK_PATH
    )

    if output_dir:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        if tree_id:
            output_ply = out_dir / f"{tree_id}_single_tree.ply"
            supersplat_ply = out_dir / f"{tree_id}_supersplat.ply"
        else:
            output_ply = out_dir / config.OUTPUT_PLY_PATH.name
            supersplat_ply = out_dir / config.SUPERSPLAT_PLY_PATH.name
    else:
        output_ply = config.OUTPUT_PLY_PATH
        supersplat_ply = config.SUPERSPLAT_PLY_PATH
        if tree_id:
            output_ply = output_ply.with_name(f"{tree_id}_single_tree.ply")
            supersplat_ply = supersplat_ply.with_name(f"{tree_id}_supersplat.ply")
        output_ply.parent.mkdir(parents=True, exist_ok=True)
        supersplat_ply.parent.mkdir(parents=True, exist_ok=True)

    if tree_id:
        print(f"🌳 Tree ID: {tree_id}")

    print(f"讀取高斯模型: {input_ply}")
    vertices, header_lines = load_ply_vertices(input_ply)
    print(f"   原始高斯球數量: {len(vertices):,} 個")

    with open(str(calib_path), "r", encoding="utf-8") as f:
        calib_data = json.load(f)
    cam = utils.build_camera_model(calib_data)
    if source_photo_path:
        from park_inventory.cameras import find_frame_for_photo

        frame = find_frame_for_photo(source_photo_path)
        if frame is None:
            print(f"   ⚠️ 找不到照片對應的 cameras.json 幀: {source_photo_path}")
        else:
            cam = utils.apply_c2w_pose(cam, frame.position, frame.rotation_c2w)
            print(f"   已套用幀姿態: {frame.img_name}")

    mask = load_binary_mask(mask_path, (cam["width"], cam["height"]))
    mask = fuse_masks(
        mask, secondary, (cam["width"], cam["height"]),
        threshold=config.SECONDARY_MASK_THRESHOLD, mode=config.SECONDARY_MASK_MODE,
    )

    points_3d = np.stack(
        [vertices["x"], vertices["y"], vertices["z"]], axis=1
    ).astype(np.float64)
    is_in_mask, u, v, depth = utils.points_in_mask(
        points_3d, cam, mask, config.DEPTH_MIN, config.DEPTH_MAX
    )
    candidate_idx = np.where(is_in_mask)[0]
    print(f"   落在遮罩範圍內的高斯球: {len(candidate_idx):,} 個")

    occlusion_keep = utils.apply_depth_buffer_filter(
        depth[candidate_idx], u[candidate_idx], v[candidate_idx],
        cam["width"], cam["height"], tolerance=config.GAUSSIAN_OCCLUSION_TOLERANCE_M,
    )
    surface_idx = candidate_idx[occlusion_keep]
    print(f"   遮蔽過濾後 (排除視線背後的其他樹/背景): {len(surface_idx):,} 個")

    above_ground = ground_cutoff_mask(points_3d[surface_idx], ground_ply_path=ground_ply)
    surface_idx = surface_idx[above_ground]
    print(
        f"   地面截斷 (Z > {config.GROUND_CUTOFF_Z_M} m)："
        f"{len(surface_idx):,} 個 (物理砍斷跟地板的連結)"
    )

    tmp_pcd = o3d.geometry.PointCloud()
    tmp_pcd.points = o3d.utility.Vector3dVector(points_3d[surface_idx])
    keep_in_surface, num_clusters = utils.largest_cluster_indices(
        tmp_pcd, eps=config.CLUSTER_EPS, min_points=config.CLUSTER_MIN_POINTS, verbose=True
    )
    if keep_in_surface is None:
        print("   ⚠️ DBSCAN 沒找到有效群集 (太稀疏)，跳過這道保險。")
        final_idx = surface_idx
    else:
        final_idx = surface_idx[keep_in_surface]
        print(
            f"   DBSCAN 共發現 {num_clusters} 群，"
            f"保留最大連續群集: {len(final_idx):,} 個高斯球"
        )

    final_xyz = points_3d[final_idx]
    bbox_min, bbox_max = final_xyz.min(axis=0), final_xyz.max(axis=0)
    print(
        "   [診斷] 最終保留點雲的原始座標包絡範圍 (未校正)："
        f"X[{bbox_min[0]:.2f}, {bbox_max[0]:.2f}] "
        f"Y[{bbox_min[1]:.2f}, {bbox_max[1]:.2f}] "
        f"Z[{bbox_min[2]:.2f}, {bbox_max[2]:.2f}]"
    )

    save_ply_vertices(output_ply, vertices[final_idx], header_lines)

    orig_mb = os.path.getsize(input_ply) / (1024 * 1024)
    new_mb = os.path.getsize(output_ply) / (1024 * 1024)
    print(
        f"完成！{orig_mb:.1f} MB -> {new_mb:.1f} MB "
        f"(瘦身 {100 - new_mb / orig_mb * 100:.0f}%)"
    )
    print(f"輸出檔案: {output_ply}")

    if make_supersplat:
        convert_ply_for_supersplat(output_ply, supersplat_ply)
        print(f"SuperSplat 用: {supersplat_ply}")

    return {
        "tree_id": tree_id,
        "output_ply": str(output_ply),
        "supersplat_ply": str(supersplat_ply) if make_supersplat else None,
        "num_gaussians": int(len(final_idx)),
    }
