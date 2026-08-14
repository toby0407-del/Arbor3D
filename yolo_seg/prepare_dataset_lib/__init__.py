"""prepare_dataset_lib 套件：把 LabelMe 標記轉換成 YOLOv8-seg 訓練用的 dataset。"""
from .pipeline import main

__all__ = ["main"]
