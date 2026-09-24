# Phi-4 雲端推論架構

## 目標

Arbor3D 選用 Microsoft `Phi-4-mini-instruct` 作為可控的開放模型。RAG 檢索仍由 App 伺服器執行，再把當次盤點 JSON 與最多三段知識片段送到 Azure 上的 Phi-4 endpoint。這樣使用者端不需下載數 GB 模型，也不會在手機或一般筆電長時間運算。

## 已完成

- `ARBOR_AI_PROVIDER=phi4-cloud` provider 與狀態檢查。
- Microsoft Foundry／OpenAI 相容 HTTPS chat-completions adapter。
- 伺服器端 API key 或 Azure Managed Identity，憑證不傳到瀏覽器。
- `ARBOR_ALLOW_BILLABLE_CLOUD` 費用鎖；未開啟或 endpoint 失敗時退回本機證據模式。
- 1,000 題 RAG、900 題 QLoRA 訓練集與 100 題保留評測集。

## 尚未完成

- 尚未建立 Phi-4 Managed Compute GPU deployment，也未取得學生訂閱 GPU quota。
- 尚未在 Windows NVIDIA GPU 執行 QLoRA，因此目前沒有可部署的 Arbor3D LoRA adapter。
- Managed Compute 目前屬 Azure 預覽服務；建立後會產生專用 GPU 費用，不能視為 F1 App Service 免費額度。

## 正式設定

取得 Foundry Managed Compute endpoint 與 deployment name 後，在 Azure App Service 設定：

```env
ARBOR_AI_PROVIDER=phi4-cloud
PHI4_CLOUD_ENDPOINT=https://YOUR-ACCOUNT.services.ai.azure.com/openai/v1
PHI4_CLOUD_MODEL=Phi-4-mini-instruct
ARBOR_ALLOW_BILLABLE_CLOUD=YES_I_ACCEPT_COSTS
```

正式環境優先使用 App Service Managed Identity；只有部署不支援 Entra 驗證時才使用伺服器端 `PHI4_CLOUD_API_KEY`。設定後以 `/api/assistant/status` 確認 `activeMode=phi4-cloud`，再用保留問題與人工盤點案例驗收答案、引用、延遲與成本。

## 成本控制

部署前先確認可用區域、GPU quota、每小時計價、閒置縮容能力與 Azure for Students spending limit。先以最小可用部署做短時測試，驗收後再決定是否長期開啟；不展示時應停止或刪除專用 GPU deployment。
