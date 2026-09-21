# 本機驗證紀錄

日期：2026-09-21。基準版本：d398b69；工作分支：feat/microsoft-ai-data。

- Python unittest：18 項通過（精度算式、缺值、非法數值、日期／高度排除、固定身份、負增量、方法隔離、重複／孤立紀錄、CSV 注入防護、CLI bundle、OneLake 雜湊、離線 Agent 與雲端鎖）。
- App / Excel Node 測試：7 項通過（AI／人工／推估標示、鄰近月份不當實測、匯出缺值、複核燈號、Excel 逐格與類型一致性）。
- `npm run build --prefix app`：通過。仍有既有大型 bundle 提示（約 2.83 MB 未壓縮）。
- `npm run lint --prefix app`：exit 0；既有 SitePickerPage.tsx useEffect/discardDraft 依賴警告仍存在，未改動該頁。
- `npm audit --prefix app --audit-level=moderate`：0 vulnerabilities。ExcelJS 的 UUID 間接依賴以 override 更新為修補版本，Excel 讀寫測試通過。
- Python compileall、git diff --check：通過。
- JSON Schema Draft 2020-12：示範 analytics.json 通過；Power BI 模型欄位／關係端點檢查通過。
- Excel：獨立 openpyxl 只讀核對全部資料儲存格與 canonical JSON 一致；scan_id 保留文字。以工作表渲染查看 7 張表並修正欄寬、換行、係數精度；渲染器對長數字字串可能顯示科學記號，但 XLSX 實際型別與完整值已核對。
- App 瀏覽器：示範登入 → 逢甲大學 → 既有掃描正常；分析匯出入口、日期欄與預設未勾選標準高度確認欄可見。修正後為 8 待確認 + 8 需複核，待複核合計 16。
- 既有示範資料實際輸出：16 observations、0 valid pairs、MAE/RMSE/Bias/MAPE=null、0 growth rows，沒有填造人工測量。
- 本機 RAG、Foundry dry-run、Fabric dry-run、含 10 個檔案的 OneLake 匯入 ZIP 已生成，沒有雲端呼叫或上傳。

## 未執行的環境驗證

- 沒有 Windows Power BI Desktop，因此 model.bim、Power Query 和 DAX 是本機模型草稿，未驗證 DAX 引擎或製作 PBIX。
- 沒有開通 Fabric／Foundry／付費容量，也沒有 cloud integration test、容器 build 或部署。
- 核心 YOLO、DBH、3DGS 檔案不變；未重新執行需要 GPU／原始點雲的完整重建管線。

以上限制已在操作指南中明列；本機測試通過不能等同雲端部署成功。
