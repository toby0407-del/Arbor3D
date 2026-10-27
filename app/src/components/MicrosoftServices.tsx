import { useEffect, useState } from "react";
import { fetchAssistantStatus, type AssistantStatus } from "../lib/assistant";

type Services = {
  checkedAt: string;
  storage: { provider: string; state: string };
  identity: { configured: boolean; sessionMode: string };
  powerBi: { reportUrl: string | null; state: string };
  compute?: { configured: boolean; state: string };
};

export function MicrosoftServices({ onClose }: { onClose: () => void }) {
  const [services, setServices] = useState<Services | null>(null);
  const [ai, setAi] = useState<AssistantStatus | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function refresh() {
    setBusy(true); setError("");
    try {
      const [response, status] = await Promise.all([fetch("/api/auth/services", { signal: AbortSignal.timeout(15000) }), fetchAssistantStatus()]);
      if (!response.ok) throw new Error("無法讀取服務狀態，請確認登入仍有效。");
      setServices(await response.json() as Services); setAi(status);
    } catch { setServices(null); setAi(null); setError("連線檢查失敗，請確認網路及登入狀態後重試。"); }
    finally { setBusy(false); }
  }
  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    const key = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", key); return () => window.removeEventListener("keydown", key);
  }, [onClose]);
  return <div className="assistant-backdrop" onClick={onClose}>
    <section className="assistant-panel services-panel" role="dialog" aria-modal="true" aria-labelledby="services-title" onClick={e=>e.stopPropagation()}>
      <header className="assistant-head"><div><p>Arbor3D × Microsoft</p><h2 id="services-title">服務連線</h2></div><button className="ghost-btn" onClick={onClose}>關閉</button></header>
      {error && <p role="alert" className="assistant-error">{error}</p>}
      <dl className="services-list">
        <div><dt>Microsoft Phi-4</dt><dd>{!ai ? "檢查中…" : ai.connection?.state === "reachable" ? "本機模型服務已連通" : ai.phi4Configured ? "模型服務無法連線，請先啟動模型" : "尚未設定"}</dd>
          {ai?.lastInference?.provider === "phi4" && <dd>已實際回覆：{new Date(ai.lastInference.verifiedAt).toLocaleString("zh-TW")}</dd>}</div>
        <div><dt>Azure Cosmos DB</dt><dd>{!services ? "檢查中…" : services.storage.provider !== "cosmos" ? "目前使用本機檔案" : services.storage.state === "reachable" ? "已實際連通資料庫" : "資料庫無法連線"}</dd><dd>儲存人工量測及複核紀錄。</dd></div>
        <div><dt>Azure 樹木量測運算</dt><dd>{!services ? "檢查中…" : services.compute?.state === "hybrid_ready" ? "混合運算已就緒：本機處理影像與點雲，Azure 計算截面幾何與品質" : services.compute?.state === "ready" ? "正式量測依賴與成果下載已就緒，待批次驗收" : services.compute?.state === "prepare_only" ? "目前只能整理資料，尚不能正式量測" : services.compute?.state === "authentication_required" ? "雲端驗證尚未完成" : services.compute?.state === "unavailable" ? "雲端運算服務無法連線" : "尚未接通，匯入目前使用快速預覽"}</dd></div>
        <div><dt>Microsoft Entra ID</dt><dd>{!services ? "檢查中…" : services.identity.configured ? "目前使用 Microsoft 登入" : "尚未設定組織登入，目前使用本機帳號"}</dd></div>
        <div><dt>Power BI</dt><dd>{services?.powerBi.reportUrl ? <a href={services.powerBi.reportUrl} target="_blank" rel="noreferrer">開啟 Power BI 報表</a> : "尚未連結線上報表"}</dd><dd>校方授權問題已記錄，待開通後連結報表。</dd></div>
      </dl>
      <button className="primary-btn" disabled={busy} onClick={()=>void refresh()}>{busy ? "檢查中…" : "重新檢查"}</button>
      {services && <p className="muted">檢查時間：{new Date(services.checkedAt).toLocaleString("zh-TW")}</p>}
    </section>
  </div>;
}
