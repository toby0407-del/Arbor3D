"""多樹木盤點的預設參數。"""
from pathlib import Path

from dbh_seg import config as dbh_config

PROJECT_ROOT = dbh_config.PROJECT_ROOT
BASE_DIR = Path(__file__).resolve().parent.parent
SCAN_ID = dbh_config.SCAN_ID

# --- 輸入 ---
CALIB_PATH = dbh_config.CALIB_PATH
DENOISED_PLY_PATH = dbh_config.PLY_PATH
CAMERA_LEFT_DIR = (
    PROJECT_ROOT / "3D_treedata" / SCAN_ID / "gaussian" / "camera_left"
)
CAMERAS_JSON = (
    PROJECT_ROOT / "3D_treedata" / SCAN_ID / "ray_gaussian" / "cameras.json"
)

# --- 抽幀 ---
# 每 N 張 left 相機取 1 張；同時若移動距離超過 SAMPLE_MIN_DISTANCE_M 也強制取樣
SAMPLE_EVERY_N = 12
SAMPLE_MIN_DISTANCE_M = 1.5

# --- YOLO ---
# 0.15 會漏掉遠距/側拍樹幹；全公園盤點建議 0.05（單樹量測仍可用較高門檻）
YOLO_CONF = 0.05
YOLO_IMGSZ = 960
YOLO_IOU = 0.45  # 一張裡很多樹靠很近時，0.7 會把旁邊的框壓掉

# 整張魚眼縮成 960 只看得到最大那棵；改切方塊再跑同一個 best.pt
TILE_ENABLE = True
TILE_SIZE = 960
TILE_COLS = 8          # 左 → 右
TILE_ROWS = 4          # 上 → 下（一張約 32 塊）
TILE_OVERLAP = 0.30
TILE_Y0_FRAC = 0.12    # 上緣（避開太多天空）
TILE_Y1_FRAC = 0.92    # 下緣（避開車頭／黑邊）
# 測試主掃描（檔名結尾 325）；其他掃描可另指定路徑，但不必同等強度驗證
PRIMARY_SCAN_ID = "20260812070325"

# --- 地面交點 ---
GROUND_VOXEL_SIZE = 0.2
GROUND_DIST_THRESHOLD = 0.25
# 交點若離相機過近/過遠則丟棄（公尺）
RAY_DEPTH_MIN_M = 1.0
RAY_DEPTH_MAX_M = 40.0

# --- Tree center DBSCAN（樹與樹之間的最小間距尺度）---
TREE_CLUSTER_EPS_M = 1.5
TREE_CLUSTER_MIN_POINTS = 2  # 至少被兩張抽樣照片看到才成樹

# --- 輸出 ---
DEFAULT_OUTPUT_DIR = BASE_DIR / "inventory_out"
