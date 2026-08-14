"""YOLO 樹幹分割：全專案統一從這裡讀取權重路徑。

推論 (predict_mask / 公園盤點) 一律使用你自己訓練的
tree_trunk 模型，不用 Ultralytics 官方 yolov8s-seg.pt。
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# 你訓練完成的權重 (類別只有 tree_trunk，見 dataset/data.yaml)
YOLO_WEIGHTS = BASE_DIR / "runs" / "v1" / "weights" / "best.pt"

YOLO_CLASS_NAME = "tree_trunk"
YOLO_IMGSZ = 960          # 跟 train.py / args.yaml 一致
YOLO_CONF_DEFAULT = 0.1   # predict_mask 預設門檻
