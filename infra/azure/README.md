# Arbor3D Azure 平台

正式平台使用 Microsoft Entra ID 驗證使用者，並以 Azure Cosmos DB for NoSQL 保存人工盤點資料；不使用 Firebase Authentication 或 Firestore。

**雲端胸徑計算：** 見 [Cloud DBH](../../docs/microsoft/CLOUD_DBH.md) 與 `infra/azure/dbh-compute.bicep`（Container Apps 包裝既有 DBH 管線）。

## 1. 建立 Cosmos DB

```bash
az deployment group create \
  --resource-group <RESOURCE_GROUP> \
  --template-file infra/azure/main.bicep \
  --parameters cosmosAccountName=<UNIQUE_ACCOUNT_NAME> appPrincipalId=<APP_MANAGED_IDENTITY_OBJECT_ID>
```

範本使用 serverless、Session consistency、停用 local/key authentication，並把 Arbor3D Managed Identity 指派為 Cosmos DB Built-in Data Contributor。`FieldMeasures` container 使用 `/scanId` 分割鍵；每個掃描以 `field-measures:<scanId>` 做 point read／upsert。

## 2. 建立 Microsoft Entra 應用程式

在 Entra admin center 建立單租戶 App registration：

1. 加入 SPA redirect URI：本機 `http://127.0.0.1:5174` 與正式 HTTPS 網址。
2. Expose an API，建立 delegated scope `access_as_user`。
3. 建立 App roles，例如 `管理者`、`承辦人`、`現場調查員`、`複核人員`，並指派使用者或群組。
4. 不要建立或放入前端 client secret；SPA 使用 Authorization Code + PKCE。

## 3. App 設定

```env
AZURE_ENTRA_TENANT_ID=<tenant-id>
AZURE_ENTRA_CLIENT_ID=<application-client-id>
AZURE_ENTRA_API_AUDIENCE=api://<application-client-id>
VITE_AZURE_ENTRA_TENANT_ID=<tenant-id>
VITE_AZURE_ENTRA_CLIENT_ID=<application-client-id>
VITE_AZURE_ENTRA_SCOPE=api://<application-client-id>/access_as_user

AZURE_COSMOS_ENDPOINT=https://<account>.documents.azure.com:443/
AZURE_COSMOS_DATABASE=Arbor3D
AZURE_COSMOS_CONTAINER=FieldMeasures
```

部署在 Azure 時使用 Managed Identity。只有本機開發才由 `DefaultAzureCredential` 沿用 `az login`；Cosmos endpoint 可以出現在設定中，但 Cosmos account key、Entra client secret 與 access token 都不得提交 Git 或放進 `VITE_` 變數。

尚未設定 Entra／Cosmos 時，App 保留伺服器端展示登入與 `.runtime` 檔案存放，僅供本機展示。

## 4. 目前訂閱中的資源（2026-09-24）

- 主要展示帳號：`arbor3dcos483bd05e16`，Japan East，Serverless，`Arbor3D`／`FieldMeasures`，分割鍵 `/scanId`。
- 早期開發帳號：`arbor3d-d1322855`，設定相同；它不是主要展示端點。確認沒有需要保留的資料後再決定是否刪除，避免同時維護兩份資源。
- 兩個帳號皆停用 local/key authentication；本機用 `az login`，Azure 主機用 Managed Identity。
- Entra App registration 尚未完成，原因是學校租戶未授權目前學生帳號註冊應用程式；不可用 Client Secret 或共用密碼繞過。
- Azure for Students spending limit 目前為 On，另有年度 100 USD 預算 `arbor3d-100usd`；仍應持續查看 Cost Management。

不要重跑範本建立第三個 Cosmos 帳號。Windows 接續請直接使用主要 endpoint，操作見 [Windows 指南](../../docs/microsoft/WINDOWS.md)。
