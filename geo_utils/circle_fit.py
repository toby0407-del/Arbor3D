"""最小平方法圓形擬合 (含帶有離群點剔除的穩健版)。"""
import numpy as np


def fit_circle_lsq(points_2d):
    """
    代數最小平方法圓形擬合 (Kasa method)。
    給定一組 2D 點 (x, y)，回傳最佳擬合圓的圓心 (xc, yc) 與半徑 r。
    """
    x = points_2d[:, 0]
    y = points_2d[:, 1]
    A = np.column_stack([2 * x, 2 * y, np.ones(len(x))])
    b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    xc, yc, c = sol
    r_sq = c + xc ** 2 + yc ** 2
    if r_sq < 0:
        return xc, yc, None
    return xc, yc, np.sqrt(r_sq)


def robust_circle_fit(points_2d, n_iter=4, std_thresh=1.5, min_points=5):
    """
    帶有離群點剔除的穩健圓形擬合。
    每一輪擬合後，計算每個點到圓周的殘差距離，把偏離過大的點（例如飛進切片裡的
    樹枝、雜訊）剔除，再重新擬合，讓結果更貼近真實樹幹輪廓。

    回傳: (xc, yc, r, 最終使用的點數)
    """
    pts = np.asarray(points_2d, dtype=float)
    xc = yc = r = None

    for _ in range(n_iter):
        if len(pts) < min_points:
            break
        xc, yc, r = fit_circle_lsq(pts)
        if r is None:
            break
        dist = np.sqrt((pts[:, 0] - xc) ** 2 + (pts[:, 1] - yc) ** 2)
        residual = np.abs(dist - r)
        thresh = residual.mean() + std_thresh * residual.std()
        mask = residual <= thresh
        if mask.sum() == len(pts) or mask.sum() < min_points:
            break
        pts = pts[mask]

    return xc, yc, r, len(pts)
