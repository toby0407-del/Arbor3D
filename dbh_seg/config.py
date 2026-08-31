"""dbh_seg 套件的檔案路徑與可調參數，全部集中在這裡方便微調。"""
from pathlib import Path

from yolo_seg.config import YOLO_WEIGHTS

BASE_DIR = Path(__file__).resolve().parent.parent

# --- 三大素材檔案路徑（專題根目錄 = treee_VScode 的上一層）
# 用 BASE_DIR.parent (treee_VScode 的上一層) 組出路徑，不寫死絕對路徑字串，
# 這樣專題資料夾整包搬到別的位置或別台電腦，也不用逐個檔案改路徑。
PROJECT_ROOT = BASE_DIR.parent

# 目前這趟掃描的 ID（照片、calib、去噪點雲、高斯模型都要同一趟）
SCAN_ID = "20260812070325"

PLY_PATH = PROJECT_ROOT / "3D_treedata_Denoised_Trees" / f"{SCAN_ID}.ply"
CALIB_PATH = PROJECT_ROOT / "3D_treedata" / SCAN_ID / "calibration" / "calib.json"
# 單樹測試用的原始魚眼照片（批次盤點會改用每棵樹自己的最佳照片）
SOURCE_PHOTO_PATH = (
    PROJECT_ROOT / "3D_treedata" / SCAN_ID / "gaussian" / "camera_left"
    / "1786489451.196078.jpg"
)
MASK_PATH = BASE_DIR / "real_tree_mask.jpg"

# --- 模型來源 (樹 vs 地板/天空 刻意分開) ---
# 樹幹：與 yolo_seg/config.py 相同，優先 v3 > v2 > v1（類別 tree_trunk）
YOLO_WEIGHTS_PATH = YOLO_WEIGHTS
# 地板/天空排除 (可選)：用公開 SegFormer，見 semantic_seg/config.py；預設關閉。
# 當雜物 (地板/天空/圍牆/告示牌/藤蔓) 在 3D 空間裡跟樹幹表面完美融合、
# 中間沒有任何空隙時，純幾何距離的方法 (geo_utils/gap_split.py) 完全切不開。
# 這種情況要回到 2D 影像的「語意」層面過濾：先用 semantic_seg 套件
# (見 semantic_seg/generate_mask.py) 對同一張照片跑 SegFormer 語意分割，
# 產生一張「地板/天空排除區域」的黑白遮罩，把輸出路徑填在這裡，
# 系統就會自動把這片區域從 YOLO 遮罩裡扣掉。留 None 就完全不受影響，
# 維持只用 YOLO 遮罩。
SECONDARY_MASK_PATH = None   # exclude_mask.jpg 已產生；此張魚眼照 YOLO 遮罩與地板/天空 0% 重疊，啟用無助 DBH
SECONDARY_MASK_MODE = "exclude"         # "exclude"=扣除排除區域(地板/天空)；"include"=取交集(兩模型都同意才算樹)
SECONDARY_MASK_THRESHOLD = 127          # 灰階值大於這個數字，視為「模型判定屬於該類別」

# --- 可調參數 ---
DEPTH_MIN, DEPTH_MAX = 0.5, 15.0        # 樹幹剝離用的深度裁切範圍 (公尺)

OCCLUSION_TOLERANCE_M = 0.05            # Z-Buffer 遮蔽過濾容許誤差 (公尺)。
                                         # 這個值等於「只留樹皮表面往內幾公分厚」：
                                         # 0.4 太厚 -> 花椰菜狀實心雜訊；0.1 對粗糙樹皮
                                         # 還是太厚，切片會出現「淺弧錯覺」把半徑撐爆。
                                         # 改成 0.05 (5公分) 強制只留最表層樹皮；如果切片
                                         # 點數變太少或出現破洞/斷裂，可以再往上微調。

SHOW_FULL_TREE_IN_VIZ = False           # 3D 檢查視窗要不要畫出灰色的完整樹幹弧面。
                                         # 灰色那坨太厚時會擋住紅色切片，不方便肉眼判斷
                                         # 切片本身乾不乾淨，先關掉只看切片+擬合圓。

CLUSTER_EPS = 0.4                       # DBSCAN 分群距離 (公尺)
CLUSTER_MIN_POINTS = 30                 # DBSCAN 最小群集點數

SLICE_CLUSTER_EPS = 0.1                 # 胸高切片內再做一次分群的距離 (公尺)，這是送進圓
                                         # 擬合前的最後一道保險，把殘留的離群雜訊清乾淨
SLICE_CLUSTER_MIN_POINTS = 15

GROUND_VOXEL_SIZE = 0.05                # 找地面前的下採樣體素大小 (公尺)
GROUND_DIST_THRESHOLD = 0.2             # RANSAC 判定地面的容許誤差 (公尺)

SLICE_Z_MIN, SLICE_Z_MAX = 1.2, 1.4     # 胸高切片範圍 (公尺)
MIN_SLICE_POINTS = 15                   # 切片內至少要有幾個點才嘗試擬合圓

RANSAC_DIST_THRESHOLD = 0.02            # 圓周 RANSAC 容許誤差 (公尺) = 2 公分
RANSAC_ITERATIONS = 3000

ARC_COVERAGE_THRESHOLD_DEG = 120        # 涵蓋角度門檻：>=此值才信任 RANSAC 圓擬合，
                                         # 小於此值代表只掃到單向的一小段弧，圓擬合
                                         # 是病態問題，改用 PCA 可見寬度法 (虛擬卡尺)

CIRCLE_INLIER_RATIO_THRESHOLD = 0.5     # 雙重防呆的第二道鎖：真正貼合圓周的點，
                                         # 至少要佔整片切片的這個比例才信任圓擬合。
                                         # 背景：RANSAC 有時會在切片裡的一坨密集雜訊
                                         # (連體嬰的圍牆/告示牌/鄰樹) 硬塞出一個涵蓋
                                         # 角度很大、但只用了一小部分點的「假圓」，
                                         # 光看角度會被騙過去，這道比例門檻可以識破。
                                         # 0.5 = 要求「過半數」的點都支持這個圓，是
                                         # 比較嚴謹的預設值；如果之後發現正常的樹也
                                         # 常被誤判成可見寬度法，可以放寬到 0.4 左右。

CALIPER_TRIM_PERCENTILE = 2.0           # 可見寬度法：捨棄投影後頭尾各 N% 的極端點，
                                         # 避免殘留雜訊點把「卡尺」撐得比實際寬

CALIPER_GAP_THRESHOLD_M = 0.10          # 可見寬度法：卡尺方向上超過這個距離 (公尺)
                                         # 沒有任何點，就視為「斷層」——代表這其實是
                                         # 兩個分開的物體被誤黏成一坨 (例如樹幹旁的
                                         # 圍牆、告示牌、鄰樹)，只取點數最多的那一段
                                         # 重新量寬度，避免算出離譜的「連體嬰」尺寸

DBH_MIN_M, DBH_MAX_M = 0.03, 1.5        # 合理 DBH 範圍：3 公分 ~ 150 公分
