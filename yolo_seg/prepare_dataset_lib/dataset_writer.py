"""把配對好的 (照片, 標記) 寫成 YOLOv8 訓練需要的 images/ 與 labels/ 檔案。"""
import json
import shutil

from . import config
from .convert import convert_shapes_to_yolo_lines


def is_negative_source(json_path):
    name = json_path.parent.name
    return any(marker in name for marker in config.NEGATIVE_FOLDER_MARKERS)


def _make_unique_stem(json_path):
    """
    用「來源資料夾名稱 + 原始檔名」組合出獨一無二的檔名，
    避免不同地點資料夾裡剛好有同樣檔名 (1).JPG 互相覆蓋。
    """
    source_tag = json_path.parent.name.replace("labelme", "").strip()
    clean_stem = json_path.stem.strip().strip("()").replace(" ", "_")
    return f"{source_tag}_{clean_stem}".replace(" ", "_")


def _clear_dir(dest):
    dest.mkdir(parents=True, exist_ok=True)
    for item in dest.iterdir():
        if item.is_file() or item.is_symlink():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item, ignore_errors=True)


def prepare_split_dirs():
    for split in ("train", "val"):
        _clear_dir(config.DATASET_DIR / "images" / split)
        _clear_dir(config.DATASET_DIR / "labels" / split)


def write_pairs(split, pairs):
    """處理單一 split。回傳 (寫入數量, 負樣本數量, 被忽略的類別名稱)。"""
    written = 0
    negatives = 0
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

        lines, skipped, negative_count = convert_shapes_to_yolo_lines(
            data.get("shapes", []), img_w, img_h
        )
        # 非樹木資料夾裡的拼寫錯誤（例如 'd'）也當負樣本，不要整張丟掉。
        if not lines and is_negative_source(jf):
            skipped = set()
            negative_count = max(negative_count, 1)
        skipped_labels |= skipped
        if not lines and negative_count == 0:
            continue

        unique_stem = _make_unique_stem(jf)
        dst_img = config.DATASET_DIR / "images" / split / f"{unique_stem}{img.suffix.lower()}"
        dst_label = config.DATASET_DIR / "labels" / split / f"{unique_stem}.txt"

        shutil.copy2(img, dst_img)
        dst_label.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        written += 1
        if not lines:
            negatives += 1

    return written, negatives, skipped_labels
