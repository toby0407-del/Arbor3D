"""用你訓練好的 tree_trunk 模型，對一張照片跑 segmentation 並存出預覽圖。

權重固定為 yolo_seg/runs/v1/weights/best.pt（你訓練的那份）。
會印出每個偵測的信心值，並把「原圖 + 遮罩 + 方框」存成 jpg，方便肉眼檢查。

用法:
    python yolo_seg/preview_seg.py "照片路徑.jpg"
    python yolo_seg/preview_seg.py "照片路徑.jpg" 0.01
第二個參數是信心門檻 (可選，預設 0.01；想看更嚴格的結果可改成 0.25)。
"""
import sys
from pathlib import Path

import cv2
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
from predict_mask import DEFAULT_WEIGHTS, load_image_bgr  # noqa: E402

OUT_DIR = BASE_DIR.parent / "runs" / "segment" / "preview"


def main():
    if len(sys.argv) < 2:
        print("用法: python yolo_seg/preview_seg.py \"照片路徑.jpg\" [信心門檻]")
        return

    image_path = Path(sys.argv[1])
    conf = float(sys.argv[2]) if len(sys.argv) >= 3 else 0.01
    if not image_path.exists():
        print(f"找不到照片: {image_path}")
        return
    if not DEFAULT_WEIGHTS.exists():
        print(f"找不到訓練權重: {DEFAULT_WEIGHTS}")
        return

    image = load_image_bgr(image_path)
    model = YOLO(str(DEFAULT_WEIGHTS))
    print(f"權重: {DEFAULT_WEIGHTS}")
    print(f"照片: {image_path}  ({image.shape[1]}x{image.shape[0]})")
    print(f"信心門檻: {conf}")

    result = model.predict(source=image, conf=conf, imgsz=960, verbose=False)[0]
    boxes = result.boxes
    print(f"偵測到 {len(boxes)} 個 tree_trunk：")
    for i in range(len(boxes)):
        c = float(boxes.conf[i])
        x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy().tolist()
        print(f"  [{i+1}] 信心值={c:.3f}  框=({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f})")

    # Ultralytics 內建繪製：遮罩 + 方框 + 標籤
    plotted = result.plot()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{image_path.stem}_preview.jpg"
    cv2.imencode(".jpg", plotted)[1].tofile(str(out_path))
    print(f"預覽圖已存到: {out_path}")


if __name__ == "__main__":
    main()
