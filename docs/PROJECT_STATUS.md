# Arbor3D 專案現況與後續路線圖

更新日期：2026-09-22。這份文件是競賽展示、開發交接與驗收的單一進度入口；技術細節仍以各子目錄文件為準。

## 目前結論

Arbor3D 已具備可展示的 **Physical → Digital → AI** 主流程、真實盤點介面、Microsoft AI/Data 離線分析層，以及已上線並通過端到端測試的 Azure Foundry 模型。現在可以從逢甲大學示範路徑查看 16 棵樹、影像／點雲、DBH 與碳匯資料，並在 App 內向 AI 助理詢問待複核項目及後續行動。

目前仍不能宣稱「完整實地長期監測已完成」：只有一期真實掃描，沒有第二期同樹實測、固定樹號與標準 1.3 m 人工 DBH，因此精度 KPI 與真實生長量仍應保持空白。

## 已完成

| 區塊 | 完成內容 | 驗證狀態 |
|---|---|---|
| 實體與數位盤點 | YOLO 樹幹分割、單木 ID、DBH、3DGS／PLY、JSON／CSV／HTML | 已有逢甲 2026-08-18 真實示範資料，16 棵 |
| Web App | 示範登入、地圖搜尋、可靠性標示路線、盤點表、燈號、影像、3D、手測、CSV、碳匯；大型盤點工具延遲載入 | App 15 項測試、lint、production build 通過 |
| 正式匯入閉環 | App 接收 PLY、照片、`calib.json`、`cameras.json`；adapter 自動整理既有資料目錄、執行 Python、發佈附件並綁定路徑 | adapter 3 項測試通過；尚待下一趟真實掃描與完整 GPU 環境驗收 |
| DEMO 完整度 | 24 組模擬盤點的四格影像改用逢甲實拍照片與真實掃描 `20260818092855` 的分割圖、胸高橫切面、點雲側視；另附 900 點示意 PLY；匯入視窗可一鍵產生完整模擬素材 | 模擬資料會標明「借用逢甲來源、非目前地點現場證據」；App 自動檢查涵蓋全部 24 組 |
| 分析資料層 | Analytics JSON／CSV／Excel、資料契約、誤差與跨期規則 | Python 23 項測試通過；真實／模擬資料分離 |
| Power BI／Fabric | PBIP/PBIR 產生器、Power Query、DAX、Spark 與 Data Agent 樣板 | 官方 JSON schema 通過；仍待 Windows Desktop 畫面驗收 |
| App AI 助理 | 以盤點證據回答待複核、精度、碳匯限制與行動建議 | 本機模式與 Azure 失敗退回機制皆已實作 |
| Azure Foundry | Azure for Students 資源、project、`gpt-4.1-mini` deployment、Entra 無金鑰認證 | 資源／project／deployment 均為 Succeeded；App API 回傳 `provider=azure` |
| 安全與依賴 | `.env.local` 不進 Git、瀏覽器拿不到金鑰、Node 依賴稽核 | `npm audit` 0 vulnerabilities |

Azure 實際部署資訊與停止費用方式見 [Microsoft Azure 部署紀錄](microsoft/AZURE_DEPLOYMENT.md)。

## 待完成與優先順序

### P0 — 競賽可信度與真正閉環

| 任務 | 為什麼必要 | 完成條件 |
|---|---|---|
| 用新掃描驗收正式 Arbor3D 匯入閉環 | App、校正／姿態輸入、正式 adapter 與自動發佈已完成；未設定正式環境時仍明確使用快速預覽 | 取得下一趟真實素材，在具 PyTorch／Open3D／Ultralytics 的環境跑完，並確認 App 出現正式結果 |
| 完成第二期同路徑真實掃描 | 現在只有一期，成長曲線不能當作實測結果 | 至少兩期掃描、同樹固定 ID 經人工確認，可產生真實 FactGrowth |
| 補標準 1.3 m 人工 DBH 與日期 | 沒有人工配對時，MAE／RMSE 不可計算 | 完成現場複核並匯出分析 bundle；有效配對數大於 0 |
| 用現場 GPX 取代暫定路線 | 25 個地點已全量檢查：23 條顯示線貼合 OSM pedestrian／footway 且不與建物、水域相交；中山醫與弘光無可靠公開步道，已停止顯示推測線。樹位仍是相對 XYZ 沿路徑插值 | 實際 GPX／App 錄製軌跡完成並核對樹序 |

### P1 — 正式使用與 Microsoft 展示

| 任務 | 完成條件 |
|---|---|
| 正式帳號與權限 API | 取代寫死的示範帳號；至少具管理者／盤點人員角色與伺服器端 session |
| 手測資料同步後端 | 人工 DBH、樹高與複核狀態不再只存在單一瀏覽器 localStorage |
| Windows Power BI Desktop 驗收 | 實際刷新 Power Query、驗證 DAX、關係、空值語意及五頁版面，再決定是否發佈 |
| Fabric／Power BI 雲端發佈決策 | 確認學生訂閱能力、容量、成本、RLS 與展示帳號後才部署；目前不宣稱已發佈 |
| Azure 成本防護 | 在 Azure Cost Management 建立可通知負責人的 budget／alert，並定期檢查用量 |

### P2 — 場域體驗與工程優化

- 手機戶外單手操作、較大按鈕與地圖全螢幕。
- PWA／離線地圖與待同步佇列，因公園現場網路可能不穩。
- 繼續拆分全臺 10,462 筆地點目錄；盤點／匯入對話框已先改為延遲載入。
- 清出至少 12 GiB 空間後，再安裝完整 PyTorch／Open3D／Ultralytics 管線並重跑 GPU 驗證。
- Docker 化本機 RAG／分析服務屬選配，不是 App 展示必要條件。

## 模擬資料界線

目前缺少的展示媒體已用可重建的合成檔補齊，目的是讓影像、3D、上傳與盤點互動能完整演示。這些資料以 `dataset_kind=simulated`、`sim*` 掃描 ID、畫面警告及資產內 `DEMO / SIMULATED` 標記隔離。它們不會補足真實的第二期掃描、人工 1.3 m DBH、現場 GPX 或精度 KPI；上述項目仍須現場取得。

## 本機展示方式

```bash
cd app
npm install
npm run dev -- --host 127.0.0.1 --port 5324 --strictPort
```

開啟 `http://127.0.0.1:5324/`，按「示範登入」，搜尋「逢甲大學」，選擇「校園掃描路徑（8/18 · 7-11）」。也可使用示範帳號 `E-1027`／`arbor1027`。

若 `.env.local` 已保留 Azure endpoint、deployment、費用鎖，且本機 `az login` 身分有效，AI 助理會使用 Azure；否則會自動使用本機證據模式，不影響盤點展示。

## 驗收界線

- 現有 16 棵是真實掃描，但目前跨期曲線中的非基準時間點不得說成真實觀測。
- 碳匯是盤點估算，不是認證碳權、年度減碳量或健康診斷。
- Power BI 專案檔與 schema 已驗證，不等於已在 Power BI Desktop 完成畫面與 DAX 引擎驗收。
- Git 不保存原始大型點雲、完整高斯、Azure 金鑰、訂閱 ID 或個人帳號。
