# Arbor3D

環保局公園樹木盤點系統。用 JMK6 魚眼掃描的**去噪點雲**量胸高直徑（DBH），再用 **3D 高斯**做展示。量測求精準，高斯求好看，兩條線分開、最後接到同一份報告與網頁介面。

| | |
|--|--|
| 開發 | Toby |
| 倉庫 | https://github.com/toby0407-del/Arbor3D |
| 前端獨立鏡像 | https://github.com/toby0407-del/arbor3d-interface |
| 本機資料夾 | `treee_VScode`（遠端名稱 Arbor3D） |
| 主掃描（介面示範） | `20260818092855`（逢甲 8/18，16 棵） |
| 文件日期 | 2026-08-21 |

---

## 1. 三層分工

| 層 | 誰做 | 做什麼 |
|----|------|--------|
| 掃描與前處理 | 人 + RayStudio | 拍照、相機校正、去噪點雲、完整 3D 高斯。程式不能代勞 |
| 自動盤點 | Python（本倉庫根目錄） | 分樹、YOLO 遮罩、胸徑、單棵樹 3D、JSON／CSV／HTML |
| 展示系統 | 網頁（**`app/`**） | 登入、地圖選點、盤點視窗、碳匯、匯入、CSV；見 [`app/README.md`](app/README.md) |

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
    app/                            前端（React + Vite）← 最新介面在這裡
    dbh_seg/ park_inventory/ …      量測程式
    inventory_out/                  本機成果（不進 Git）
    GPUCache/                       3D 檢視器快取，可刪
```

Git 只收程式、YOLO 權重 `yolo_seg/runs/v1/weights/best.pt`、前端程式，以及 `app/public/scans/` 示範媒體（不含超大 scene PLY）。

---

## 3. 一條指令（人做好素材之後）

```bash
pip install -r requirements.txt
python run_full_park_pipeline.py --scan_id 20260818092855
```

人要先放好：

1. `3D_treedata/{掃描ID}/`（左相機照片、`calibration/calib.json`、`ray_gaussian/cameras.json`）
2. `3D_treedata_Denoised_Trees/{掃描ID}.ply`
3. `3DGS_Park_Model/完整場景/{掃描ID}.ply`（必須是大檔；小於 50 MB 會被當成已瘦身，不當完整場景）

程式接著做：檢查素材 → 分樹編 ID → 綁最佳照片／YOLO 遮罩 → 算胸徑 → 瘦身高斯 → HTML。

成果在 `inventory_out_{掃描ID}/`：

- `park_inventory_report.html` / `.json` / `.csv`
- `masks/`、`dbh/` 剖面圖、`models/Tree_00X_*.ply`
- `tree_id_map_dbh.png`、`dbh_markers.ply`

前端讀 `app/src/data/inventories/{scan_id}.json`＋`app/public/scans/{scan_id}/`；欄位與管線 JSON 相同。

---

## 4. 介面已接掃描（20260818092855，逢甲 8/18）

| 項目 | 內容 |
|------|------|
| 地點 | 逢甲大學 · 學思樓／7-11 南側走廊 |
| 路徑 | 校園掃描路徑（8/18 · 7-11） |
| 棵數 | 16 |
| 前端 JSON | `app/src/data/inventories/20260818092855.json` |
| 媒體 | `app/public/scans/20260818092855/`（橫切面、Segmentation、點雲側視） |
| GPS | 無（相對 XYZ，介面沿路徑插值放點） |

驗證：`cd app && npm install && npm run dev` → 登入 → 搜尋「逢甲」→ 點 8/18 路徑。

較早一趟 `20260812070325`（5 棵）仍可用管線重跑；介面示範已改以 8/18 為主。

---

## 5. 檔名（請維持一致）

| 位置 | 規則 | 例子 |
|------|------|------|
| 完整場景 | `{掃描ID}.ply` | `20260818092855.ply`（不要再加 `backup_`） |
| 單棵樹 | `{掃描ID}_single_tree.ply` | `20260818092855_single_tree.ply` |
| SuperSplat | `{掃描ID}_supersplat.ply` | `20260818092855_supersplat.ply` |
| 盤點產出 | `Tree_00X_single_tree.ply` / `_supersplat.ply` | 在 `inventory_out/models/` |

`GPUCache` 不是模型，是瀏覽器／SuperSplat 的 GPU 著色器快取，可刪，不進管線。

原始掃描裡的 `LIDAR_`、`IMAGE_` 是機器匯出名稱，不要改。

---

## 6. 自動盤點在做什麼

| 步驟 | 說明 |
|------|------|
| 素材檢查 | 去噪點雲、calib、照片、完整 3DGS 是否齊 |
| 分樹 | 多張照片 YOLO 偵測 → 射到地面 → 分群 → Tree_001…（魚眼可切 tile） |
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
步道單向掃描往往只看到樹幹一側。弧度不夠時硬做圓，半徑會暴走。現在要**兩道都過**才用圓：

1. 涵蓋角度 ≥ **120°**
2. 貼合圓周的點 ≥ **50%**

否則改用**虛擬卡尺**：沿「相機→樹」的垂直方向量可見寬度。頭尾各修 2% 雜訊；若卡尺方向出現 >10 cm 斷層，只留最大那一段。

卡尺結果 ≥ 45 cm 會標 `wide_caliper`，畫面上當紅燈，等現場複核。

**Phase 5 — 模組與紀錄**  
程式拆在 `geo_utils/`、`dbh_seg/`、`park_inventory/`、`gaussian_prune/`。每次量測寫入 `dbh_results.json`。剖面圖同時畫不可靠的灰虛線圓，與實際採用的卡尺箭頭。

---

## 8. 展示系統（`app/`）— 2026-08-21 進度

前端已可實測，不是預留草圖。啟動見 [`app/README.md`](app/README.md)；接新掃描見 [`app/NEXT_STEPS.md`](app/NEXT_STEPS.md)。

### 已完成

| 編號 | 功能 | 狀態 |
|------|------|------|
| P1 | 登入（示範帳號／角色） | ✅ |
| P2 | 全台公園／學校地圖選點＋搜尋 | ✅ |
| P3 | 國土測繪底圖（街道／空拍）、GPS、路徑錄製／GPX | ✅ |
| P4 | 盤點視窗：樹表、燈號篩選、摘要 | ✅ |
| P5 | 影像：Segmentation、胸高橫切面、點雲側視 | ✅ |
| P6 | 3D 點雲（Three.js，直立＋繞鉛直軸） | ✅ |
| P7 | 匯入三格（去噪 PLY／高斯 PLY／照片資料夾） | ✅ |
| P8 | 現場手測＋待複核＋CSV 匯出 | ✅ |
| P9 | 碳匯工作表 | ✅ |

### 碳匯公式（介面欄位順序）

```
D  = A² × B × C
CO₂ = D × 3.667
```

| 順序 | 標籤 | 來源 |
|------|------|------|
| 1 | 高度 1.3 m 處圓周 ( A ) | π × 胸徑(m)；手測優先 |
| 2 | 樹高 ( B ) | 手測；空白則 `1.3 + 1.8√DBH` 粗估 |
| 3 | 係數 ( C ) | 表定 0.0159／闊葉 0.027／針葉 0.020／自訂 |
| 4 | 樹含碳量 ( D ) | 自動 |
| 5 | 吸收 CO₂ 當量 ( CO₂ ) | `D × 3.667`（ton） |

### 燈號（介面）

| 燈 | 條件 | 給使用者看 |
|----|------|------------|
| 綠 | 無特殊 note | 演算法較可信 |
| 黃 | （保留） | — |
| 紅 | `wide_caliper`、`gap`、`no_measurement` | 請現場再量，勿當正式樹圍 |

畫面上用中文：`circle`→圓擬合、`caliper`→虛擬卡尺、`wide_caliper`→卡尺偏寬待複核 等。

現場手測**不覆蓋**演算法 `DBH_cm`（另存 localStorage）。

### 示範帳號

| 工作編號 | 密碼 |
|---------|------|
| E-1027 | arbor1027 |
| E-2041 | arbor2041 |
| E-3308 | arbor3308 |

---

## 9. 建議還不要做／已知限制

- 紅燈樹在現場複核前不要當正式樹圍。
- 無 GPS 掃描靠路徑折線插值放點，精度取決於示範 polyline／現場錄製軌跡。
- 整場高斯 PLY 常 >100 MB，不進 Git；3D 單木可本機另放。
- 正式帳號 API、離線包、手測同步後端：尚未做。
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
| `app/` | 前端（React 19 + Vite 8 + Leaflet + Three.js） |

依賴見 `requirements.txt`（Python）與 `app/package.json`（前端）。
