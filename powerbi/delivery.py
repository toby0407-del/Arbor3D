"""Build one evidence-preserving Analytics + Power BI delivery from an App bundle."""
import argparse
import json
from pathlib import Path

from analytics.core import build, export
from powerbi.build_project import generate as build_project


def deliver(bundle, site_id, output, *, identities=None, max_pair_days=0, schema_cache=None):
    bundle_path = Path(bundle).resolve()
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a new empty delivery directory; existing output is never overwritten")
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    report = payload["report"]
    manual = [dict(row, site_id=site_id) for row in payload.get("manual_measurements", [])]

    identity_rows = []
    if identities:
        from analytics.core import load_csv
        identity_rows = load_csv(identities)

    tables = build(
        [(site_id, str(bundle_path), report)],
        manual,
        identity_rows,
        max_pair_days,
    )
    analytics_dir = output / "analytics"
    project_dir = output / "powerbi"
    export(tables, analytics_dir, max_pair_days)
    project = build_project(analytics_dir, project_dir)
    schema = None
    if schema_cache:
        from powerbi.validate_project import validate as validate_project
        schema = validate_project(project_dir, schema_cache, download=False)
    result = {
        "bundle": str(bundle_path),
        "site_id": site_id,
        "dataset_kind": tables["Summary"][0]["dataset_kind"],
        "analytics": str(analytics_dir),
        "powerbi_project": project["project"],
        "pages": project["pages"],
        "schema_validation": schema,
        "desktop_validated": False,
        "notes": [
            "Canonical Analytics and PBIP/PBIR were generated from the same App bundle.",
            "Schema validation does not replace Power BI Desktop refresh, DAX, layout or RLS validation.",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "delivery-report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, help="App analytics-input JSON")
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--identities")
    parser.add_argument("--max-pair-days", type=int, default=0)
    parser.add_argument("--schema-cache", help="Existing offline Microsoft schema cache")
    args = parser.parse_args()
    try:
        print(json.dumps(deliver(
            args.bundle,
            args.site_id,
            args.out,
            identities=args.identities,
            max_pair_days=args.max_pair_days,
            schema_cache=args.schema_cache,
        ), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"Power BI delivery failed: {exc}\n")


if __name__ == "__main__":
    main()
