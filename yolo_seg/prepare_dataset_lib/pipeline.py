"""整合流程：掃描配對 -> 切訓練/驗證集 -> 寫出 dataset -> 產生 data.yaml。"""
import random

from . import config
from .dataset_writer import prepare_split_dirs, write_pairs
from .pairing import collect_pairs
from .yaml_writer import write_data_yaml


def main():
    if not config.TREEDATA_DIR.exists():
        print(f"錯誤: 找不到 treedata 資料夾: {config.TREEDATA_DIR}")
        return

    pairs = collect_pairs()
    print(f"\n總共配對成功 {len(pairs)} 組 (照片, 標記) 資料")
    if len(pairs) == 0:
        print("沒有任何資料可以轉換，請確認照片檔案已經放到對應的「XXX照片」資料夾內，")
        print("而且檔名要跟 labelme 資料夾內的 .json 檔名一致 (例如 (1).JPG 對應 (1).json)。")
        return

    random.seed(config.RANDOM_SEED)
    random.shuffle(pairs)
    val_count = max(1, int(len(pairs) * config.VAL_RATIO))
    val_pairs = pairs[:val_count]
    train_pairs = pairs[val_count:]
    print(f"訓練集: {len(train_pairs)} 筆 | 驗證集: {len(val_pairs)} 筆")

    prepare_split_dirs()

    all_skipped_labels = set()
    written = 0
    negatives = 0
    for split, split_pairs in (("train", train_pairs), ("val", val_pairs)):
        split_written, split_negatives, skipped = write_pairs(split, split_pairs)
        written += split_written
        negatives += split_negatives
        all_skipped_labels |= skipped

    print(f"\n實際寫入 {written} 組訓練用圖片與標記檔（其中非樹木負樣本 {negatives} 張，空標記）")
    if all_skipped_labels:
        print(
            "[注意] 以下類別名稱不在對照表內，這些標記已被忽略。"
            "如果這些也該算是樹幹，請到 prepare_dataset_lib/config.py 的 LABEL_ALIAS 補上對照: "
            f"{sorted(all_skipped_labels)}"
        )

    write_data_yaml()
