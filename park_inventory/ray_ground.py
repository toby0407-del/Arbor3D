"""魚眼像素 → 相機射線 → 與地面平面交點。"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import open3d as o3d


def load_fisheye_intrinsics(calib_path: Path) -> dict:
    calib = json.loads(Path(calib_path).read_text(encoding="utf-8"))
    left = calib["camera_info"]["left"]
    return {
        "K": np.array(left["K"], dtype=np.float64).reshape(3, 3),
        "D": np.array(left["coeff"], dtype=np.float64).reshape(4, 1),
        "width": int(left["image_width"]),
        "height": int(left["image_height"]),
    }


def fit_ground_plane(ply_path: Path, voxel_size: float = 0.2, dist_threshold: float = 0.25):
    """RANSAC 擬合地面平面 ax+by+cz+d=0，回傳 (a,b,c,d)。"""
    pcd = o3d.io.read_point_cloud(str(ply_path))
    down = pcd.voxel_down_sample(voxel_size=voxel_size)
    plane_model, inliers = down.segment_plane(
        distance_threshold=dist_threshold, ransac_n=3, num_iterations=2000
    )
    a, b, c, d = [float(x) for x in plane_model]
    if c < 0:
        a, b, c, d = -a, -b, -c, -d
    print(
        f"   地面平面: {a:.4f}x + {b:.4f}y + {c:.4f}z + {d:.4f} = 0 "
        f"(inliers={len(inliers):,}/{len(down.points):,})"
    )
    return np.array([a, b, c, d], dtype=np.float64)


def pixel_to_ray_dir_cam(u: float, v: float, K: np.ndarray, D: np.ndarray) -> np.ndarray:
    """魚眼像素 → 相機座標系單位方向向量。"""
    pts = np.array([[[u, v]]], dtype=np.float64)
    undist = cv2.fisheye.undistortPoints(pts, K, D)
    x, y = float(undist[0, 0, 0]), float(undist[0, 0, 1])
    direction = np.array([x, y, 1.0], dtype=np.float64)
    n = np.linalg.norm(direction)
    if n < 1e-12:
        return np.array([0.0, 0.0, 1.0])
    return direction / n


def ray_plane_intersection(
    origin: np.ndarray,
    direction: np.ndarray,
    plane: np.ndarray,
    depth_min: float = 1.0,
    depth_max: float = 40.0,
):
    """射線 O+tD 與平面 ax+by+cz+d=0 求交。成功回傳 (point, t)，失敗回傳 (None, None)。"""
    a, b, c, d = plane
    denom = a * direction[0] + b * direction[1] + c * direction[2]
    if abs(denom) < 1e-9:
        return None, None
    t = -(a * origin[0] + b * origin[1] + c * origin[2] + d) / denom
    if t < depth_min or t > depth_max:
        return None, None
    return origin + t * direction, float(t)


def mask_centroid_to_ground_point(
    u: float,
    v: float,
    camera_position: np.ndarray,
    rotation_c2w: np.ndarray,
    K: np.ndarray,
    D: np.ndarray,
    plane: np.ndarray,
    depth_min: float = 1.0,
    depth_max: float = 40.0,
):
    """2D 遮罩中心 → 射線與地面交點（世界座標）。"""
    dir_cam = pixel_to_ray_dir_cam(u, v, K, D)
    dir_world = rotation_c2w @ dir_cam
    dir_world = dir_world / (np.linalg.norm(dir_world) + 1e-12)
    return ray_plane_intersection(
        camera_position, dir_world, plane, depth_min=depth_min, depth_max=depth_max
    )
