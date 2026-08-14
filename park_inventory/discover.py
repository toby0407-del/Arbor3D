"""階段一主流程：抽幀 → YOLO → 射線-地面 → DBSCAN → tree_registry.json。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np

from . import config
from .cameras import load_left_camera_frames, sample_frames
from .cluster_trees import cluster_detections_to_trees, trees_to_jsonable
from .detect import detect_trunks_on_frames
from .ray_ground import (
    fit_ground_plane,
    load_fisheye_intrinsics,
    mask_centroid_to_ground_point,
)


def _save_topdown_plot(trees, output_path: Path):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("⚠️ 未安裝 matplotlib，略過俯視圖。")
        return None

    fig, ax = plt.subplots(figsize=(8, 8))
    xs = [t.center_xyz[0] for t in trees]
    ys = [t.center_xyz[1] for t in trees]
    ax.scatter(xs, ys, c="green", s=60, edgecolors="black", zorder=2)
    for t in trees:
        ax.annotate(t.tree_id, (t.center_xyz[0], t.center_xyz[1]), fontsize=8)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title(f"Tree ID map ({len(trees)} trees)")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(output_path, dpi=140)
    plt.close(fig)
    print(f"俯視圖: {output_path}")
    return output_path


def discover_trees(
    cameras_json: Path | None = None,
    camera_left_dir: Path | None = None,
    calib_path: Path | None = None,
    ply_path: Path | None = None,
    output_dir: Path | None = None,
    every_n: int | None = None,
    min_distance_m: float | None = None,
    cluster_eps_m: float | None = None,
    cluster_min_points: int | None = None,
    yolo_conf: float | None = None,
) -> dict:
    cameras_json = Path(cameras_json or config.CAMERAS_JSON)
    camera_left_dir = Path(camera_left_dir or config.CAMERA_LEFT_DIR)
    calib_path = Path(calib_path or config.CALIB_PATH)
    ply_path = Path(ply_path or config.DENOISED_PLY_PATH)
    output_dir = Path(output_dir or config.DEFAULT_OUTPUT_DIR)
    every_n = every_n if every_n is not None else config.SAMPLE_EVERY_N
    min_distance_m = (
        min_distance_m if min_distance_m is not None else config.SAMPLE_MIN_DISTANCE_M
    )
    cluster_eps_m = (
        cluster_eps_m if cluster_eps_m is not None else config.TREE_CLUSTER_EPS_M
    )
    cluster_min_points = (
        cluster_min_points
        if cluster_min_points is not None
        else config.TREE_CLUSTER_MIN_POINTS
    )
    yolo_conf = yolo_conf if yolo_conf is not None else config.YOLO_CONF

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== 階段一：多樹木分群與 Tree ID ===")
    print(f"cameras.json: {cameras_json}")
    print(f"camera_left:  {camera_left_dir}")

    frames = load_left_camera_frames(cameras_json, camera_left_dir)
    print(f"left 相機幀數（有對應 jpg）: {len(frames)}")
    sampled = sample_frames(frames, every_n=every_n, min_distance_m=min_distance_m)
    print(
        f"抽樣後: {len(sampled)} 張 "
        f"(every_n={every_n}, min_distance={min_distance_m} m)"
    )

    print("\n擬合地面平面（一次）...")
    plane = fit_ground_plane(
        ply_path,
        voxel_size=config.GROUND_VOXEL_SIZE,
        dist_threshold=config.GROUND_DIST_THRESHOLD,
    )
    intr = load_fisheye_intrinsics(calib_path)

    print("\nYOLO 批次推論...")
    detections = detect_trunks_on_frames(
        sampled, conf=yolo_conf, imgsz=config.YOLO_IMGSZ
    )
    print(f"共偵測到 {len(detections)} 個 tree_trunk 實例")

    # 建立 frame_id → CameraFrame 對照
    frame_by_id = {f.frame_id: f for f in sampled}
    projected = 0
    for det in detections:
        frame = frame_by_id.get(det.frame_id)
        if frame is None:
            continue
        point, depth = mask_centroid_to_ground_point(
            det.base_uv[0],
            det.base_uv[1],
            frame.position,
            frame.rotation_c2w,
            intr["K"],
            intr["D"],
            plane,
            depth_min=config.RAY_DEPTH_MIN_M,
            depth_max=config.RAY_DEPTH_MAX_M,
        )
        if point is None:
            continue
        det.ground_xyz = point
        det.ray_depth_m = depth
        projected += 1

    print(f"成功投影到地面: {projected}/{len(detections)}")

    trees = cluster_detections_to_trees(
        detections, eps_m=cluster_eps_m, min_points=cluster_min_points
    )
    print(f"\nDBSCAN 分群結果: {len(trees)} 棵樹 (eps={cluster_eps_m} m)")

    plot_path = output_dir / "tree_id_map.png"
    _save_topdown_plot(trees, plot_path)

    registry = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "scan_id": config.SCAN_ID,
        "method": "ray_ground_intersection + DBSCAN",
        "params": {
            "sample_every_n": every_n,
            "sample_min_distance_m": min_distance_m,
            "yolo_conf": yolo_conf,
            "cluster_eps_m": cluster_eps_m,
            "cluster_min_points": cluster_min_points,
            "ray_depth_min_m": config.RAY_DEPTH_MIN_M,
            "ray_depth_max_m": config.RAY_DEPTH_MAX_M,
        },
        "stats": {
            "total_left_frames": len(frames),
            "sampled_frames": len(sampled),
            "raw_detections": len(detections),
            "projected_detections": projected,
            "num_trees": len(trees),
        },
        "trees": trees_to_jsonable(trees),
        "tree_id_map_image": str(plot_path),
    }

    out_json = output_dir / "tree_registry.json"
    out_json.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRegistry: {out_json}")
    for t in trees:
        print(
            f"  {t.tree_id}: center={t.center_xyz}, "
            f"detections={t.num_detections}, max_conf={t.max_confidence}"
        )
    return registry
