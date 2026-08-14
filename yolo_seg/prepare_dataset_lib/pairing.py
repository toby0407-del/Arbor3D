"""掃描 treedata 資料夾，把「照片」和「labelme 標記」配對成一組一組。"""
from . import config
from .matching import build_image_index, find_image_for_json, find_matching_photo_dir


def collect_pairs():
    """回傳 (json_path, image_path) 的 list。"""
    all_dirs = sorted(p for p in config.TREEDATA_DIR.iterdir() if p.is_dir())
    label_dirs = [p for p in all_dirs if p.name.endswith("labelme")]
    print(f"找到 {len(label_dirs)} 個標記資料夾")

    pairs = []
    for label_dir in label_dirs:
        photo_dir = find_matching_photo_dir(label_dir, all_dirs)
        if photo_dir is None:
            print(f"  [警告] 找不到對應的照片資料夾，跳過 '{label_dir.name}'")
            continue

        image_index = build_image_index(photo_dir)
        json_files = list(label_dir.glob("*.json"))
        matched, unmatched = 0, 0
        for jf in json_files:
            img = find_image_for_json(jf, image_index)
            if img is None:
                unmatched += 1
                continue
            pairs.append((jf, img))
            matched += 1
        print(f"  {label_dir.name}: 配對成功 {matched} 筆, 找不到對應照片 {unmatched} 筆")

    return pairs
