"""把 DBH 畫回俯視圖，並產出可疊在點雲/3DGS 上的樹位標記 PLY。"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def save_inventory_map(report: dict, output_path: Path) -> Path | None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("⚠️ 未安裝 matplotlib，略過 DBH 俯視圖。")
        return None

    trees = report.get("trees") or []
    if not trees:
        return None

    fig, ax = plt.subplots(figsize=(8, 8))
    for row in trees:
        xyz = row.get("Local_XYZ_m") or [0, 0, 0]
        x, y = float(xyz[0]), float(xyz[1])
        note = row.get("DBH_note") or ""
        color = "#c0392b" if "wide_caliper" in note else "#1e8449"
        ax.scatter([x], [y], c=color, s=80, edgecolors="black", zorder=3)
        dbh = row.get("DBH_cm")
        label = row["Tree_ID"]
        if dbh is not None:
            label = f"{label}\n{dbh} cm"
        ax.annotate(label, (x, y), fontsize=8, ha="left", va="bottom")

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title(f"Park inventory  {report.get('scan_id')}  ({len(trees)} trees)")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=140)
    plt.close(fig)
    print(f"DBH 俯視圖: {output_path}")
    return output_path


def save_dbh_marker_ply(report: dict, output_path: Path, n_ring: int = 64) -> Path | None:
    """在每棵樹地面座標畫一圈等於 DBH 半徑的標記，方便疊進 CloudCompare。"""
    trees = report.get("trees") or []
    pts = []
    for row in trees:
        xyz = row.get("Local_XYZ_m")
        dbh_cm = row.get("DBH_cm")
        if not xyz or dbh_cm is None:
            continue
        radius = max(float(dbh_cm) / 200.0, 0.05)
        note = row.get("DBH_note") or ""
        if "wide_caliper" in note:
            rgb = (192, 57, 43)
        elif row.get("DBH_method") == "circle":
            rgb = (39, 174, 96)
        else:
            rgb = (241, 196, 15)
        cx, cy, cz = float(xyz[0]), float(xyz[1]), float(xyz[2])
        angles = np.linspace(0, 2 * np.pi, n_ring, endpoint=False)
        for a in angles:
            pts.append((cx + radius * np.cos(a), cy + radius * np.sin(a), cz, *rgb))
        pts.append((cx, cy, cz, *rgb))

    if not pts:
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="ascii") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(pts)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")
        for x, y, z, r, g, b in pts:
            f.write(f"{x:.4f} {y:.4f} {z:.4f} {r} {g} {b}\n")
    print(f"DBH 標記點雲: {output_path}")
    return output_path
