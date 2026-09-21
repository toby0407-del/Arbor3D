# Arbor3D Microsoft AI/Data 競賽強化版

本版本在既有 YOLO → DBH → 3DGS → App 之後加入離線分析層，不修改核心量測演算法。
所有指令預設只讀寫本機。沒有建立雲端資源、開啟試用、升級訂閱或呼叫付費模型。

**Windows 接續更新：** 既有功能分支已合併 main；新增四年季度模擬及五頁 PBIP/PBIR 產生器，詳見 [Windows 指南](WINDOWS.md)。
分析契約 1.1 為所有表新增 `dataset_kind`，真實和合成資料必須分開輸出。App 輸入 bundle 仍維持 1.0。
以下原先 Mac 上的驗證限制屬歷史紀錄，最新執行結果以 [驗證紀錄](VALIDATION.md) 的 Windows 章節為準。

## 已有資料與限制

檢查基準：Git `d398b69`。正式示範資料在 `app/src/data/inventories/20260818092855.json`，16 棵樹，掃描日期 2026-08-18。
現有資料無人工 DBH，且 16 筆 `dbh_is_strict_breast_height=false`。
因此有效配對數 0、MAE/RMSE/Bias/MAPE 為 null，16 筆待複核；不可將空值解讀為零誤差。
示範資料只有一期，也沒有已確認固定樹號，跨期表保持空白。測試中的合成資料只驗證程式，不當作競賽實測成果。

## 一次完成本機資料輸出

需要 Python 3.9+、Node 22.12+（原 App 使用 Vite 8）。從 repo 根目錄執行：

```sh
npm ci --prefix app
python3 -m analytics --report app/src/data/inventories/20260818092855.json --site-id fengchia --out outputs/competition
node app/scripts/export-analytics-excel.mjs outputs/competition/analytics.json outputs/competition/analytics.xlsx
```

輸出同一份 canonical snapshot 的 `analytics.json`、6 張 UTF-8 BOM CSV、`analytics.xlsx` 和雜湊 manifest。
Excel 是可篩選、凍結標題的數值快照，並非編輯後自動回寫 App 的資料庫；變更資料後需重跑分析與匯出。
空表保留 CSV 欄名；Excel 顯示「無可用資料」。數值缺測保留 null/空白，不補 0。
CSV 防公式注入會在危險字串前加單引號；JSON 保留原始字串，Excel 使用文字儲存。一般 Tree_ID 不受影響。

## App 人工複核 → 分析

1. 啟動 `npm run dev --prefix app`，開啟掃描樹木詳情。
2. 輸入人工胸徑／樹高、日期，確認實際量測位置是標準 1.3 m 後才勾選確認。
3. 按「匯出分析資料」，下載含原報告和人工資料的 JSON。
4. 執行：

```sh
python3 -m analytics --bundle /absolute/path/20260818092855-analytics-input.json --site-id fengchia --out outputs/field-review
node app/scripts/export-analytics-excel.mjs outputs/field-review/analytics.json outputs/field-review/analytics.xlsx
```

人工資料仍存於該瀏覽器 localStorage；下載 JSON 才會交給分析程式。新增的標準高度確認預設 false，舊人工紀錄不自動視為已確認。
日期為必要欄位。原有「匯出 CSV」保留，增加來源欄位；Microsoft 匯入使用新分析輸出。
單次掃描的生長曲線現在標示人工、AI 或推估；所有非基準月份均為模擬，不再因接近掃描日期而被視為實測。
盤點視窗不再於路徑圖下方逐棵展開待複核清單；請使用樹表上方的「待確認」、「需複核」或「待複核」篩選查看相同資料，個別樹木詳情仍會顯示複核原因。

## 資料契約與誤差定義

機器可讀契約：`analytics/schema.json`；明確資料型別：`fabric/table-schema.json`。

| 資料表 | 粒度／主鍵 | 用途 |
|---|---|---|
| DimTree | site + confirmed persistent ID，或 site + scan + local ID | 固定樹號及 identity_status |
| DimScan | site + scan | 日期、原始檔、SHA-256 |
| FactObservation | site + scan + local Tree_ID | AI、人工、可比性與誤差 |
| FactEstimate | 一筆 observation | 樹高／碳量推估、輸入來源、公式版本 |
| FactGrowth | 固定樹號 + source + method + 相鄰日期 | 真正觀測的跨期差值 |
| Summary | all 與各 scan | 離線統計；Power BI 以 DAX 重新計算，避免平均的平均 |

`auto_source=ai`、`manual_source=measured`、公式結果 `source=estimated`、缺值 `missing`。
預設有效配對：同場址／掃描樹號、兩側均標準高度、正數胸徑、同一天。必要時可明確指定 `--max-pair-days N`，此選擇寫入 manifest。
Error=AI−人工；MAE=mean(|Error|)；RMSE=sqrt(mean(Error²))；Bias=mean(Error)；MAPE=mean(|Error|/人工×100)。
非標準高度不列入精度 KPI，原始兩側數字仍保留。待複核與有效配對是不同概念；可在 Power BI 按方法、信心、複核原因分組檢查。
重複 scan、重複樹號、孤立人工資料、非有限／非正量測、未確認的映射都會拒絕，避免靜默覆蓋。

## 多期資料與固定 Tree ID

複製 `analytics/examples/manual.csv`、`analytics/examples/identities.csv` 的空表填寫。
一筆映射需 `site_id,scan_id,local_tree_id,persistent_tree_id,confirmed=true`。同次掃描不可有兩個 local ID 對到同棵樹。

```sh
python3 -m analytics --report first.json --report second.json --site-id fengchia --manual manual.csv --identities identities.csv --out outputs/multi-period
```

不要直接把每次掃描的 Tree_001 當成同棵樹。只有人工確認的映射可跨期比較，未確認時保留各期觀測但不產生增長。
AI 依方法分組、人工獨立分組；只比較標準高度，同組同日重複資料拒絕。年化增量=差值/實際天數×365.25，不代表已建立生物生長模型。
負增量會標記，必須人工檢查方法、對應樹號、量測條件。現階段不自動 GPS 配對，避免掃描座標差異造成誤認。

## 碳量來源

沿用 `app/src/lib/carbon.ts` 的盤點公式；支援人工輸入係數，未填預設 0.0159。
人工 DBH 優先，再採 AI DBH；人工樹高優先，再採報告樹高，最後才由 DBH 估高，各來源分開記錄。
D=(π×DBH_cm/100)²×Height_m×係數，CO₂ 當量=D×3.667。公式適用性、係數及單位需專業驗證。
不把此估算宣称为認證碳權、年度吸收量或已驗證減碳。跨掃描的碳存量不能直接相加。

## Power BI 本機模型（草稿；已有專案產生器）

`powerbi/model.bim` 是 Tabular 模型草稿；`queries.pq`、`measures.dax` 供 Desktop 手動建立；`dashboard.md` 是頁面設計。
前次 Mac 環境未執行 Desktop 引擎驗證。本次 Windows 接續已可用 `python -m powerbi.build_project` 產生 PBIP/PBIR 專案；目前仍未偵測到 Desktop，不能宣稱 DAX 引擎或版面驗收成功。

在 Windows Power BI Desktop：
1. 新建空白報表，Power Query 建立文字參數 AnalyticsFolder，填 analytics 輸出絕對路徑。
2. 在 `queries.pq` 每段 `// Query: Name` 建立一個對應名稱的空白查詢，貼上其 let/in 內容。
3. 建立 `DimTree[tree_key]`、`DimScan[scan_key]` 到 Observation/Estimate 的單向 1:* 關係。Growth 連 tree_key 與 to_scan_key；不建立 from_scan 的作用中關係以免日期歧義。
4. 依 `measures.dax` 逐個新增 measure。不要直接把 Summary 當 DAX 分子或平均它的 MAE。
5. 依 dashboard 文件製作頁面，確認 16 筆觀測／0 配對／空白 MAE／16 待複核，再儲存 PBIP 或 PBIX。

也可用已安裝的 Tabular Editor 匯入 model.bim；它不是可雙擊的 PBIX。未建立或宣稱完成已驗證的 PBIX 報表。
資料目前只在本機。若未來發佈，需先在 semantic model 設場址權限與 RLS，並實際測試角色；Agent 提示詞不是安全邊界。

## Fabric / OneLake 與 Data Agent

部署步驟见 `fabric/README.md`。目前僅提供可匯入資料、明確型別的 Spark 程式、Data Agent 設定草稿與問題清單。
不要在本任務啟動容量、試用或新付費資源。沒有已授權且費用可接受的環境，停在本機交付。

## Foundry 與 RAG

```sh
python3 -m agents.rag 'DBH 誤差分析需要哪些資料？'
python3 -m agents.foundry '可以把估算碳量當碳權嗎？'
```

第一個是免費本機關鍵字檢索／文件摘錄，附檔名、行號和文件指紋；不是生成式模型。把審核過的 Markdown 放入 `agents/knowledge/` 即可索引。
第二個只產生 Foundry 設定預覽與檢索片段，不需要 Azure SDK、登入或網路。無證據時回覆不足。
Foundry 後續部署樣板與成本鎖見 `agents/README.md`。本機 RAG、分析與 App 不依賴任何雲端帳號。

## 驗證

```sh
python3 -m unittest discover -s analytics/tests -v
npm test --prefix app
npm run lint --prefix app
npm run build --prefix app
python3 -m compileall -q analytics agents powerbi fabric
```

核心 GPU 推論需要原始點雲、GPU 及模型環境，這次未重新訓練或跑完整 YOLO/3DGS；核心檔案保持原樣。
雲端、DAX 執行引擎及容器部署驗證不包含在本機測試通過範圍。
