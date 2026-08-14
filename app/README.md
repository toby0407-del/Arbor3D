# Arbor3D App（前端）

這個資料夾是**網頁／App 專用區**。量測 Python 在上一層，請不要把前端檔案散到倉庫根目錄。

## 開始做畫面

在這個 `app/` 資料夾裡建立專案，例如：

```bash
cd app
npm create vite@latest . -- --template react
```

或 Flutter、Next.js 都可以，重點是專案根目錄就是這裡。`node_modules`、`dist`、`build` 已在倉庫 `.gitignore`。

開發時先讀 [`example-data/park_inventory_report.sample.json`](example-data/park_inventory_report.sample.json)，欄位會跟之後真實的 `inventory_out/park_inventory_report.json` 相同。

## 建議畫面

1. **公園總覽：** 掃描編號、樹的數量、俯視圖、樹卡片（樹號、胸徑、狀態燈）
2. **單棵樹詳情：** 胸徑、量測方法、照片、YOLO 遮罩、胸高剖面、相對座標
3. **3D 檢視：** SuperSplat／3DGS（可後做）
4. **警示：** `wide_caliper`、非 1.3 m 胸高 → 待複核；預留現場量測欄
5. **先留位置：** GPS 地圖、多趟掃描切換、匯出 CSV

狀態可依 `DBH_note`：含 `wide_caliper` 為紅燈，僅 `not_1.3m` 為黃燈，`ok` 為綠燈。
