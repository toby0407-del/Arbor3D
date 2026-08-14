"""
YOLOv8 樹幹分割 (segmentation) 模型訓練腳本。

第一次使用：
    1. 確認照片都已經放進 treedata 底下對應資料夾
    2. 執行: python prepare_dataset.py   (產生 dataset/ 與 data.yaml)
    3. 執行: python train.py             (開始訓練)

之後有新照片、新標記要加入重新訓練 (微調)：
    1. 把新照片與新的 labelme 標記放進 treedata 底下對應/新增的資料夾
    2. 重新執行一次 prepare_dataset.py
       (會用「舊資料 + 新資料」全部重新產生一份完整的 dataset，
        而不是只用新資料，避免模型忘記舊資料學過的東西)
    3. 把下面的 RESUME_WEIGHTS 改成上一輪訓練出來的 best.pt 路徑，
       例如: RESUME_WEIGHTS = "runs/v1/weights/best.pt"
    4. 把 RUN_NAME 改成新的版本名稱，例如 "v2"
    5. 執行: python train.py
       (這樣訓練會以上一輪的權重當起點微調，而不是從頭開始)
"""

import time
from pathlib import Path

from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
DATA_YAML = BASE_DIR / "dataset" / "data.yaml"

# 第一次訓練：使用 Ultralytics 官方 COCO 預訓練權重當起點 (會自動下載)。
# 之後要微調時，改成上一輪的 best.pt，例如 "runs/v1/weights/best.pt"
RESUME_WEIGHTS = "yolov8s-seg.pt"

# 每一輪訓練都取一個版本名稱，方便追蹤這個模型是用哪一批資料訓練出來的。
# 訓練結果會存放在 runs/<RUN_NAME>/weights/best.pt
RUN_NAME = "v1"

EPOCHS = 150
IMG_SIZE = 960
BATCH = -1  # -1 = 讓 ultralytics 依照 RTX 3070 的 VRAM 大小自動決定 batch size
PATIENCE = 30  # 連續這麼多個 epoch 沒有進步就提早停止，避免浪費時間


def format_duration(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h} 小時 {m} 分鐘 {s} 秒"


def main():
    if not DATA_YAML.exists():
        print(f"錯誤: 找不到 {DATA_YAML}")
        print("請先執行: python prepare_dataset.py")
        return

    train_dir = BASE_DIR / "dataset" / "images" / "train"
    val_dir = BASE_DIR / "dataset" / "images" / "val"
    train_count = len(list(train_dir.glob("*"))) if train_dir.exists() else 0
    val_count = len(list(val_dir.glob("*"))) if val_dir.exists() else 0

    print(f"使用權重: {RESUME_WEIGHTS}")
    print(f"資料集設定: {DATA_YAML}")
    print(f"本次訓練版本名稱: {RUN_NAME}")
    print(f"訓練圖片數: {train_count} 張 | 驗證圖片數: {val_count} 張")
    print(f"影像大小: {IMG_SIZE} | Epochs: {EPOCHS} | Batch: {'自動' if BATCH == -1 else BATCH}")
    print("下面每一行進度列會顯示目前跑到第幾個 batch / 總共幾個 batch，")
    print("以及預估剩餘時間 (ETA)，代表目前跑到第幾張圖片的進度。")
    print("=" * 60)

    start_time = time.time()

    model = YOLO(RESUME_WEIGHTS)
    model.train(
        data=str(DATA_YAML),
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH,
        patience=PATIENCE,
        project=str(BASE_DIR / "runs"),
        name=RUN_NAME,
        exist_ok=False,
        verbose=True,
    )

    elapsed = time.time() - start_time
    best_path = BASE_DIR / "runs" / RUN_NAME / "weights" / "best.pt"

    print("=" * 60)
    print(f"[完成] 訓練結束！本次訓練總共花費: {format_duration(elapsed)}")
    print(f"[完成] 最佳權重存放在: {best_path}")


if __name__ == "__main__":
    main()
