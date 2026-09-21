# Fabric / OneLake 部署樣板（本機交付）

建議資料夾：

- `Files/arbor3d/bronze/<site>/<scan>/inventory.json`：原始掃描報告與人工紀錄，不覆寫。
- `Files/arbor3d/silver/<batch>/analytics.json`：驗證、來源區分後的 canonical snapshot。
- `Files/arbor3d/gold/<batch>/*.csv`：全部分析表與 manifest、table-schema.json。
- `Tables/arbor_DimTree`、`arbor_DimScan`、`arbor_FactObservation`、`arbor_FactEstimate`、`arbor_FactGrowth`：Delta 表。

`python3 fabric/load_tables.py` 只輸出預覽，不連線。

未來若使用者另行授權雲端費用，且已有可用 workspace/capacity/lakehouse：
1. 選擇專用開發 Lakehouse，手動上傳完整 snapshot；batch 可用 manifest 雜湊命名。
2. 在連接該 Lakehouse 的 Spark notebook 貼上 `load_tables.py` 定義，讀取上傳的 table-schema.json。
3. 手動呼叫 `load(spark, 'Files/arbor3d/gold/<batch>', schema, authorized=True)`。
4. 此程式只覆寫 `arbor_*` 專用表；每個 batch 應含所有要分析的歷史報告。重跑同一批不增加重複資料。
5. 多表写入不是原子交易；只有全部表完成後才刷新 semantic model。發生中斷則用同一完整 batch 重跑；保留前一批以回復。
6. 建立 semantic model，使用 powerbi/model.bim 對應關係和 measures；實際 Delta 表有 arbor_ 前綴，在模型中重命名為對應名稱。
7. 檢查型別、主鍵、筆數、missing/paired 數、時間與 site 過濾，再設權限。

Data Agent：
- `data-agent.json` 是專案設定樣板，不是官方可直接 POST 的 API payload。
- 把已驗證 semantic model 加為資料來源；在模型 Prep for AI 設定 AI schema、說明與 verified answers，保留措施依賴欄位。
- Power BI semantic model 來源不支援 Data Agent example query pairs；`evaluation-questions.json` 用於人工驗收，不宣稱能直接匯入。
- 如改用 Lakehouse SQL 來源，可提供 SQL 問答例子；本版本以 semantic model 為主。
- 對問題清單逐題記錄實際回答與 DAX，檢查是否使用正確配對與來源。權限由資料來源／模型執行，提示詞不能替代 RLS。

官方依據（查核 2026-09-21）：
- [CSV/Parquet 載入 Delta 與型別控制](https://learn.microsoft.com/en-us/fabric/data-engineering/load-to-tables)
- [Notebook 載入 Lakehouse](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-notebook-load-data)
- [建立 Data Agent](https://learn.microsoft.com/en-us/fabric/data-science/how-to-create-data-agent)
- [Semantic model 與 Prep for AI](https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices)
- [範例查詢支援範圍](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-example-queries)

本次沒有建立或啟用任何上述服務，不能將樣板稱為已上線整合。

## 本機資料包

```sh
python3 fabric/package_snapshot.py --input outputs/competition --output outputs/competition/onelake-import.zip
```

產生完整 bronze/silver/gold ZIP；上傳前需解壓縮，ZIP 本身不是 Delta table。
程式檢查 CSV 和原始報告的雜湊，拒絕混用已變更檔案。bronze 資料夾使用場址／掃描 ID 的 SHA-256 前 16 碼，原 ID 保留於 DimScan。
