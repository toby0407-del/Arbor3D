"""開 Open3D 視窗，檢查切片位置與 DBH 量測結果 (圓 or 卡尺線) 是否合理。"""
import numpy as np
import open3d as o3d

from . import config


def _make_circle_lines(xc, yc, r, z, color=(0.0, 1.0, 0.0)):
    theta = np.linspace(0, 2 * np.pi, 100)
    pts = np.column_stack(
        [xc + r * np.cos(theta), yc + r * np.sin(theta), np.full_like(theta, z)]
    )
    lines = [[i, (i + 1) % len(theta)] for i in range(len(theta))]
    line_set = o3d.geometry.LineSet()
    line_set.points = o3d.utility.Vector3dVector(pts)
    line_set.lines = o3d.utility.Vector2iVector(lines)
    line_set.colors = o3d.utility.Vector3dVector([list(color)] * len(lines))
    return line_set


def _make_caliper_line(p1, p2, z):
    pts = np.array([[p1[0], p1[1], z], [p2[0], p2[1], z]])
    line_set = o3d.geometry.LineSet()
    line_set.points = o3d.utility.Vector3dVector(pts)
    line_set.lines = o3d.utility.Vector2iVector([[0, 1]])
    line_set.colors = o3d.utility.Vector3dVector([[0.0, 0.3, 1.0]])
    return line_set


def _make_slice_pcd(slice_pts, kept_mask):
    """紅色 = 採用的切片點；橘色 = 疑似連體嬰雜物、已被排除的點 (若有偵測到)。"""
    slice_pcd = o3d.geometry.PointCloud()
    slice_pcd.points = o3d.utility.Vector3dVector(slice_pts)
    colors = np.tile([1.0, 0.0, 0.0], (len(slice_pts), 1))
    if kept_mask is not None:
        colors[~kept_mask] = [1.0, 0.55, 0.0]
    slice_pcd.colors = o3d.utility.Vector3dVector(colors)
    return slice_pcd


def visualize(aligned_tree_points, slice_pts, result):
    slice_pcd = _make_slice_pcd(slice_pts, result.caliper_kept_mask)

    circle_z = float(np.mean(slice_pts[:, 2]))
    geometries = [slice_pcd]
    if result.method == "circle":
        geometries.append(_make_circle_lines(result.xc, result.yc, result.r, circle_z))
        measure_desc = "綠色圓圈   = RANSAC 擬合出的 DBH 圓"
    else:
        if result.r is not None:
            # 灰色圓：畫出原本病態、不可靠的圓擬合，方便對照
            geometries.append(
                _make_circle_lines(result.xc, result.yc, result.r, circle_z, color=(0.5, 0.5, 0.5))
            )
        geometries.append(_make_caliper_line(result.caliper_p1, result.caliper_p2, circle_z))
        measure_desc = "藍色線段   = PCA 可見寬度法量出的卡尺線 (灰色圓 = 不可靠的圓擬合對照)"

    mesh_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.5, origin=[0, 0, 0])
    geometries.append(mesh_frame)

    print("\n" + "=" * 60)
    print("3D 檢查視窗顏色說明：")
    if config.SHOW_FULL_TREE_IN_VIZ:
        tree_pcd = o3d.geometry.PointCloud()
        tree_pcd.points = o3d.utility.Vector3dVector(aligned_tree_points)
        tree_pcd.paint_uniform_color([0.6, 0.6, 0.6])  # 灰色 = 完整樹幹弧面
        geometries.insert(0, tree_pcd)
        print("  灰色       = 剝離出的完整樹幹弧面點雲")
    else:
        print("  (灰色樹幹已隱藏，把 config.SHOW_FULL_TREE_IN_VIZ 改成 True 可以重新顯示)")
    print("  紅色       = 胸高切片 (Z = 1.2m ~ 1.4m)")
    if result.caliper_kept_mask is not None:
        print("  橘色       = 疑似連體嬰雜物 (卡尺量測時已排除)")
    print(f"  {measure_desc}")
    print("操作：滑鼠左鍵拖曳=旋轉視角，右鍵拖曳=平移，滾輪=縮放。")
    print("=" * 60)
    o3d.visualization.draw_geometries(geometries)
