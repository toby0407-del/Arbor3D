import { useState } from 'react';
import type { ParkInventoryReport } from '../types';

export function QuarterlySimulation({ report }: { report: ParkInventoryReport }) {
  const [selected, setSelected] = useState(report.trees[0]?.Tree_ID ?? '');
  const tree = report.trees.find(t => t.Tree_ID === selected) ?? report.trees[0];
  const rows = tree?.quarterly_observations;
  if (!rows?.length) return null;
  const download = () => {
    const all = report.trees.flatMap(t => t.quarterly_observations ?? []);
    const keys = Object.keys(all[0]) as (keyof typeof all[0])[];
    const csv = '\ufeff' + [keys, ...all.map(r => keys.map(k => r[k]))]
      .map(r => r.map(v => `"${String(v).replaceAll('"', '""')}"`).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url; a.download = `${report.scan_id}-quarterly-SIMULATED.csv`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <details className="quarterly-simulation">
    <summary>四年季度模擬紀錄 · 2022 Q3–2026 Q2 · 16 季</summary>
    <p>人工胸徑、AI 胸徑、樹高、固定樹號及位置均為合成情境，非現場量測；不能用來驗證真實精度或判斷樹木健康。</p>
    <label>選擇季度樹號 <select value={tree.Tree_ID} onChange={e => setSelected(e.target.value)}>
      {report.trees.map(t => <option key={t.Tree_ID}>{t.Tree_ID}</option>)}
    </select></label>{' '}
    <button type="button" className="ghost-btn" onClick={download}>匯出全園季度模擬 CSV</button>
    <p>模擬固定樹號：{rows[0].persistent_tree_id}</p>
    <p>模擬座標：{rows[0].simulated_latitude}, {rows[0].simulated_longitude} · 胸徑量測高度假設 1.3 m</p>
    <div className="quarterly-table-scroll"><table>
      <thead><tr><th>季度／模擬日期</th><th>模擬人工 DBH (cm)</th><th>模擬 AI DBH (cm)</th><th>AI 季增量 (cm)</th><th>模擬樹高 (m)</th></tr></thead>
      <tbody>{rows.map((r, i) => <tr key={r.quarter}>
        <td>{r.quarter} / {r.date}</td><td>{r.simulated_manual_dbh_cm.toFixed(2)}</td>
        <td>{r.simulated_ai_dbh_cm.toFixed(2)}</td>
        <td>{i ? (r.simulated_ai_dbh_cm - rows[i - 1].simulated_ai_dbh_cm).toFixed(2) : '—'}</td>
        <td>{r.simulated_height_m.toFixed(2)}</td>
      </tr>)}</tbody>
    </table></div>
  </details>;
}
