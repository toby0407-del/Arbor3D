# Arbor3D

環保局公園樹木盤點系統。用 JMK6 魚眼掃描的**去噪點雲**量胸高直徑（DBH），再用 **3D 高斯**做展示。量測求精準，高斯求好看，兩條線分開、最後接到同一份報告。

| | |
|--|--|
| 開發 | Toby |
| 倉庫 | https://github.com/toby0407-del/Arbor3D |
| 本機資料夾 | `treee_VScode`（遠端名稱 Arbor3D） |
| 主掃描 | `20260812070325` |
| 文件日期 | 2026-08-14 |

---

## 1. 三層分工

| 層 | 誰做 | 做什麼 |
|----|------|--------|
| 掃描與前處理 | 人 + RayStudio | 拍照、相機校正、去噪點雲、完整 3D 高斯。程式不能代勞 |
| 自動盤點 | Python（本倉庫根目錄） | 分樹、YOLO 遮罩、胸徑、單棵樹 3D、JSON／CSV／HTML |
| 展示系統 | 網頁／App（只放 `app/`） | 給人看樹號、胸徑、照片、3D；之後可接地圖 |

請不要在倉庫根目錄執行 `npm create` 或 `flutter create`。前端只開在 `app/`，才不會跟量測程式混在一起。

---

## 2. 本機資料與 Git

點雲、照片、完整高斯**不進 Git**（檔太大）。本機維持：

```
環保局樹木專題/
  3D_treedata/                      掃描匯出（照片、calib、cameras.json）
  3D_treedata_Denoised_Trees/       去噪點雲 {掃描ID}.ply
  3DGS_Park_Model/
    完整場景/                       {掃描ID}.ply（大檔，整座公園）
    單棵樹/                         {掃描ID}_single_tree.ply
    SuperSplat/                     {掃描ID}_supersplat.ply
  tree_VScode_no/                   已淘汰、不再使用的舊程式
  treee_VScode/                     本倉庫（GitHub：Arbor3D）
    app/                            前端，之後只改這裡
    dbh_seg/ park_inventory/ …      量測程式
    inventory_out/                  本機成果（不進 Git）
    GPUCache/                       3D 檢視器快取，可刪
```

Git 只收程式、YOLO 權重 `yolo_seg/runs/v1/weights/best.pt`、以及前端示範 JSON。

---

## 3. 一條指令（人做好素材之後）

```bash
pip install -r requirements.txt
python run_full_park_pipeline.py --scan_id 20260812070325
```

人要先放好：

1. `3D_treedata/{掃描ID}/`（左相機照片、`calibration/calib.json`、`ray_gaussian/cameras.json`）
2. `3D_treedata_Denoised_Trees/{掃描ID}.ply`
3. `3DGS_Park_Model/完整場景/{掃描ID}.ply`（必須是大檔；小於 50 MB 會被當成已瘦身，不當完整場景）

程式接著做：檢查素材 → 分樹編 ID → 綁最佳照片／YOLO 遮罩 → 算胸徑 → 瘦身高斯 → HTML。

成果在 `inventory_out_{掃描ID}/`（舊的一趟也還在 `inventory_out/`）：

- `park_inventory_report.html` / `.json` / `.csv`
- `masks/`、`dbh/` 剖面圖、`models/Tree_00X_*.ply`
- `tree_id_map_dbh.png`、`dbh_markers.ply`

前端先用 `app/example-data/park_inventory_report.sample.json` 畫畫面，欄位與真實 JSON 相同。

---

## 4. 主掃描目前數字（20260812070325，5 棵）

現場樹圍還沒量到，下表是**演算法結果**，不是已確認的正式樹圍。

| 樹號 | 胸徑 | 方法 | 燈號 | 說明 |
|------|------|------|------|------|
| Tree_001 | 12.2 cm | 圓擬合 | 黃 | 切片不是嚴格 1.3 m |
| Tree_002 | 72.0 cm | 虛擬卡尺 | 紅 | `wide_caliper`，遮罩可能污染，現場先複核 |
| Tree_003 | 12.4 cm | 圓擬合 | 黃 | 非嚴格 1.3 m |
| Tree_004 | 78.3 cm | 虛擬卡尺 | 紅 | 弧度只有約 39°，現場先複核 |
| Tree_005 | 11.5 cm | 圓擬合 | 黃 | 非嚴格 1.3 m |

此掃描 `calib.json` **沒有 GPS**。座標用公園內相對 XYZ。

---

## 5. 檔名（請維持一致）

| 位置 | 規則 | 例子 |
|------|------|------|
| 完整場景 | `{掃描ID}.ply` | `20260812070325.ply`（不要再加 `backup_`） |
| 單棵樹 | `{掃描ID}_single_tree.ply` | `20260812070325_single_tree.ply` |
| SuperSplat | `{掃描ID}_supersplat.ply` | `20260812070325_supersplat.ply` |
| 盤點產出 | `Tree_00X_single_tree.ply` / `_supersplat.ply` | 在 `inventory_out/models/` |

`GPUCache` 不是模型，是瀏覽器／SuperSplat 的 GPU 著色器快取，可刪，不進管線。

原始掃描裡的 `LIDAR_`、`IMAGE_` 是機器匯出名稱，不要改。

---

## 6. 自動盤點在做什麼

| 步驟 | 說明 |
|------|------|
| 素材檢查 | 去噪點雲、calib、照片、完整 3DGS 是否齊 |
| 分樹 | 多張照片 YOLO 偵測 → 射到地面 → 分群 → Tree_001… |
| 最佳視角 | 每棵樹選一張最適合量的照片（偏好遮罩靠下、距離較近） |
| YOLO 遮罩 | 只用自訓模型 `best.pt`，類別 `tree_trunk`；信心門檻 0.05。SegFormer 地板／天空排除預設關閉 |
| 胸徑 | 見下一節 |
| 3D 瘦身 | 依同一張遮罩從完整公園高斯切出一棵，並轉 SuperSplat |
| 報告 | HTML、JSON、CSV、俯視圖 |

每張照片的姿態來自 `cameras.json`（旋轉是 **C2W**），不要用一份 `calib.json` 外參套所有樹。

---

## 7. 胸徑演算法（從單樹做到全公園）

量測走**去噪點雲**，不走高斯球。高斯邊界糊，不適合作為公信力樹圍。

**Phase 1 — 3D 投到 2D 遮罩**  
用相機內外參把點雲投到 YOLO 樹幹遮罩上過濾。Windows 中文路徑用 `np.fromfile` + `cv2.imdecode`。

**Phase 2 — 不要手電筒效應**  
遮罩會變成一條無限射線，把幾十公尺外的背景也算進去。用 Z-Buffer 只留最靠近相機的樹皮（容許約 5 cm）。

**Phase 3 — 扶正再切胸高**  
RANSAC 找地面，把樹擺正，切離地 **1.2–1.4 m**。若這段沒點（照片常只拍到中上段），改切最接近 1.3 m、厚度 0.2 m 的視窗，並標記 `not_1.3m`。

**Phase 4 — 淺弧不能硬套圓**  
步道單向掃描往往只看到樹幹一側。弧度不夠時硬做圓，半徑會暴走（曾出現 180–411 cm）。現在要**兩道都過**才用圓：

1. 涵蓋角度 ≥ **120°**
2. 貼合圓周的點 ≥ **50%**

否則改用**虛擬卡尺**：沿「相機→樹」的垂直方向量可見寬度（比單純 PCA 更接近現場卡尺）。頭尾各修 2% 雜訊；若卡尺方向出現 >10 cm 斷層，只留最大那一段，避免樹跟圍牆黏在一起。

卡尺結果 ≥ 45 cm 會標 `wide_caliper`，畫面上當紅燈，等現場複核。

**Phase 5 — 模組與紀錄**  
程式拆在 `geo_utils/`、`dbh_seg/`、`park_inventory/`、`gaussian_prune/`。每次量測寫入 `dbh_results.json`。剖面圖同時畫不可靠的灰虛線圓，與實際採用的卡尺箭頭。

---

## 8. 展示系統功能表

標「預留」的先畫位置。登入、權限、即時掃描、後台改數字：第一版不做。

### 頁面

| 編號 | 頁面 | 第一版 | 說明 |
|------|------|--------|------|
| P1 | 公園總覽 | 必做 | 掃描編號、樹數、俯視圖、樹卡片（樹號、胸徑、燈號） |
| P2 | 單棵樹詳情 | 必做 | 照片、遮罩、剖面、胸徑與方法 |
| P3 | 3D 檢視 | 必做 | 單棵樹 SuperSplat，可旋轉縮放 |
| P4 | 待複核 | 必做 | 紅燈樹列表（現在是 Tree_002、004） |
| P5 | 掃描場次 | 預留 | 多趟切換（另有 `20260731134533`） |
| P6 | 地圖 | 預留 | 現在寫「尚未定位」 |
| P7 | 匯出 | 次要 | CSV／JSON（後端已有檔） |
| P8 | 完整公園 3D | 次要 | 檔很大，做成選開 |

### 燈號

| 燈 | 條件 | 給使用者看 |
|----|------|------------|
| 綠 | `DBH_note` 為 `ok` | 演算法較可信 |
| 黃 | 只有 `not_1.3m` | 有數字，但不是嚴格 1.3 m |
| 紅 | `wide_caliper`、`gap`、或沒胸徑 | 請現場再量，勿當正式樹圍 |

畫面上用中文，不要只丟英文代碼：

| 欄位值 | 寫成 |
|--------|------|
| `circle` | 圓擬合 |
| `caliper` | 虛擬卡尺 |
| `ok` | 演算法較可信 |
| `not_1.3m` | 切片不是標準 1.3 m 胸高 |
| `wide_caliper` | 卡尺結果偏寬，待現場複核 |
| `gap` | 點雲有缺口 |
| `no_measurement` | 無法量測 |

詳情頁要有：樹號、胸徑、方法、弧度、是否嚴格胸高、最佳照片、YOLO 遮罩、胸高剖面、相對座標。預留「現場量測胸徑」空白欄。GPS 目前皆空。

建議實作順序：P1 → P2 → P4 → P3 → P7 → P5／P6。

---

## 9. 建議還不要做／已知限制

- 現場 DBH 對過之前，Tree_002／004 只能當待複核。
- 沒有 GPS 就不要做地圖釘點。
- 多視角（同一棵樹前後左右）之後才比較容易走出完整圓擬合。
- 已搬到 `tree_VScode_no/`、不再維護：無遮罩 DBSCAN 量胸徑、舊的選照片腳本、早期實驗 JSON。

---

## 10. 主要套件

| 資料夾 | 用途 |
|--------|------|
| `dbh_seg/` | 單樹：遮罩剝離、胸高切片、圓／卡尺 |
| `park_inventory/` | 全公園：分樹、最佳視角、報告、HTML |
| `gaussian_prune/` | 完整場景瘦成單棵樹 + SuperSplat |
| `geo_utils/` | 投影、地面、弧度、PCA／視線寬度 |
| `yolo_seg/` | 樹幹分割訓練與推論 |
| `semantic_seg/` | SegFormer（可選，預設關） |
| `app/` | 前端 |

依賴見 `requirements.txt`。
