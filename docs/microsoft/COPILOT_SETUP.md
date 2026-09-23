# Copilot Studio 接上 Arbor3D App

目標：盤點視窗「詢問 AI 助理」優先走 Microsoft Copilot Studio；未就緒時自動本機證據模式（不計費）。

## 資料庫怎麼分（重要）

| 資料 | 儲存 | 說明 |
|---|---|---|
| 現場手測（胸徑／樹高／日期） | **Azure Cosmos DB** `FieldMeasures`（有設 endpoint 時） | 離線先寫 localStorage，連線後同步 |
| 盤點報告／影像路徑 | **App JSON／public/scans** | 不進 Cosmos |
| Power BI 圖表／KPI | **匯出檔**（CSV／analytics-input JSON／PBIP） | 不是線上資料庫 |

目前 Cosmos：`arbor3dcos483bd05e16`（Japan East）。Entra App registration 需租戶目錄權限，學生帳若無法建立，繼續用示範登入＋Cosmos（本機 `az login`）。

## Copilot 設定步驟

1. 開啟 [Microsoft Copilot Studio](https://copilotstudio.microsoft.com/)，建立代理「Arbor3D」。
2. 知識／主題：以「待複核、精度限制、碳匯非碳權、下一步」為主；可上傳 `agents/` RAG 摘要。
3. **Channels → Mobile app**：複製 **Token Endpoint**（HTTPS）。
4. 填入 `app/.env.local`（勿提交 Git）：

```env
ARBOR_AI_PROVIDER=copilot
COPILOT_STUDIO_TOKEN_ENDPOINT=https://...
COPILOT_STUDIO_AGENT_NAME=Arbor3D Copilot
# 只有確認要計費時才改成：
ARBOR_ALLOW_BILLABLE_CLOUD=YES_I_ACCEPT_COSTS
```

5. 重啟 `npm run dev`。助理面板會顯示「Microsoft Copilot Studio（已就緒）」；否則維持本機證據模式並列出缺項。
6. 健康檢查：`GET /api/assistant/status`。

## 費用

學生訂閱約 **$100** 額度。預設 `ARBOR_ALLOW_BILLABLE_CLOUD=NO`，不會打 Copilot／Azure AI。展示前再開。
