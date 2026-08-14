"""PCA 可見寬度法 (虛擬卡尺)：圓擬合不可靠時的備用方案，含連體嬰斷層切割。"""
import geo_utils as utils

from . import config
from .result import DBHResult


def build_caliper_result(
    slice_pts, arc_deg, ref_xc=None, ref_yc=None, ref_r=None, camera_xy=None,
):
    """算出可見寬度法的 DBH 結果；如果卡尺方向上有斷層，先切掉疑似連體嬰雜物。"""
    pts2d = slice_pts[:, :2]
    width, center, axis, p1, p2 = _measure_width(pts2d, camera_xy)

    # 「連體嬰」防呆：卡尺方向上如果有明顯斷層，代表混入了緊貼樹幹的其他物體，
    # 只取點數最多的那一段重新量寬度，而不是照單全收整段 (含斷層另一邊的雜物)。
    kept_mask, gap_detected, gap_m = utils.largest_contiguous_segment(
        pts2d, axis, center, gap_threshold=config.CALIPER_GAP_THRESHOLD_M
    )
    if gap_detected:
        print(
            f"   🚨 卡尺方向上偵測到 {gap_m * 100:.1f} 公分的斷層，懷疑混入了緊貼樹幹的其他物體"
            f"(圍牆/告示牌/鄰樹)，只取點數最多的一段重新量測 ({kept_mask.sum()}/{len(pts2d)} 個點)..."
        )
        width, center, axis, p1, p2 = _measure_width(pts2d[kept_mask], camera_xy)

    xc = ref_xc if ref_xc is not None else float(center[0])
    yc = ref_yc if ref_yc is not None else float(center[1])
    if arc_deg is None:
        arc_deg = utils.arc_coverage_deg(pts2d, xc, yc)
    return DBHResult(
        method="caliper", dbh_m=width, arc_deg=arc_deg,
        xc=xc, yc=yc, r=ref_r, caliper_p1=p1, caliper_p2=p2,
        gap_detected=gap_detected, gap_m=gap_m,
        caliper_kept_mask=kept_mask if gap_detected else None,
    )


def _measure_width(pts2d, camera_xy):
    if camera_xy is not None:
        width, center, axis, p1, p2 = utils.view_aligned_width(
            pts2d, camera_xy, trim_percentile=config.CALIPER_TRIM_PERCENTILE
        )
        pca_w, *_ = utils.pca_visible_width(
            pts2d, trim_percentile=config.CALIPER_TRIM_PERCENTILE
        )
        print(
            f"   卡尺軸：垂直於相機視線（可見寬度 {width * 100:.1f} cm；"
            f"PCA 對照 {pca_w * 100:.1f} cm）"
        )
        return width, center, axis, p1, p2
    return utils.pca_visible_width(
        pts2d, trim_percentile=config.CALIPER_TRIM_PERCENTILE
    )
