import argparse
import json
from pathlib import Path
from .core import build, export, load_csv

def main():
    parser = argparse.ArgumentParser(description="Arbor3D offline analytics, no cloud calls")
    parser.add_argument("--report", action="append", default=[], help="Repeat for multiple scans")
    parser.add_argument("--bundle", help="App analytics-input JSON including report and manual records")
    parser.add_argument("--site-id", required=True, help="Stable site identifier; one site per invocation")
    parser.add_argument("--manual", help="Manual CSV, or App analytics-input JSON bundle")
    parser.add_argument("--identities", help="Confirmed cross-scan identity CSV")
    parser.add_argument("--max-pair-days", type=int, default=0)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--allow-simulated",
        action="store_true",
        help="Allow dataset_kind=simulated reports (demo only; not field evidence)",
    )
    args = parser.parse_args()
    try:
        if not args.report and not args.bundle:
            raise ValueError("provide --report or --bundle")
        reports = [(args.site_id, path, json.loads(Path(path).read_text(encoding="utf-8"))) for path in args.report]
        if args.bundle:
            bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
            reports.append((args.site_id, args.bundle, bundle["report"]))
            if args.manual:
                raise ValueError("--bundle already contains manual data; do not pass --manual")
            manual = [dict(r, site_id=args.site_id) for r in bundle["manual_measurements"]]
        elif args.manual and args.manual.endswith(".json"):
            bundle = json.loads(Path(args.manual).read_text(encoding="utf-8"))
            manual = [dict(r, site_id=args.site_id) for r in bundle["manual_measurements"]]
        else:
            manual = load_csv(args.manual)
        tables = build(
            reports,
            manual,
            load_csv(args.identities),
            args.max_pair_days,
            allow_simulated=args.allow_simulated,
        )
        export(tables, args.out, args.max_pair_days)
        print(json.dumps(tables["Summary"][0], ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"Analytics validation failed: {exc}\n")

if __name__ == "__main__":
    main()
