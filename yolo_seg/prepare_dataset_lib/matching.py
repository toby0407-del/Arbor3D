"""比對「XXX照片」與「XXX照片labelme」資料夾，並建立圖片檔名索引。"""
from pathlib import Path

from . import config


def normalize_folder_core(name: str) -> str:
    """
    去掉「照片」「labelme」「年」這幾個常見詞，取出資料夾名稱的地點核心。
    因為實際資料夾命名不太一致，例如：
        '公七公園102年labelme'  vs  '公七公園102年照片'
        '惠來公園106年照片labelme'  vs  '惠來公園106照片'
    用這個函式各自處理過後，兩邊都會變成同樣的核心字串，才能正確配對。
    """
    core = name
    for token in ("labelme", "照片", "年"):
        core = core.replace(token, "")
    return core.strip()


def find_matching_photo_dir(label_dir: Path, all_dirs: list[Path]):
    label_core = normalize_folder_core(label_dir.name)
    # 先試最直覺的：直接去掉 labelme 字尾
    direct = label_dir.parent / label_dir.name[: -len("labelme")]
    if direct.exists() and direct.is_dir():
        return direct
    # 找不到的話，改用去除「照片/labelme/年」之後的核心地點名稱模糊比對
    for d in all_dirs:
        if d == label_dir or d.name.endswith("labelme"):
            continue
        if normalize_folder_core(d.name) == label_core:
            return d
    return None


def build_image_index(photo_dir: Path) -> dict:
    """
    遞迴掃描 photo_dir 底下所有圖片檔，用檔名(不含副檔名)當 key 建立索引。
    這樣不管照片實際上是直接放在資料夾裡，還是不小心多包了一層子資料夾，都找得到。
    """
    index = {}
    duplicates = set()
    for ext in config.IMAGE_EXTS:
        for img_path in photo_dir.rglob(f"*{ext}"):
            stem = img_path.stem.strip()
            if stem in index and index[stem] != img_path:
                duplicates.add(stem)
            index[stem] = img_path
    if duplicates:
        print(f"    [注意] '{photo_dir.name}' 底下有 {len(duplicates)} 個檔名重複的照片，已取其中一個使用")
    return index


def find_image_for_json(json_path: Path, image_index: dict):
    stem = json_path.stem.strip()
    return image_index.get(stem)
