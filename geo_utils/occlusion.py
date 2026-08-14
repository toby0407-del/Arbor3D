"""Z-Buffer 遮蔽過濾：解決森林場景裡背景樹被誤判成同一棵樹的問題。"""
import numpy as np


def apply_depth_buffer_filter(depth, u, v, width, height, tolerance=0.3):
    """
    對「已經通過 2D 遮罩篩選」的候選點，做關鍵的遮蔽 (occlusion) 過濾。

    問題背景：把 3D 點投影到 2D 遮罩時，只要點落在遮罩範圍內就會被保留，
    但完全沒有考慮「這條視線方向上，其實有更近的物體擋住了它」——在茂密的
    森林裡，同一條視線背後常常還藏著其他樹幹，會被誤判成同一棵樹的一部分，
    導致剝離出來的點雲其實混雜了好幾棵樹。

    解法：模擬相機的 Z-Buffer (深度緩衝) —— 針對每一個像素座標 (u, v)，
    只保留「深度最接近相機」的那批點，容許 tolerance 公尺的誤差範圍
    (對應樹幹本身的厚度、曲面弧度與掃描雜訊)，比這個範圍更遠的點視為
    背後被遮住的其他物體，直接濾除。

    參數:
        depth, u, v: 長度相同的一維陣列，分別是候選點的深度、像素 u、像素 v 座標
        width, height: 影像寬高，用來把 (u, v) 轉成一維像素索引
        tolerance: 容許比「該像素最近深度」多遠 (公尺) 仍視為同一個表面
                   (太小會把整個弧面切碎，太大則遮蔽過濾會失效)

    回傳: 布林陣列 (長度與輸入相同)，True 表示這個點通過遮蔽過濾、應該保留
    """
    depth = np.asarray(depth, dtype=np.float64)
    u = np.asarray(u, dtype=np.int64)
    v = np.asarray(v, dtype=np.int64)
    pixel_id = v * int(width) + u

    min_depth_buffer = np.full(int(width) * int(height), np.inf, dtype=np.float64)
    np.minimum.at(min_depth_buffer, pixel_id, depth)

    nearest_depth = min_depth_buffer[pixel_id]
    return depth <= nearest_depth + tolerance
