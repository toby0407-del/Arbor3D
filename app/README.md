# 前端（app/）

環保局樹木盤點**展示／複核介面**。量測 Python 在上一層（倉庫根目錄），前端**只改這個資料夾**。

獨立倉庫鏡像：https://github.com/toby0407-del/arbor3d-interface  
（本資料夾與該倉庫同步；優先以本倉庫 `app/` 為準。）

---

## 啟動

```bash
cd app
npm install
npm run dev
```

瀏覽器開 Vite 印出的位址（預設 http://127.0.0.1:5173/；埠被占用時可 `npx vite --port 5300 --host 0.0.0.0 --strictPort`）。  
示範帳號見下方；登入後搜尋「逢甲」→ 點 8/18 路徑即可驗證。

| 指令 | 說明 |
|------|------|
| `npm run dev` | Vite 開發伺服器 |
| `npm run build` | TypeScript 檢查 + 打包 |
| `npm run lint` | oxlint |
| `npm run preview` | 預覽 build |
| `npm run postprocess` | 呼叫上層 Arbor3D 管線（可選） |

---

## 目前已完成（2026-09-01）

1. 示範帳號登入（工作編號＋密碼／示範登入）
2. 全台公園／學校地圖選點（OSM 目錄＋國土測繪底圖）
3. GPS 定位、路徑錄製（≤ 10 m 起測）、GPX 下載
4. 盤點視窗：樹表（最後一欄健康度）、燈號篩選、Segmentation、橫切面、點雲側視、3D
5. 匯入三格：去噪 PLY、高斯濺射 PLY、原始照片資料夾
6. 現場手測（localStorage，不覆蓋演算法 DBH）＋ CSV 匯出
7. **碳匯工作表**（欄位依公式排序）
8. **時序成長**：前期盤點 → 本期盤點 → 成長趨勢；左側 Warning 清單，健康度圖示（非整列紅底）

```
D  = A² × B × C
CO₂ = D × 3.667
```

| 順序 | 標籤 | 說明 |
|------|------|------|
| 1 | 高度 1.3 m 處圓周 ( A ) | π × 胸徑(m) |
| 2 | 樹高 ( B ) | 手測或粗估 |
| 3 | 係數 ( C ) | 表定 0.0159／闊葉／針葉／自訂 |
| 4 | 樹含碳量 ( D ) | 自動計算 |
| 5 | 吸收 CO₂ 當量 ( CO₂ ) | `D × 3.667`（ton） |

量測分頁已移除「胸高窗口 0.9–1.7 m」列。

詳細接新掃描步驟見 [NEXT_STEPS.md](./NEXT_STEPS.md)。

---

## 示範帳號

| 工作編號 | 姓名 | 角色 | 密碼 |
|---------|------|------|------|
| E-1027 | 林志偉 | 現場調查員 | arbor1027 |
| E-2041 | 陳雅婷 | 複核人員 | arbor2041 |
| E-3308 | 黃建宏 | 承辦人 | arbor3308 |

---

## 已接實測掃描

| 項目 | 內容 |
|------|------|
| 地點 | 逢甲大學 · 學思樓／7-11 南側走廊 |
| 路徑 | 校園掃描路徑（8/18 · 7-11） |
| scan_id | `20260818092855` |
| JSON | `src/data/inventories/20260818092855.json` |
| 媒體 | `public/scans/20260818092855/` |
| 棵數 | 16 |

舊示範 JSON 仍可參考：[`example-data/park_inventory_report.sample.json`](example-data/park_inventory_report.sample.json)。

---

## 技術棧

React 19 + TypeScript + Vite 8 + Leaflet + Three.js  
燈號／碳匯／時序成長／CSV：`src/lib/status.ts`、`carbon.ts`、`growth.ts`、`csv.ts`  
量測管線對接：`server/importApiPlugin.ts` + `scripts/run-postprocess.mjs`（可設 `ARBOR3D_ROOT` 指向上層本倉庫）
