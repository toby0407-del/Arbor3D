"""用 Matplotlib 畫出胸高切片的 2D 俯視圖。

角度足夠時畫「整個塗滿顏色的擬合圓」；角度不足、改用可見寬度法時，
改畫一條藍色「卡尺線」標出量測到的寬度，比 3D 點雲更容易一眼判斷結果。
"""
from . import config


def _use_chinese_font(plt):
    """指定支援中文的字型，避免標題/圖例印出一堆「豆腐塊」缺字符號。"""
    plt.rcParams["font.sans-serif"] = [
        "Microsoft JhengHei", "Microsoft YaHei", "SimHei", "Noto Sans CJK TC",
    ]
    plt.rcParams["axes.unicode_minus"] = False  # 避免負號被中文字型畫成方塊


def save_slice_plot(slice_pts, result, out_path=None):
    """存一張俯視圖 PNG，回傳存檔路徑字串 (沒裝 matplotlib 時回傳 None)。"""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Circle
    except ImportError:
        print("⚠️ 沒有安裝 matplotlib，略過 2D 俯視圖繪製。")
        print("   可執行 `pip install matplotlib` 安裝後再重新執行一次。")
        return None

    _use_chinese_font(plt)
    out_path = str(out_path or (config.BASE_DIR / "dbh_slice_top_down.png"))
    fig, ax = plt.subplots(figsize=(7, 7))

    if result.method == "circle":
        ax.add_patch(Circle(
            (result.xc, result.yc), result.r,
            facecolor="limegreen", alpha=0.35,
            edgecolor="green", linewidth=2.5, zorder=1,
        ))
        ax.plot(result.xc, result.yc, "g+", markersize=16, markeredgewidth=2, zorder=3)
        method_label = "RANSAC 圓形擬合"
    else:
        if result.r is not None:
            # 淡灰色虛線圓：畫出原本病態、不可靠的圓擬合，方便對照「為什麼改用卡尺法」
            ax.add_patch(Circle(
                (result.xc, result.yc), result.r,
                facecolor="none", edgecolor="gray", linestyle="--",
                linewidth=1.5, zorder=0, label="圓擬合 (不可靠，僅供對照)",
            ))
        p1, p2 = result.caliper_p1, result.caliper_p2
        ax.annotate(
            "", xy=p2, xytext=p1,
            arrowprops=dict(arrowstyle="<->", color="blue", linewidth=2.5),
        )
        mid = (p1 + p2) / 2
        ax.text(mid[0], mid[1], f"  {result.dbh_m * 100:.1f} cm",
                 color="blue", fontsize=12, fontweight="bold", zorder=3)
        method_label = "PCA 可見寬度法 (虛擬卡尺)"

    if result.caliper_kept_mask is not None:
        kept = result.caliper_kept_mask
        ax.scatter(
            slice_pts[~kept, 0], slice_pts[~kept, 1],
            s=30, c="darkorange", edgecolors="black", linewidths=0.3,
            zorder=2, label="疑似連體嬰雜物 (已排除)",
        )
        ax.scatter(
            slice_pts[kept, 0], slice_pts[kept, 1],
            s=30, c="red", edgecolors="darkred", linewidths=0.3,
            zorder=2, label="胸高切片實際點雲 (採用)",
        )
    else:
        ax.scatter(
            slice_pts[:, 0], slice_pts[:, 1],
            s=30, c="red", edgecolors="darkred", linewidths=0.3,
            zorder=2, label="胸高切片實際點雲",
        )

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title(
        f"胸高切片俯視圖 (由上往下看) - {method_label}\n"
        f"DBH = {result.dbh_m * 100:.1f} 公分，涵蓋角度 = {result.arc_deg:.0f}°"
    )
    ax.legend(loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.4)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

    print(f"\n🖼️  已產生俯視圖：{out_path}")
    return out_path
