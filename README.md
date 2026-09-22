# Arbor3D

把真實世界的公園樹木做成可持續被 AI 分析的數位表徵（Digital Representation）。現場掃描是 **Physical**；去噪點雲、單木 ID、胸徑、碳匯與 3D 高斯是 **Digital**；YOLO 分割與時序成長判定是 **AI**。量測求精準，高斯求好看，兩條線分開，最後接到同一份長期監測報告與網頁介面。

不是只做「替環保局量一次樹」，而是把每一棵樹從實體資產變成可跨期比對的數位分身：前期盤點 → 本期盤點 → 成長趨勢。

| | |
|--|--|
| 開發 | Toby |
| 倉庫 | https://github.com/toby0407-del/Arbor3D |
| 前端獨立鏡像 | https://github.com/toby0407-del/arbor3d-interface |
| 本機資料夾 | `treee_VScode`（遠端名稱 Arbor3D） |
| 主掃描（介面示範） | `20260818092855`（逢甲 8/18，16 棵） |
| 文件日期 | 2026-09-01 |

---

## 1. Physical → Digital → AI

| 層 | 誰做 | 做什麼 |
|----|------|--------|
| Physical | 人 + JMK6／RayStudio | 現場掃描、相機校正、去噪點雲、完整 3D 高斯。程式不能代勞 |
| Digital | Python（本倉庫根目錄） | 分樹、遮罩、胸徑、單木 3D、JSON／CSV／HTML；每棵樹一份可重跑的數位表徵 |
| AI | YOLO 分割 + 介面時序判定 | 樹幹分割、負樣本抑制誤檢；前期／本期／趨勢比對，標正常成長、幾乎停長、健康異常 |

請不要在倉庫根目錄執行 `npm create` 或 `flutter create`。前端只開在 `app/`，才不會跟量測程式混在一起。

研究定位是 **Physical → Digital → AI**：把現場環境資產（樹）做成可持續被 AI 分析的 Digital Representation，而不是一次性量測報告。文獻只收 **2024 年以後的 T1**（Nature 系列、ECCV、SIGGRAPH、ICLR、*Remote Sensing of Environment*）。2023 以前的論文、專案網站、ISPRS Annals、MDPI、*Urban Forestry & Urban Greening* 不列入。以下為對照入口，**不是本系統實作來源**：

| 層 | 文獻 | 場刊 | 本系統怎麼對 |
|----|------|------|----------------|
| Physical → 單木監測 | Brandt et al., tree resource monitoring | **Nature Reviews Electrical Engineering 2025** | 監測必須把樹當物件、估結構與碳匯，不能只報覆蓋率 |
| Digital／可量測 3D | Huang et al., 2D Gaussian Splatting | **SIGGRAPH 2024** | 高斯不只求好看，幾何要能對齊量測；本系統量測線與高斯線分開 |
| Digital → 碳（點雲） | Oehmcke et al., point-cloud AGB | **Remote Sensing of Environment 2024** | 碳匯從點雲結構來，不能只數棵數 |
| Digital → 碳（TLS） | Chen et al., leaf–wood / AGB | **Remote Sensing of Environment 2024** | 樹幹幾何決定碳匯可信度；異常株 Warning、不得逕列正式統計 |
| AI 分割 | Ravi et al., SAM 2 | **ICLR 2025** | 分割必須可重跑、可泛化；本系統用自訓 YOLO 樹幹遮罩 |
| AI／數位孿生＋成長 | Lee et al., Tree-D Fusion | **ECCV 2024** | 真實樹 → 可模擬成長的 3D 孿生；本系統：前期盤點 → 本期盤點 → 成長趨勢 |

都市林由單次調查走向可重跑的 digital inventory 之後，才能談成長、健康異常與碳匯增量。本系統的時序層就是把這一點接到實務。

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

Git 只收程式、YOLO 權重（`yolo_seg/runs/v1`、`v2`、`v3` 的 `weights/best.pt`；推論優先用最新的 v3）、前端程式，以及 `app/public/scans/` 示範媒體（不含超大 scene PLY）。訓練用照片在本機 `treedata/`，不進 Git。

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

## 5. 時序成長（Temporal Growth）

盤點窗把單次量測提升為長期環境監測：

**前期盤點 → 本期盤點 → 成長趨勢**

| 判定 | 顏色 | 含義 | 碳匯 |
|------|------|------|------|
| 正常成長 | 綠 | 年增量落在都市林常態 | 較前期增量可列管、納入下期比對 |
| 幾乎停長 | 黃 | 大徑木年增量趨近下限 | 長期吸收量將偏低 |
| 待觀察 | 黃 | 幼木或 YOLO 信心偏低 | 僅供參考，下期實測再定案 |
| 異常 Warning | 紅 | 量測不可信或胸徑極端（疑併株） | **不得逕列正式統計**，請現場手測 |

尚無前期實測時，前期／趨勢依本趟胸徑與拍攝期（3／7／9 月）推估；下一趟 JSON 進來後改掛實測比對。App 左側列出 Warning 樹；樹表最後一欄「健康度」用圖示標正常／停長／待觀察／Warning，不再整列上紅底。

---

## 6. 檔名（請維持一致）

| 位置 | 規則 | 例子 |
|------|------|------|
| 完整場景 | `{掃描ID}.ply` | `20260818092855.ply`（不要再加 `backup_`） |
| 單棵樹 | `{掃描ID}_single_tree.ply` | `20260818092855_single_tree.ply` |
| SuperSplat | `{掃描ID}_supersplat.ply` | `20260818092855_supersplat.ply` |
| 盤點產出 | `Tree_00X_single_tree.ply` / `_supersplat.ply` | 在 `inventory_out/models/` |

`GPUCache` 不是模型，是瀏覽器／SuperSplat 的 GPU 著色器快取，可刪，不進管線。

原始掃描裡的 `LIDAR_`、`IMAGE_` 是機器匯出名稱，不要改。

---

## 7. 自動盤點在做什麼

| 步驟 | 說明 |
|------|------|
| 素材檢查 | 去噪點雲、calib、照片、完整 3DGS 是否齊 |
| 分樹 | 多張照片 YOLO 偵測 → 射到地面 → 分群 → Tree_001…（魚眼可切 tile） |
| 最佳視角 | 每棵樹選一張最適合量的照片（偏好遮罩靠下、距離較近） |
| YOLO 遮罩 | 只用自訓模型（優先 `yolo_seg/runs/v3/weights/best.pt`），類別 `tree_trunk`；信心門檻 0.05。SegFormer 地板／天空排除預設關閉 |
| 胸徑 | 見下一節 |
| 3D 瘦身 | 依同一張遮罩從完整公園高斯切出一棵，並轉 SuperSplat |
| 報告 | HTML、JSON、CSV、俯視圖 |

每張照片的姿態來自 `cameras.json`（旋轉是 **C2W**），不要用一份 `calib.json` 外參套所有樹。

---

## 8. YOLO 樹幹分割（v1 → v3）

訓練與資料轉換在 `yolo_seg/`。新照片放進本機 `treedata/` 後跑 `python prepare_dataset.py`，再改 `train.py` 的 `RESUME_WEIGHTS`／`RUN_NAME` 做微調。推論一律走 `yolo_seg/config.py`：有 v3 用 v3，否則退回 v2、v1。

| 版 | 起點 | 這輪加什麼 | 資料集 | 權重 |
|----|------|------------|--------|------|
| v1 | Ultralytics COCO | 既有公園／校園樹幹標記 | 初版 | `runs/v1/weights/best.pt` |
| v2 | v1 `best.pt` | 100 張非樹木負樣本（空 YOLO 標記，抑制路燈／招牌誤檢） | train 1039／val 115 | `runs/v2/weights/best.pt` |
| v3 | v2 `best.pt` | 惠來公園 102 年 238 張（LabelMe `trunk+branch1`） | **1123** 組（train 1011／val 112，含約 100 張負樣本） | `runs/v3/weights/best.pt` ← **目前正式用** |

v3 約 21 epoch 提早停止。`公七公園102年labelme` 有標記、沒有對應照片資料夾，這輪沒進訓練。

負樣本規則：資料夾名含「非樹木」或標記類別 `nottree` 等，寫成空 `.txt`，讓模型學「這張沒有樹幹」。惠來 102 照片若多包一層子資料夾，`prepare_dataset` 會遞迴找檔名對應的 JPG。

---

## 9. 胸徑演算法（從單樹做到全公園）

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

## 10. 展示系統（`app/`）— 2026-09-01 進度

前端已可實測，不是預留草圖。啟動見 [`app/README.md`](app/README.md)；接新掃描見 [`app/NEXT_STEPS.md`](app/NEXT_STEPS.md)。

### 已完成

| 編號 | 功能 | 狀態 |
|------|------|------|
| P1 | 登入（示範帳號／角色） | ✅ |
| P2 | 全台公園／學校地圖選點＋搜尋 | ✅ |
| P3 | 國土測繪底圖（街道／空拍）、GPS、路徑錄製／GPX | ✅ |
| P4 | 盤點視窗：樹表、燈號篩選、摘要、最後一欄健康度 | ✅ |
| P5 | 影像：Segmentation、胸高橫切面、點雲側視（預覽不重複標標題） | ✅ |
| P6 | 3D 點雲（Three.js，直立＋繞鉛直軸） | ✅ |
| P7 | 匯入三格（去噪 PLY／高斯 PLY／照片資料夾） | ✅ |
| P8 | 現場手測＋待複核篩選＋CSV 匯出 | ✅ |
| P9 | 碳匯工作表 | ✅ |
| P10 | Microsoft AI/Data 分析層：DBH 誤差、Analytics CSV/Excel、Power BI/Fabric/Agent 樣板 | ✅ |
| P11 | App 內盤點 AI 助理：待複核、精度、碳匯與行動建議；Azure AI 可選、本機可退回 | ✅ |

盤點視窗左側只保留路徑圖；原本會逐棵列出的待複核清單已移除，避免在 16 棵以上資料時占滿畫面。待確認、需複核與全部待複核仍可由樹表上方的篩選頁籤查看。

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

樹表用卡片底色＋斑馬紋，表頭深藍、最後一欄「健康度」；篩選列精簡（例如 `全 16`、`! 1`）。成長視窗只留管線與趨勢圖，不再重複一張表。選點頁已拿掉 ColorLegend。

### 示範帳號

| 工作編號 | 密碼 |
|---------|------|
| E-1027 | arbor1027 |
| E-2041 | arbor2041 |
| E-3308 | arbor3308 |

---

## 11. 主要套件

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

## Microsoft AI/Data 競賽分析層

新增離線 DBH 誤差驗證、統一 Analytics CSV／Excel、確認固定樹號後的跨期比較、Power BI 模型草稿、Fabric／Data Agent 設定與預設關閉雲端的 Foundry／本機 RAG。
完整操作與驗證限制見 [競賽版操作指南](docs/microsoft/README.md)。既有 YOLO／DBH／3DGS 管線維持原樣。
macOS 競賽開發環境與 Azure CLI／Foundry SDK 安裝狀態見 [macOS 建置指南](docs/microsoft/MACOS_SETUP.md)。
已建立的 Azure for Students Foundry 專案、模型部署與安全設定見 [Azure 部署紀錄](docs/microsoft/AZURE_DEPLOYMENT.md)。

App 的盤點視窗新增「詢問 AI 助理」。它會把當次樹木盤點整理成受限證據，回答待複核、精度、碳匯與下一步；沒有 Azure 設定時使用本機規則，Azure 暫時失敗也會安全退回。金鑰只由 Vite 伺服器讀取，不送進瀏覽器 bundle。設定方式見 `app/.env.example`。

2026-09-21 已合併既有競賽分支至 main，Windows 接續版新增：
- 四年季度模擬（2022 Q3–2026 Q2，16 季×16 棵=256 筆），來源及身份明確標為模擬，禁止混入真實 snapshot。
- 五頁 Power BI PBIP/PBIR 產生器，真實／模擬專案分開，真實精度 measures 排除合成資料。
- Windows Python 路徑／UTF-8 測試修正，以及季度 CSV 範例。

重建指令、Power BI 開啟方法與仍待 Desktop 驗收的項目見 [Windows 與季度模擬指南](docs/microsoft/WINDOWS.md)。
