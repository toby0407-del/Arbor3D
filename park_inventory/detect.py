"""對抽樣照片批次跑 YOLO，取出每個 tree_trunk 實例的遮罩中心。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from yolo_seg.config import YOLO_WEIGHTS
from yolo_seg.predict_mask import load_image_bgr

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


def detect_trunks_on_frames(
    frames: list[CameraFrame],
    conf: float = 0.15,
    imgsz: int = 960,
    weights_path: Path = YOLO_WEIGHTS,
) -> list[Detection]:
    model = YOLO(str(weights_path))
    print(f"使用 YOLO 權重: {weights_path}")
    detections: list[Detection] = []

    for i, frame in enumerate(frames):
        image = load_image_bgr(frame.photo_path)
        h, w = image.shape[:2]
        result = model.predict(source=image, conf=conf, imgsz=imgsz, verbose=False)[0]

        if result.masks is None or len(result.masks.data) == 0:
            if (i + 1) % 10 == 0 or i == 0:
                print(f"   [{i + 1}/{len(frames)}] {frame.photo_path.name}: 0 棵")
            continue

        masks = result.masks.data.cpu().numpy()
        boxes = result.boxes
        n_hit = 0
        for j in range(len(masks)):
            inst = masks[j]
            resized = cv2.resize(inst, (w, h), interpolation=cv2.INTER_NEAREST)
            ys, xs = np.where(resized > 0.5)
            if len(xs) < 20:
                continue
            u_c, v_c = float(xs.mean()), float(ys.mean())
            # 取遮罩最下方 10% 像素的中心，近似樹幹貼近地面處
            v_cut = np.percentile(ys, 90)
            base_sel = ys >= v_cut
            u_b, v_b = float(xs[base_sel].mean()), float(ys[base_sel].mean())
            conf_j = float(boxes.conf[j])
            x1, y1, x2, y2 = boxes.xyxy[j].cpu().numpy().tolist()
            detections.append(
                Detection(
                    photo_path=frame.photo_path,
                    frame_id=frame.frame_id,
                    instance_id=j,
                    confidence=conf_j,
                    centroid_uv=(u_c, v_c),
                    base_uv=(u_b, v_b),
                    mask_area_px=int(len(xs)),
                    bbox_xyxy=(x1, y1, x2, y2),
                )
            )
            n_hit += 1

        print(f"   [{i + 1}/{len(frames)}] {frame.photo_path.name}: {n_hit} 棵")

    return detections
