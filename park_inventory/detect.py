"""對抽樣照片批次跑 YOLO，取出每個 tree_trunk 實例的遮罩中心。

預設把魚眼切成 960×960 方塊（左→右 8 塊、上→下 4 排）再跑
你自己的 best.pt。整張縮成 960 時旁邊的樹太小，模型會只出最大那一棵。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from yolo_seg.config import YOLO_WEIGHTS
from yolo_seg.predict_mask import load_image_bgr

from . import config
from .cameras import CameraFrame


@dataclass
class Detection:
    photo_path: Path
    frame_id: int
    instance_id: int
    confidence: float
    centroid_uv: tuple[float, float]
    base_uv: tuple[float, float]  # 遮罩底部中心，用來射向地面
    mask_area_px: int
    bbox_xyxy: tuple[float, float, float, float]
    # filled after projection
    ground_xyz: np.ndarray | None = None
    ray_depth_m: float | None = None


def _axis_starts(length: int, tile: int, count: int) -> list[int]:
    if length <= tile or count <= 1:
        return [0]
    span = length - tile
    return [int(round(i * span / (count - 1))) for i in range(count)]


def iter_tiles(width: int, height: int):
    """樹幹帶上的 960 方塊，左→右 TILE_COLS、上→下 TILE_ROWS。"""
    tile = min(config.TILE_SIZE, width, height)
    y0 = int(height * config.TILE_Y0_FRAC)
    y1 = int(height * config.TILE_Y1_FRAC)
    y0 = max(0, min(y0, height - tile))
    y1 = max(y0 + tile, min(y1, height))
    band_top = y0
    band_h = max(tile, y1 - y0)
    if band_top + band_h > height:
        band_top = height - band_h

    xs = _axis_starts(width, tile, config.TILE_COLS)
    ys = [band_top + s for s in _axis_starts(band_h, tile, config.TILE_ROWS)]
    for y in ys:
        for x in xs:
            yield x, y, tile, tile


def _append_instances(detections, photo_path, frame_id, start_id, result, ox, oy, crop_w, crop_h):
    if result.masks is None or len(result.masks.data) == 0:
        return start_id, 0
    masks = result.masks.data.cpu().numpy()
    boxes = result.boxes
    added = 0
    next_id = start_id
    for j in range(len(masks)):
        resized = cv2.resize(masks[j], (crop_w, crop_h), interpolation=cv2.INTER_NEAREST)
        ys, xs = np.where(resized > 0.5)
        if len(xs) < 20:
            continue
        u_c, v_c = float(xs.mean() + ox), float(ys.mean() + oy)
        v_cut = np.percentile(ys, 90)
        base_sel = ys >= v_cut
        u_b = float(xs[base_sel].mean() + ox)
        v_b = float(ys[base_sel].mean() + oy)
        x1, y1, x2, y2 = boxes.xyxy[j].cpu().numpy().tolist()
        detections.append(
            Detection(
                photo_path=photo_path,
                frame_id=frame_id,
                instance_id=next_id,
                confidence=float(boxes.conf[j]),
                centroid_uv=(u_c, v_c),
                base_uv=(u_b, v_b),
                mask_area_px=int(len(xs)),
                bbox_xyxy=(x1 + ox, y1 + oy, x2 + ox, y2 + oy),
            )
        )
        next_id += 1
        added += 1
    return next_id, added


def detect_trunks_on_frames(
    frames: list[CameraFrame],
    conf: float = 0.15,
    imgsz: int = 960,
    weights_path: Path = YOLO_WEIGHTS,
) -> list[Detection]:
    model = YOLO(str(weights_path))
    iou = getattr(config, "YOLO_IOU", 0.45)
    use_tiles = getattr(config, "TILE_ENABLE", True)
    print(f"使用 YOLO 權重: {weights_path}")
    if use_tiles:
        print(
            f"切塊偵測: {config.TILE_COLS}×{config.TILE_ROWS}、"
            f"{config.TILE_SIZE}px、iou={iou}（仍用同一份 tree_trunk 模型）"
        )
    detections: list[Detection] = []

    for i, frame in enumerate(frames):
        image = load_image_bgr(frame.photo_path)
        h, w = image.shape[:2]
        n_hit = 0
        next_id = 0

        if use_tiles:
            for x, y, tw, th in iter_tiles(w, h):
                crop = image[y : y + th, x : x + tw]
                result = model.predict(
                    source=crop, conf=conf, imgsz=imgsz, iou=iou, verbose=False
                )[0]
                next_id, added = _append_instances(
                    detections, frame.photo_path, frame.frame_id, next_id, result, x, y, tw, th
                )
                n_hit += added
        else:
            result = model.predict(
                source=image, conf=conf, imgsz=imgsz, iou=iou, verbose=False
            )[0]
            next_id, n_hit = _append_instances(
                detections, frame.photo_path, frame.frame_id, 0, result, 0, 0, w, h
            )

        print(f"   [{i + 1}/{len(frames)}] {frame.photo_path.name}: {n_hit} 棵")

    return detections
