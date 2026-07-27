"""Command-line entry point.

    python -m property_scout search --area "East London" --max-rent 12000 \
        --min-size 25 --out ./exports/

Also:
    python -m property_scout serve            # launch the web UI
    python -m property_scout smoke            # adapter smoke test
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .logging_config import setup_logging
from .pipeline import Pipeline
from .exporters import export_docx, export_xlsx, write_json_report, console_summary


def _cli_progress(event: str, data: dict) -> None:
    if event == "source_start":
        print(f"  … querying {data['source']}")
    elif event == "source_done":
        tag = "BLOCKED" if data.get("blocked") else data.get("status", "ok").upper()
        print(f"  ✓ {data['source']}: {data['found']} found [{tag}]")
    elif event == "recheck_start":
        print("  … re-checking previously exported listings")


def cmd_search(args) -> int:
    config = load_config(args.config)
    setup_logging(config.log_path)

    out_dir = Path(args.out) if args.out else config.export_path
    pipeline = Pipeline(config)

    only = args.sources.split(",") if args.sources else None
    print(f"Searching '{args.area}' …")
    result = pipeline.run(
        area=args.area,
        max_rent=args.max_rent,
        min_size_sqm=args.min_size,
        radius_km=args.radius,
        include_residential=args.include_residential,
        only_sources=only,
        progress=_cli_progress,
    )

    print("\n" + console_summary(result))

    docx_path = export_docx(result, out_dir)
    xlsx_path = export_xlsx(result, out_dir)
    json_path = write_json_report(result, out_dir)

    print(f"\nCall sheet : {docx_path}")
    print(f"Spreadsheet: {xlsx_path}")
    print(f"Run report : {json_path}")
    return 0


def cmd_serve(args) -> int:
    import uvicorn
    print(f"Starting Property Scout web UI on http://{args.host}:{args.port}")
    uvicorn.run("property_scout.web.app:app", host=args.host, port=args.port,
                reload=args.reload)
    return 0


def cmd_smoke(args) -> int:
    from .smoke import run_smoke
    config = load_config(args.config)
    setup_logging(config.log_path)
    only = args.sources.split(",") if args.sources else None
    return run_smoke(config, area=args.area, only=only)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="property_scout",
                                description="SA rental sourcing tool")
    p.add_argument("--config", default=None, help="path to config.yaml")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="run a search and export documents")
    s.add_argument("--area", required=True, help='e.g. "East London, Eastern Cape"')
    s.add_argument("--max-rent", type=int, default=None, dest="max_rent")
    s.add_argument("--min-size", type=int, default=None, dest="min_size")
    s.add_argument("--radius", type=int, default=None, help="radius in km")
    s.add_argument("--include-residential", action="store_true",
                   dest="include_residential")
    s.add_argument("--sources", default=None,
                   help="comma-separated subset of sources")
    s.add_argument("--out", default=None, help="output directory")
    s.set_defaults(func=cmd_search)

    sv = sub.add_parser("serve", help="launch the web UI")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8000)
    sv.add_argument("--reload", action="store_true")
    sv.set_defaults(func=cmd_serve)

    sm = sub.add_parser("smoke", help="verify each source still parses")
    sm.add_argument("--area", default="East London, Eastern Cape")
    sm.add_argument("--sources", default=None)
    sm.set_defaults(func=cmd_smoke)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
