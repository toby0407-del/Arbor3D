> 歷史紀錄：比賽導覽現已移除，最新狀態見 ../microsoft/LIVE_CONNECTIONS.md。

# 本機驗收紀錄

日期：2026-10-27。環境：Windows、Node 24.18、Python 3.11、Open3D 0.19。分支：`competition-quality-workflow`。

已通過：

- App 39 項測試、Lint、TypeScript／Vite 正式建置及伺服器編譯。
- Python `tests/` 12 項、`analytics/tests/` 26 項、Cloud DBH 狀態 1 項，共 39 項。
- `npm run demo:check`：16 棵原始觀測雜湊、媒體、18 個模擬場景、五張概念圖、本機知識庫與建置輸出。
- `npm audit`：本次鎖檔 0 個已知弱點；不是永久安全保證。
- 合成圓截面的實際估測 → 品質判斷 → JSON → 盤點報告：沒有校準模型時，候選保留、正式 DBH 為 null。此檢查是幾何整合測試，不是真實掃描精度結果。
- 瀏覽器：展示登入、五步驟導覽、觀測資料直接開啟、季度模擬直接開啟、900 點 PLY、候選安全防呆／排序／保存／移除、本機證據助理與 1,000 題知識檢索。
- 最終導覽預載成功 84 項圖檔／模型資產。已修正模擬場景共用路徑的誤拒絕；缺圖檢查不會把共用影像誤報為網路問題。
- 直接呼叫本機狀態 API：`activeMode=local`、`billableAllowed=false`，概念圖片 HTTP 200。

原始 16 棵資料與模擬盤點 JSON 沒有修改。測試用補掃候選已移除，沒有往觀測資料填入假人工胸徑。

已新增 Windows／Ubuntu CI 驗證流程，但尚未推送，因此沒有把本機成功說成遠端 CI 已成功。完整新掃描、實際斷外網彩排、外部登入與雲端服務驗收仍按展示手冊處理。

畫面：`demo-tour.png`、`demo-quality.png`、`demo-3d.png`。品質頁顯示的是歷史觀測的資料不足狀態；3D 畫面為明確標記的模擬情境。
