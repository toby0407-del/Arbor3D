"""
將 LabelMe 標記好的樹木照片，轉換成 YOLOv8 segmentation 訓練需要的格式。

使用時機：
    等所有照片都放進 ..\..\treedata 底下對應的「XXX照片」資料夾之後，
    直接執行這支程式即可（可以重複執行，每次都會用當下 treedata 裡
    最新、最完整的資料重新產生一份 dataset）：

        python prepare_dataset.py

實際邏輯都拆到 prepare_dataset_lib/ 套件裡了 (每個檔案負責一小步)：
    config.py           路徑與可調參數 (含類別名稱對照表)
    matching.py          照片/標記資料夾比對、圖片檔名索引
    pairing.py           掃描 treedata，配對出 (json, image)
    convert.py           LabelMe 多邊形轉 YOLO 標準化座標
    dataset_writer.py    寫出 images/ 與 labels/
    yaml_writer.py       產生 data.yaml
    pipeline.py          整合以上所有步驟
"""
from prepare_dataset_lib import main

if __name__ == "__main__":
    main()
