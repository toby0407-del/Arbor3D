import * as React from "react";
import type { ParkInventoryReport, TreeRecord } from "../types";
import { downloadJson, qualityReasons } from "../lib/measurementQuality";
import { scanAssetUrl } from "../lib/scanMedia";

export function RescanPanel({tree, report}: {tree: TreeRecord; report: ParkInventoryReport}) {
  const [showLayer, setShowLayer] = React.useState(true);
  const plan = tree.rescan_plan;
  const required = report.trees.filter(t => t.rescan_plan?.required);
  const unknown = report.trees.filter(t => !t.rescan_plan).length;
  const overlay = scanAssetUrl(report.scan_id, tree.Rescan_Overlay_Image);
  const original = scanAssetUrl(report.scan_id, tree.Cross_Section_Image);
  return <section className="quality-card rescan-panel" aria-label={`${tree.Tree_ID} 補測範圍`}>
    <h4>{tree.Tree_ID} · 補測範圍</h4>
    <p>本批待處理 {required.length} 棵{unknown > 0 ? ` · ${unknown} 棵尚未評估補測區域` : ""}</p>
    {!plan ? <p>尚無這棵樹的截面缺口紀錄；重新量測後產生圖層。</p>
      : !plan.required ? <p>本次品質已通過，無需新增補測任務。</p>
      : <>
        {plan.sectors.length ? <>
          <p><strong>{plan.sectors.length} 個缺口區域 · 合計 {plan.minimum_scope_deg}°</strong></p>
          <p>先補區域 1，再重新評估；達標即停止，不必一次補完所有缺口。</p>
          <details><summary>範圍計算方式</summary><p>以 {plan.bin_deg}° 分箱，只標示未覆蓋表面；橘色為待補測區域。這是完整涵蓋的最小缺失集合，並非精度達標所需的最小掃描角度。</p></details>
          <ol>{plan.sectors.map((s,i) => <li key={s.start_deg}>區域 {i+1}：{s.start_deg}° → {s.end_deg}°（{s.span_deg}°）{i===0 ? ` · 優先觀測方向 ${s.view_local_deg}°` : ""}</li>)}</ol>
          <p>角度以截面局部 +X 為 0°、逆時針增加，尚未轉為地理方位。觀測方向為缺口中心線，現場須確認能看見目標表面與安全可達的位置。</p>
          {overlay ? <>
            <label className="quality-check"><input type="checkbox" checked={showLayer} onChange={e=>setShowLayer(e.target.checked)}/>顯示補測圖層</label>
            <a href={(showLayer ? overlay : original) ?? overlay} target="_blank" rel="noreferrer" title="開啟完整補測圖">
              <img src={(showLayer ? overlay : original) ?? overlay} alt={`${tree.Tree_ID} 原始截面與橘色補測區域`} style={{width:"100%", height:"auto", borderRadius:8}}/>
            </a>
            <a className="ghost-btn" href={overlay} download={`${report.scan_id}-${tree.Tree_ID}-rescan.svg`}>下載補測圖</a>
          </> : <p>已記錄缺口，但沒有可配準的原始截面圖；不在未知位置疊加圖層。</p>}
        </> : <p>目前無法定位可信的角度缺口。請確認胸高、尺度、截面中心與影像邊界；點數不足或缺少校準也需人工處理。</p>}
        <details><summary>本次待確認項目</summary><ul>{plan.reasons.map(r=><li key={r}>{qualityReasons[r] ?? r}</li>)}</ul></details>
        <p>完成補測後重新量測並通過品質判斷，系統才會清除此任務；圖層不代表可飛航線。</p>
        <button className="ghost-btn" onClick={()=>downloadJson({scan_id:report.scan_id,tree_id:tree.Tree_ID,...plan},`${report.scan_id}-${tree.Tree_ID}-rescan.json`)}>下載此樹補測任務</button>
      </>}
    <button className="ghost-btn" onClick={()=>downloadJson({scan_id:report.scan_id,required_tree_count:required.length,unassessed_tree_count:unknown,tasks:required.map(t=>({tree_id:t.Tree_ID,local_xyz_m:t.Local_XYZ_m,plan:t.rescan_plan,overlay:t.Rescan_Overlay_Image}))},`${report.scan_id}-rescan-tasks.json`)}>下載全批補測清單</button>
  </section>;
}
