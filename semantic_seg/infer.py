"""對一張照片跑 SegFormer 推論，找出「確定不是樹」的像素 (地板、天空...)。"""
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from . import config
from .model_loader import get_model_and_processor


def predict_exclude_mask(image_path, exclude_class_names=None):
    """回傳布林陣列 (H, W)，True = 這個像素屬於 exclude_class_names 裡的類別
    (預設是地板+天空)，代表「確定不是樹」，應該從 YOLO 遮罩裡扣掉。
    """
    exclude_class_names = exclude_class_names or config.EXCLUDE_CLASS_NAMES
    model, processor = get_model_and_processor()

    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")

    with torch.no_grad():
        outputs = model(**inputs)

    # 模型輸出的 logits 解析度比原圖小，放大回原始照片大小才能跟 YOLO 遮罩對齊
    logits = F.interpolate(
        outputs.logits, size=image.size[::-1], mode="bilinear", align_corners=False
    )
    pred_ids = logits.argmax(dim=1)[0].numpy()

    label2id = model.config.label2id
    exclude_ids = [label2id[name] for name in exclude_class_names if name in label2id]
    missing = [name for name in exclude_class_names if name not in label2id]
    if missing:
        print(f"   ⚠️ 語意分割模型沒有這些類別名稱，已忽略: {missing}")

    return np.isin(pred_ids, exclude_ids)
