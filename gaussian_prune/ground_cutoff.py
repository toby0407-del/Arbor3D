"""B 計畫：3D 幾何地面截斷，繞過語意分割在魚眼照片上失效的問題。

不管照片被魚眼鏡頭扭曲成什麼樣子，在真實的 3D 世界座標系裡，地板永遠
貼在最下面。這裡對「去噪點雲」做 RANSAC 地面偵測 (去噪點雲比稀疏的高斯
球中心更適合擬合平面)，算出地面校正，再把同一組校正套用到高斯球座標，
直接依照高度砍掉貼近地面的球——完全不依賴 2D 語意判斷。
"""
import numpy as np
import open3d as o3d

import geo_utils as utils

from . import config


def ground_cutoff_mask(points_3d, ground_ply_path=None):
    """回傳布林陣列，True = 這個點的校正後高度高於地面截斷閾值 (應該保留)。"""
    ply_path = ground_ply_path or config.GROUND_PLY_PATH
    scene_pcd = o3d.io.read_point_cloud(str(ply_path))
    scene_down = scene_pcd.voxel_down_sample(voxel_size=config.GROUND_VOXEL_SIZE)
    rotation_matrix, z_offset, _ = utils.compute_ground_transform(
        scene_down, distance_threshold=config.GROUND_DIST_THRESHOLD
    )

    aligned = utils.apply_ground_transform(points_3d, rotation_matrix, z_offset)
    z = aligned[:, 2]

    # 診斷用：印出校正後高度的分佈，用實際數字判斷截斷方向對不對、
    # 閾值選得合不合理，而不是用猜的。正常情況下應該會看到一大群
    # 點集中在接近 0 (地板)，另一群比較稀疏、往上散開到好幾公尺 (樹)。
    percentiles = np.percentile(z, [0, 5, 25, 50, 75, 95, 100])
    print(
        "   [診斷] 校正後高度分佈 (公尺)："
        f"min={percentiles[0]:.2f} p5={percentiles[1]:.2f} p25={percentiles[2]:.2f} "
        f"median={percentiles[3]:.2f} p75={percentiles[4]:.2f} p95={percentiles[5]:.2f} "
        f"max={percentiles[6]:.2f}"
    )
    for threshold in (0.15, 0.5, 1.0, 2.0):
        kept = int(np.sum(z > threshold))
        print(f"   [診斷] 若門檻設為 {threshold:.2f} m，會保留 {kept:,} / {len(z):,} 個點")

    return z > config.GROUND_CUTOFF_Z_M
