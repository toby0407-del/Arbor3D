"""SegFormer 語意分割設定：用來偵測「確定不是樹」的區域 (地板、天空...)。

背景：YOLO 樹幹遮罩偶爾會把緊貼樹幹的地板、天空、圍牆等雜物也框進去，
而且這些雜物在 3D 空間裡有時跟樹幹表面完全連續、沒有空隙，純幾何演算法
(geo_utils/gap_split.py) 切不開。這個套件改用「語意」層面過濾：拿一個
已經訓練好、認識 150 種常見場景類別的公開模型 (SegFormer, ADE20K)，
直接把地板/天空這類確定不是樹的像素找出來，從 YOLO 遮罩裡扣掉。
"""

# 公開預訓練語意分割 (Hugging Face)，用來扣地板/天空——不是 YOLO，也不取代你的樹幹模型。
MODEL_NAME = "nvidia/segformer-b0-finetuned-ade-512-512"

# 想從 YOLO 樹幹遮罩裡「扣掉」的類別名稱 (ADE20K 150 個類別裡的英文名字)。
# 只要 SegFormer 判定某個像素屬於下面任何一個類別，就會被視為「不是樹」而排除。
# 依實際照片裡出現的雜物類型調整，例如加入 "wall"(圍牆)、"building"(建築)、
# "fence"、"road"、"sidewalk"、"earth"、"signboard"(告示牌) 等。
EXCLUDE_CLASS_NAMES = ["floor", "sky"]
