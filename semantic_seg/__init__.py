"""semantic_seg 套件：用公開的 SegFormer 語意分割模型 (ADE20K, 150 類別)，
找出照片裡「地板/天空」等確定不是樹的區域，產生排除遮罩，
供 dbh_seg/mask_fusion.py 拿去跟 YOLO 樹幹遮罩做「扣除」融合。
"""
from .infer import predict_exclude_mask

__all__ = ["predict_exclude_mask"]
