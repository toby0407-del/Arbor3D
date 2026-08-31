"""prepare_dataset 的路徑與可調參數。"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TREEDATA_DIR = BASE_DIR.parent.parent / "treedata"  # ...\環保局樹木專題\treedata
DATASET_DIR = BASE_DIR / "dataset"

VAL_RATIO = 0.1
RANDOM_SEED = 42

# 不同批次標記時用了不同的類別名稱，這裡全部歸一化成同一個類別。
# 如果之後發現新的照片用了新的類別名稱，程式執行完會列出來，
# 到時候再加進這個對照表裡即可。
LABEL_ALIAS = {
    "trunk+branch1": "tree_trunk",
    "樹幹": "tree_trunk",
}
CLASS_NAMES = ["tree_trunk"]  # index 0
CLASS_TO_ID = {name: i for i, name in enumerate(CLASS_NAMES)}

# 非樹木／負樣本標記：不寫成 tree_trunk，但照片仍進訓練（空的 YOLO txt）。
# 模型才學得到「電線桿、路燈、人、招牌不是樹幹」。
NEGATIVE_LABELS = {
    "nottree",
    "not_tree",
    "nontree",
    "non_tree",
    "非樹木",
    "非樹",
    "background",
    "bg",
}
NEGATIVE_FOLDER_MARKERS = ("非樹木", "nottree", "nontree", "non_tree", "negative")

IMAGE_EXTS = [".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"]
