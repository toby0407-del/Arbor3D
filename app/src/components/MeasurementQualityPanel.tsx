import { useState } from "react";
import type { FieldMeasure } from "../hooks/useFieldMeasures";
import type { ParkInventoryReport, TreeRecord } from "../types";
import { downloadJson, qualityAccepted, qualityEvidence, qualityReasons, qualityState, rankViews, type ViewCandidate } from "../lib/measurementQuality";

type Plan = { candidates: ViewCandidate[]; remaining: number };
function readPlan(key: string): Plan {
  try {
    const p = JSON.parse(localStorage.getItem(key) ?? "null");
    if (p && Array.isArray(p.candidates) && p.candidates.length <= 50 && Number.isInteger(p.remaining) && p.remaining >= 0 && p.remaining <= 50)
      return { candidates: p.candidates.filter((c: unknown): c is ViewCandidate => !!c && typeof c === "object" && "azimuth_deg" in c), remaining: p.remaining };
  } catch { /* A corrupt local plan must not hide the tree evidence. */ }
  return { candidates: [], remaining: 2 };
}

export function MeasurementQualityPanel({tree,report,measures,update,onImport}: {
  tree: TreeRecord; report: ParkInventoryReport; measures: Record<string, FieldMeasure>;
  update: (id: string, patch: Partial<FieldMeasure>) => void; onImport?: () => void;
}) {
  const key = `arbor3d.rescan.${report.scan_id}.${tree.Tree_ID}`;
  const [plan,setPlan] = useState(() => readPlan(key));
  const [azimuth,setAzimuth] = useState(""); const [coverage,setCoverage] = useState(""); const [seconds,setSeconds] = useState("");
  const [safe,setSafe] = useState(false); const [message,setMessage] = useState("");
  const q = tree.measurement_quality;
  const field = measures[tree.Tree_ID];
  const ranked = rankViews(plan.candidates);
  const commit = (next: Plan) => {
    setPlan(next);
    try { localStorage.setItem(key, JSON.stringify(next)); setMessage("補掃計畫已保存在此裝置"); }
    catch { setMessage("裝置無法保存，請下載計畫備份"); }
  };
  const addCandidate = () => {
    const candidate = {azimuth_deg:Number(azimuth),new_coverage_deg:Number(coverage),time_s:Number(seconds),safe,reachable:safe};
    if (![azimuth,coverage,seconds].every(v=>v.trim()) || !rankViews([candidate]).length) {
      setMessage("請填入有效方向、規劃角度與時間，並先確認位置安全可達。"); return;
    }
    if (plan.candidates.length >= 50) {setMessage("最多保留 50 個候選，請先移除不用的位置。");return;}
    commit({...plan,candidates:[...plan.candidates,candidate]});setSafe(false);
  };
  return <section className="quality-panel" aria-label="品質與補掃">
    <div className="quality-heading"><p className="path-db-kicker">{tree.Tree_ID} · 品質證據 · 點左側樹號切換</p><h3>{qualityState(tree)}</h3>
      <p>像素、點數與角度需聯合實驗決定。YOLO 信心與 120° 均不代表胸徑精度已達標。</p></div>
    <p className="quality-summary-note">{tree.execution?.platform === "azure-app-service"
      ? `截面幾何與品質由 Azure 計算${tree.execution.completed_at ? `，完成於 ${new Date(tree.execution.completed_at).toLocaleString("zh-TW")}` : ""}。影像辨識與大型點雲前處理在本機執行。`
      : "本筆未記錄 Azure 截面計算證據；歷史資料不會自動改標為雲端成果。"}</p>
    <div className="quality-metrics">
      <div><span>截面有效點</span><strong>{q?.features?.effective_points ?? tree.num_slice_points ?? "未記錄"}</strong></div>
      <div><span>胸高像素寬</span><strong>{q?.features?.trunk_width_px != null ? `${q.features.trunk_width_px} px` : "未記錄"}</strong></div>
      <div><span>占用角度比例</span><strong>{q?.features?.occupied_fraction != null ? `${(q.features.occupied_fraction*100).toFixed(1)}%` : "未記錄"}</strong></div>
      <div><span>最大連續缺口</span><strong>{q?.features?.max_gap_deg != null ? `${q.features.max_gap_deg.toFixed(1)}°` : "未記錄"}</strong></div>
    </div>
    <div className="quality-card"><h4>方法與達標機率</h4>
      {(tree.quality_candidates?.length ? tree.quality_candidates : q ? [q] : []).map(c=><div key={c.method} className="quality-method">
        <strong>{c.method === "circle" ? "圓擬合" : "虛擬卡尺"} · {qualityAccepted(c) ? "可採用" : "待複核"}</strong>
        <p>{c.probability != null ? `校準機率 ${(c.probability*100).toFixed(1)}%（容許誤差 ±${c.tolerance_cm ?? "未指定"} cm）` : "尚無可用的人工真值校準機率"}</p>
        <ul>{c.reasons.map(r=><li key={r}>{qualityReasons[r] ?? "模型或資料格式需複核"}</li>)}</ul>
      </div>)}
      {!q && <p>這份歷史盤點沒有校準紀錄，原始候選尺寸保留供查驗。重新處理掃描後才能取得新品質特徵。</p>}
      <p>最小像素／點數／角度：尚待同設備、同規範的真值實驗，現在不填推測門檻。卡尺須確認兩側切向邊界、尺度與方向，短弧弦寬不能直接當 DBH。</p>
    </div>
    <div className="quality-card"><h4>人工真值與校準資料</h4>
      <label className="field-measure"><span>人工胸徑（cm）</span><input inputMode="decimal" value={field?.dbhCm ?? ""} onChange={e=>update(tree.Tree_ID,{dbhCm:e.target.value})} /></label>
      <label className="field-measure"><span>量測日期</span><input type="date" value={field?.measuredAt ?? ""} onChange={e=>update(tree.Tree_ID,{measuredAt:e.target.value})} /></label>
      <label className="quality-check"><input type="checkbox" checked={field?.strict13m === true} onChange={e=>update(tree.Tree_ID,{strict13m:e.target.checked})}/>已確認是標準胸高的現場量測</label>
      <button className="ghost-btn" onClick={()=>downloadJson(qualityEvidence(report,measures),`${report.scan_id}-quality-evidence.json`)}>匯出全園校準證據</button>
      <p>匯出後須確認跨期固定樹號與互斥分組；只有真實、同日配對、特徵齊全的資料能建立模型。</p>
    </div>
    <div className="quality-card"><h4>安全補掃計畫</h4><p>先確認安全可達，再以「規劃補足角度 ÷ 作業時間」排序。這是涵蓋效益代理，不是精度增益預測或自動航線。</p>
      <div className="quality-inputs"><label>方向（0–359°）<input type="number" min="0" max="359" value={azimuth} onChange={e=>setAzimuth(e.target.value)}/></label>
        <label>規劃補足角度（°）<input type="number" min="1" max="360" value={coverage} onChange={e=>setCoverage(e.target.value)}/></label>
        <label>規劃時間（秒）<input type="number" min="1" value={seconds} onChange={e=>setSeconds(e.target.value)}/></label></div>
      <label className="quality-check"><input type="checkbox" checked={safe} onChange={e=>setSafe(e.target.checked)}/>操作者已確認位置與路徑安全可達；未知區域不列入</label>
      <button className="ghost-btn" onClick={addCandidate}>加入候選位置</button>
      <label className="field-measure"><span>剩餘補掃次數預算</span><input type="number" min="0" max="50" value={plan.remaining} onChange={e=>{const n=Number(e.target.value);if(Number.isInteger(n)&&n>=0&&n<=50)commit({...plan,remaining:n});}}/></label>
      {!plan.remaining ? <p className="red-banner">預算已用盡：停止補掃，轉人工複核。</p> : !ranked.length ? <p>沒有已確認的安全候選：先人工檢查，勿自動推算可飛位置。</p> : <ol>{ranked.map((c,i)=><li key={i}>{i===0 ? "優先建議：" : "備選："}{c.azimuth_deg}° · {c.new_coverage_deg}°／{c.time_s} 秒
        <button className="ghost-btn" aria-label={`移除 ${c.azimuth_deg} 度候選`} onClick={()=>commit({...plan,candidates:plan.candidates.filter(v=>v!==c && !(v.azimuth_deg===c.azimuth_deg&&v.time_s===c.time_s&&v.new_coverage_deg===c.new_coverage_deg))})}>移除</button></li>)}</ol>}
      <div className="quality-actions"><button className="ghost-btn" onClick={()=>downloadJson({schema_version:"arbor3d-rescan-1",scan_id:report.scan_id,tree_id:tree.Tree_ID,...plan,ranked,advisory_only:true},`${report.scan_id}-${tree.Tree_ID}-rescan.json`)}>下載補掃計畫</button>
        {onImport && <button className="ghost-btn" onClick={onImport}>匯入新掃描並重新評估</button>}</div>
      <p role="status">{message}</p>
    </div>
  </section>;
}
