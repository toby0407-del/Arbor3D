"""DBSCAN 分群，只保留最大的連續群集，把零星雜訊丟棄。"""
import numpy as np


def largest_cluster_indices(pcd, eps=0.1, min_points=30, verbose=False):
    """
    對點雲做 DBSCAN 分群，回傳 (最大群集的索引陣列, 總群集數)。

    只算索引、不直接篩選點雲，方便呼叫端拿這批索引去篩選「跟 pcd 座標
    一一對應、但帶有額外欄位的其他陣列」(例如 gaussian_prune 需要保留
    的高斯球專屬屬性，Open3D 的 PointCloud 裝不下這些欄位)。

    參數:
        pcd: Open3D 點雲物件 (只需要有 xyz 座標)
        eps: 同一群內，點與點之間的最大距離 (公尺)
        min_points: 一群至少要有幾個點才算數
        verbose: True 時印出前 5 大群集的點數，用來判斷是不是「過度破碎」
                 (例如本來該是一整棵樹，卻被切成一堆零星小群)。

    回傳: 若沒有找到任何有效群集 (太稀疏)，回傳 (None, 0)。
    """
    labels = np.array(pcd.cluster_dbscan(eps=eps, min_points=min_points, print_progress=False))
    valid = labels >= 0
    if not np.any(valid):
        return None, 0

    counts = np.bincount(labels[valid])
    largest_label = counts.argmax()
    keep_idx = np.where(labels == largest_label)[0]

    if verbose:
        top5 = np.sort(counts)[::-1][:5]
        print(f"   [診斷] 前 5 大群集點數: {top5.tolist()} (共 {len(counts)} 群，雜訊點 {int(np.sum(~valid)):,} 個)")

    return keep_idx, int(labels.max()) + 1


def keep_largest_cluster(pcd, eps=0.1, min_points=30):
    """
    對點雲做 DBSCAN 分群，只保留點數最多的那一群，其餘一律視為雜訊丟棄。

    用途：即使已經用遮蔽過濾 (occlusion.apply_depth_buffer_filter) 濾掉了
    大部分背景樹，仍可能殘留一些零星的離群點 (例如遮罩邊緣誤判、雜草)。
    這是最後一道保險，確保送進圓形擬合的點雲，是「單一個連續表面」而不是
    好幾坨混在一起。

    回傳: (kept_pcd, num_clusters)
          若沒有找到任何有效群集 (太稀疏)，會原封不動回傳輸入的 pcd 與 0。
    """
    keep_idx, num_clusters = largest_cluster_indices(pcd, eps, min_points)
    if keep_idx is None:
        return pcd, 0
    return pcd.select_by_index(keep_idx), num_clusters
