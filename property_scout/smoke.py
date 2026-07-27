"""Adapter smoke test.

Hits each enabled source once for a known area and reports whether it still
returns parseable results. This is how we find out a site changed its layout:
a source that suddenly returns 0 (while others work) or gets BLOCKED shows up
here immediately.

Run: ``python -m property_scout smoke --area "East London, Eastern Cape"``
"""
from __future__ import annotations

from typing import List, Optional

from .adapters import build_adapters
from .adapters.base import PoliteClient, SourceBlocked
from .config import Config
from .logging_config import get_logger

log = get_logger("smoke")


def run_smoke(config: Config, area: str, only: Optional[List[str]] = None) -> int:
    client = PoliteClient(config)
    adapters = build_adapters(config, only=only, client=client)
    print(f"Smoke test - area '{area}', {len(adapters)} sources\n")
    print(f"{'Source':<26} {'Status':<10} {'Found':<7} Notes")
    print("-" * 70)

    exit_code = 0
    for adapter in adapters:
        status, found, note = "OK", 0, ""
        try:
            raws = adapter.search(area, config.default_max_rent,
                                  config.default_min_size_sqm, None,
                                  include_residential=False)
            found = len(raws)
            if adapter.stats.blocked:
                status, note = "BLOCKED", "bot wall / 403"
                exit_code = max(exit_code, 2)
            elif found == 0:
                status, note = "ZERO", "no listings parsed - check selectors"
                exit_code = max(exit_code, 1)
            else:
                # Sanity: did we parse anything useful out of the first result?
                sample = raws[0]
                bits = [b for b in (sample.rent_text, sample.size_text,
                                    sample.title) if b]
                note = f"e.g. {sample.title[:40]!r}" if bits else "parsed but empty fields"
        except SourceBlocked as exc:
            status, note = "BLOCKED", str(exc)[:40]
            exit_code = max(exit_code, 2)
        except Exception as exc:  # noqa: BLE001
            status, note = "ERROR", repr(exc)[:40]
            exit_code = max(exit_code, 3)
        print(f"{adapter.display_name:<26} {status:<10} {found:<7} {note}")

    client.close()
    print("\nExit code:", exit_code,
          "(0=all ok, 1=a source returned zero, 2=blocked, 3=error)")
    return exit_code
