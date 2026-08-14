"""階段二：為每棵 Tree_ID 選最佳觀測視角，並產出專屬二值遮罩。"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from yolo_seg.config import YOLO_IMGSZ, YOLO_WEIGHTS
from yolo_seg.predict_mask import load_image_bgr

from . import config


@dataclass
class BestView:
    tree_id: str
    photo_path: str
    mask_path: str
    score: float
    confidence: float
    mask_area_px: int
    center_dist_norm: float
    centroid_uv: list[float]
    base_uv: list[float]
    frame_id: int
    instance_id: int


def _image_center_distance_norm(u: float, v: float, width: int, height: int) -> float:
    """0 = 正中央，1 = 畫面角落。"""
    cx, cy = width / 2.0, height / 2.0
    dist = np.hypot(u - cx, v - cy)
    max_dist = np.hypot(cx, cy)
    return float(dist / max_dist) if max_dist > 0 else 1.0


def score_detection(det: dict, image_width: int = 3600, image_height: int = 3600) -> float:
    """遮罩底部越靠畫面下方、拍得越近、信心與面積適中 → 分數越高。

    舊版偏愛「大遮罩 + 畫面中央」，容易選到中上段樹幹遠拍，胸高 1.3 m 沒點。
    """
    conf = float(det.get("confidence") or 0.0)
    area = float(det.get("mask_area_px") or 0.0)
    u, v = det.get("centroid_uv") or [image_width / 2, image_height / 2]
    base_u, base_v = det.get("base_uv") or [u, v]
    center_dist = _image_center_distance_norm(u, v, image_width, image_height)
    depth = float(det.get("ray_depth_m") or 10.0)

    area_term = np.log1p(area) / np.log1p(200_000)
    conf_term = conf
    center_term = 1.0 - center_dist
    # 魚眼畫面：v 越大越靠下，越可能拍到近地面 / 胸高
    base_term = float(np.clip(base_v / max(image_height, 1), 0.0, 1.0))
    # 2 m 內接近滿分，之後隨距離下降
    depth_term = float(np.clip(1.0 - (depth - 2.0) / 10.0, 0.15, 1.0))
    return float(
        0.22 * conf_term
        + 0.18 * area_term
        + 0.10 * center_term
        + 0.32 * base_term
        + 0.18 * depth_term
    )


def select_best_detection(tree: dict, image_width: int = 3600, image_height: int = 3600) -> dict | None:
    dets = tree.get("detections") or []
    if not dets:
        return None
    ranked = sorted(
        dets,
        key=lambda d: score_detection(d, image_width, image_height),
        reverse=True,
    )
    best = dict(ranked[0])
    best["score"] = round(score_detection(best, image_width, image_height), 4)
    best["center_dist_norm"] = round(
        _image_center_distance_norm(
            best["centroid_uv"][0], best["centroid_uv"][1], image_width, image_height
        ),
        4,
    )
    return best


def extract_instance_mask(
    photo_path: Path,
    target_uv: tuple[float, float],
    conf: float = 0.05,
    imgsz: int = YOLO_IMGSZ,
    weights_path: Path = YOLO_WEIGHTS,
) -> tuple[np.ndarray, float, int]:
    """對照片跑 YOLO，取出最靠近 target_uv 的那一個 tree_trunk 實例遮罩。

    回傳 (mask_uint8, confidence, mask_area_px)。
    """
    image = load_image_bgr(photo_path)
    h, w = image.shape[:2]
    model = YOLO(str(weights_path))
    result = model.predict(source=image, conf=conf, imgsz=imgsz, verbose=False)[0]

    blank = np.zeros((h, w), dtype=np.uint8)
    if result.masks is None or len(result.masks.data) == 0:
        return blank, 0.0, 0

    masks = result.masks.data.cpu().numpy()
    boxes = result.boxes
    best_j, best_dist = -1, 1e18
    tu, tv = target_uv
    for j in range(len(masks)):
        resized = cv2.resize(masks[j], (w, h), interpolation=cv2.INTER_NEAREST)
        ys, xs = np.where(resized > 0.5)
        if len(xs) < 20:
            continue
        cu, cv = float(xs.mean()), float(ys.mean())
        dist = (cu - tu) ** 2 + (cv - tv) ** 2
        if dist < best_dist:
            best_dist = dist
            best_j = j

    if best_j < 0:
        return blank, 0.0, 0

    resized = cv2.resize(masks[best_j], (w, h), interpolation=cv2.INTER_NEAREST)
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[resized > 0.5] = 255
    return mask, float(boxes.conf[best_j]), int(np.count_nonzero(mask))


def bind_best_views(
    registry_path: Path | None = None,
    output_dir: Path | None = None,
    yolo_conf: float | None = None,
) -> dict:
    registry_path = Path(registry_path or (config.DEFAULT_OUTPUT_DIR / "tree_registry.json"))
    output_dir = Path(output_dir or config.DEFAULT_OUTPUT_DIR)
    yolo_conf = yolo_conf if yolo_conf is not None else config.YOLO_CONF
    mask_dir = output_dir / "masks"
    mask_dir.mkdir(parents=True, exist_ok=True)

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    trees = registry.get("trees") or []
    print(f"=== 階段二：最佳視角綁定 ===")
    print(f"讀取 registry: {registry_path} ({len(trees)} 棵樹)")
    print(f"YOLO 權重: {YOLO_WEIGHTS}")

    best_views: list[BestView] = []
    for tree in trees:
        tree_id = tree["tree_id"]
        best = select_best_detection(tree)
        if best is None:
            print(f"  {tree_id}: 無可用偵測，跳過")
            continue

        photo_path = Path(best["photo_path"])
        target_uv = tuple(best["centroid_uv"])
        print(
            f"  {tree_id}: 選 {photo_path.name} "
            f"(score={best['score']}, conf={best['confidence']}, area={best['mask_area_px']})"
        )

        mask, conf_i, area_i = extract_instance_mask(
            photo_path, target_uv, conf=yolo_conf
        )
        mask_path = mask_dir / f"real_tree_mask_{tree_id}.jpg"
        if area_i == 0:
            print(f"    ⚠️ 重新推論沒抓到實例，改用空白遮罩標記失敗")
        cv2.imencode(".jpg", mask)[1].tofile(str(mask_path))

        bv = BestView(
            tree_id=tree_id,
            photo_path=str(photo_path),
            mask_path=str(mask_path),
            score=best["score"],
            confidence=round(conf_i or best["confidence"], 4),
            mask_area_px=area_i or int(best["mask_area_px"]),
            center_dist_norm=best["center_dist_norm"],
            centroid_uv=best["centroid_uv"],
            base_uv=best.get("base_uv") or best["centroid_uv"],
            frame_id=int(best["frame_id"]),
            instance_id=int(best["instance_id"]),
        )
        best_views.append(bv)
        # 回寫進 registry 的該棵樹
        tree["best_view"] = asdict(bv)

    out = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "scan_id": registry.get("scan_id"),
        "source_registry": str(registry_path),
        "yolo_conf": yolo_conf,
        "num_trees": len(best_views),
        "best_views": [asdict(v) for v in best_views],
    }
    out_json = output_dir / "best_views.json"
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # 更新 registry（附 best_view 欄位）
    registry["best_views_bound_at"] = out["created_at"]
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n完成：{len(best_views)} 棵樹已綁定最佳視角")
    print(f"遮罩目錄: {mask_dir}")
    print(f"摘要: {out_json}")
    return out
