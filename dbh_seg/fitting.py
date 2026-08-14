"""對胸高切片做 RANSAC 圓形擬合 (失敗時退回最小平方法)。"""
import geo_utils as utils

from . import config


def fit_dbh(slice_pts):
    """回傳 (xc, yc, r, inlier_count)；擬合失敗時 r 為 None。"""
    xc, yc, r, inlier_count = utils.ransac_circle_fit(
        slice_pts[:, :2],
        distance_threshold=config.RANSAC_DIST_THRESHOLD,
        num_iterations=config.RANSAC_ITERATIONS,
        min_inliers=max(5, len(slice_pts) // 4),
    )

    if r is None:
        print("   RANSAC 擬合失敗，改用最小平方法穩健擬合當備案...")
        xc, yc, r, inlier_count = utils.robust_circle_fit(slice_pts[:, :2])

    return xc, yc, r, inlier_count
