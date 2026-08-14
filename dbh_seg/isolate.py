"""用相機矩陣 + YOLO 遮罩，從完整點雲剝離出樹幹弧面點雲 (含遮蔽過濾)。"""
import numpy as np

import geo_utils as utils

from . import config
from .mask_fusion import fuse_masks, load_binary_mask


def isolate_tree_points(pcd, calib_data, mask_path, camera_pose=None):
    """
    複製 test_3d.py 已驗證過的邏輯：用相機矩陣 + YOLO 遮罩，剝離出樹幹弧面點雲，
    再套用 Z-Buffer 遮蔽過濾，避免視線背後的其他樹幹混進來。

    camera_pose: 可選 (position, rotation_c2w)，來自 cameras.json 單幀姿態。
    多樹木時每張遮罩對應不同拍攝位置，必須覆寫 calib.json 裡那組固定外參。
    """
    cam = utils.build_camera_model(calib_data)
    if camera_pose is not None:
        position, rotation_c2w = camera_pose
        cam = utils.apply_c2w_pose(cam, position, rotation_c2w)
        print("   已套用該張照片的 cameras.json 世界姿態（而非 calib 固定外參）")

    # NumPy 讀取二進制資料再交由 OpenCV 解碼，繞過中文路徑限制
    mask = load_binary_mask(mask_path, (cam["width"], cam["height"]))
    mask = fuse_masks(
        mask, config.SECONDARY_MASK_PATH, (cam["width"], cam["height"]),
        threshold=config.SECONDARY_MASK_THRESHOLD, mode=config.SECONDARY_MASK_MODE,
    )

    points_3d = np.asarray(pcd.points)
    colors_3d = np.asarray(pcd.colors) if pcd.has_colors() else None

    is_tree, u, v, depth = utils.points_in_mask(
        points_3d, cam, mask, config.DEPTH_MIN, config.DEPTH_MAX
    )

    # 🚨 關鍵修正：Z-Buffer 遮蔽過濾，避免視線背後的其他樹幹混進來
    candidate_idx = np.where(is_tree)[0]
    occlusion_keep = utils.apply_depth_buffer_filter(
        depth[candidate_idx],
        u[candidate_idx],
        v[candidate_idx],
        cam["width"],
        cam["height"],
        tolerance=config.OCCLUSION_TOLERANCE_M,
    )
    refined_idx = candidate_idx[occlusion_keep]
    print(
        f"   遮蔽過濾 (Z-Buffer)：{len(candidate_idx):,} -> {len(refined_idx):,} 個點 "
        f"(濾除視線背後其他樹幹造成的混雜)"
    )

    is_tree_final = np.zeros(len(points_3d), dtype=bool)
    is_tree_final[refined_idx] = True

    tree_points = points_3d[is_tree_final]
    tree_colors = colors_3d[is_tree_final] if colors_3d is not None else None
    return tree_points, tree_colors
