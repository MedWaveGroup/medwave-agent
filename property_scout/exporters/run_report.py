"""Run report - JSON file plus a console summary."""
from __future__ import annotations

import json
from pathlib import Path

from ..pipeline import RunResult


def write_json_report(result: RunResult, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_area = result.area.split(",")[0].strip().lower().replace(" ", "_")
    path = out_dir / f"run_report_{safe_area}_{result.run_id}.json"
    path.write_text(json.dumps(result.report_dict(), indent=2), encoding="utf-8")
    return path


def console_summary(result: RunResult) -> str:
    lines = []
    lines.append("=" * 68)
    lines.append(f"Property Scout run - {result.area}")
    lines.append(f"Run ID: {result.run_id}")
    lines.append("-" * 68)
    lines.append(f"  Qualifying listings   : {len(result.main)}")
    lines.append(f"  Age unconfirmed       : {len(result.age_unconfirmed)}")
    lines.append(f"  Needs verification    : {len(result.needs_verification)}")
    lines.append(f"  Dropped since last run: {len(result.dropped_since_last)}")
    lines.append(f"  Stale excluded        : {result.stale_dropped_count}"
                 f" (+{result.inferred_dropped_count} on inferred dates)")
    lines.append("-" * 68)
    lines.append("  Sources:")
    for s in result.sources:
        tag = s.status.upper()
        lines.append(
            f"    {s.display_name:<26} {tag:<8} "
            f"req={s.requests_made:<4} found={s.listings_found:<4} "
            f"pass={s.listings_passing:<4} {s.duration_seconds:.1f}s"
        )
        for err in s.errors[:2]:
            lines.append(f"        ! {err[:90]}")
    lines.append("=" * 68)
    return "\n".join(lines)
