"""CLI 工具：對一張照片跑語意分割，把「地板/天空」等排除區域存成黑白遮罩圖片。

用法:
    python -m semantic_seg.generate_mask <輸入照片路徑> <輸出遮罩路徑>

輸出的遮罩圖片是白色=要排除的區域 (地板/天空等)，黑色=保留區域。存好之後，
把輸出路徑填到 dbh_seg/config.py 的 SECONDARY_MASK_PATH，
下次執行 dbh_from_segmentation.py 就會自動把這片區域從 YOLO 遮罩裡扣掉。
"""
import sys

import cv2
import numpy as np

from .infer import predict_exclude_mask


def main():
    if len(sys.argv) < 3:
        print("用法: python -m semantic_seg.generate_mask <輸入照片路徑> <輸出遮罩路徑>")
        return

    photo_path, out_path = sys.argv[1], sys.argv[2]
    print(f"讀取照片: {photo_path}")
    exclude_mask = predict_exclude_mask(photo_path)

    out_img = exclude_mask.astype(np.uint8) * 255
    ok, buf = cv2.imencode(".jpg", out_img)
    if not ok:
        raise RuntimeError("遮罩編碼失敗")
    buf.tofile(str(out_path))  # 用 tofile (而非 cv2.imwrite) 繞過中文路徑限制

    excluded_pct = exclude_mask.mean() * 100
    print(f"完成！排除區域佔整張照片 {excluded_pct:.1f}%，已存到: {out_path}")


if __name__ == "__main__":
    main()
