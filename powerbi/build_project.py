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


def generate(analytics, output):
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
    prefix = "模擬 DEMO｜" if simulated else "本機快照｜"
    measure = lambda name: field("FactObservation", name, True)
    specifications = [
        ("overview", "盤點總覽", ["Observations", "Observed Trees", "Review Observations", "Review Rate"],
         "FactObservation", ["local_tree_id", "auto_dbh_cm", "manual_dbh_cm", "review_reason", "dataset_kind"]),
        ("accuracy", "DBH 驗證（模擬不代表精度）", ["Valid Pairs", "MAE cm", "Demo Pairs", "Demo MAE cm"] if simulated else ["Valid Pairs", "MAE cm", "RMSE cm", "Bias cm"],
         "FactObservation", ["local_tree_id", "comparison_status", "error_cm", "ape_pct", "dataset_kind"]),
        ("growth", "季度比較", ["Growth Records", "Mean Observed Delta cm"],
         "FactGrowth", ["tree_key", "from_date", "to_date", "source", "method", "delta_dbh_cm", "negative_change", "dataset_kind"]),
        ("quality", "資料品質與來源", ["Observations", "Review Observations"],
         "DimScan", ["scan_id", "observed_at", "source_file", "source_sha256", "dataset_kind"]),
        ("carbon", "推估碳存量（非碳權）", ["Estimated CO2 Snapshot ton"],
         "FactEstimate", ["tree_key", "dbh_input_source", "height_source", "co2_equivalent_ton", "formula_version", "dataset_kind"]),
    ]
    pages = []
    for page_name, title, cards, table, columns in specifications:
        pages.append(page_name)
        folder = definition / "pages" / page_name
        write(folder / "page.json", {"$schema": schema("page"), "name": page_name,
            "displayName": prefix + title, "displayOption": "FitToPage", "width": 1280, "height": 900})
        visuals = []
        for i, (name, column) in enumerate((("場址", "site_id"), ("掃描季度", "scan_id"), ("日期", "observed_at"))):
            visuals.append(visual(f"filter{i}", "slicer", prefix + name, 20 + i * 415, 15, 400, 100,
                {"Values": [field("DimScan", column)]}))
        for i, name in enumerate(cards):
            visuals.append(visual(f"card{i}", "card", prefix + name, 20 + i * 310, 135, 295, 130, {"Values": [measure(name)]}))
        if page_name == "growth":
            for i, name in enumerate(("source", "method")):
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
