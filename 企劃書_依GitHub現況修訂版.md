# 編號：

中文專題名稱：Arbor3D 數位孿生之樹木三維空間解析與碳匯評估系統  
英文專題名稱：Arbor3D: A Digital Twin-Based System for Three-Dimensional Spatial Analysis of Trees and Carbon Sequestration Assessment

## 一、前言

合作單位：＿＿＿＿＿＿＿＿  
聯絡人：＿＿＿＿＿＿＿＿  
電話號碼：＿＿＿＿＿＿＿＿

本專題以臺中市公園、校園與都市綠地之樹木盤點及後續管理需求為應用情境，開發「Arbor3D 數位孿生之樹木三維空間解析與碳匯評估系統」。聯合國環境規劃署發布之《Emissions Gap Report 2025》指出，2024 年全球溫室氣體排放量達 57.7 GtCO₂e，較前一年增加 2.3%[1]。在淨零轉型與都市韌性議題下，管理單位不只需要知道區域內有多少樹，更需要持續掌握每棵樹的位置、胸徑、樹高、三維形態、量測可信度、跨期變化及碳量估算依據。

傳統樹木調查多仰賴人員逐棵量測胸徑、記錄位置、拍照及整理試算表，耗費人力，且照片、地圖、量測值及歷次紀錄容易分散於不同檔案，造成後續查驗與跨期追蹤困難。近年 LiDAR、三維點雲與深度學習已逐漸應用於森林及單木解析。相關研究顯示，高密度 LiDAR 與三維深度學習可支援個體樹分割及結構參數取得[2]；SegmentAnyTree 探討跨感測器與跨平台的樹木分割能力[3]；ForestFormer3D 則進一步整合語意分割與個體樹分割，以提升不同森林環境及感測資料下的泛化能力[4]。

然而，都市公園與校園環境仍會遇到樹幹遮擋、單側掃描、點雲缺口、鄰樹或設施干擾、量測高度不一致及跨期樹號無法對應等問題。若只輸出單次胸徑結果，仍不足以支援長期管理；系統還必須保留資料來源、量測日期、演算法方法、人工複核與固定樹號，才能建立可查驗的 Digital Representation。

Arbor3D 因此整合 JMK6／RayStudio 掃描流程、去噪點雲、自訓 YOLO 樹幹分割、胸高截面幾何量測、3D Gaussian Splatting／PLY、GIS 地圖、Microsoft Azure、Azure Cosmos DB、Microsoft Foundry Phi-4、1,000 題 RAG 知識庫及 Power BI 分析層。系統將「實體掃描（Physical）」、「可量測的數位資料（Digital）」與「AI 分析及跨期判定（AI）」串成同一流程，目標不是只完成一次量測，而是讓每棵樹形成可持續更新、可複核及可分析的數位表徵。

圖 1、人工逐棵量測胸徑  
圖 2、JMK6／RayStudio 現場掃描與資料取得

## 二、創意描述

### （一）Physical → Digital → AI 整體架構

Arbor3D 將系統分為三層。Physical 層由人員完成現場掃描、照片、校正資料、去噪點雲與完整三維場景；Digital 層將原始素材轉為單木 ID、樹幹遮罩、胸高橫切面、DBH、單木點雲、三維模型及可追溯 JSON／CSV；AI 層則負責樹幹分割、量測可信度判斷、異常篩選、RAG 問答及跨期分析。三層最後匯入同一個 Web App 與 Power BI 分析模型。

目前 GitHub `main` 分支已連接 GitHub Actions 與 Azure App Service。每次推送會自動安裝套件、執行測試及 production build，全部通過後才更新公開網站，避免失敗版本覆蓋線上系統。

圖 3、Arbor3D Physical → Digital → AI 系統流程

### （二）掃描資料與自動盤點流程

現場素材包含照片、`calib.json`、`cameras.json`、去噪 PLY 及完整 3D Gaussian Splatting 場景。正式管線會先檢查檔案命名、格式與完整性，再進行照片定位、樹木分群、單木編號、最佳視角選擇、YOLO 樹幹分割、胸徑計算、單木三維模型切分及報告產生。

目前介面已接入逢甲大學 2026 年 8 月 18 日一期掃描，共 16 棵樹；影像、胸高橫切面與點雲側視均可由盤點視窗查看。由於該期資料沒有現場 GPS，樹點位置以相對 XYZ 沿參考路徑呈現，不宣稱為精密測量座標。

為驗證大量資料載入、跨期圖表及 Power BI 資料模型，系統另建立臺中 18 個公園／綠地展示場景，共 295 棵樹及 4,720 筆季度資料。這些資料在程式中以 `dataset_kind=simulated` 與 `sim*` 掃描 ID 隔離，僅用於系統展示與分析流程驗證，不取代第二期真實掃描、人工胸徑或現場 GPX。

圖 4、去噪點雲  
圖 5、3D Gaussian Splatting／單木 PLY 顯示

### （三）DBH 雙軌量測與可信度判斷

Arbor3D 的 DBH 量測使用去噪點雲，不以視覺效果較佳但邊界較模糊的高斯球直接量測。流程先利用相機姿態把三維點投影至 YOLO 樹幹遮罩，再以 Z-Buffer 移除同一視線後方的背景點；接著以 RANSAC 尋找地面並扶正樹幹，擷取離地 1.2–1.4 公尺範圍的胸高點雲。若該高度資料不足，系統會標記 `not_1.3m`，不得直接納入正式精度 KPI。

胸高截面採「圓擬合＋虛擬卡尺」雙軌機制。只有當截面弧度涵蓋至少 120°，且貼合圓周的點至少達 50% 時才採用圓擬合；若單側掃描造成弧度不足，則改以相機視線垂直方向的可見寬度作為虛擬卡尺。若出現資料缺口、無法量測或卡尺結果偏寬等情況，系統分別以 `gap`、`no_measurement`、`wide_caliper` 標記，並在 App 中列為待複核。此機制不把低品質量測硬轉成單一數值，而是保留演算法判斷與人工查驗入口。

圖 6、胸高橫切面與圓擬合  
圖 7、虛擬卡尺及待複核標記

### （四）三維視覺化與 Digital Representation

系統以唯一單次樹號串聯影像、遮罩、胸高橫切面、DBH、信心度、點雲與三維模型，並預留 `persistent_tree_id` 作為跨期固定樹號。TUM2TWIN 顯示，多模態資料可用於建立大尺度都市數位孿生與多種下游任務[6]。Arbor3D 將此概念縮小到單株樹木管理，使每棵樹不只是地圖上的點，而是一組可重新計算、可比對與可查驗的 Digital Representation。

App 使用 Three.js 顯示單木點雲，支援直立校正與旋轉檢視；3D Gaussian Splatting 則用於場景與視覺呈現。量測線與展示線分開，避免以視覺模型取代幾何量測證據。

### （五）跨期成長與異常篩選

相關研究顯示，多期 TLS 可捕捉樹木徑向生長變化[7]。Arbor3D 已建立跨期資料結構、固定樹號欄位、季度趨勢圖、負增量標記與 Power BI `FactGrowth` 模型。當同一棵樹具有至少兩期、日期完整且量測方法可比較的真實資料時，系統可計算 DBH 差值、年化增量及異常下降。

目前真實資料只有一期，尚未取得第二期同路徑掃描與人工確認的固定樹號，因此現階段不能宣稱已完成真實生長監測。展示用季度資料可呈現正常、緩慢、停滯與負增量待複核等情境，但不會混入正式精度或真實成長 KPI。

圖 8、跨期 DBH 成長趨勢  
圖 9、異常樹木與人工複核提示

### （六）Phi-4 雲端 AI 與 1,000 題 RAG

本系統選用 Microsoft `Phi-4-mini-instruct` 作為 Arbor3D 領域助理的開放模型。該模型為 3.8B 參數、支援中文及 128K context 的小型語言模型[8]，相較 14B 模型較適合成本受限的展示情境。系統已建立 20 類、共 1,000 題 Arbor3D 領域問答，涵蓋資料來源揭露、1.3 公尺胸徑、AI／人工配對、MAE／RMSE／Bias、跨期固定樹號、碳量估算、點雲品質、Power BI 與權限管理等主題。

使用者提問時，App 伺服器會先執行本機 RAG，取回最多三段相關規範，再連同本次盤點 JSON 送至 Phi-4。RAG 可隨規範更新，並保留來源；模型則負責將證據整理成繁體中文、可執行的回答。系統另已將資料拆為 900 題 QLoRA 訓練集與 100 題保留評測集，但實際微調尚待具 NVIDIA GPU 的訓練環境完成，不能將資料集準備寫成模型已微調。

考量 Phi-4 推論及後續微調耗時，正式架構規劃不在使用者本機長時間運算，而是部署至 Microsoft Foundry Managed Compute GPU，由 Azure 提供 HTTPS/OpenAI 相容端點[9]。App 已完成 `phi4-cloud` adapter、Managed Identity／伺服器端金鑰、120 秒逾時、費用鎖及失敗退回機制；實際 GPU deployment 仍須確認 Azure for Students 的區域配額與費用後建立。未部署前，公開站會使用本機證據模式，不會假裝已呼叫雲端 Phi-4。

## 三、系統功能簡介

### （一）地圖選點與路徑管理

系統以 Leaflet 整合國土測繪底圖、街道／空拍切換、地點搜尋、定位、路徑顯示、GPS 錄製及 GPX 匯入。全臺 10,462 筆地點改為獨立 JSON 並按需載入，降低首頁負擔。正式路線應使用現場 GPX；OSM 參考線與展示軌跡只作導航及介面驗證。

### （二）掃描素材匯入與自動發佈

App 可接收 PLY、照片、`calib.json` 與 `cameras.json`，由伺服器整理素材並呼叫 Python adapter。正式 GPU 管線可在具 PyTorch、Open3D 與 Ultralytics 的環境執行；Azure Cloud DBH App Service 已建立 `prepare-only` 服務及健康檢查，完整 GPU 推論仍待雲端映像、GPU 配額或外部運算端點。

### （三）盤點、影像與三維複核

盤點視窗提供樹木表格、可靠度燈號、待確認／需複核篩選、Segmentation、胸高橫切面、點雲側視與可旋轉單木 PLY。演算法 DBH 與人工 DBH 分開保存，人工數值不覆寫原始結果，使後續誤差分析保有可追溯性。

### （四）人工量測、離線作業與 Cosmos DB

現場人員可填寫標準 1.3 公尺人工 DBH、樹高、量測日期、係數及備註。弱網或離線時先保存於瀏覽器 localStorage；恢復連線後再同步 Azure Cosmos DB `Arbor3D／FieldMeasures`。盤點主資料與媒體仍由 App JSON／檔案管理，不把所有大型點雲寫入 Cosmos DB。

### （五）碳量管理試算

App 目前實作的管理試算公式為：

```text
A = π × DBH(m)
D = A² × B × C
CO₂ = D × 3.667
```

其中 A 為胸高圓周，B 為樹高，C 為係數，D 為樹含碳量試算值，3.667 為碳轉換為 CO₂ 當量的分子量比例。胸徑以人工量測優先；樹高缺值時，以 `1.3 + 1.8√DBH` 進行 3.5–22 公尺範圍的粗估，並標記為 estimated。係數可選表定 0.0159、闊葉 0.027、針葉 0.020 或自訂。

此結果是盤點管理估算，不是認證碳權、年度吸收速率或經第三方查證的減碳量。正式應用仍須依樹種、木材密度、在地係數、量測期間與主管機關方法調整。

### （六）Power BI 分析輔助

Power BI 是本系統的主要分析輔助，不以 Excel 作為唯一分析工具。App 可匯出 canonical Analytics JSON、CSV、Excel 快照及圖表 CSV 包；資料模型已拆為 `DimTree`、`DimScan`、`FactObservation`、`FactEstimate`、`FactGrowth` 與 `Summary`，避免把多次盤點或平均值錯誤相加。

目前已產生五頁 PBIP／PBIR 草稿：盤點總覽、DBH 驗證、多期比較、資料品質及推估碳量。DAX 已包含 Observations、Valid Pairs、MAE、RMSE、Bias、MAPE、Review Rate 與 Estimated CO₂ Snapshot 等指標；只有 `dataset_kind=observed`、同樹、同日且標準 1.3 公尺人工值完整的配對，才能進入正式精度 KPI。沒有有效配對時，MAE／RMSE／Bias 保持空白，不以零或展示資料代替。

目前 50 個 PBIP／PBIR／PBISM 定義檔已通過 Microsoft JSON schema cache 驗證，但尚未在 Windows Power BI Desktop 實際刷新 Power Query、執行 DAX、檢查五頁版面及測試 RLS，因此不能宣稱 Power BI 報表已正式發布。後續若發佈至 Power BI Service／Fabric，需建立場址權限、RLS、更新排程及成本控管。

### （七）帳號、安全與持續部署

系統已完成 Microsoft Entra ID、MSAL＋PKCE、JWT 驗證、App roles、HttpOnly Session 與角色寫入限制的程式架構；但學校租戶目前缺少建立 App registration 的目錄權限，因此正式 Entra 登入尚未啟用，展示環境仍提供本機示範帳號。

Azure App Service 使用 system-assigned Managed Identity 存取主要 Cosmos DB，機密與 API key 不進前端、不提交 Git。GitHub `main` 每次推送後會由 GitHub Actions 自動測試、建置並部署至 `https://arbor3d-platform-1ec69a14.azurewebsites.net/`。

## 四、系統特色

### （一）量測與視覺化分流

DBH 由去噪點雲與胸高截面計算；3D Gaussian Splatting 與單木 PLY 負責場景及三維呈現。系統不因視覺模型較好看就把它當成正式幾何量測來源。

### （二）可信度導向的雙軌 DBH

系統依弧度涵蓋、圓周貼合、缺口與可見寬度選擇圓擬合或虛擬卡尺；無法可靠計算時直接標記待複核，讓管理者優先處理問題樹，而不是逐棵重查。

### （三）從單次報告轉為可持續資料模型

每棵樹的影像、點雲、DBH、人工紀錄、碳量估算及來源可由固定資料契約串聯，後續加入第二期掃描後即可產生真實 `FactGrowth`，支援長期監測。

### （四）Phi-4＋RAG 的領域助理

以 Phi-4-mini-instruct 搭配 1,000 題受控知識庫，讓 AI 回答盤點複核、精度條件、碳量限制及下一步，而不是只依模型記憶自由生成。運算規劃放在 Azure GPU，減少使用者設備負擔；憑證與費用開關保留在伺服器端。

### （五）Power BI 決策分析

系統同時提供 App 即時操作與 Power BI 管理分析。App 適合現場查看與填寫，Power BI 適合跨場址 KPI、誤差、資料品質、跨期趨勢與碳量快照。真實與展示資料以 `dataset_kind` 分流，避免展示季度數據進入正式 KPI。

### （六）可重建、可測試與可部署

目前 App 32 項測試、production build 與 Lint 均通過；Power BI 50 個定義檔通過 schema 驗證。模型、RAG、資料轉換與 Windows 安裝流程均保存在 GitHub，大型原始點雲及模型權重則由外部儲存或 Microsoft catalog 管理，避免 Git 倉庫失控。

## 五、系統開發工具與技術

前端採 React 19、TypeScript、Vite 8、Leaflet 與 Three.js，支援響應式 Web App、PWA 快取、離線提示、地圖、資料表、影像及點雲視覺化。Node.js 版本要求為 22.12 以上；production 由 Node HTTP server 同時提供靜態頁面及 API。

後端量測以 Python、Open3D、NumPy、OpenCV、PyTorch 及 Ultralytics YOLO 執行點雲處理、影像分割與幾何量測。自訓 YOLO v3 為目前優先權重，資料集含正樣本與非樹木負樣本，用於降低路燈、招牌等誤檢。

Microsoft 技術包含 Azure App Service、Azure Cosmos DB for NoSQL、Microsoft Entra ID 架構、Microsoft Foundry Phi-4、Managed Identity、Power BI／Fabric 資料模型及 Azure Cost Management。雲端 DBH 與 Phi-4 GPU 推論均採服務化介面，App 不需在使用者裝置長時間執行重型運算。

## 六、目前完成度與待完成項目

### （一）已完成

1. 逢甲一期 16 棵真實掃描資料之盤點介面、影像、DBH、點雲及碳量試算。
2. YOLO 樹幹分割、胸高切片、圓擬合／虛擬卡尺與待複核規則。
3. 全臺地點搜尋、國土測繪底圖、GPS／GPX、路線與盤點視窗。
4. 人工 DBH／樹高／日期離線保存及 Cosmos DB 同步 adapter。
5. Azure App Service 公開網站及 GitHub Actions 自動部署。
6. 1,000 題 RAG、Phi-4 本機與 Azure 雲端 adapter、900／100 QLoRA 資料切分。
7. Power BI canonical 資料、Power Query、DAX、五頁 PBIP／PBIR 草稿、Excel／CSV 匯出及 50 檔 schema 驗證。
8. 臺中 18 個公園／綠地、295 棵、4,720 筆季度展示資料，用於大量載入及跨期分析驗證。

### （二）尚待完成

1. 取得第二期同路徑真實掃描，人工確認 `persistent_tree_id`，才能計算真實成長。
2. 補齊每棵樹標準 1.3 公尺人工 DBH、樹高與日期，正式計算 MAE、RMSE、Bias 與 MAPE。
3. 以現場 GPX 取代參考／展示路線。
4. 在完整 GPU 環境驗收從 YOLO、點雲、DBH、3DGS 到 App 自動匯入的整套閉環。
5. 取得 Azure GPU quota 並部署 Phi-4-mini-instruct Managed Compute；驗收延遲、費用、安全與失敗退回。
6. 在 Windows NVIDIA GPU 執行 QLoRA、評估保留 100 題並人工抽查；通過後才發佈 adapter。
7. 在 Windows Power BI Desktop 刷新 Power Query、執行 DAX、檢查關係與五頁版面，再決定是否發布 Fabric／Power BI Service。
8. 由租戶管理員建立 Entra App registration，啟用正式機關帳號、角色與 RLS。
9. 持續監控 Azure 100 USD 年度預算與 50%、80%、100% 告警，展示結束後停止未使用的 GPU 資源。

## 七、系統使用對象與環境

主要使用者包括環保局、公園及校園管理人員、現場調查人員與資料分析人員。現場人員可使用手機或平板查看路線、樹木資料、點雲及待複核項目，並填寫人工量測；管理者可在電腦端查看場址、異常、碳量估算及跨期資料；分析人員則可使用 Power BI 檢查有效配對、誤差、資料品質及趨勢。

App 可於現代手機、平板及電腦瀏覽器使用。開發與建置需 Node.js 22.12 以上；完整量測管線需 Python、Open3D、PyTorch、Ultralytics 及足夠的 CPU／GPU／磁碟。一般使用者不需在本機安裝 Phi-4 或執行重型點雲運算，正式規劃由 Azure 雲端端點處理。離線時可保留已開啟頁面、靜態資產與人工量測，恢復連線後再同步。

## 八、結語

Arbor3D 將現場掃描、AI 樹幹分割、胸高幾何量測、三維視覺化、人工複核、Azure 資料服務、Phi-4＋RAG 及 Power BI 分析整合於同一套可持續部署的系統。相較傳統一次性調查，Arbor3D 更重視資料來源、量測方法、可信度、人工配對與跨期身分，使每棵樹形成可重新計算、可查驗及可延伸的 Digital Representation。

目前系統已完成可操作的 Web App、一期真實示範、雲端部署、自動測試、RAG、Phi-4 雲端介面與 Power BI 草稿；下一階段重點是取得第二期真實掃描與標準人工胸徑、完成 Azure GPU／QLoRA 驗收，以及在 Power BI Desktop 驗證 DAX 與報表版面。完成上述工作後，Arbor3D 才能從競賽展示平台進一步提升為可支援都市樹木長期監測、量測品質管理與碳量分析的正式系統。

## 九、參考文獻

[1] United Nations Environment Programme. (2025). *Emissions Gap Report 2025: Off Target—Continued Collective Inaction Puts Global Temperature Goal at Risk*. https://www.unep.org/resources/emissions-gap-report

[2] Wielgosz, M., Puliti, S., Astrup, R., & Schindler, K. (2024). Automated forest inventory: Analysis of high-density airborne LiDAR point clouds with 3D deep learning. *Remote Sensing of Environment, 305*, 114078. https://doi.org/10.1016/j.rse.2024.114078

[3] Wielgosz, M., Puliti, S., Xiang, B., Schindler, K., & Astrup, R. (2024). SegmentAnyTree: A sensor and platform agnostic deep learning model for tree segmentation using laser scanning data. *Remote Sensing of Environment, 313*, 114367. https://doi.org/10.1016/j.rse.2024.114367

[4] Xiang, B., Wielgosz, M., Puliti, S., Král, K., Krůček, M., Missarov, A., & Astrup, R. (2025). ForestFormer3D: A Unified Framework for End-to-End Segmentation of Forest LiDAR 3D Point Clouds. *Proceedings of the IEEE/CVF International Conference on Computer Vision*, 24717–24727.

[5] Terryn, L., Calders, K., Akerblom, M., Bartholomeus, H., Disney, M., Levick, S., Origo, N., Raumonen, P., & Verbeeck, H. (2023). Analysing individual 3D tree structure using the R package ITSMe. *Methods in Ecology and Evolution, 14*(1), 231–241. https://doi.org/10.1111/2041-210X.14026

[6] Wysocki, O., et al. (2026). TUM2TWIN: Introducing the large-scale multimodal urban digital twin benchmark dataset. *ISPRS Journal of Photogrammetry and Remote Sensing, 232*, 810–830. https://doi.org/10.1016/j.isprsjprs.2025.12.013

[7] Yrttimaa, T., Junttila, S., Luoma, V., Calders, K., Kankare, V., Saarinen, N., et al. (2023). Capturing seasonal radial growth of boreal trees with terrestrial laser scanning. *Forest Ecology and Management, 529*, 120733. https://doi.org/10.1016/j.foreco.2022.120733

[8] Microsoft. *Phi-4-mini-instruct—Microsoft Foundry Model Catalog*. https://ai.azure.com/catalog/models/Phi-4-mini-instruct

[9] Microsoft Learn. *Deploy open-source models with managed compute in Microsoft Foundry*. https://learn.microsoft.com/en-us/azure/foundry/how-to/deploy-models-managed

[10] Arbor3D GitHub Repository. https://github.com/toby0407-del/Arbor3D
