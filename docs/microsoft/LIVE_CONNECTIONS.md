# Microsoft 實際連線與待辦

2026-10-28：Power BI 改採 Desktop 本機流程，已實際在未登入狀態刷新及執行 DAX，核對後更新 App 的當期分析快照；線上服務仍未啟用。詳見 [操作流程](POWERBI_LOCAL.md)。下方學校授權紀錄仍適用於線上報表，不能解讀為本機 Desktop 無法使用。

最新：Azure 既有 F1 已實際完成真實截面計算，本機 App 已接上混合運算。未新增付費資源；大型點雲與 YOLO 仍在本機，雲端只做截面幾何及品質，詳見 [混合運算紀錄](CLOUD_DBH.md)。前端修改尚未推送或部署，DBH API 本次已部署。


更新：2026-10-27（台灣時間）。範圍為本機 Arbor3D，尚未部署這批修改至 Azure 網站。

## 已驗證

1. Foundry Local 官方 Windows SDK 1.2.4，以 WebGPU 載入 Phi-4-mini-instruct-generic-gpu:5。模型原生探測回覆 Arbor3D connected。
2. App 使用原有掃描 20260818092855 的 16 棵資料送入模型，回覆 provider=phi4，約 3.5 秒。模型正確指出資料尚不能宣稱胸徑精度已驗證。這是服務功能測試，不是模型正確率或林業量測精度驗證。
3. Cosmos DB 使用既有 Arbor3D / FieldMeasures 容器、scanId 分割鍵、Azure CLI 使用者身分，沒有金鑰。獨立 connection-verification 文件寫入、點讀回比對、刪除均成功；未寫入虛構樹木人工真值。
4. 正式 Node 伺服器會讀取 app/.env.local，並能載入 agents/knowledge。未開啟付費雲端模型備援。本機模式若要求 Microsoft 模型而服務無法回覆，會顯示錯誤，不把規則回答標為 Phi-4。

本機驗證 JSON 位於 .runtime/microsoft-verification.json（忽略追蹤）。狀態面板的連通檢查只讀取模型清單與 Cosmos 容器；不在每次開面板時寫測試資料。推論驗證時間以本次伺服器實際取得的回答為準，重啟後重新累計。

## 操作

1. 雙擊根目錄「啟動Microsoft模型.cmd」，首次啟動可能下載模型。此機器已完成安裝及下載；腳本使用使用者目錄下的獨立 Python 環境。
2. 雙擊「啟動Arbor3D.cmd」，開啟 http://127.0.0.1:5324/。不再有比賽導覽，直接選擇地點與路線操作。
3. 登入後可按「服務連線」。進入盤點後開啟 AI 助理提問，確認回答來源為 Microsoft Phi-4。
4. 關閉兩個啟動終端可停止 App 與模型。重開機後需再次啟動。Azure CLI 登入過期時，重新在本機執行 az login；不將認證內容放進前端或 Git。

重建：在 app 執行 npm ci、npm run build。模型 SDK 的重現安裝：以 Python 3.11 建立獨立 venv，再安裝 foundry-local-sdk-winml==1.2.4；不要在同一環境混裝非 WinML 套件。執行 scripts/run_foundry_local.py，依實際模型 ID 設定 FOUNDRY_LOCAL_MODEL。

## 暫緩：Power BI 校方授權

**使用者於 2026-10-27 指示先記錄並跳過，之後自行聯絡學校。**

觀察到：登入學校帳號後，Microsoft 註冊頁顯示「您的 IT 部門已經關閉 Microsoft Fabric free 的註冊功能」。這不是由 App 修正密碼或反覆登入能解決的錯誤。

向校方申請：請檢查此學生帳號的 Power BI/Fabric 服務是否啟用，並指派 Fabric（免費版）或符合需求的 Power BI 授權；若允許學生自行申請，也請確認學校的自助註冊政策。線上分享或嵌入的授權需求，須依最後展示方式再確認。

官方說明：https://learn.microsoft.com/en-us/power-bi/fundamentals/service-self-service-sign-up-help

解鎖後：登入 Power BI → 確認可用工作區與授權 → 匯入既有真實觀測分析資料 → 建立及驗證報表 → 將核對過的報表網址填入 POWERBI_REPORT_URL。現在未設定網址，不能宣稱線上報表已可用。既有 PBIP/CSV 是可編輯資料包，並不等於線上服務已完成。

## 待管理員：Microsoft Entra ID

Azure CLI 建立 Arbor3D 應用程式時回傳 Insufficient privileges。尚無可用 Client ID／授權 scope，不能用別的 Microsoft 應用程式 ID 代替。請管理員提供核准的單頁應用程式與 API 公開識別、回呼網址、scope 和角色設定後，再完成真實登入驗收。

## 研究資料限制

原有 16 棵掃描、模擬公園及跨期示意資料仍保留來源區分。未新增真實人工胸徑、第二期掃描或校準成功機率。Copilot Studio 尚無發布代理及 Token Endpoint；實際模型是 Phi-4，不宣稱為已發布的 Copilot Studio 代理。


## 本次同步強化與驗證

- 手測改用 PATCH，只傳送使用者修改的單木欄位；Cosmos 更新使用 ETag，遇到其他使用者同時修改會讀取最新版本再合併重試。若兩人改同一欄位，最後成功寫入者為準，不宣稱具備人工衝突裁決。
- 瀏覽器保留待同步修改，讀取雲端時不會蓋掉剛輸入的欄位。失敗會顯示「尚未同步」並提供重試；登入失效會提示重新登入。未編輯時只讀取，不把舊瀏覽器快取整批上傳。
- 舊版 PUT 全批次 API 保留相容用途，新的 App 一律使用 PATCH。勿將舊版客戶端的整批覆寫行為誤認成欄位合併。
- App 顯示資料庫來源與實際同步狀態；AI 狀態分開標示設定、服務連通及本次伺服器已實際取得的模型回覆。
- 桌面窄視窗不再被橫向提示阻擋；手機和平板仍保留觸控橫向使用提示。
- `app/scripts/verify-cosmos-sync.ts` 在唯一 connection-verification 分割區執行實際並行 PATCH、讀回、未登入拒絕及非法欄位拒絕，最後只刪除本次產生的測試文件。已執行成功，未更動觀測樹木紀錄。
- 本機驗證：App 47 項測試、Lint、正式建置通過；Python 39 項通過。Phi-4 經 App API 實際回答，Cosmos 容器實際連通，並已從瀏覽器驗證「手測庫：Cosmos DB／已同步」。
- 截圖證據位於忽略追蹤的 `.runtime/services-connected.png`、`.runtime/field-measures-synced.png`、`.runtime/phi4-live-answer.png`。

這批修改仍留在本機，尚未推送 GitHub 或部署 Azure。Power BI 及 Entra 的外部權限待辦維持原狀。
