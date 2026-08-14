"""3D 視覺化輔助工具。"""
import numpy as np
import open3d as o3d


def create_ground_grid(points_xyz, spacing=5.0, z=0.0, color=(1.0, 0.0, 0.0), margin=2.0):
    """
    建立一個位於高度 z (預設 Z=0) 的紅色格線地板，範圍涵蓋整份點雲的 XY 範圍。
    這是給非專業使用者最直觀的「地面在哪裡」參考物：只要樹幹底部有壓在
    這個網格上，就代表地面校正成功；如果整棵樹浮在網格上方或穿到網格下方，
    就代表地面對齊還需要調整。
    """
    x_min = points_xyz[:, 0].min() - margin
    x_max = points_xyz[:, 0].max() + margin
    y_min = points_xyz[:, 1].min() - margin
    y_max = points_xyz[:, 1].max() + margin

    xs = np.arange(np.floor(x_min / spacing) * spacing, x_max + spacing, spacing)
    ys = np.arange(np.floor(y_min / spacing) * spacing, y_max + spacing, spacing)

    pts = []
    lines = []
    idx = 0
    for x in xs:
        pts.append([x, y_min, z])
        pts.append([x, y_max, z])
        lines.append([idx, idx + 1])
        idx += 2
    for y in ys:
        pts.append([x_min, y, z])
        pts.append([x_max, y, z])
        lines.append([idx, idx + 1])
        idx += 2

    line_set = o3d.geometry.LineSet()
    line_set.points = o3d.utility.Vector3dVector(np.array(pts))
    line_set.lines = o3d.utility.Vector2iVector(np.array(lines))
    line_set.colors = o3d.utility.Vector3dVector(np.tile(color, (len(lines), 1)))
    return line_set
