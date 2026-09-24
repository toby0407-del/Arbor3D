# Copilot Studio RAG 與本機檢索

預設完全離線。`python3 -m agents.rag 'DBH 誤差'` 從 `knowledge/*.md` 與 `knowledge/*.jsonl` 擷取相符文件片段，回傳文件／行號／SHA-256。沒有匹配時明確回覆無依據。
支援英文詞與中文雙字切分；此輕量檢索不需要向量資料庫或付費 embedding。它不是完整語意搜尋，近義詞可能無法匹配。

`knowledge/arbor3d-qa-1000.jsonl` 是 20 類、每類 50 題的 Arbor3D 領域問答庫，共 1,000 題。它用於 RAG 參考與迴歸評測，不代表 1,000 筆現場觀測，也不是 fine-tuning。執行 `cd app && npm run rag:generate` 可依受控規則重新產生；`npm run rag:copilot-pack` 會同步產生可上傳至 Copilot Studio Knowledge 的 `copilot-upload/Arbor3D-RAG-1000.md`。

`python3 -m agents.evaluate_rag --out outputs/rag-evaluation.json` 會執行零費用的 leave-one-out 檢索評測：逐題排除原題，再檢查前 1／前 3 筆是否仍命中同分類。這只評估 retrieval，不取代 GPT 答案正確性與領域專家人工審核。

App 的 `/api/assistant` 已使用同一個 `knowledge/`：先在本機擷取最多三段，再把盤點證據與檢索片段交給 Copilot Studio；回答會顯示 `+ RAG` 並列出來源檔名與行號。Copilot 尚未連線或失敗時仍使用本機規則回答，檢索本身不產生模型費用。可用 `ARBOR_RAG_KNOWLEDGE` 指向另一個受控知識資料夾。

`python3 -m agents.foundry 'DBH 誤差'` 產生 agent definition 預覽及同一批檢索來源。
`config.env.example` 無任何密鑰，程式不自動載入 env 檔。使用者未來可透過環境變數配置已存在的專案與模型。

## 未來部署步驟（本任務不執行）

1. 只有另行確認成本並已有 Azure/Foundry 資源時，才安裝 `requirements-foundry.txt`，登入符合最小權限的 Azure 身分。
2. 設定 FOUNDRY_PROJECT_ENDPOINT、FOUNDRY_MODEL_DEPLOYMENT、FOUNDRY_AGENT_NAME。
3. 預設 ARBOR_ALLOW_BILLABLE_CLOUD=NO。呼叫雲端同時需要 `--execute` 與環境變數 `ARBOR_ALLOW_BILLABLE_CLOUD=YES_I_ACCEPT_COSTS`；程式在 SDK import／認證之前檢查。
4. 首次建立需另加 `--create-agent`；後續只指定 `--execute` 使用已存在 agent。這些操作可能計費，本次均未執行。
5. 檢索片段以不可信資料傳給 agent，要求逐項引用，不提供 shell、支付、修改或部署工具。回覆仍需人工核對引文，不能宣稱完全消除幻覺。

此 adapter 依 [Microsoft Foundry prompt agent 官方 Python 2.x 範例](https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/prompt-agent) 設計。SDK 將來可能改版；雲端執行未驗證。
程式只使用既有模型部署，不包含建立 subscription、capacity、搜尋服務、儲存服務或模型部署的指令。

Dockerfile 是離線執行樣板：`docker build -f agents/Dockerfile -t arbor3d-rag .` 後可 `docker run --rm --network none arbor3d-rag 'DBH 誤差'`。
需要自行取得基底映像；本次沒有建立或推送容器，也沒有部署任何雲端主機。
不要在 knowledge 放入憑證、私密人員資料；未來啟用 Foundry 時檢索片段會送往指定專案。
