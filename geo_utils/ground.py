"""地面偵測與座標校正：算出讓地面水平且貼齊 Z=0 所需要的旋轉與平移。"""
import numpy as np


def compute_ground_transform(pcd, distance_threshold=0.2, ransac_n=3, num_iterations=1000):
    """
    對點雲執行 RANSAC 地面偵測，回傳「讓地面水平且貼齊 Z=0」所需要的
    旋轉矩陣與垂直偏移量，但不會修改傳入的 pcd。

    這樣設計的好處是：這組校正參數算出來後，可以套用到「其他還沒校正過、
    但屬於同一個場景座標系」的點雲上（例如只剝離出單一棵樹的樹幹點雲），
    不需要把地面偵測跟目標點雲綁在同一份資料裡。

    參數:
        pcd: Open3D 點雲物件 (通常用完整場景或其下採樣版本來偵測地面)
        distance_threshold: RANSAC 判定為地面的距離閥值
        ransac_n: RANSAC 隨機取樣點數
        num_iterations: 迭代次數
    回傳:
        rotation_matrix: 3x3 旋轉矩陣，套用方式為 (rotation_matrix @ points.T).T
        z_offset: 旋轉後地面的平均高度，套用方式為 rotated_points[:, 2] -= z_offset
        inliers: RANSAC 判定為地面的點雲索引 (相對於傳入的 pcd)
    """
    plane_model, inliers = pcd.segment_plane(
        distance_threshold=distance_threshold,
        ransac_n=ransac_n,
        num_iterations=num_iterations,
    )
    a, b, c, d = plane_model

    # 確保法向量是朝上 (如果 c 是負的，就把法向量反向)
    if c < 0:
        a, b, c, d = -a, -b, -c, -d

    # 透過外積求旋轉軸、內積求旋轉角，把地面法向量對齊到絕對 Z 軸
    normal_vector = np.array([a, b, c])
    target_vector = np.array([0, 0, 1])
    v = np.cross(normal_vector, target_vector)
    c_dot = np.dot(normal_vector, target_vector)
    s = np.linalg.norm(v)

    if s != 0:
        kmat = np.array(
            [[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]
        )
        # 羅德里格旋轉公式
        rotation_matrix = np.eye(3) + kmat + kmat.dot(kmat) * ((1 - c_dot) / (s ** 2))
    else:
        rotation_matrix = np.eye(3)

    # 用旋轉後的地面點，算 Z 座標的平均高度，當作要扣掉的偏移量
    ground_points = np.asarray(pcd.points)[inliers]
    rotated_ground = (rotation_matrix @ ground_points.T).T
    z_offset = float(np.mean(rotated_ground[:, 2]))

    return rotation_matrix, z_offset, inliers


def apply_ground_transform(points_xyz, rotation_matrix, z_offset):
    """
    把 compute_ground_transform() 算出來的地面校正，套用到任意一組 3D 點上
    (例如另外用 YOLO 遮罩剝離出來、還沒校正過的單棵樹幹點雲)。

    回傳一份「新的」座標陣列，不會修改傳入的 points_xyz。
    """
    points_xyz = np.asarray(points_xyz, dtype=float)
    aligned = (rotation_matrix @ points_xyz.T).T
    aligned[:, 2] -= z_offset
    return aligned
