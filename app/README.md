# Arbor3D 盤點介面

> **倉庫**：https://github.com/toby0407-del/arbor3d-interface  
> **量測管線（Python）**：https://github.com/toby0407-del/Arbor3D

---

## 一、系統概覽

本專案是一套基於瀏覽器的**樹木盤點複核工具**，用於：

1. 在地圖上選擇公園／學校 → 選擇掃描路徑
2. 上傳去噪 PLY、高斯濺射 PLY、原始照片 → 系統收檔並可接量測管線
3. 查看盤點結果：樹表、胸徑燈號、Segmentation、橫切面、3D 點雲
4. 填寫現場手測、碳匯計算、匯出 CSV
5. 在盤點視窗詢問 AI 助理，取得待複核、精度、碳匯與下一步建議

AI 助理採用 Microsoft Foundry Local Phi-4／Copilot Studio＋本機 RAG：知識庫含 1,000 題 Arbor3D 領域問答，先檢索相關證據再交給模型；模型未設定或呼叫失敗時會回退到本機規則回答。這 1,000 題是知識與評測資料，不是 1,000 筆現場盤點。

**技術棧**：React 19 + TypeScript + Vite 8 + Leaflet（國土測繪底圖）+ Three.js（3D 點雲）

Production build 會註冊 PWA Service Worker。使用者曾開啟的頁面、程式資產、地點 JSON 與影像可在弱網／離線時重用；畫面會顯示離線提示，人工量測繼續保存在裝置，恢復連線後同步 Cosmos DB。尚未查看過的地圖區域仍需要網路。

---

## 二、使用流程

```
┌──────────┐     ┌────────────┐     ┌──────────────┐     ┌───────────────┐
│  1. 登入  │ ──→ │ 2. 地圖選點 │ ──→ │ 3. 點路徑     │ ──→ │ 4. 盤點／匯入  │
│  帳密驗證  │     │ 搜尋＋GPS   │     │ 已盤點→樹表   │     │ 正式素材上傳   │
└──────────┘     └────────────┘     │ 未盤點→匯入   │     │ 碳匯＋CSV      │
                                    └──────────────┘     └───────────────┘
```

### 步驟詳解

| 步驟 | 操作 | 說明 |
|------|------|------|
| **1. 登入** | 正式環境使用 Microsoft 工作帳號；本機可按「示範登入」 | Entra ID + App roles + HttpOnly Session |
| **2. 地圖選點** | 搜尋欄打「台中逢甲」、或直接點地圖上的點 | 支援台／臺互轉、縣市＋名稱連打 |
| **3a. 已盤點路徑** | 點路徑 → 直接開盤點視窗（樹表、影像、3D、碳匯） | 旁邊有「匯入」按鈕可再上傳新一組 |
| **3b. 尚未盤點** | 點路徑 → 開匯入對話框 | 快速預覽三項；正式盤點再加校正／姿態（見下方） |
| **4. 錄製路徑**（可選） | 側欄展開 → 開始記錄 → 停止時問是否保存 | 精度 ≤ 10 m 才記點；可下載 GPX |
| **5. 匯入** | 去噪 PLY、高斯濺射 PLY、原始照片；正式模式另加 `calib.json`、`cameras.json` | 編號自動跟資料夾名；可選年度 |
| **6. 盤點視窗** | 樹表（燈號篩選）、影像分頁、量測分頁、3D 分頁、碳匯工作表 | 手測離線暫存並同步 Cosmos DB、匯出 CSV |

沒有掃描素材時，可在匯入視窗按「一鍵載入完整模擬素材（DEMO）」測試上傳與快速盤點。既有模擬盤點使用 4 種 Segmentation、4 種橫切面與 4 種點雲側視合成素材，依掃描與樹號固定分派；不顯示逢甲實拍原圖。3D 使用 900 點示意 PLY，畫面仍保留合成展示標記。

### 匯入素材

| 格位 | 類型 | 內容 |
|------|------|------|
| 去噪 PLY | 選 `.ply` 檔 | RayStudio 解算去噪後的 PLY |
| 高斯濺射 PLY | 選 `.ply` 檔 | 訓練完成後**匯出**的 PLY（不要用 `ray_gaussian/input.ply`） |
| 原始照片 | 選**資料夾** | 這一趟訓練用的影像資料夾 |
| 相機校正／姿態 | 選**資料夾** | 正式管線必須同時包含 `calib.json`、`cameras.json`；快速預覽可不選 |

上傳前會驗證副檔名和 PLY 檔頭（ASCII `ply` magic）。編號 ID 自動等於原始照片資料夾名。

---

## 三、專案架構

```
arbor3d-interface/
├── index.html                      # Vite 入口
├── vite.config.ts                  # Vite 設定（含 importApiPlugin）
├── package.json
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
│
├── server/                         # Vite dev server 中介層
│   └── importApiPlugin.ts          # POST /api/import/jobs 收檔 + 跑管線
│
├── scripts/
│   ├── run-postprocess.mjs         # 後續量測（呼叫 Arbor3D Python）
│   ├── compute-inventory.mjs       # 本機計算盤點 JSON
│   └── render_inventory_figures.py # 產生俯視圖等圖片
│
├── inbox/                          # 匯入上傳暫存（.gitignore）
│
├── public/
│   ├── favicon.svg
│   ├── icons.svg
│   └── scans/
│       └── 20260818092855/         # 8/18 逢甲 7-11 實測
│           ├── dbh/                # 胸高橫切面
│           ├── masks/              # Segmentation
│           ├── maps/               # 俯視圖
│           ├── previews/           # 點雲側視
│           └── inventory.json
│
└── src/
    ├── main.tsx                    # React 進入點
    ├── App.tsx                     # 路由：login ↔ sites
    ├── types.ts                    # TreeRecord, ParkInventoryReport, TrafficLight
    ├── index.css                   # 全站樣式
    │
    ├── pages/
    │   ├── LoginPage.tsx           # 登入畫面（帳密 + 示範登入）
    │   ├── SitePickerPage.tsx      # 地圖選點＋側欄（錄製、路徑列表、overlays）
    │   ├── PathInventoryDialog.tsx  # 盤點視窗（樹表、影像、量測、3D、碳匯）
    │   └── PathImportDialog.tsx    # 匯入對話框（正式素材 + 年度 + 進度）
    │
    ├── components/
    │   ├── OsmSiteMap.tsx          # Leaflet 地圖（定位、底圖切換、overlays）
    │   ├── PathTreeMap.tsx         # 路徑小地圖（盤點視窗內）
    │   ├── PlyViewer.tsx           # Three.js 3D 點雲（直立、繞鉛直軸）
    │   ├── ColorLegend.tsx         # 綠黃紅燈號說明
    │   └── BrandMark.tsx           # Logo SVG
    │
    ├── hooks/
    │   ├── usePathRecorder.ts      # GPS 錄製（起測 ≤ 10 m）
    │   └── useFieldMeasures.ts     # 現場手測（離線暫存 + Cosmos 同步）
    │
    ├── lib/
    │   ├── session.ts              # sessionStorage 登入狀態
    │   ├── geolocation.ts          # 快速定位策略（Wi-Fi → GPS）
    │   ├── mapBounds.ts            # 台灣範圍常數
    │   ├── mapTiles.ts             # 國土測繪底圖（街道 / 空拍）
    │   ├── mapViewStore.ts         # 地圖視野持久化（sessionStorage）
    │   ├── mapOverlays.ts          # 錄製／匯入路段 overlays
    │   ├── treePlacement.ts        # 無 GPS 時沿路徑折線放樹點
    │   ├── scanMedia.ts            # 組 /scans/{scanId}/{path} URL
    │   ├── loadPly.ts              # 解析 PLY（ascii / binary）
    │   ├── importApi.ts            # 前端 fetch /api/import/*
    │   ├── status.ts               # 燈號判定 + inventoryStats
    │   ├── carbon.ts               # 碳匯公式（圓周 × 高 × 係數）
    │   ├── csv.ts                  # 匯出 CSV（盤點 + 碳匯）
    │   ├── format.ts               # 格式化胸徑、弧度、坐標
    │   └── gpx.ts                  # GPX 匯出 + haversine
    │
    └── data/
        ├── taiwan_sites.json       # 全台公園／學校目錄（OSM 匯出）
        ├── sites.ts                # 地點搜尋、tokenize
        ├── scanBindings.ts         # 掃描 ↔ 公園／路徑綁定
        ├── inventory.ts            # 自動載入 inventories/*.json
        ├── inventories/
        │   └── 20260818092855.json # 8/18 逢甲 7-11 實測盤點
        └── park_inventory_report.sample.json
```

---

## 四、資料流

```
現場拍攝
   │
   ▼
RayStudio 去噪 → 去噪 .ply ─┐
RayStudio 高斯濺射 → 濺射 .ply ─┤──→ 介面「匯入素材」
原始照片資料夾 ──────────────────┤        │
calib.json + cameras.json ───────┘        │
                                         ▼
                                  inbox/{jobId}/
                                  ├── denoised/
                                  ├── gaussian/
                                  ├── raw/
                                  └── metadata/
                                         │
                         ┌───────────────┤
                         │ 有設正式管線？ │
                         │               │
                    是   ▼          否   ▼
              run-postprocess.mjs   compute-inventory.mjs
              → Arbor3D Python      → 點雲快速預覽
              → 正式 JSON + 媒體     → 標示非正式 YOLO／DBH
                         │
                         ▼
              src/data/inventories/{scanId}.json  ← 盤點報告
              public/scans/_bindings.json          ← 動態綁到公園路徑
              public/scans/{scanId}/              ← 照片/遮罩/剖面/PLY
                         │
                         ▼
                    介面顯示盤點
```

---

## 五、燈號規則

程式：`src/lib/status.ts`

| 燈號 | 條件 | 意義 |
|------|------|------|
| **淡綠** | 無特殊 note | 演算法較可信，可作盤點參考 |
| **淡黃** | — | （保留，目前未使用） |
| **淡紅** | `wide_caliper`、`gap`、`no_measurement` | 卡尺偏寬／切片缺口／量不到；**勿當正式樹圍**，進「待複核」 |

現場手測欄位（`useFieldMeasures`）離線保存在 localStorage，連線後同步 Cosmos DB，**不覆蓋**演算法 `DBH_cm`。

---

## 六、碳匯計算

程式：`src/lib/carbon.ts`

公式：`碳儲量D = 圓周² × 樹高 × 係數`，`CO₂當量 = D × 3.667`

| 欄位 | 來源 | 備註 |
|------|------|------|
| 圓周 (m) | π × DBH(m) | 手測優先，回退演算法 |
| 樹高 (m) | 手測 or 估算 | 無實測時用 `1.3 + 1.8√DBH` 粗估，標記「估算」 |
| 係數 | 預設 0.0159（表定）| 可選闊葉 0.027 / 針葉 0.020 / 自訂 |

---

## 七、示範帳號

| 工作編號 | 姓名 | 角色 | 密碼 |
|---------|------|------|------|
| E-1027 | 林志偉 | 現場調查員 | arbor1027 |
| E-2041 | 陳雅婷 | 複核人員 | arbor2041 |
| E-3308 | 黃建宏 | 承辦人 | arbor3308 |

---

## 八、已接上的實測掃描

| 項目 | 內容 |
|------|------|
| 地點 | 逢甲大學 · 學思樓／7-11 南側走廊 |
| 路徑 | 校園掃描路徑（8/18 · 7-11） |
| scan_id | `20260818092855` |
| JSON | `src/data/inventories/20260818092855.json` |
| 媒體 | `public/scans/20260818092855/`（橫切面、Segmentation、點雲側視） |
| 棵數 | 16 棵 |
| GPS | 無（用相對座標沿路徑放置） |

本機驗證：登入 → 搜尋「逢甲」→ 點 8/18 路徑 → 樹表、橫切面、點雲側視。高斯濺射整場 PLY 超過 GitHub 100 MB，3D 需本機另放 `public/scans/20260818092855/models/scene_gaussian.ply`。

---

## 九、啟動

```bash
git clone https://github.com/toby0407-del/Arbor3D.git
cd Arbor3D/app
npm install
npm run dev
```

瀏覽器開 http://127.0.0.1:5173/，登入後搜尋「逢甲」即可驗證。

### 帳號、Session 與人工量測同步

正式登入改用 Microsoft Entra ID（原 Azure Active Directory）：前端透過 MSAL Authorization Code + PKCE 取得 App API access token，伺服器驗證租戶 issuer、audience、簽章及 App roles 後，才建立 8 小時 HttpOnly、SameSite=Strict Session Cookie。帳號密碼只交由 Microsoft 處理，App 不保存正式密碼或 client secret。

人工 DBH、樹高、1.3 m 確認、日期與備註會先保存在裝置供離線使用；恢復連線後同步到 Azure Cosmos DB for NoSQL。Cosmos document 使用 `scanId` 分割鍵與 point read／upsert，伺服器以 Managed Identity 存取，不把 account key 送到瀏覽器。未設定 Entra／Cosmos 時才啟用伺服器端展示帳號與 `.runtime` 本機檔案備援。

Entra App registration、App roles、Cosmos Bicep 與環境變數見 [`infra/azure/README.md`](../infra/azure/README.md)。正式模式會要求 `/api/assistant` 與匯入 API 具有效 Session；預設只有「管理者、承辦人」可寫入匯入 API，可用 `ARBOR_IMPORT_ROLES` 調整。

### 盤點 AI 助理（Windows 本機 Phi-4＋雲端 Copilot Studio）

Windows 本機版使用 Foundry Local `Phi-4-mini`；Azure 公開站可使用 Copilot Studio 的 Mobile app／Direct Line 通道。兩種模式未設定時，助理會使用本機證據規則回答。

助理會先從 `../agents/knowledge/` 執行本機 RAG，再把當次盤點證據與命中的規範片段送給 Phi-4 或 Copilot Studio。回答畫面會顯示模型名稱及 `+ RAG`；RAG 檢索本身不呼叫付費 embedding 或搜尋服務。Phi-4 安裝與微調資料見 `docs/microsoft/PHI4_LOCAL.md`。

```bash
cp .env.example .env.local
```

先在 Copilot Studio 建立並發布代理，到 **Channels → Mobile app** 複製 Token Endpoint。在 `.env.local` 填入 `COPILOT_STUDIO_TOKEN_ENDPOINT`、`COPILOT_STUDIO_AGENT_NAME`，把 `ARBOR_AI_PROVIDER` 設為 `copilot`，並把 `ARBOR_ALLOW_BILLABLE_CLOUD` 設為 `YES_I_ACCEPT_COSTS` 後重啟。`copilot` 模式失敗時只退回本機證據模式，不會呼叫 GPT。Token Endpoint 不要改成 `VITE_` 前綴，也不要提交 `.env.local`。

正式網站固定使用 `ARBOR_AI_PROVIDER=copilot`，不設定 `AZURE_AI_ENDPOINT`／`AZURE_AI_MODEL`，因此不會直接呼叫 Azure GPT。所有 Direct Line token 只在伺服器端處理。

### 接量測管線（可選）

未設定下列變數時，「開始計算」仍會產生點雲快速預覽盤點，但不得當作正式 YOLO／標準 1.3 m DBH 成果。設定後會切換到正式 adapter：

```bash
# 方法 A：完整指令（{jobDir}、{scanId}、{pathId} 會被代入）
export ARBOR3D_CMD='python3 /path/to/Arbor3D/scripts/postprocess_from_inbox.py --job-dir {jobDir} --scan-id {scanId} --path-id {pathId}'

# 方法 B：指定 Arbor3D 倉庫路徑
export ARBOR3D_ROOT=/path/to/Arbor3D

# Windows PowerShell
$env:ARBOR3D_CMD='python3 ...'
```

### 其他 npm scripts

| 指令 | 說明 |
|------|------|
| `npm run dev` | 啟動 Vite 開發伺服器 |
| `npm run build` | TypeScript 檢查 + 打包 |
| `npm run lint` | oxlint 檢查 |
| `npm run preview` | 預覽 build 產物 |
| `npm run postprocess` | 手動跑後續量測 `node scripts/run-postprocess.mjs <jobDir> <scanId> [pathId]` |

---

## 十、接新掃描（詳細步驟）

見 [NEXT_STEPS.md](./NEXT_STEPS.md)

---

## 十一、重要檔案索引

| 路徑 | 用途 |
|------|------|
| `src/App.tsx` | 根元件（login ↔ sites 兩畫面） |
| `src/pages/SitePickerPage.tsx` | 地圖選點主頁 |
| `src/pages/PathInventoryDialog.tsx` | 盤點視窗（樹表＋影像＋量測＋3D＋碳匯） |
| `src/pages/PathImportDialog.tsx` | PLY、照片、校正／姿態匯入對話框 |
| `src/components/OsmSiteMap.tsx` | Leaflet 地圖 |
| `src/components/PlyViewer.tsx` | Three.js 3D 點雲 |
| `src/data/taiwan_sites.json` | 全台公園／學校 OSM 目錄 |
| `src/data/inventories/*.json` | 盤點報告 JSON |
| `src/data/scanBindings.ts` | 掃描 ↔ 地點綁定 |
| `src/lib/status.ts` | 燈號判定 |
| `src/lib/carbon.ts` | 碳匯公式 |
| `src/lib/treePlacement.ts` | 無 GPS 時樹位插值 |
| `src/hooks/useFieldMeasures.ts` | 現場手測（localStorage + Cosmos DB） |
| `src/lib/csv.ts` | CSV 匯出 |
| `server/importApiPlugin.ts` | `/api/import` 後端 |
| `server/accountApiPlugin.ts` | Entra ID、角色與 Session API |
| `server/fieldMeasureStore.ts` | Cosmos DB／本機 fallback repository |
| `../infra/azure/main.bicep` | Azure Cosmos DB 基礎設施 |
| `scripts/run-postprocess.mjs` | 管線呼叫腳本 |
| `scripts/generate-simulated-media.mjs` | 重建 24 組明確標示的 DEMO 媒體與 PLY |
| `../scripts/postprocess_from_inbox.py` | 正式輸入整理、前置檢查、Python 管線與 App 發佈 adapter |
