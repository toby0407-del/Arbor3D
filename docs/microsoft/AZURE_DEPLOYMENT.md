# Azure for Students 實際部署

更新日期：2026-09-22。以下資源已建立在「Azure for Students」訂閱；文件不保存訂閱 ID、使用者帳號或 API key。

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

學生訂閱政策只允許 Japan East、East Asia、Malaysia West、Indonesia Central、Korea Central；模型清單顯示 Japan East 同時支援本部署與按量 `GlobalStandard`，因此選用 Japan East。

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

## 費用與停止方式

App 仍需 `ARBOR_ALLOW_BILLABLE_CLOUD=YES_I_ACCEPT_COSTS` 才會呼叫模型。部署 capacity 是速率配額，不代表預付的 VM；實際費用仍應在 Azure Cost Management 查看。

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
