"""把剝離出的樹幹點雲做兩層清潔：統計雜訊濾除 + DBSCAN 只留最大群集。"""
import numpy as np
import open3d as o3d

import geo_utils as utils

from . import config


def clean_tree_points(tree_points, tree_colors):
    """回傳清潔後的 (tree_pcd, tree_points)，並印出每一步的點數變化。"""
    tree_pcd = o3d.geometry.PointCloud()
    tree_pcd.points = o3d.utility.Vector3dVector(tree_points)
    if tree_colors is not None:
        tree_pcd.colors = o3d.utility.Vector3dVector(tree_colors)

    tree_pcd, _ = tree_pcd.remove_statistical_outlier(nb_neighbors=50, std_ratio=1.5)
    print(f"   統計雜訊清除後剩餘 {len(tree_pcd.points):,} 個點。")

    print("   最後一道保險：DBSCAN 分群，只保留最大的連續群集...")
    tree_pcd, num_clusters = utils.keep_largest_cluster(
        tree_pcd, eps=config.CLUSTER_EPS, min_points=config.CLUSTER_MIN_POINTS
    )
    if num_clusters:
        print(f"   共發現 {num_clusters} 群，保留最大群集 {len(tree_pcd.points):,} 個點。")
    else:
        print("   ⚠️ DBSCAN 沒找到有效群集 (可能點太稀疏)，跳過這道保險，維持原點雲。")

    return tree_pcd, np.asarray(tree_pcd.points)
