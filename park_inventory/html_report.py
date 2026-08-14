"""產出可在瀏覽器打開的公園盤點成果頁（DBH + 照片 + 3DGS）。"""
from __future__ import annotations

import html
from pathlib import Path


def _uri(path_str: str | None) -> str:
    if not path_str:
        return ""
    p = Path(path_str)
    if not p.is_absolute():
        p = p.resolve()
    if not p.exists():
        return ""
    return p.as_uri()


def _img(path_str: str | None, alt: str) -> str:
    uri = _uri(path_str)
    if not uri:
        return f'<p class="muted">{html.escape(alt)} 檔案不存在</p>'
    return f'<a href="{uri}" target="_blank"><img src="{uri}" alt="{html.escape(alt)}"></a>'


def write_html_report(report: dict, output_dir: Path) -> Path:
    trees = report.get("trees") or []
    cards = []
    for row in trees:
        note = row.get("DBH_note") or ""
        flag = "warn" if "wide_caliper" in note or "gap" in note else "ok"
        dbh = row.get("DBH_cm")
        dbh_txt = f"{dbh} cm" if dbh is not None else "—"
        method = row.get("DBH_method") or "—"
        arc = row.get("arc_coverage_deg")
        arc_txt = f"{arc}°" if arc is not None else "—"
        xyz = row.get("Local_XYZ_m")
        xyz_txt = ", ".join(str(v) for v in xyz) if isinstance(xyz, list) else "—"
        model_uri = _uri(row.get("3D_Model_Path") or row.get("Single_Tree_Ply"))
        photo_uri = _uri(row.get("Best_Photo"))
        model_link = (
            f'<a href="{model_uri}">打開 SuperSplat / 3DGS PLY</a>'
            if model_uri else '<span class="muted">尚無 3D 模型</span>'
        )
        photo_link = (
            f'<a href="{photo_uri}" target="_blank">原圖</a>'
            if photo_uri else '<span class="muted">無照片</span>'
        )
        cards.append(
            f"""
<article class="card {flag}">
  <h2>{html.escape(str(row.get("Tree_ID")))}</h2>
  <p class="dbh">{html.escape(dbh_txt)} <small>{html.escape(str(method))} · 弧度 {html.escape(arc_txt)}</small></p>
  <p class="note">註記：{html.escape(note or "ok")}</p>
  <p>座標 (m)：{html.escape(xyz_txt)}</p>
  <p>{photo_link} · {model_link}</p>
  <div class="thumbs">
    {_img(row.get("Mask_Path"), "YOLO 遮罩")}
    {_img(row.get("Cross_Section_Image"), "胸高剖面")}
  </div>
</article>
"""
        )

    map_png = output_dir / "tree_id_map_dbh.png"
    map_block = _img(str(map_png) if map_png.exists() else None, "DBH 俯視圖")
    body = "\n".join(cards) if cards else "<p>沒有樹木紀錄。</p>"
    page = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>公園樹木盤點 {html.escape(str(report.get("scan_id") or ""))}</title>
<style>
body {{ font-family: "Microsoft JhengHei", sans-serif; margin: 24px; background: #f4f1ea; color: #1d1d1d; }}
h1 {{ margin-bottom: 4px; }}
.meta {{ color: #555; margin-bottom: 24px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }}
.card {{ background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
.card.warn {{ border-left: 6px solid #c0392b; }}
.card.ok {{ border-left: 6px solid #1e8449; }}
.dbh {{ font-size: 28px; margin: 8px 0; }}
.note, .muted {{ color: #666; font-size: 13px; }}
.thumbs img {{ width: 100%; max-height: 180px; object-fit: contain; background: #111; border-radius: 8px; margin-top: 8px; }}
.map img {{ max-width: 720px; width: 100%; background: #fff; border-radius: 12px; }}
a {{ color: #1a5276; }}
</style>
</head>
<body>
<h1>公園樹木盤點</h1>
<p class="meta">掃描 {html.escape(str(report.get("scan_id") or ""))} · {report.get("num_trees", 0)} 棵 · {html.escape(str(report.get("created_at") or ""))}<br>
圓擬合用於弧度 ≥ 120°；不足則用虛擬卡尺。紅色邊框 = 寬卡尺，建議之後現場核對。</p>
<div class="map">{map_block}</div>
<div class="grid">
{body}
</div>
</body>
</html>
"""
    out = output_dir / "park_inventory_report.html"
    out.write_text(page, encoding="utf-8")
    print(f"成果頁 HTML: {out}")
    return out
