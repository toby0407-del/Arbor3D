# Windows 接續與四年季度模擬

## 2026-09-24 最新接續狀態

GitHub `main` 目前基準為 `f5cb0e4`。新電腦第一次使用：

```powershell
git clone https://github.com/toby0407-del/Arbor3D.git
cd Arbor3D
npm ci --prefix app
az login
```

已經 Clone 過的電腦，在沒有未提交變更時執行：

```powershell
git switch main
git pull --ff-only origin main
npm ci --prefix app
```

建立不進 Git 的 `app\.env.local`，至少填入主要 Cosmos DB：

```env
AZURE_COSMOS_ENDPOINT=https://arbor3dcos483bd05e16.documents.azure.com:443/
AZURE_COSMOS_DATABASE=Arbor3D
AZURE_COSMOS_CONTAINER=FieldMeasures
ARBOR_COSMOS_AUTO_CREATE=NO
ARBOR_ALLOW_BILLABLE_CLOUD=NO
```

使用同一個 Azure for Students 帳號執行 `az login`。不要把 access token、Cosmos key、Client Secret 或 `.env.local` 提交到 Git。Entra App registration 仍需學校租戶管理員開放應用程式註冊或指派 Application Developer；在此之前 App 使用展示登入＋Cosmos。

```powershell
npm test --prefix app
npm run build --prefix app
npm run dev --prefix app -- --host 127.0.0.1 --port 5174
```

既有 `feat/microsoft-ai-data` 已經由 PR #1 合併至 `main`（1624ee9）。
本次接續加入 Windows 測試支援、明確的模擬資料契約及五頁 PBIP/PBIR 專案產生器。
不變更核心 YOLO／DBH／3DGS 演算法，不開通付費服務。

## 四年季度示範

預設涵蓋 **2022 Q3–2026 Q2，共 16 季、每季 16 棵、256 筆觀測**。
截至 2026-09-21，2026 Q3 尚未結束，故以 2026-06-30 為最後完整季。
16 個季末觀測點的首末距離為 15 個季度，代表四年季度槽位，而非四整年的兩端基準點。
如需首末剛好相隔四年，可改 `--quarters 17`。

所有歷史量測、日期、AI 數值、人工欄位、固定樹號均為合成；現有非標準 DBH 僅作尺寸參考。
成長參數、量測雜訊、停滯與負增量情境是展示設定，不是生物模型校正或健康診斷。
種子預設 42，可重現。假設見輸出 `simulation.json`；方便直接查看的 256 筆資料也收錄在
`analytics/examples/quarterly-SIMULATED.csv`。

分析契約升為 **1.1**：每張表新增 `dataset_kind=observed|simulated`；模擬來源標示 `simulated_*`，
固定身份標示 `simulated`。同一 snapshot 禁止混合 observed 和 simulated，普通分析入口拒絕模擬報告。
示範資料需由 `analytics.simulate` 的明確入口建立。真實精度 DAX 使用 observed 過濾；示範誤差由
`Demo Pairs`、`Demo MAE cm` 顯示，反映注入的噪音，不能用於宣稱演算法實測精度。

## 本機重建

需要 Python 3.9+、Node 22.12+、npm；選用 schema 檢查需要 `jsonschema`。
在專案根目錄執行 PowerShell：

```powershell
npm ci --prefix app
python -X utf8 -m analytics --report app/src/data/inventories/20260818092855.json --site-id fengchia --out outputs/competition
python -X utf8 -m analytics.simulate --out outputs/simulated-quarterly --quarters 16 --end 2026-06-30 --seed 42
node app/scripts/export-analytics-excel.mjs outputs/competition/analytics.json outputs/competition/analytics.xlsx
node app/scripts/export-analytics-excel.mjs outputs/simulated-quarterly/analytics/analytics.json outputs/simulated-quarterly/analytics/analytics-SIMULATED.xlsx
python -X utf8 -m powerbi.build_project --analytics outputs/competition --out outputs/powerbi-observed
python -X utf8 -m powerbi.build_project --analytics outputs/simulated-quarterly/analytics --out outputs/powerbi-simulated
python -X utf8 -m fabric.package_snapshot --input outputs/simulated-quarterly/analytics --output outputs/simulated-quarterly/onelake-SIMULATED.zip
```

`simulate` 和 `build_project` 拒絕覆寫非空目錄，以免覆蓋現場資料或 Desktop 手動修改；重建時請改用新目錄名稱。
Excel 是 canonical JSON 的值快照，重新產生 JSON 後要重跑匯出，不會自動回寫 App。
生成內容位於 Git 忽略的 `outputs/`；Git 收錄程式、文件及清楚標示的季度 CSV 範例。

## Power BI Desktop 驗收

本機產物是真正的 PBIP/PBIR 文字專案與 Import semantic model，仍為**尚未 Desktop 驗收的草稿**。
這次 Windows 環境未偵測到 Power BI Desktop，不以 JSON schema 驗證替代 Desktop 開啟、Power Query 刷新、DAX 執行或視覺驗收。

1. 在已安裝的 Power BI Desktop 開啟 `outputs/powerbi-simulated/Arbor3D.pbip`。
2. 若版本需要，於選項啟用 PBIP／PBIR 支援。重新整理本機 CSV，不需登入或發佈雲端。
3. 若移動資料夾，修改 `AnalyticsFolder` 參數至對應 `analytics` 絕對路徑。
4. 檢查五頁：盤點總覽、DBH 驗證、季度比較、資料品質、推估碳量。模擬版每頁及視覺标题都有 DEMO。
5. 未篩選時應有 256 觀測、16 棵模擬固定樹、480 跨期紀錄（16×15×2 來源）。
   真實 `Valid Pairs` 不得顯示 256；真實 MAE 必須空白。`Demo Pairs` 才顯示 256。
6. 季度比較依 `source` 和 `method` 分別篩選，避免把模擬人工與模擬 AI 的差值平均。
7. 碳存量卡僅在選定單個掃描時顯示；不加總 16 季存量。
8. 真實資料版另開 `outputs/powerbi-observed/Arbor3D.pbip`：16 觀測、0 有效配對、16 待複核、0 跨期。
9. Desktop 刷新後另存專案；若有 M/DAX 或視覺錯誤，保留完整訊息修正後再標記驗收通過。

格式依据：[Microsoft PBIP](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview)、
[PBIR 報表](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report)、
[semantic model](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset)。

選用格式驗證（僅第一次需要下載 Microsoft 官方 schema，沒有 Power BI 雲端呼叫）：

```powershell
python -m pip install -r powerbi/requirements-validation.txt
python -m powerbi.validate_project outputs/powerbi-simulated --download-schemas
python -m powerbi.validate_project outputs/powerbi-observed
```

## 測試及 App 預覽

```powershell
$env:ARBOR_PYTHON = (Get-Command python).Source
python -m unittest discover -s analytics/tests -v
npm test --prefix app
npm run lint --prefix app
npm run build --prefix app
npm run dev --prefix app -- --host 127.0.0.1 --port 5174
```

自訂 Python 可用 `ARBOR_PYTHON` 指向絕對路徑。原 App 示範登入／掃描流程保持不變；
本次季度資料在 Analytics／Power BI 展示，**尚未接到 App 原有模擬月曲線**，不把季度合成掃描偽裝成實際上傳。

## 合成展示影像

由逢甲實圖與既有 4 組合成圖衍生 **12 組 × 3 類**（mask／橫切面／點雲預覽），全部打上 `DEMO / SIMULATED` 浮水印。

```powershell
python scripts/expand_synthetic_media.py --count 12
npm run simulate:media --prefix app
# 或一次：
npm run simulate:media:expand --prefix app
```

- 人工 DBH 和第二期真實掃描仍未取得；模擬資料不補足真實精度或生長證據。
- Power BI Desktop 的 DAX、刷新及畫面驗收仍待執行；未產生已驗收 PBIX。可用 `scripts/windows/rebuild-microsoft-outputs.ps1` 先產生 PBIP。
- Fabric／Data Agent／Foundry 維持本機樣板與費用鎖，沒有部署、容量試用或付款。
- **Cloud DBH**：`cloud_dbh/` + `infra/azure/dbh-compute.bicep` 已就緒；本機 HTTP `/health` 與 prepare-only job 已在 Windows 煙測通過。完整 GPU 映像與 Azure 部署需 ACR、`az login`（安裝 Azure CLI 需系統管理員）與配額。見 [CLOUD_DBH.md](CLOUD_DBH.md)。
- Docker 若未安裝，可先本機 `uvicorn cloud_dbh.app:app`；GPU 管線仍需本機原始資料與 `requirements.txt` 依賴。
