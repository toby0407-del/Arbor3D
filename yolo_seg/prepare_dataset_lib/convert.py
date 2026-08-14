"""把 LabelMe 的多邊形標記，轉換成 YOLOv8-seg 需要的標準化座標格式。"""
from . import config


def convert_shapes_to_yolo_lines(shapes, img_w, img_h):
    lines = []
    skipped_labels = set()
    for shape in shapes:
        raw_label = shape.get("label", "").strip()
        mapped = config.LABEL_ALIAS.get(raw_label)
        if mapped is None and raw_label in config.CLASS_TO_ID:
            mapped = raw_label
        if mapped is None:
            skipped_labels.add(raw_label)
            continue

        class_id = config.CLASS_TO_ID[mapped]
        points = shape.get("points", [])
        if len(points) < 3:
            continue

        norm_coords = []
        for x, y in points:
            nx = min(max(x / img_w, 0.0), 1.0)
            ny = min(max(y / img_h, 0.0), 1.0)
            norm_coords.append(f"{nx:.6f}")
            norm_coords.append(f"{ny:.6f}")
        lines.append(f"{class_id} " + " ".join(norm_coords))
    return lines, skipped_labels
