"""gaussian_prune 套件的檔案路徑與可調參數。

刻意沿用 dbh_seg/config.py 的相機校正、YOLO 遮罩、SegFormer 排除遮罩
設定，確保「算 DBH 用的樹」跟「瘦身後留下的樹」是同一棵、同一份遮罩。
"""
from dbh_seg import config as dbh_config
from .layout import DIR_SINGLE, DIR_SPLAT, resolve_full_scene_ply, single_tree_ply, supersplat_ply

PROJECT_ROOT = dbh_config.PROJECT_ROOT
SCAN_ID = dbh_config.SCAN_ID

# 完整場景在 3DGS_Park_Model/完整場景/；瘦身結果分開放單棵樹、SuperSplat
GAUSSIAN_PLY_PATH = resolve_full_scene_ply(SCAN_ID)
OUTPUT_PLY_PATH = single_tree_ply(SCAN_ID)
SUPERSPLAT_PLY_PATH = supersplat_ply(SCAN_ID)
DIR_SINGLE_TREE = DIR_SINGLE
DIR_SUPERSPLAT = DIR_SPLAT

# 直接沿用 dbh_seg 已經驗證過的遮罩設定 (YOLO 樹幹遮罩 + 可選的
# semantic_seg 排除遮罩)，兩條線 (算 DBH / 瘦身高斯) 用同一份資料源
CALIB_PATH = dbh_config.CALIB_PATH
MASK_PATH = dbh_config.MASK_PATH
SECONDARY_MASK_PATH = dbh_config.SECONDARY_MASK_PATH
SECONDARY_MASK_MODE = dbh_config.SECONDARY_MASK_MODE
SECONDARY_MASK_THRESHOLD = dbh_config.SECONDARY_MASK_THRESHOLD

DEPTH_MIN, DEPTH_MAX = dbh_config.DEPTH_MIN, dbh_config.DEPTH_MAX

# --- B 計畫：3D 幾何地面截斷 (魚眼照片讓 SegFormer 認不出彎曲的地板時的備案) ---
# 不管照片被魚眼鏡頭扭曲成什麼樣子，在真實的 3D 世界座標系裡，地板永遠
# 貼在最下面。這裡直接沿用 dbh_seg 算 DBH 時已經驗證過的 RANSAC 地面
# 偵測，對去噪點雲 (比稀疏的高斯球中心更適合抓平面) 算出「地面校正」，
# 再把同一組校正套用到高斯球座標上，只要校正後高度低於 GROUND_CUTOFF_Z_M
# 就直接視為地板砍掉——完全不依賴 2D 語意判斷，魚眼扭曲再嚴重也不影響。
GROUND_PLY_PATH = dbh_config.PLY_PATH
GROUND_VOXEL_SIZE = dbh_config.GROUND_VOXEL_SIZE
GROUND_DIST_THRESHOLD = dbh_config.GROUND_DIST_THRESHOLD
GROUND_CUTOFF_Z_M = 0.15

# 跟 dbh_seg 算 DBH 用的「薄殼」Z-Buffer (tolerance=0.05) 不一樣，這裡
# 要保留整棵樹的完整體積 (樹幹+枝葉都要留著)，只需要濾掉「同一條視線
# 背後」明顯更遠的背景物件 (背景樹、圍牆)，所以容許誤差要放大很多。
GAUSSIAN_OCCLUSION_TOLERANCE_M = 1.0

# 遮蔽過濾後，再做一次 DBSCAN、只保留最大連續群集，確保最終留下的是
# 「單一棵完整的樹」而不是混雜了零星雜訊或視線邊緣誤判的碎片。
# eps 比 dbh_seg 大一些，因為高斯球之間的間距通常比去噪點雲疏一點。
#
# 2026-08-11 診斷發現：地面截斷後的樹幹被切成兩大群 (36496 + 33178)，
# 兩群點數都很大、明顯都是同一棵樹的真實部分 (不是雜訊)，只是中間有一段
# 間距超過 0.3m 沒被 DBSCAN 認定為同一群 (可能是遮罩邊緣造成局部稀疏，
# 或樹幹中段被遮蔽過濾削掉了一圈)。把 eps 放大到 0.6m 讓它們重新連起來；
# 如果之後又出現地板/雜訊被一起黏回來，再往下調。
CLUSTER_EPS = 0.6
CLUSTER_MIN_POINTS = 20
