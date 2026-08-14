"""當弧度不足以擬合圓時，改用 PCA 找出「可見寬度」，模擬用游標卡尺
夾住樹幹左右兩側量出的直線距離 (單向掃描林業遙測的經典替代做法)。

原理：相機只能拍到樹幹面向鏡頭那一側的弧面。這片弧面因為淺、幾乎貼平，
所以點雲沿著「切線方向 (左右寬度)」的分佈範圍，會遠大於沿著「徑向
(往鏡頭方向的深度)」的分佈範圍。PCA 抓到的第一主軸 (變異數最大的方向)，
正好就是這個左右寬度方向；沿此軸投影後的最大跨距，就是可見寬度。
"""
import numpy as np


def pca_visible_width(points_2d, trim_percentile=0.0):
    """
    回傳 (width, center, major_axis, p1, p2)：
        width       -- 點雲沿主軸方向的跨距 (公尺)，視為可見寬度 (近似 DBH)
        center      -- 點雲重心 (2,)
        major_axis  -- 主軸方向單位向量 (2,)
        p1, p2      -- 沿主軸投影後的兩個「卡尺端點」2D 座標 (畫線用)

    參數:
        trim_percentile: 用百分位數而非絕對 min/max 當卡尺端點 (0~ <50)。
            例如設成 2.0，代表捨棄投影值最極端的頭尾各 2%，避免單一顆
            噴出去的雜訊點 (未被 DBSCAN 濾乾淨) 就把卡尺撐得比實際寬。
            設成 0 則退回原本的絕對 min/max (不做修剪)。
    """
    pts = np.asarray(points_2d, dtype=float)
    center = pts.mean(axis=0)
    centered = pts - center

    cov = np.cov(centered.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    major_axis = eigvecs[:, np.argmax(eigvals)]

    proj = centered @ major_axis
    lo = np.percentile(proj, trim_percentile)
    hi = np.percentile(proj, 100.0 - trim_percentile)
    width = float(hi - lo)

    p1 = center + major_axis * lo
    p2 = center + major_axis * hi
    return width, center, major_axis, p1, p2


def view_aligned_width(points_2d, camera_xy, trim_percentile=0.0):
    """沿「相機→樹」的垂直方向量可見寬度。

    PCA 第一主軸在弧面被視線方向拉長時，會量到深度拖影而不是左右寬度。
    有相機位置時改用視線的法向當卡尺軸，比較接近現場用卡尺從鏡頭這面夾樹幹。
    """
    pts = np.asarray(points_2d, dtype=float)
    cam = np.asarray(camera_xy, dtype=float).reshape(2)
    center = pts.mean(axis=0)
    view = center - cam
    n = float(np.linalg.norm(view))
    if n < 1e-6:
        return pca_visible_width(pts, trim_percentile=trim_percentile)

    tangent = np.array([-view[1], view[0]], dtype=float) / n
    centered = pts - center
    proj = centered @ tangent
    lo = np.percentile(proj, trim_percentile)
    hi = np.percentile(proj, 100.0 - trim_percentile)
    width = float(hi - lo)
    p1 = center + tangent * lo
    p2 = center + tangent * hi
    return width, center, tangent, p1, p2
