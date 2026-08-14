"""量化切片點雲相對圓心，實際涵蓋了多少角度的弧，用來評估圓擬合的可信度。"""
import numpy as np


def arc_coverage_deg(points_2d, xc, yc):
    """
    回傳點雲相對 (xc, yc) 涵蓋的角度範圍 (0~360 度)。

    做法：把每個點換算成相對圓心的角度，排序後找出「最大的角度空隙」，
    360 度扣掉這個最大空隙，就是點雲實際佔滿的弧長角度。
    角度越小，代表只掃到樹幹的一小段側面，圓擬合在數學上會越不穩定
    (病態問題：小雜訊就能讓反推出來的半徑暴增或暴縮)。

    ⚠️ 注意：這個函式對「離圓心很遠的雜訊點」極度敏感——只要有一條連體嬰
    雜物的長尾巴飄得夠遠，用 arctan2 算出來的角度就可能繞著圓心轉出一圈
    看似涵蓋很大的假象，把防呆機制唬過去。呼叫這個函式時，務必只傳入
    「真正貼在圓周附近」的點 (見 circle_inlier_mask)，不要傳整坨未過濾的
    切片點雲。
    """
    dx = points_2d[:, 0] - xc
    dy = points_2d[:, 1] - yc
    angles = np.sort(np.degrees(np.arctan2(dy, dx)) % 360.0)
    if len(angles) < 2:
        return 0.0
    gaps = np.diff(np.concatenate([angles, angles[:1] + 360.0]))
    return 360.0 - float(np.max(gaps))


def circle_inlier_mask(points_2d, xc, yc, r, tolerance):
    """
    回傳「真正貼在圓周 ± tolerance 範圍內」的點的布林遮罩。

    用途：把飄得很遠的雜訊 (例如連體嬰雜物的長尾巴) 從角度計算裡排除，
    只留下真正支撐這個圓擬合結果的點，這樣算出來的涵蓋角度才有意義。
    """
    pts = np.asarray(points_2d, dtype=float)
    dist_to_circle = np.abs(np.hypot(pts[:, 0] - xc, pts[:, 1] - yc) - r)
    return dist_to_circle <= tolerance
