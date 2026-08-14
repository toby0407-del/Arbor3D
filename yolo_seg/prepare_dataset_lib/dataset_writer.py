"""把配對好的 (照片, 標記) 寫成 YOLOv8 訓練需要的 images/ 與 labels/ 檔案。"""
import json
import shutil

from . import config
from .convert import convert_shapes_to_yolo_lines


def _make_unique_stem(json_path):
    """
    用「來源資料夾名稱 + 原始檔名」組合出獨一無二的檔名，
    避免不同地點資料夾裡剛好有同樣檔名 (1).JPG 互相覆蓋。
    """
    source_tag = json_path.parent.name.replace("labelme", "").strip()
    clean_stem = json_path.stem.strip().strip("()").replace(" ", "_")
    return f"{source_tag}_{clean_stem}".replace(" ", "_")


def prepare_split_dirs():
    for split in ("train", "val"):
        (config.DATASET_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (config.DATASET_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)


def write_pairs(split, pairs):
    """處理單一 split (train 或 val) 的所有配對，回傳 (寫入數量, 被忽略的類別名稱集合)。"""
    written = 0
    skipped_labels = set()

    for jf, img in pairs:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [跳過] 讀取失敗: {jf} ({e})")
            continue

        img_h = data.get("imageHeight")
        img_w = data.get("imageWidth")
        if not img_h or not img_w:
            print(f"  [跳過] 缺少影像尺寸資訊: {jf}")
            continue

        lines, skipped = convert_shapes_to_yolo_lines(data.get("shapes", []), img_w, img_h)
        skipped_labels |= skipped
        if not lines:
            continue

        unique_stem = _make_unique_stem(jf)
        dst_img = config.DATASET_DIR / "images" / split / f"{unique_stem}{img.suffix.lower()}"
        dst_label = config.DATASET_DIR / "labels" / split / f"{unique_stem}.txt"

        shutil.copy2(img, dst_img)
        dst_label.write_text("\n".join(lines), encoding="utf-8")
        written += 1

    return written, skipped_labels
