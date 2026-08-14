"""gaussian_prune 套件：把整座場景的 3D 高斯模型 (3DGS)，依照跟 dbh_seg
同一份 YOLO+SegFormer 遮罩做「物理刪減」，只留下目標樹，大幅縮小檔案。
"""
from .prune import prune_gaussian_to_single_tree

__all__ = ["prune_gaussian_to_single_tree"]
