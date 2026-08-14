"""RANSAC 圓形擬合：比單純最小平方法更能抵抗離群點干擾。"""
import numpy as np

from .circle_fit import fit_circle_lsq


def _circle_from_3_points(p1, p2, p3):
    """
    由三個不共線的 2D 點，解出唯一通過這三點的正圓。
    這是 RANSAC 圓擬合裡「隨機取樣建立候選模型」的那一步。

    回傳: (xc, yc, r)，若三點共線 (無法決定唯一圓) 則回傳 None。
    """
    ax, ay = p1
    bx, by = p2
    cx, cy = p3
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None

    ux = ((ax ** 2 + ay ** 2) * (by - cy) +
          (bx ** 2 + by ** 2) * (cy - ay) +
          (cx ** 2 + cy ** 2) * (ay - by)) / d
    uy = ((ax ** 2 + ay ** 2) * (cx - bx) +
          (bx ** 2 + by ** 2) * (ax - cx) +
          (cx ** 2 + cy ** 2) * (bx - ax)) / d
    r = float(np.hypot(ax - ux, ay - uy))
    return float(ux), float(uy), r


def ransac_circle_fit(points_2d, distance_threshold=0.01, num_iterations=2000,
                       min_inliers=10, seed=42):
    """
    以 RANSAC (RANdom SAmple Consensus) 演算法擬合圓形，比單純最小平方法更能
    抵抗離群點(飛進切片裡的樹枝、雜訊、鄰近雜草)干擾：

    1. 每一輪隨機取 3 個點，解出一個候選圓。
    2. 統計整批點裡，有多少點落在「候選圓周 ± distance_threshold」內 (inliers)。
    3. 重複 num_iterations 輪，保留 inliers 最多的候選模型。
    4. 最後用這批最佳 inliers 重新跑一次最小平方法微調，讓結果更精準。

    回傳: (xc, yc, r, inlier_count)
          找不到合理模型時回傳 (None, None, None, 0)
    """
    pts = np.asarray(points_2d, dtype=float)
    n = len(pts)
    if n < 3:
        return None, None, None, 0

    rng = np.random.default_rng(seed)
    best_inlier_mask = None
    best_count = -1

    for _ in range(num_iterations):
        idx = rng.choice(n, size=3, replace=False)
        candidate = _circle_from_3_points(pts[idx[0]], pts[idx[1]], pts[idx[2]])
        if candidate is None:
            continue
        xc, yc, r = candidate
        if r <= 0:
            continue

        dist_to_circle = np.abs(np.hypot(pts[:, 0] - xc, pts[:, 1] - yc) - r)
        inlier_mask = dist_to_circle <= distance_threshold
        count = int(inlier_mask.sum())

        if count > best_count:
            best_count = count
            best_inlier_mask = inlier_mask

    if best_inlier_mask is None or best_count < min_inliers:
        return None, None, None, 0

    xc, yc, r = fit_circle_lsq(pts[best_inlier_mask])
    if r is None:
        return None, None, None, 0

    return xc, yc, r, best_count
