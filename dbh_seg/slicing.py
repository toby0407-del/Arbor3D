"""地面校正 + 胸高切片：把樹幹點雲擺正，切出 1.2m~1.4m 的胸高薄片。"""
import numpy as np
import open3d as o3d

import geo_utils as utils

from . import config


def align_to_ground(pcd, tree_points):
    """對完整場景做 RANSAC 地面偵測，並把同一組校正套用到樹幹點雲上。"""
    aligned, _, _ = ground_align_points(pcd, tree_points)
    return aligned


def ground_align_points(pcd, tree_points):
    """回傳 (校正後樹幹點, 旋轉矩陣, Z 偏移)，方便把相機位置轉到同一座標系。"""
    scene_down = pcd.voxel_down_sample(voxel_size=config.GROUND_VOXEL_SIZE)
    rotation_matrix, z_offset, _ = utils.compute_ground_transform(
        scene_down,
        distance_threshold=config.GROUND_DIST_THRESHOLD,
        ransac_n=3,
        num_iterations=1000,
    )
    print(f"   地面校正完成 (Z 軸偏移量 = {z_offset:.3f} m)")
    aligned = utils.apply_ground_transform(tree_points, rotation_matrix, z_offset)
    return aligned, rotation_matrix, z_offset


def extract_breast_height_slice(aligned_tree_points):
    """從已校正的樹幹點雲中，切出胸高範圍的薄片，並做二次分群清潔。

    若 1.2~1.4 m 沒有足夠點（最佳照片常只拍到中上段樹幹），
    改切「最接近胸高、且點數足夠」的 0.2 m 視窗，並在終端機標註備援。
    """
    z = aligned_tree_points[:, 2]
    print(f"   校正後樹幹點雲離地高度範圍: {z.min():.2f} m ~ {z.max():.2f} m")

    z_min, z_max = config.SLICE_Z_MIN, config.SLICE_Z_MAX
    slice_mask = (z >= z_min) & (z <= z_max)
    slice_pts = aligned_tree_points[slice_mask]
    print(f"   胸高切片 ({z_min:.2f}~{z_max:.2f} m) 內共有 {len(slice_pts)} 個點。")

    if len(slice_pts) < config.MIN_SLICE_POINTS:
        z_min, z_max, slice_pts = _fallback_height_window(aligned_tree_points, z)
        if slice_pts is None:
            return aligned_tree_points[:0]
        print(
            f"   ⚠️ 標準胸高無足夠點，改用備援切片 {z_min:.2f}~{z_max:.2f} m "
            f"（{len(slice_pts)} 點）。此 DBH 不是嚴格 1.3 m 胸高。"
        )

    print("   對切片再做一次 DBSCAN，只保留最大的弧面群集 (送進圓擬合前的最後保險)...")
    slice_pcd = o3d.geometry.PointCloud()
    slice_pcd.points = o3d.utility.Vector3dVector(slice_pts)
    slice_pcd, slice_clusters = utils.keep_largest_cluster(
        slice_pcd, eps=config.SLICE_CLUSTER_EPS, min_points=config.SLICE_CLUSTER_MIN_POINTS
    )
    if slice_clusters:
        slice_pts = np.asarray(slice_pcd.points)
        print(f"   切片分群結果：共 {slice_clusters} 群，保留最大群集 {len(slice_pts)} 個點。")
    else:
        print("   ⚠️ 切片分群沒找到有效群集，維持原切片點雲。")

    return slice_pts


def _fallback_height_window(aligned_tree_points, z):
    """在 0.8~2.5 m 之間滑動 0.2 m 視窗，選最接近 1.3 m 且點數足夠的一段。"""
    window = config.SLICE_Z_MAX - config.SLICE_Z_MIN
    target = 0.5 * (config.SLICE_Z_MIN + config.SLICE_Z_MAX)
    best = None
    for start in np.arange(0.80, 2.50, 0.05):
        end = start + window
        pts = aligned_tree_points[(z >= start) & (z <= end)]
        if len(pts) < config.MIN_SLICE_POINTS:
            continue
        dist = abs(0.5 * (start + end) - target)
        if best is None or dist < best[0]:
            best = (dist, start, end, pts)
    if best is not None:
        return best[1], best[2], best[3]

    # 再退一步：用實際抓到的最低 0.2 m
    lo = float(z.min())
    if lo < 0.3:
        return None, None, None
    hi = lo + window
    pts = aligned_tree_points[(z >= lo) & (z <= hi)]
    if len(pts) < config.MIN_SLICE_POINTS:
        return None, None, None
    return lo, hi, pts
