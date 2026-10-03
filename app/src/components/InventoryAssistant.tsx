import { useEffect, useMemo, useState } from "react";
import type { FieldMeasure } from "../hooks/useFieldMeasures";
import {
  askInventoryAssistant,
  fetchAssistantStatus,
  inventoryAssistantContext,
  type AssistantReply,
  type AssistantStatus,
} from "../lib/assistant";
import type { ParkInventoryReport } from "../types";

const SUGGESTIONS = [
  "哪些樹要優先現場複核？",
  "這批資料可以宣稱 AI 精度嗎？",
  "碳匯估算是多少？有哪些限制？",
  "請給我下一步行動建議",
];

type Props = {
  parkName: string;
  pathName: string;
  report: ParkInventoryReport;
  measures: Record<string, FieldMeasure>;
  onClose: () => void;
};

export function InventoryAssistant({
  parkName,
  pathName,
  report,
  measures,
  onClose,
}: Props) {
  const [question, setQuestion] = useState("");
  const [reply, setReply] = useState<AssistantReply | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<AssistantStatus | null>(null);
  const context = useMemo(
    () => inventoryAssistantContext(parkName, pathName, report, measures),
    [measures, parkName, pathName, report],
  );

  useEffect(() => {
    let active = true;
    void fetchAssistantStatus().then((next) => {
      if (active) setStatus(next);
    });
    return () => {
      active = false;
    };
  }, []);

  const submit = async (nextQuestion = question) => {
    const value = nextQuestion.trim();
    if (!value || busy) return;
    setQuestion(value);
    setBusy(true);
    setError("");
    try {
      setReply(await askInventoryAssistant(value, context));
    } catch (err) {
      setReply(null);
      setError(err instanceof Error ? err.message : "AI 助理暫時無法回答");
    } finally {
      setBusy(false);
    }
  };

  const modeLabel =
    status?.activeMode === "phi4"
      ? "Microsoft Phi-4 本機模型（已就緒）"
      : status?.activeMode === "copilot"
      ? "Microsoft Copilot Studio（已就緒）"
      : status?.activeMode === "azure"
        ? "Azure AI（已就緒）"
        : "本機證據模式";

  return (
    <div className="assistant-backdrop" role="presentation" onClick={onClose}>
      <section
        className="assistant-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="assistant-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="assistant-head">
          <div>
            <p>{status?.activeMode === "phi4" ? "Microsoft Phi-4 × Arbor3D" : "Microsoft Copilot × Arbor3D"}</p>
            <h2 id="assistant-title">盤點 AI 助理</h2>
            <p className="assistant-mode" role="status">
              目前：{modeLabel}
            </p>
          </div>
          <button type="button" className="ghost-btn" onClick={onClose}>
            關閉
          </button>
        </header>

        {status?.hints?.length ? (
          <ul className="assistant-hints" aria-label="Copilot 設定提示">
            {status.hints.map((hint) => (
              <li key={hint}>{hint}</li>
            ))}
          </ul>
        ) : null}

        <div className="assistant-context" aria-label="本次盤點摘要">
          <span>{context.summary.total} 棵</span>
          <span>較可信 {context.summary.reliable}</span>
          <span>待複核 {context.summary.review}</span>
          <span>CO₂ 約 {context.summary.co2Ton.toFixed(2)} t</span>
        </div>

        <div className="assistant-suggestions">
          {SUGGESTIONS.map((item) => (
            <button
              key={item}
              type="button"
              disabled={busy}
              onClick={() => void submit(item)}
            >
              {item}
            </button>
          ))}
        </div>

        <form
          className="assistant-form"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <label htmlFor="assistant-question">詢問這次盤點</label>
          <div>
            <input
              id="assistant-question"
              value={question}
              maxLength={500}
              placeholder="例如：今天應先複核哪些樹？"
              onChange={(event) => setQuestion(event.target.value)}
            />
            <button type="submit" className="primary-btn" disabled={busy || !question.trim()}>
              {busy ? "分析中…" : "送出"}
            </button>
          </div>
        </form>

        {error ? <p className="assistant-error">{error}</p> : null}
        {reply ? (
          <article className="assistant-answer" aria-live="polite">
            <div className="assistant-answer-label">
              <strong>回答</strong>
              <span>
                {reply.provider === "phi4"
                  ? `Microsoft Phi-4 · ${reply.model || "本機模型"}`
                  : reply.provider === "copilot"
                  ? `Microsoft Copilot · ${reply.model || "Copilot Studio"}`
                  : reply.provider === "azure"
                    ? `Azure AI · ${reply.model || "模型部署"}`
                    : "本機證據模式"}
                {reply.ragSources?.length
                  ? reply.ragQuestionCount
                    ? ` + ${reply.ragQuestionCount.toLocaleString("zh-TW")} 題 RAG`
                    : " + RAG"
                  : ""}
              </span>
            </div>
            {reply.answer.split("\n").map((line, index) => (
              <p key={`${index}-${line}`}>{line || " "}</p>
            ))}
            <h3>資料依據</h3>
            <ul>
              {reply.evidence.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        ) : (
          <p className="assistant-empty">
            回答只使用目前盤點資料與 RAG；資料不足時會明確說明。Phi-4／Copilot
            未設定或無法使用時，自動切換成本機證據模式。
          </p>
        )}
      </section>
    </div>
  );
}
