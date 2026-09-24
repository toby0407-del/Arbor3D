# Azure for Students 實際部署

更新日期：2026-09-24。以下資源已建立在「Azure for Students」訂閱；文件不保存訂閱 ID、使用者帳號、access token 或 API key。

## 已建立資源

| 項目 | 值 |
|---|---|
| Resource group | `arbor3d-competition-rg` |
| Foundry resource | `arbor3d-fcu-20260922` |
| Foundry project | `arbor3d-campus-trees` |
| Resource region | Japan East |
| Model deployment | `gpt-4-1-mini` |
| Model | `gpt-4.1-mini` `2025-04-14` |
| SKU | `GlobalStandard`，capacity 10 |
| Foundry project endpoint | `https://arbor3d-fcu-20260922.services.ai.azure.com/api/projects/arbor3d-campus-trees` |
| App inference endpoint | `https://arbor3d-fcu-20260922.openai.azure.com` |
| Primary Cosmos DB | `arbor3dcos483bd05e16`，Japan East，Serverless |
| Cosmos database／container | `Arbor3D`／`FieldMeasures`，partition key `/scanId` |
| Development Cosmos DB | `arbor3d-d1322855`，Japan East，Serverless；非主要展示端點 |
| Cloud DBH App Service | `arbor3d-dbh-1ec69a14`，East Asia，F1 Free，Running |
| Arbor3D Web App | `arbor3d-platform-1ec69a14`，East Asia，共用 F1 Free plan |
| Public URL | `https://arbor3d-platform-1ec69a14.azurewebsites.net` |
| Cost budget | `arbor3d-100usd`，100 USD／年 |

學生訂閱政策只允許 Japan East、East Asia、Malaysia West、Indonesia Central、Korea Central；模型清單顯示 Japan East 同時支援本部署與按量 `GlobalStandard`，因此選用 Japan East。

兩個 Cosmos 帳號均已成功建立 `Arbor3D`／`FieldMeasures`，採 Serverless 並停用 local/key authentication。正式展示與 Windows 接續統一使用 `arbor3dcos483bd05e16`；`arbor3d-d1322855` 是較早的開發帳號，確認無資料依賴後再決定是否刪除。Entra App registration 因學校租戶權限不足尚未建立，正式 Microsoft 登入仍未啟用。

## App 本機設定

`app/.env.local` 已設定 endpoint、deployment name 與明確費用鎖，且由 `.gitignore` 排除。沒有把 API key 寫入磁碟。

伺服器認證順序：

1. 若存在 `AZURE_AI_API_KEY`，只在伺服器端使用。
2. 否則使用 `DefaultAzureCredential`；本機沿用 `az login`，Azure 主機使用 Managed Identity。
3. 雲端錯誤或未設定時，自動退回本機證據模式。

目前登入者只取得資料平面使用角色：Foundry project 的 `Foundry User`，以及 Foundry resource 的 `Cognitive Services OpenAI User`；沒有為 App 增加 Owner 或管理員權限。

## 驗證紀錄

- Foundry resource：Succeeded。
- Foundry project：Succeeded。
- Model deployment：Succeeded。
- 直接模型最小測試：HTTP 200，模型回覆 `OK`。
- App `/api/assistant` 端到端測試：`provider=azure`，能依 Tree_002 的待複核證據作答。
- Microsoft Entra 無金鑰推論：資源的 `openai.azure.com` endpoint HTTP 200；專案 endpoint 保留給 Foundry project／agent SDK。
- API key 僅注入單次測試程序，未寫入 `.env.local`、log 或 Git。
- Primary／development Cosmos DB 均為 Succeeded，`FieldMeasures` 使用 `/scanId`；實際 Azure 身分讀寫測試通過，測試文件已清除。
- Cloud DBH App Service 為 Running；目前 F1 prepare-only，完整 GPU 計算仍需本機 GPU 或另行取得 Azure 配額。
- 2026-09-24 同步 `f5cb0e4` 後，App 29 項與 Cloud DBH 1 項測試通過，production build 成功。

## GitHub 持續部署

`.github/workflows/deploy-azure-app.yml` 監聽 `main`。每次 push 依序執行：

1. 安裝鎖定版本的 Node 套件。
2. 執行全部 App 測試。
3. 建置 React 靜態檔與 production Node API server。
4. 組裝不含 `.env.local` 的部署包。
5. 使用 GitHub Actions Secret 中的 App Service publish profile 發布。

Azure App Service 使用 system-assigned Managed Identity 讀寫主要 Cosmos DB。正式網站的 AI provider 已指定為 Copilot Studio，並移除 Azure AI endpoint/model；既有 Foundry 部署僅保留為先前技術驗證紀錄。網站設定不含 Cosmos account key 或 Azure AI API key。由於學校租戶禁止目前帳號建立 App Registration，GitHub 部署暫用 App Service 層級 publish profile；未來取得租戶權限後可改成 Microsoft 建議的 OIDC 短期憑證。

線上伺服器健康檢查：`https://arbor3d-platform-1ec69a14.azurewebsites.net/healthz`。

## 費用與停止方式

App 仍需 `ARBOR_ALLOW_BILLABLE_CLOUD=YES_I_ACCEPT_COSTS` 才會呼叫模型。部署 capacity 是速率配額，不代表預付的 VM；Cosmos Serverless 依請求與儲存量計費。訂閱 spending limit 為 On，並已建立年度 100 USD 預算，但實際費用與通知仍應在 Azure Cost Management 查看。

暫停 App 雲端呼叫：

```bash
sed -i '' 's/ARBOR_ALLOW_BILLABLE_CLOUD=YES_I_ACCEPT_COSTS/ARBOR_ALLOW_BILLABLE_CLOUD=NO/' app/.env.local
```

查看資源：

```bash
az resource list --resource-group arbor3d-competition-rg --output table
az cognitiveservices account deployment show \
  --name arbor3d-fcu-20260922 \
  --resource-group arbor3d-competition-rg \
  --deployment-name gpt-4-1-mini
```

競賽結束且確認不再使用時，可在 Azure Portal 刪除整個 `arbor3d-competition-rg`。刪除不可逆，執行前必須重新確認。
