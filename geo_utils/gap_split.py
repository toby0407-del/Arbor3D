"""偵測並切開沿著某個投影軸方向的「斷層 (gap)」。

用途：PCA 可見寬度法量出異常寬的結果時，常常是因為 YOLO 遮罩或 DBSCAN
把緊貼樹幹的圍牆、告示牌、鄰近樹木也黏在同一坨點雲裡 (「連體嬰」現象)。
真正的樹皮弧面點雲沿卡尺方向應該是連續的，如果中間出現一段明顯比點雲
密度大很多的空隙，代表那其實是兩個各自獨立的物體被誤判成同一塊。
"""
import numpy as np


def largest_contiguous_segment(points_2d, axis, center, gap_threshold):
    """
    把點雲投影到 axis 方向後排序，只要相鄰兩點的投影距離超過 gap_threshold，
    就視為斷層，在那裡切開成不同區段，只留下「點數最多」的那一段。

    回傳: (mask, has_gap, max_gap_m)
        mask       -- 布林陣列，True 表示保留 (屬於點數最多的那一段)
        has_gap    -- 是否真的偵測到超過門檻的斷層
        max_gap_m  -- 實際偵測到的最大斷層距離 (公尺)，方便印出來給人工檢查
    """
    pts = np.asarray(points_2d, dtype=float)
    proj = (pts - center) @ axis
    order = np.argsort(proj)
    sorted_proj = proj[order]

    gaps = np.diff(sorted_proj)
    max_gap = float(gaps.max()) if len(gaps) else 0.0
    if max_gap <= gap_threshold:
        return np.ones(len(pts), dtype=bool), False, max_gap

    # 用超過門檻的斷層位置，把排序後的點切成好幾段
    split_at = np.where(gaps > gap_threshold)[0] + 1
    segment_ids = np.zeros(len(sorted_proj), dtype=int)
    segment_ids[split_at] = 1
    segment_ids = np.cumsum(segment_ids)

    biggest_segment = np.bincount(segment_ids).argmax()
    keep_in_sorted_order = segment_ids == biggest_segment

    mask = np.zeros(len(pts), dtype=bool)
    mask[order[keep_in_sorted_order]] = True
    return mask, True, max_gap
