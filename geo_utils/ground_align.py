"""舊版一次到位的地面校正介面：偵測地面 + 直接把點雲校正好 + 分離地面/非地面。"""
from .ground import compute_ground_transform


def remove_ground_and_align(pcd, distance_threshold=0.2, ransac_n=3, num_iterations=1000):
    """
    使用 RANSAC 濾除地面，並自動將點雲的地面校正為水平且貼齊 Z=0 軸。
    (內部呼叫 compute_ground_transform 取得校正參數，再實際套用到 pcd 上)

    參數:
        pcd: Open3D 點雲物件
        distance_threshold: RANSAC 判定為地面的距離閥值
        ransac_n: RANSAC 隨機取樣點數
        num_iterations: 迭代次數
    回傳:
        aligned_pcd: 校正後的完整點雲
        ground_cloud: 地面點雲
        non_ground_cloud: 非地面點雲 (樹木)
    """
    rotation_matrix, z_offset, inliers = compute_ground_transform(
        pcd,
        distance_threshold=distance_threshold,
        ransac_n=ransac_n,
        num_iterations=num_iterations,
    )

    # 套用旋轉，以原點 (0,0,0) 為旋轉中心
    pcd.rotate(rotation_matrix, center=(0, 0, 0))
    # 將整塊點雲往 Z 軸反向平移這個高度，強制歸零
    pcd.translate((0, 0, -z_offset))

    # 注意：點雲平移和旋轉後，點的順序 index 不會變
    aligned_ground = pcd.select_by_index(inliers)
    aligned_non_ground = pcd.select_by_index(inliers, invert=True)

    return pcd, aligned_ground, aligned_non_ground
