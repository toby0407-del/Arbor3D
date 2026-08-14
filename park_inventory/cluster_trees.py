"""對地面交點做 DBSCAN，賦予 Tree_ID。"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

import numpy as np
import open3d as o3d

from .detect import Detection


@dataclass
class TreeRecord:
    tree_id: str
    center_xyz: list[float]
    num_detections: int
    mean_confidence: float
    max_confidence: float
    max_mask_area_px: int
    detections: list[dict]


def cluster_detections_to_trees(
    detections: list[Detection],
    eps_m: float = 1.5,
    min_points: int = 2,
) -> list[TreeRecord]:
    valid = [d for d in detections if d.ground_xyz is not None]
    if not valid:
        return []

    xyz = np.array([d.ground_xyz for d in valid], dtype=np.float64)
    # 只用 XY 分群：把 Z 壓成同一個值，避免地形起伏干擾
    pts = xyz.copy()
    pts[:, 2] = 0.0
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts)
    labels = np.asarray(pcd.cluster_dbscan(eps=eps_m, min_points=min_points, print_progress=False))

    groups: dict[int, list[Detection]] = defaultdict(list)
    for det, label in zip(valid, labels):
        if label < 0:
            continue
        groups[int(label)].append(det)

    trees: list[TreeRecord] = []
    for label in sorted(groups.keys()):
        members = groups[label]
        pts_m = np.array([m.ground_xyz for m in members], dtype=np.float64)
        center = pts_m.mean(axis=0)
        det_dicts = []
        for m in members:
            det_dicts.append(
                {
                    "photo_path": str(m.photo_path),
                    "frame_id": m.frame_id,
                    "instance_id": m.instance_id,
                    "confidence": round(m.confidence, 4),
                    "centroid_uv": [round(m.centroid_uv[0], 1), round(m.centroid_uv[1], 1)],
                    "base_uv": [round(m.base_uv[0], 1), round(m.base_uv[1], 1)],
                    "mask_area_px": m.mask_area_px,
                    "ground_xyz": [round(float(x), 3) for x in m.ground_xyz],
                    "ray_depth_m": round(float(m.ray_depth_m), 3) if m.ray_depth_m else None,
                }
            )
        trees.append(
            TreeRecord(
                tree_id="TMP",
                center_xyz=[round(float(x), 3) for x in center],
                num_detections=len(members),
                mean_confidence=round(float(np.mean([m.confidence for m in members])), 4),
                max_confidence=round(float(max(m.confidence for m in members)), 4),
                max_mask_area_px=int(max(m.mask_area_px for m in members)),
                detections=det_dicts,
            )
        )

    trees.sort(
        key=lambda t: (t.num_detections, t.max_confidence, t.max_mask_area_px),
        reverse=True,
    )
    renumbered = []
    for i, tree in enumerate(trees, start=1):
        renumbered.append(
            TreeRecord(
                tree_id=f"Tree_{i:03d}",
                center_xyz=tree.center_xyz,
                num_detections=tree.num_detections,
                mean_confidence=tree.mean_confidence,
                max_confidence=tree.max_confidence,
                max_mask_area_px=tree.max_mask_area_px,
                detections=tree.detections,
            )
        )
    return renumbered


def trees_to_jsonable(trees: list[TreeRecord]) -> list[dict]:
    return [asdict(t) for t in trees]
