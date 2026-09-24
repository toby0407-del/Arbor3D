# Phi-4 本機模型＋1,000 題 RAG

## 目前架構

Arbor3D 支援 `ARBOR_AI_PROVIDER=phi4`。伺服器先從 1,000 題知識庫取回最多三段，再將盤點 JSON、規範片段與問題送到 Foundry Local 的 `Phi-4-mini`。若模型未啟動或呼叫失敗，會退回不生成內容的本機證據規則。

Azure 公開網站不能存取使用者 Windows 的 localhost，因此此模式用於 Windows 本機展示。Azure App Service 可繼續使用 Copilot Studio，兩者共用相同知識內容。

## Windows 安裝與啟動

```powershell
winget install Microsoft.FoundryLocal
foundry model list
foundry model download phi-4-mini
foundry server start
foundry server status
```

把 `foundry server status` 顯示的本機 endpoint 填入 `app/.env.local`：

```env
ARBOR_AI_PROVIDER=phi4
FOUNDRY_LOCAL_ENDPOINT=http://127.0.0.1:PORT
FOUNDRY_LOCAL_MODEL=phi-4-mini
```

Arbor3D 只接受 loopback endpoint，不會把提示傳送到區網中的其他主機。啟動 App 後以 `GET /api/assistant/status` 確認 `activeMode` 為 `phi4`。

## RAG 與 fine-tuning 不同

- RAG：每次提問即時搜尋 1,000 題知識，容易更新且能顯示來源；App 已完成。
- Fine-tuning：改變模型權重，適合固定回答風格與規則，但不取代 RAG，也不能保證事實正確。

執行以下命令產生訓練資料：

```powershell
cd app
npm run phi4:sft-data
```

輸出位於 `agents/fine-tuning/data/`：900 題訓練集、100 題保留評測集，以及完整 1,000 題版本。請先由領域人員抽查內容，再在具 CUDA NVIDIA GPU 的 Windows 電腦執行 QLoRA：

```powershell
python -m venv .venv-phi4
.\.venv-phi4\Scripts\Activate.ps1
pip install -r agents\fine-tuning\requirements.txt
python agents\fine-tuning\train_phi4_lora.py
```

訓練程式使用 Microsoft 的 `microsoft/Phi-4-mini-instruct` 基礎模型、4-bit QLoRA、900 題訓練與 100 題逐期評測。模型權重、checkpoint 與 LoRA adapter 不提交 Git。訓練完成後仍需跑保留集與人工驗收；若要讓 Foundry Local 載入自訂 adapter，需依當時支援格式合併／轉換為 ONNX，不能直接把 PEFT 資料夾當作 Foundry Local 模型。
