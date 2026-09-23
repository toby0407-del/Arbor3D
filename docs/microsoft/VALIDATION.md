# 本機驗證紀錄

## Entra／Cosmos 與效能更新（2026-09-23）

- App 26 項、Analytics／AI 26 項測試通過；lint、production build、npm audit、compileall 與 diff check 通過。
- 正式登入 adapter 使用 MSAL Authorization Code + PKCE；後端驗證 Entra v2 issuer、audience、JWKS 簽章與 App roles，再建立 HttpOnly Session。尚未取得本專案的 tenant／client ID，因此未宣稱完成真實租戶登入。
- Cosmos DB repository 使用 Managed Identity／DefaultAzureCredential、`/scanId` 分割鍵及 point read／upsert；本機 file fallback 的寫入、讀回與登出後 401 已用 HTTP 驗證。尚未建立或寫入付費 Cosmos 資源。
- `infra/azure/main.bicep` 已由 Azure CLI Bicep compiler 成功編譯；部署仍需資源群組、全域唯一帳號名稱、Managed Identity object ID 與預算決策。
- 首頁主程式由約 5.2 MB 降至約 193 KB；地點 JSON、31 份盤點、MSAL 與 Three.js 均按需載入。Three.js 點雲 chunk 約 542 KB，只在使用者打開 3D 頁籤時下載。
- App bundle 已可用 `python3 -m powerbi.delivery` 一次產生 canonical Analytics、五頁 PBIP/PBIR 與交付報告；仍不等於 Windows Desktop 的 DAX、刷新、版面或 RLS 驗收。

## Azure for Students 雲端驗證（2026-09-22）

- 登入與訂閱：Azure CLI 登入成功，預設訂閱為 Azure for Students。
- Japan East Foundry resource／project 與 `gpt-4.1-mini` deployment 均為 Succeeded。
- 直接推論最小測試 HTTP 200；App `/api/assistant` 端到端回傳 `provider=azure`。
- 測試問題只含兩筆去識別化樹木盤點證據；沒有上傳人員資料、原始照片、點雲或 Azure key。
- App 新增 Microsoft Entra `DefaultAzureCredential`；API key 僅用於單次記憶體內驗證，沒有寫入檔案或 Git。
- 訂閱／帳號 ID 與 API key 不記錄在專案文件。

## App 盤點 AI 助理（2026-09-22）

- App 測試：11 項通過，其中 3 項驗證待複核樹號、無人工配對時拒絕捏造準確率，以及碳匯必須標為估算。
- Production build 與 lint：通過；既有大型 bundle 警告仍在。
- Python analytics：23 項通過。
- `/api/assistant` 已用實際 HTTP 請求驗證本機證據模式、回傳樹號與依據。
- Azure 金鑰只由 Vite server 讀取，環境變數沒有 `VITE_` 前綴；請求失敗會退回本機證據模式。
- 此 Mac 未安裝 Azure CLI，也沒有提供資源端點、模型 deployment 或金鑰，因此本輪沒有建立 Azure 資源或做會計費的雲端推論。程式已可依 `app/.env.example` 接上既有部署。

## Windows 接續驗證（2026-09-21）

基準：PR #1 合併後 `1624ee9`。以下取代原 Mac 階段對本機環境的描述。

- Python unittest：23 項通過，不需以 UTF-8 啟動才能通過中文 fixture。
- App／Excel：8 項通過，真實和模擬兩份快照皆逐格核對，包含 ID、數字、null、公式注入字串與 DEMO 標示。
- Lint：通過且無原 SitePickerPage hook 依賴警告；production build 通過。約 2.83 MB 的既有 bundle 警告仍在。
- 真實 snapshot：16 observations、0 valid pairs、16 review、0 growth；精度保持 null。
- 模擬 snapshot：2022 Q3–2026 Q2，16 季×16 棵=256 筆、16 個模擬固定身份、480 筆跨期（兩來源）。
- 模擬隔離：禁止混合真實與模擬報告；一般分析入口拒絕模擬；每表附 dataset_kind；每項合成來源有 simulated_ 前綴。
- PBIP：已實際產生真實和模擬兩份五頁專案，各 50 個 JSON／PBIP／PBIR／PBISM 定義檔通過 Microsoft 官方 JSON schema。
  測試同時檢查視覺欄位／measure 引用，CSV 雜湊、型別欄名契約與非空專案目錄防覆寫。
- Excel：既有匯出器成功輸出兩份 XLSX；模擬 Overview 已用 Artifact Tool 讀取及渲染檢視，DEMO 標示清楚。
- OneLake ZIP：真實包 10 個檔案、模擬包 25 個檔案；雜湊驗證通過，未上傳。
- Foundry 與 Fabric：本機 dry-run 成功，cloud_called/cloud_write 均 false。
- compileall 與 git diff --check 通過。

**未執行：** Windows 未偵測到 Power BI Desktop 或 Docker。PBIP 是待 Desktop 驗收的草稿；未執行 DAX、
Power Query 刷新、Desktop 視覺驗收或容器 build。沒有建立 Fabric／Foundry 雲端資源。
未取得新的人工實測或第二期真實掃描；模擬資料不代表補齊真實驗證。
季度合成資料交付於 CSV／Excel／Power BI，尚未接入 App 原有月曲線。操作見 [Windows 指南](WINDOWS.md)。

## 原 Mac 階段紀錄

日期：2026-09-21。基準版本：d398b69；工作分支：feat/microsoft-ai-data。

- Python unittest：18 項通過（精度算式、缺值、非法數值、日期／高度排除、固定身份、負增量、方法隔離、重複／孤立紀錄、CSV 注入防護、CLI bundle、OneLake 雜湊、離線 Agent 與雲端鎖）。
- App / Excel Node 測試：7 項通過（AI／人工／推估標示、鄰近月份不當實測、匯出缺值、複核燈號、Excel 逐格與類型一致性）。
- `npm run build --prefix app`：通過。仍有既有大型 bundle 提示（約 2.83 MB 未壓縮）。
- `npm run lint --prefix app`：exit 0；既有 SitePickerPage.tsx useEffect/discardDraft 依賴警告仍存在，未改動該頁。
- `npm audit --prefix app --audit-level=moderate`：0 vulnerabilities。ExcelJS 的 UUID 間接依賴以 override 更新為修補版本，Excel 讀寫測試通過。
- Python compileall、git diff --check：通過。
- JSON Schema Draft 2020-12：示範 analytics.json 通過；Power BI 模型欄位／關係端點檢查通過。
- Excel：獨立 openpyxl 只讀核對全部資料儲存格與 canonical JSON 一致；scan_id 保留文字。以工作表渲染查看 7 張表並修正欄寬、換行、係數精度；渲染器對長數字字串可能顯示科學記號，但 XLSX 實際型別與完整值已核對。
- App 瀏覽器：示範登入 → 逢甲大學 → 既有掃描正常；分析匯出入口、日期欄與預設未勾選標準高度確認欄可見。修正後為 8 待確認 + 8 需複核，待複核合計 16。路徑圖下方的逐棵待複核清單已依介面需求移除，樹表篩選與個別複核原因保留。
- 既有示範資料實際輸出：16 observations、0 valid pairs、MAE/RMSE/Bias/MAPE=null、0 growth rows，沒有填造人工測量。
- 本機 RAG、Foundry dry-run、Fabric dry-run、含 10 個檔案的 OneLake 匯入 ZIP 已生成，沒有雲端呼叫或上傳。

## 未執行的環境驗證

- 沒有 Windows Power BI Desktop，因此 model.bim、Power Query 和 DAX 是本機模型草稿，未驗證 DAX 引擎或製作 PBIX。
- 沒有開通 Fabric／Foundry／付費容量，也沒有 cloud integration test、容器 build 或部署。
- 核心 YOLO、DBH、3DGS 檔案不變；未重新執行需要 GPU／原始點雲的完整重建管線。

以上限制已在操作指南中明列；本機測試通過不能等同雲端部署成功。
