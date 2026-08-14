"""把 YOLO 樹幹遮罩，跟另一個語意分割模型 (例如 semantic_seg 套件用的
SegFormer) 產生的遮罩融合，濾掉緊貼樹幹、但語意上根本不是樹的雜物
(地板、天空、圍牆、告示牌、藤蔓...)。

背景：當雜物在 3D 空間裡跟樹幹表面完美融合、中間沒有任何空隙時，
純幾何距離的方法 (geo_utils/gap_split.py 的斷層偵測) 完全無從下手——
再怎麼算距離，連續貼在一起的點就是切不開。這種情況只能退回 2D 影像的
「語意」層面過濾：預設用「扣除法」(mode="exclude")，把 semantic_seg
判定為地板/天空的像素直接從 YOLO 遮罩挖掉；也支援「交集法」
(mode="include")，適合有另一個獨立「樹木」偵測模型的情境。
"""
import cv2
import numpy as np


def load_binary_mask(mask_path, target_size, threshold=127):
    """讀取一張灰階遮罩圖片，縮放到 target_size=(width, height)，
    回傳布林陣列 (True = 是目標物件)。
    """
    mask = cv2.imdecode(np.fromfile(str(mask_path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise FileNotFoundError(f"找不到或無法解析遮罩圖片: {mask_path}")
    width, height = target_size
    mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
    return mask > threshold


def fuse_masks(primary_mask, secondary_mask_path, target_size, threshold=127, mode="exclude"):
    """把第二個模型的遮罩融合進 YOLO 遮罩，濾掉緊貼樹幹但語意上不是樹的雜物。

    參數:
        primary_mask: YOLO 遮罩的布林陣列 (True = YOLO 判定是樹幹)
        secondary_mask_path: 第二個模型輸出的遮罩路徑，設成 None 代表沒有
            第二個模型可用，直接回傳 primary_mask 不做任何融合
            (完全不影響原本只用 YOLO 遮罩的行為)。
        target_size: (width, height)，要跟 primary_mask 對齊的解析度
        mode: "exclude" (預設) = secondary_mask 是「排除區域」(例如
            semantic_seg 產生的地板/天空遮罩)，兩者做「扣除」(A AND NOT B)。
            "include" = secondary_mask 是「樹木」遮罩，兩者做「交集」(A AND B)。
    """
    if secondary_mask_path is None:
        return primary_mask

    secondary_mask = load_binary_mask(secondary_mask_path, target_size, threshold)
    if mode == "exclude":
        fused = primary_mask & ~secondary_mask
        action = "扣除地板/天空等排除區域"
    else:
        fused = primary_mask & secondary_mask
        action = "取交集 (兩模型都同意才算樹)"

    kept_ratio = fused.sum() / max(1, primary_mask.sum())
    print(
        f"   🔬 語意交叉比對 ({action})：YOLO 遮罩 {int(primary_mask.sum()):,} px "
        f"-> 融合後 {int(fused.sum()):,} px (保留原始 YOLO 遮罩範圍的 {kept_ratio * 100:.0f}%)"
    )
    return fused
