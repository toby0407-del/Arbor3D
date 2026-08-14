# Arbor3D

環保局公園樹木盤點：掃描後處理（胸徑 DBH + 3D 高斯）與之後的展示網頁／App，放在**同一個倉庫、兩個資料夾**，互不覆蓋。

## 怎麼分才不會打亂

| 位置 | 做什麼 | 之後怎麼改 |
|------|--------|------------|
| 倉庫根目錄（Python） | 分樹、YOLO 遮罩、胸徑、3DGS 瘦身 | 量測／演算法才動這裡 |
| [`app/`](app/) | 網頁或 App 前端 | **只在這裡** `npm create` / Flutter / 設計稿 |

請不要在倉庫根目錄執行 `npm create`、`npx create-react-app` 或 `flutter create`。前端專案請開在 `app/` 裡面。

點雲、照片、完整 3D 高斯**不進 Git**（檔太大）。本機維持：

```
環保局樹木專題/
  3D_treedata/                 ← 掃描匯出
  3D_treedata_Denoised_Trees/  ← 去噪點雲
  3DGS_Park_Model/             ← 完整場景 / 單棵樹 / SuperSplat
  treee_VScode/                ← 這個 Git 倉庫（遠端名稱 Arbor3D）
    app/                       ← 前端
    dbh_seg/ park_inventory/ … ← 量測程式
```

## 量測程式（根目錄）

人先做好 RayStudio 去噪與 3DGS 後：

```bash
python run_full_park_pipeline.py --scan_id 20260812070325
```

成果在本機 `inventory_out/`（已加入 `.gitignore`）。前端之後讀的欄位契約見 [`app/example-data/`](app/example-data/)。

依賴：`pip install -r requirements.txt`  
YOLO 權重：`yolo_seg/runs/v1/weights/best.pt`  
較完整的演算法說明：[`README_3D_Segmentation.md`](README_3D_Segmentation.md)

## 前端（app/）

先用 `app/example-data/park_inventory_report.sample.json` 畫畫面。本機管線跑完後，再把 `inventory_out` 的真實資料接進去。
