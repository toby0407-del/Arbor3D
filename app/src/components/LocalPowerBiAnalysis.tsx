import { useEffect, useState } from 'react';
import type { FieldMeasure } from '../hooks/useFieldMeasures';
import type { ParkInventoryReport } from '../types';
import { currentAnalyticsFingerprint, parseLocalPowerBi, type LocalPowerBiSnapshot } from '../lib/localPowerBi';

export function LocalPowerBiAnalysis({report, measures}: {report:ParkInventoryReport; measures:Record<string,FieldMeasure>}) {
  const [snapshot,setSnapshot] = useState<LocalPowerBiSnapshot|null>(null);
  const [fingerprint,setFingerprint] = useState('');
  const [error,setError] = useState('');
  const [revision,setRevision] = useState(0);
  const [loading,setLoading] = useState(true);
  useEffect(()=>{
    let active=true;
    setFingerprint('');
    void currentAnalyticsFingerprint(report,measures).then(v=>{if(active)setFingerprint(v);}).catch(()=>{if(active)setError('無法核對目前資料版本');});
    return ()=>{active=false;};
  },[report,measures]);
  useEffect(()=>{
    const controller=new AbortController();
    setLoading(true); setSnapshot(null); setError('');
    void fetch(`/analysis/${encodeURIComponent(report.scan_id)}.json?t=${Date.now()}`,{cache:'no-store',signal:controller.signal})
      .then(async response=>{
        if(response.status===404)return null;
        if(!response.ok)throw new Error();
        return parseLocalPowerBi(await response.json(),report);
      }).then(data=>{if(!controller.signal.aborted)setSnapshot(data);})
      .catch(()=>{if(!controller.signal.aborted)setError('無法載入本機分析結果，請稍後重試。');})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[report,revision]);
  const stale = snapshot && fingerprint && snapshot.input_fingerprint!==fingerprint;
  const display=(n:number|null,unit='')=>n===null?'—':`${n.toFixed(2)}${unit}`;
  return <section className="local-pbi" aria-label="Power BI 本機分析結果">
    <header><div><h3>Power BI 本機分析</h3><p>在此電腦計算，結果保存在 App；展示不需登入 Power BI。</p></div>
      <button className="ghost-btn" disabled={loading} onClick={()=>setRevision(n=>n+1)}>{loading?'讀取中…':'讀取更新結果'}</button></header>
    {error && <p role="alert">{error}</p>}
    {!loading&&!snapshot&&!error&&<p>此盤點尚未匯入 Desktop 分析結果；下方仍可查看即時計算圖表。</p>}
    {snapshot&&<>
      <p className="local-pbi-status" role="status">{stale?'資料已變更，以下保留上次分析，需重新整理 Desktop 並更新結果。':!fingerprint?'正在核對資料版本…':'已與目前資料版本核對一致'}</p>
      <div className="local-pbi-cards">
        <div><span>盤點樹木</span><strong>{snapshot.metrics.observations} 棵</strong></div>
        <div><span>建議人工核對</span><strong>{snapshot.metrics.review_count} 棵</strong></div>
        <div><span>有效實測配對</span><strong>{snapshot.metrics.paired_count} 組</strong></div>
        <div><span>胸徑 MAE</span><strong>{display(snapshot.metrics.mae_cm,' cm')}</strong></div>
        <div><span>平均 AI 胸徑</span><strong>{display(snapshot.metrics.average_dbh_cm,' cm')}</strong></div>
        <div><span>候選 CO₂ 存量試算</span><strong>{display(snapshot.metrics.co2_ton,' t')}</strong></div>
      </div>
      <details><summary>資料說明</summary><p>{snapshot.dataset_kind==='simulated'?`來源：模擬情境。情境配對 ${snapshot.metrics.demo_pairs??0} 組，情境差異 ${display(snapshot.metrics.demo_mae_cm,' cm')}；不計入實測精度。`:'來源：實際掃描與已同步的人工量測。'} CO₂ 數值為盤點估算。</p></details>
      <small>運算：Microsoft Power BI Desktop · {new Date(snapshot.calculated_at).toLocaleString('zh-TW')} · RMSE {display(snapshot.metrics.rmse_cm,' cm')}</small>
    </>}
  </section>;
}
