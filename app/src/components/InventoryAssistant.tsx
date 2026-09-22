import { useMemo, useState } from "react";
import type { FieldMeasure } from "../hooks/useFieldMeasures";
import {
  askInventoryAssistant,
  inventoryAssistantContext,
  type AssistantReply,
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
  const context = useMemo(
    () => inventoryAssistantContext(parkName, pathName, report, measures),
    [measures, parkName, pathName, report],
  );

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
            <p>Microsoft AI × Arbor3D</p>
            <h2 id="assistant-title">盤點 AI 助理</h2>
          </div>
          <button type="button" className="ghost-btn" onClick={onClose}>
            關閉
          </button>
        </header>

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
              <span>{reply.provider === "azure" ? "Azure AI" : "本機證據模式"}</span>
            </div>
            {reply.answer.split("\n").map((line, index) => (
              <p key={`${index}-${line}`}>{line || " "}</p>
            ))}
            <h3>資料依據</h3>
            <ul>
              {reply.evidence.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </article>
        ) : (
          <p className="assistant-empty">
            回答只使用目前盤點資料；資料不足時會明確說明。未設定 Azure 時自動使用本機證據模式。
          </p>
        )}
      </section>
    </div>
  );
}
