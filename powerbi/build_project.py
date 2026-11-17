"""Generate a local PBIP/PBIR draft; never publish or claim Desktop validation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

BASE = "https://developer.microsoft.com/json-schemas/fabric/"


def schema(name, version="2.0.0"):
    return BASE + f"item/report/definition/{name}/{version}/schema.json"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def field(table, name, measure=False):
    return {"field": {"Measure" if measure else "Column": {
        "Expression": {"SourceRef": {"Entity": table}}, "Property": name}},
        "queryRef": f"{table}.{name}", "nativeQueryRef": name}


def literal(value):
    return {"expr": {"Literal": {"Value": "'" + value.replace("'", "''") + "'"}}}


def visual(name, kind, title, x, y, w, h, roles):
    return {"$schema": schema("visualContainer"), "name": name,
        "position": {"x": x, "y": y, "z": y + x, "width": w, "height": h, "tabOrder": y + x},
        "visual": {"visualType": kind, "query": {"queryState": {
            role: {"projections": columns} for role, columns in roles.items()}},
            "visualContainerObjects": {"title": [{"properties": {
                "show": {"expr": {"Literal": {"Value": "true"}}}, "text": literal(title)}}]}}}


def generate(analytics, output, *, clean_titles=True):
    source, output = Path(analytics).resolve(), Path(output).resolve()
    snapshot = json.loads((source / "analytics.json").read_text(encoding="utf-8"))
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != "1.1":
        raise ValueError("Regenerate a v1.1 analytics snapshot")
    kinds = {row.get("dataset_kind") for row in snapshot["tables"]["DimScan"]}
    if len(kinds) != 1 or not kinds <= {"observed", "simulated"}:
        raise ValueError("Regenerate a v1.1 snapshot containing one explicit dataset_kind")
    simulated = kinds == {"simulated"}
    if manifest.get("dataset_kind") not in kinds:
        raise ValueError("Manifest and analytics dataset kind disagree")
    model = json.loads(Path(__file__).with_name("model.bim").read_text(encoding="utf-8"))
    for table in model["model"]["tables"]:
        name = table["name"]
        raw = (source / f"{name}.csv").read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest["files"].get(f"{name}.csv"):
            raise ValueError(f"Snapshot hash mismatch: {name}")
        with (source / f"{name}.csv").open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != [c["name"] for c in table["columns"]]:
                raise ValueError(f"CSV schema mismatch: {name}")
            if any(row["dataset_kind"] not in kinds for row in reader):
                raise ValueError(f"CSV dataset kind mismatch: {name}")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a new empty project directory; do not overwrite Desktop edits")
    parameter = source.as_posix().replace('"', '""')
    model["model"]["expressions"][0]["expression"] = f'"{parameter}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'
    if clean_titles:
        by_name={table['name']:table for table in model['model']['tables']}
        sites=json.loads((Path(__file__).resolve().parents[1]/'app/scenarios/parks/manifest.json').read_text(encoding='utf-8'))['sites']
        aliases={'fengchia':'逢甲大學'}
        for site in sites:
            aliases[site['siteId']]=site['parkName'];aliases[site['scanId']]=site['parkName']
        quote=lambda value:'"'+value.replace('"','""')+'"'
        cases=', '.join(quote(k)+', '+quote(v) for k,v in aliases.items())
        def column(table,name,expression):
            by_name[table]['columns'].append(dict(name=name,type='calculated',dataType='string',summarizeBy='none',expression=expression))
        column('DimScan','場址',f'SWITCH(DimScan[site_id], {cases}, DimScan[site_id])')
        column('DimScan','季度','FORMAT(DimScan[observed_at], "yyyy") & " Q" & FORMAT(ROUNDUP(MONTH(DimScan[observed_at])/3,0),"0")')
        column('FactGrowth','來源','SWITCH(FactGrowth[source], "ai", "演算法", "simulated_ai", "演算法", "measured", "參考數值", "simulated_measured", "參考數值", "未分類")')
        column('FactGrowth','方法','IF(CONTAINSSTRING(FactGrowth[method], "circle"), "圓擬合", IF(CONTAINSSTRING(FactGrowth[method], "caliper"), "虛擬卡尺", "參考量測"))')
        column('FactObservation','核對狀態','IF(FactObservation[review_required], "需核對", "正常")')
    write(output / "Arbor3D.pbip", {"$schema": BASE + "pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
        "artifacts": [{"report": {"path": "Arbor3D.Report"}}], "settings": {"enableAutoRecovery": True}})
    model_dir, report_dir = output / "Arbor3D.SemanticModel", output / "Arbor3D.Report"
    write(model_dir / "definition.pbism", {"$schema": BASE + "item/semanticModel/definitionProperties/1.0.0/schema.json", "version": "1.0"})
    write(model_dir / "model.bim", model)
    write(report_dir / "definition.pbir", {"$schema": BASE + "item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": "../Arbor3D.SemanticModel"}}})
    definition = report_dir / "definition"
    write(definition / "version.json", {"$schema": schema("versionMetadata", "1.0.0"), "version": "2.0.0"})
    write(definition / "report.json", {"$schema": schema("report"), "themeCollection": {}})
    prefix = "" if clean_titles else "模擬 DEMO｜" if simulated else "本機快照｜"
    labels = {'Observations':'觀測紀錄', 'Observed Trees':'樹木數', 'Review Observations':'建議人工核對',
              'Review Rate':'人工核對比例', 'Valid Pairs':'有效實測配對', 'MAE cm':'實測 MAE（cm）',
              'RMSE cm':'實測 RMSE（cm）', 'Bias cm':'實測 Bias（cm）', 'Demo Pairs':'情境配對數',
              'Demo MAE cm':'情境差異（cm）', 'Growth Records':'成長比較紀錄',
              'Mean Observed Delta cm':'平均胸徑變化（cm）', 'Estimated CO2 Snapshot ton':'候選 CO₂ 存量（t）',
              'Latest Review Trees':'最新一期需核對樹木', 'Latest Review Rate':'最新一期核對比例', 'Latest CO2 Snapshot ton':'最新一期候選 CO₂ 存量（t）'}
    measure = lambda name: field("FactObservation", name, True)
    specifications = [
        ("overview", "盤點總覽", ["Observed Trees", "Observations", "Latest Review Trees", "Latest Review Rate"],
         "FactObservation", ["local_tree_id", "auto_dbh_cm", "manual_dbh_cm", "review_reason", "dataset_kind"]),
        ("accuracy", "DBH 驗證（模擬不代表精度）", ["Valid Pairs", "MAE cm", "Demo Pairs", "Demo MAE cm"] if simulated else ["Valid Pairs", "MAE cm", "RMSE cm", "Bias cm"],
         "FactObservation", ["local_tree_id", "comparison_status", "error_cm", "ape_pct", "dataset_kind"]),
        ("growth", "季度比較", ["Growth Records", "Observed Trees"],
         "FactGrowth", ["tree_key", "from_date", "to_date", "source", "method", "delta_dbh_cm", "negative_change", "dataset_kind"]),
        ("quality", "資料品質與來源", ["Observed Trees", "Latest Review Trees", "Latest Review Rate"],
         "DimScan", ["scan_id", "observed_at", "source_file", "source_sha256", "dataset_kind"]),
        ("carbon", "碳存量分析", ["Latest CO2 Snapshot ton"],
         "FactEstimate", ["tree_key", "dbh_input_source", "height_source", "co2_equivalent_ton", "formula_version", "dataset_kind"]),
    ]
    pages = []
    for page_name, title, cards, table, columns in specifications:
        if clean_titles:
            title = {'accuracy':'胸徑比較','quality':'資料說明與來源'}.get(page_name,title)
            if page_name != 'quality':
                columns = [column for column in columns if column not in {'dataset_kind','review_reason','source','method','formula_version'}]
                if page_name=='overview':columns.append('核對狀態')
                if page_name=='growth':columns.extend(['來源','方法'])
                if page_name=='carbon':columns=[c for c in columns if c not in {'dbh_input_source','height_source'}]
            else:
                columns=['場址','季度','observed_at']
        pages.append(page_name)
        folder = definition / "pages" / page_name
        write(folder / "page.json", {"$schema": schema("page"), "name": page_name,
            "displayName": prefix + title, "displayOption": "FitToPage", "width": 1280, "height": 900})
        visuals = []
        for i, (name, column) in enumerate((("場址", "場址" if clean_titles else "site_id"), ("季度", "季度" if clean_titles else "scan_id"), ("日期", "observed_at"))):
            visuals.append(visual(f"filter{i}", "slicer", prefix + name, 20 + i * 415, 15, 400, 100,
                {"Values": [field("DimScan", column)]}))
        for i, name in enumerate(cards):
            card=visual(f"card{i}", "card", prefix + (labels.get(name,name) if clean_titles else name), 20 + i * 310, 135, 295, 130, {"Values": [measure(name)]})
            card['visual']['objects']={'categoryLabels':[{'properties':{'show':{'expr':{'Literal':{'Value':'false'}}}}}],
                'labels':[{'properties':{'labelDisplayUnits':{'expr':{'Literal':{'Value':'1D'}}}}}]}
            visuals.append(card)
        if page_name == "growth":
            for i, name in enumerate(("來源", "方法") if clean_titles else ("source", "method")):
                visuals.append(visual(f"growthfilter{i}", "slicer", prefix + name, 650 + i * 310, 135, 290, 130,
                    {"Values": [field("FactGrowth", name)]}))
        visuals.append(visual("details", "tableEx", prefix + title + "；資料不足時留白", 20, 290, 1240, 330,
            {"Values": [field(table, name) for name in columns]}))
        if page_name in ("overview", "growth"):
            visuals.append(visual("trend", "lineChart", prefix + "平均 DBH（cm）；使用樹號篩選比較單木", 20, 640, 940, 240,
                {"Category": [field("DimScan", "observed_at")], "Y": [measure("Average DBH cm")]}))
            visuals.append(visual("treefilter", "slicer", prefix + "固定樹號", 980, 640, 280, 240,
                {"Values": [field("DimTree", "persistent_tree_id")]}))
        for item in visuals:
            write(folder / "visuals" / item["name"] / "visual.json", item)
    write(definition / "pages" / "pages.json", {"$schema": schema("pagesMetadata", "1.0.0"), "pageOrder": pages, "activePageName": pages[0]})
    (output / "README.md").write_text("# Arbor3D Power BI 本機專案草稿\n\n"
        + ("**模擬 DEMO ONLY：非真實量測／精度／生長。**\n\n" if simulated else "真實來源快照；缺值保持空白。\n\n")
        + "在 Power BI Desktop 開啟 Arbor3D.pbip，啟用 PBIP/PBIR 支援後重新整理本機 CSV。\n"
        "移動資料夾後請修改 AnalyticsFolder 參數。未登入或發佈任何雲端。\n"
        "JSON/schema 驗證不等於 Desktop/DAX 引擎或版面驗收；請依 docs/microsoft/WINDOWS.md 驗收。\n",
        encoding="utf-8")
    return {"project": str(output / "Arbor3D.pbip"), "pages": len(pages), "dataset_kind": kinds.pop(), "desktop_validated": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analytics", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.analytics, args.out), indent=2))
