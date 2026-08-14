"""用訓練好的樹幹分割模型，對一張照片跑推論，輸出「乾淨的黑白二值遮罩」。

之前 dbh_seg/gaussian_prune 用的 MASK_PATH，一直指向 Ultralytics
`predict(save=True)` 自動存的那張圖——那張圖其實是「原始照片疊加半透明
藍色標註」的視覺化圖片，不是真正的黑白遮罩！拿它去跑 `mask_path > 127`
的灰階門檻，選到的範圍會跟真正的樹幹範圍完全對不上 (亮的天空/地磚反而
被當成「是樹幹」，暗色的藍色標註區域反而被當成「不是樹幹」)。

這支腳本直接從模型的 `results[0].masks.data` 拿到真正的二值遮罩陣列，
存成乾淨的黑白圖片 (255=樹幹, 0=背景)，這樣 MASK_PATH 才是真的可信。

用法:
    python yolo_seg/predict_mask.py "照片路徑.jpg" "輸出遮罩路徑.jpg"
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import cv2
import numpy as np
from PIL import Image, ImageOps
from ultralytics import YOLO

from yolo_seg.config import YOLO_CONF_DEFAULT, YOLO_IMGSZ, YOLO_WEIGHTS

DEFAULT_WEIGHTS = YOLO_WEIGHTS


def load_image_bgr(image_path):
    """讀取照片並回傳 BGR numpy 陣列，正確處理兩件事：
    1. 中文路徑 (用 PIL.Image.open 讀 Path 物件，Windows 上不像 cv2.imread
       對非 ASCII 路徑會讀取失敗)。
    2. EXIF 方向資訊 (手機/相機拍照時常會夾帶「這張圖要轉幾度才是正確方向」
       的中繼資料，PIL 預設不會自動套用，要呼叫 exif_transpose 才會真的把
       圖片轉正。如果模型訓練用的照片都已經是轉正後存的，但這張照片還帶著
       未套用的旋轉資訊，模型看到的角度會跟訓練時完全不同，導致偵測失敗)。
    """
    pil_img = Image.open(str(image_path))
    pil_img = ImageOps.exif_transpose(pil_img)
    return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)


def predict_binary_mask(image_path, weights_path=DEFAULT_WEIGHTS, conf=YOLO_CONF_DEFAULT, imgsz=YOLO_IMGSZ):
    """回傳 (mask_uint8, num_detections)。mask 是跟原圖同尺寸的 0/255 陣列，
    只要任何一個偵測到的 tree_trunk 實例覆蓋到該像素，就算是樹幹 (union)。

    imgsz 預設 960，是因為 yolo_seg/train.py 訓練時用的就是 imgsz=960
    (見 yolo_seg/runs/v1/args.yaml)。Ultralytics predict() 預設是 640，
    跟訓練解析度不一致會讓模型看到的物件比例跟訓練時不一樣，容易讓本來
    信心值就偏低的偵測 (魚眼畫面裡這棵樹只有 0.28) 直接掉到偵測不到。

    刻意不把路徑字串直接丟給 model.predict(source=...)：整個專案資料夾
    路徑含有中文 (環保局樹木專題)，Ultralytics 內部用 cv2.imread 讀圖在
    Windows 上對非 ASCII 路徑會直接讀取失敗 (回傳 None/空圖)。改成自己
    用 load_image_bgr() 讀成 numpy 陣列 (同時處理中文路徑跟 EXIF 方向)，
    再把陣列本身傳給模型。
    """
    image = load_image_bgr(image_path)

    model = YOLO(str(weights_path))
    results = model.predict(source=image, conf=conf, imgsz=imgsz, verbose=False)
    result = results[0]

    orig_h, orig_w = result.orig_shape
    mask = np.zeros((orig_h, orig_w), dtype=np.uint8)

    if result.masks is None or len(result.masks.data) == 0:
        return mask, 0

    for instance_mask in result.masks.data.cpu().numpy():
        resized = cv2.resize(
            instance_mask, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST
        )
        mask[resized > 0.5] = 255

    return mask, len(result.masks.data)


def main():
    print("=== predict_mask.py 版本標記: DEBUG_V5_REGION_CHECK (如果沒看到這行，代表你跑到舊版本) ===")
    if len(sys.argv) != 3:
        print("用法: python yolo_seg/predict_mask.py 照片路徑.jpg 輸出遮罩路徑.jpg")
        return

    image_path, output_path = sys.argv[1], sys.argv[2]
    mask, num_detections = predict_binary_mask(image_path)

    covered_ratio = float(np.mean(mask > 0)) * 100
    print(f"偵測到 {num_detections} 個 tree_trunk 實例，遮罩覆蓋整張照片 {covered_ratio:.1f}%")

    if num_detections == 0:
        # 診斷：肉眼判斷樹幹大約在畫面 寬35~55% x 高20~55% 這個範圍。之前
        # 抓到的「最高分候選框」其實都落在寬70~90%的另一棵背景樹上，不是
        # 目標樹幹。這裡改成不管排名，把「真正落在樹幹預期範圍內」的候選框
        # 通通列出來 (門檻壓到 0.0001，看這個範圍內到底有沒有任何反應)。
        image = load_image_bgr(image_path)
        model = YOLO(str(DEFAULT_WEIGHTS))
        expect_x, expect_y = (0.30, 0.58), (0.15, 0.60)
        print(f"   [診斷] 肉眼預期樹幹範圍: 寬{expect_x[0]*100:.0f}~{expect_x[1]*100:.0f}%, "
              f"高{expect_y[0]*100:.0f}~{expect_y[1]*100:.0f}%")
        for test_imgsz in (640, 960, 1280, 1920, 2560):
            debug_results = model.predict(
                source=image, conf=0.0001, imgsz=test_imgsz, verbose=False
            )
            boxes = debug_results[0].boxes
            h, w = debug_results[0].orig_shape
            hits = []
            for i in range(len(boxes)):
                x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy().tolist()
                cx, cy = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
                if expect_x[0] <= cx <= expect_x[1] and expect_y[0] <= cy <= expect_y[1]:
                    hits.append((float(boxes.conf[i]), x1, y1, x2, y2))
            if not hits:
                print(f"      imgsz={test_imgsz}: 樹幹預期範圍內完全沒有任何候選框 (共 {len(boxes)} 個框，全在別處)")
            else:
                for conf_i, x1, y1, x2, y2 in sorted(hits, reverse=True):
                    print(f"      imgsz={test_imgsz}: 樹幹範圍內命中！信心值={conf_i:.4f}  位置=({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f})")

    cv2.imencode(".jpg", mask)[1].tofile(output_path)
    print(f"已存成乾淨的黑白二值遮罩: {output_path}")


if __name__ == "__main__":
    main()
