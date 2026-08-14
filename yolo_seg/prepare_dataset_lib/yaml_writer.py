"""產生 Ultralytics 訓練需要的 data.yaml 設定檔。"""
from . import config


def write_data_yaml():
    data_yaml_path = config.DATASET_DIR / "data.yaml"
    yaml_lines = [
        f"path: {config.DATASET_DIR.as_posix()}",
        "train: images/train",
        "val: images/val",
        "names:",
    ]
    for i, name in enumerate(config.CLASS_NAMES):
        yaml_lines.append(f"  {i}: {name}")
    data_yaml_path.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    print(f"\n[完成] data.yaml 已產生於: {data_yaml_path}")
    print("接下來可以執行: python train.py")
