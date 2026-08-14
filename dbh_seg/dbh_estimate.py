"""雙重防呆分流：涵蓋角度「與」內點比例都達標，才信任 RANSAC 圓擬合，
否則自動切換成 PCA 可見寬度法 (虛擬卡尺)，避免病態或被污染的圓擬合結果暴走。
"""
import geo_utils as utils

from . import config
from .caliper import build_caliper_result
from .fitting import fit_dbh
from .result import DBHResult

__all__ = ["DBHResult", "estimate_dbh"]


def estimate_dbh(slice_pts, camera_xy=None) -> DBHResult:
    xc, yc, r, inlier_count = fit_dbh(slice_pts)
    if r is None:
        print("   圓形擬合完全失敗 (連備案最小平方法都不收斂)，直接改用可見寬度法...")
        return build_caliper_result(slice_pts, arc_deg=None, camera_xy=camera_xy)

    pts2d = slice_pts[:, :2]
    inlier_mask = utils.circle_inlier_mask(
        pts2d, xc, yc, r, tolerance=config.RANSAC_DIST_THRESHOLD
    )
    inlier_ratio = float(inlier_mask.sum()) / len(pts2d)
    arc_deg = _arc_deg_from_mask(pts2d, xc, yc, inlier_mask)
    print(
        f"   內點比例：貼合圓周的點佔整片切片 {int(inlier_mask.sum())}/{len(pts2d)} "
        f"= {inlier_ratio * 100:.0f}%"
    )

    good_coverage = arc_deg >= config.ARC_COVERAGE_THRESHOLD_DEG
    good_ratio = inlier_ratio >= config.CIRCLE_INLIER_RATIO_THRESHOLD

    if good_coverage and good_ratio:
        return DBHResult(
            method="circle", dbh_m=2 * r, arc_deg=arc_deg,
            xc=xc, yc=yc, r=r, inlier_count=inlier_count, inlier_ratio=inlier_ratio,
        )

    if not good_ratio:
        print(
            f"   🚨 內點比例過低 (<{config.CIRCLE_INLIER_RATIO_THRESHOLD * 100:.0f}%)，"
            "懷疑這片切片被其他物體污染 (連體嬰)，即使涵蓋角度夠大也拒絕採用這個圓，"
            "強制改用可見寬度法。"
        )
    else:
        print(f"   🚨 涵蓋角度不足 (<{config.ARC_COVERAGE_THRESHOLD_DEG}°)，改用可見寬度法。")

    return build_caliper_result(
        slice_pts, arc_deg, ref_xc=xc, ref_yc=yc, ref_r=r, camera_xy=camera_xy
    )


def _arc_deg_from_mask(pts2d, xc, yc, mask):
    """只用貼合圓周的點算涵蓋角度，避免雜訊的長尾巴在 arctan2 底下
    繞出虛假的大角度，騙過涵蓋角度防呆機制。
    """
    if mask.sum() < 3:
        print("   ⚠️ 貼合圓周的點太少，涵蓋角度改用全部切片點估算 (可能不準)。")
        return utils.arc_coverage_deg(pts2d, xc, yc)
    return utils.arc_coverage_deg(pts2d[mask], xc, yc)
