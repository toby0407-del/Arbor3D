"""
geo_utils 套件
==============
原本的 utils.py 拆分而成，每個檔案只放一小群相關函式，方便閱讀與維護。
外部程式碼完全不用改寫呼叫方式，一樣用 `import geo_utils as utils` 後
呼叫 `utils.xxx(...)` 即可 (跟以前 `import utils` 的行為一致)。

各檔案負責的功能：
    ground.py         地面偵測、座標校正 (旋轉+平移)
    ground_align.py   舊版一次到位的地面校正介面 (內部呼叫 ground.py)
    circle_fit.py     最小平方法圓形擬合 (含穩健版)
    ransac_circle.py  RANSAC 圓形擬合
    occlusion.py      Z-Buffer 遮蔽過濾 (解決背景樹混雜問題)
    clustering.py     DBSCAN 分群，只保留最大群集
    viz.py            3D 視覺化輔助 (地面格線)
    arc_coverage.py   計算切片點雲涵蓋的弧度角度 (評估圓擬合可信度)
    pca_width.py      PCA 可見寬度法 (圓擬合不可靠時的備用「虛擬卡尺」)
    gap_split.py      偵測卡尺方向上的斷層，切開誤黏的「連體嬰」物體
    projection.py     相機投影模型 + 3D 點對 2D 遮罩的比對 (dbh_seg 與
                      gaussian_prune 共用，避免同一套投影數學各寫一份)

注意：fisheye_undistort.py（魚眼整圖拉直實驗）已移到專題旁的
tree_VScode_no/ 歸檔，主線量測仍用 projection.py 的魚眼投影模型。
"""
from .ground import compute_ground_transform, apply_ground_transform
from .ground_align import remove_ground_and_align
from .circle_fit import fit_circle_lsq, robust_circle_fit
from .ransac_circle import ransac_circle_fit
from .occlusion import apply_depth_buffer_filter
from .clustering import keep_largest_cluster, largest_cluster_indices
from .viz import create_ground_grid
from .arc_coverage import arc_coverage_deg, circle_inlier_mask
from .pca_width import pca_visible_width, view_aligned_width
from .gap_split import largest_contiguous_segment
from .projection import build_camera_model, apply_c2w_pose, project_points, points_in_mask

__all__ = [
    "compute_ground_transform",
    "apply_ground_transform",
    "remove_ground_and_align",
    "fit_circle_lsq",
    "robust_circle_fit",
    "ransac_circle_fit",
    "apply_depth_buffer_filter",
    "keep_largest_cluster",
    "largest_cluster_indices",
    "create_ground_grid",
    "arc_coverage_deg",
    "circle_inlier_mask",
    "pca_visible_width",
    "view_aligned_width",
    "largest_contiguous_segment",
    "build_camera_model",
    "apply_c2w_pose",
    "project_points",
    "points_in_mask",
]
