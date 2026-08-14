"""延遲載入 (lazy-load) SegFormer 模型，避免每次 import 這個套件就要載入一次。"""
import torch
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

from . import config

_model = None
_processor = None


def get_model_and_processor():
    """回傳 (model, processor)，第一次呼叫才會真正載入 (並自動下載權重)。"""
    global _model, _processor
    if _model is None:
        print(f"   載入語意分割模型: {config.MODEL_NAME} (第一次使用會自動下載，請稍候)")
        _processor = SegformerImageProcessor.from_pretrained(config.MODEL_NAME)
        _model = SegformerForSemanticSegmentation.from_pretrained(config.MODEL_NAME)
        _model.eval()
    return _model, _processor


def get_device():
    return "cuda" if torch.cuda.is_available() else "cpu"
