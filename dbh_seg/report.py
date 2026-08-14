"""印出 DBH 計算結果，依實際採用的方法 (圓擬合 or 可見寬度法) 顯示對應說明。"""
from . import config


def report_dbh(result):
    """印出結果與合理範圍檢查，回傳 dbh_m (公尺)。"""
    print(
        f"\n   點雲實際涵蓋角度：約 {result.arc_deg:.0f}°"
        f"（整圈 360° 的 {result.arc_deg / 360 * 100:.0f}%）"
    )

    if result.method == "circle":
        ratio_txt = (
            f"，內點比例 {result.inlier_ratio * 100:.0f}%" if result.inlier_ratio is not None else ""
        )
        print(
            f"   擬合結果：圓心 = ({result.xc:.3f}, {result.yc:.3f})，"
            f"半徑 = {result.r:.3f} m，使用點數 {result.inlier_count}{ratio_txt}"
        )
        print(
            f"   ✅ 涵蓋角度 (≥{config.ARC_COVERAGE_THRESHOLD_DEG}°) 與內點比例 "
            f"(≥{config.CIRCLE_INLIER_RATIO_THRESHOLD * 100:.0f}%) 雙重防呆都通過，"
            "採用 RANSAC 圓形擬合。"
        )
    else:
        print(
            "   🚨 圓形擬合沒通過雙重防呆 (涵蓋角度需 ≥"
            f"{config.ARC_COVERAGE_THRESHOLD_DEG}° 且內點比例需 ≥"
            f"{config.CIRCLE_INLIER_RATIO_THRESHOLD * 100:.0f}%，兩項都要達標)，"
            "自動切換成「可見寬度法 (虛擬卡尺)」："
        )
        print(
            "      找出點雲的 PCA 主軸方向 (左右寬度)，量測沿主軸的跨距 "
            f"(已修剪頭尾各 {config.CALIPER_TRIM_PERCENTILE:.0f}% 極端雜訊點)。"
        )
        if result.gap_detected:
            print(
                f"   🚨 已排除疑似「連體嬰」雜物：卡尺方向上有 {result.gap_m * 100:.1f} 公分的斷層，"
                "偵測到緊貼樹幹的其他物體 (圍牆/告示牌/鄰樹)，已自動只取最大的一段重新量測。"
            )
        print(f"   卡尺量測結果：可見寬度 = {result.dbh_m:.3f} m")
        print(
            "   ⚠️ 這是「保守下界」估計值：只量到相機拍得到的那一面，樹幹最外緣"
            "沒被掃到，真實 DBH 可能略大一些，但不會像圓擬合那樣暴增到不合理的數字。"
        )

    dbh_m = result.dbh_m
    if not (config.DBH_MIN_M <= dbh_m <= config.DBH_MAX_M):
        print(
            f"⚠️ 警告：算出的 DBH = {dbh_m * 100:.1f} 公分，超出合理範圍 "
            f"({config.DBH_MIN_M * 100:.0f}~{config.DBH_MAX_M * 100:.0f} 公分)，"
            "請人工檢查切片與遮罩品質。"
        )
    else:
        print(f"\n🎉 計算完成！這棵樹的 DBH (胸高直徑) 約為 {dbh_m * 100:.1f} 公分。")

    return dbh_m
