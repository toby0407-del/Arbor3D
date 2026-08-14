"""讀取 cameras.json、對應 camera_left 照片，並依距離/幀數抽樣。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class CameraFrame:
    frame_id: int
    img_name: str
    photo_path: Path
    position: np.ndarray  # (3,) camera center in world
    rotation_c2w: np.ndarray  # (3, 3) camera-to-world


def _stem_from_img_name(img_name: str) -> str:
    # l_1786489451.196078.png -> 1786489451.196078
    name = Path(img_name).stem
    if name.startswith("l_") or name.startswith("r_"):
        name = name[2:]
    return name


def load_left_camera_frames(cameras_json: Path, camera_left_dir: Path) -> list[CameraFrame]:
    """只取 left 相機，並對得到 camera_left/*.jpg。"""
    raw = json.loads(Path(cameras_json).read_text(encoding="utf-8"))
    frames = []
    for item in raw:
        img_name = item["img_name"]
        if not img_name.startswith("l_"):
            continue
        stem = _stem_from_img_name(img_name)
        photo = Path(camera_left_dir) / f"{stem}.jpg"
        if not photo.exists():
            continue
        frames.append(
            CameraFrame(
                frame_id=int(item["id"]),
                img_name=img_name,
                photo_path=photo,
                position=np.asarray(item["position"], dtype=np.float64),
                rotation_c2w=np.asarray(item["rotation"], dtype=np.float64),
            )
        )
    frames.sort(key=lambda f: f.photo_path.name)
    return frames


def find_frame_for_photo(photo_path, cameras_json=None, camera_left_dir=None):
    """依照片檔名在 cameras.json 找對應 left 幀。找不到回傳 None。"""
    from . import config as inv_config

    photo_path = Path(photo_path)
    cameras_json = Path(cameras_json or inv_config.CAMERAS_JSON)
    camera_left_dir = Path(camera_left_dir or inv_config.CAMERA_LEFT_DIR)
    stem = photo_path.stem
    for frame in load_left_camera_frames(cameras_json, camera_left_dir):
        if frame.photo_path.stem == stem or stem in frame.img_name:
            return frame
    return None


def sample_frames(
    frames: list[CameraFrame],
    every_n: int = 12,
    min_distance_m: float = 1.5,
) -> list[CameraFrame]:
    """每隔 every_n 幀取樣；若移動距離超過 min_distance_m 也強制取樣。"""
    if not frames:
        return []

    sampled = [frames[0]]
    last_pos = frames[0].position
    for i, frame in enumerate(frames[1:], start=1):
        moved = float(np.linalg.norm(frame.position - last_pos))
        if i % every_n == 0 or moved >= min_distance_m:
            sampled.append(frame)
            last_pos = frame.position
    return sampled
