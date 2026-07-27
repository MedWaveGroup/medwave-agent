"""Listing-age determination.

Priority of evidence (strongest first):
  1. stated   - a genuine first-published date from JSON-LD / meta / visible text
  2. first_seen - the earliest run in which *we* ever saw this id
  3. inferred - an "updated"/"refreshed" date (agents game these)
  4. unknown  - nothing at all

The pipeline uses ``age_confidence`` to decide filtering behaviour; this module
only computes the number and the confidence label.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional, Tuple

from dateutil import parser as dateparser


_REL_RE = re.compile(
    r"(\d+)\s*(day|week|month|hour|min)", re.IGNORECASE
)


def _parse_date_text(text: str, today: date) -> Optional[date]:
    """Parse an absolute or relative date string into a ``date``."""
    if not text:
        return None
    text = text.strip()

    # Relative phrasing: "3 days ago", "listed 2 weeks ago", "today", "yesterday".
    low = text.lower()
    if "today" in low or "just now" in low or "hour" in low or "minute" in low:
        return today
    if "yesterday" in low:
        return date.fromordinal(today.toordinal() - 1)
    m = _REL_RE.search(low)
    if m and "ago" in low:
        n = int(m.group(1))
        unit = m.group(2).lower()
        days = {"day": 1, "week": 7, "month": 30}.get(unit, 0) * n
        if days:
            return date.fromordinal(today.toordinal() - days)

    # Absolute date - let dateutil handle the many SA formats. ISO dates
    # (YYYY-MM-DD) must NOT use dayfirst or the month/day get flipped; SA
    # DD/MM/YYYY dates do need dayfirst.
    dayfirst = not bool(re.search(r"\d{4}-\d{1,2}-\d{1,2}", text))
    try:
        dt = dateparser.parse(text, dayfirst=dayfirst, fuzzy=True,
                              default=datetime(today.year, 1, 1))
        return dt.date()
    except (ValueError, OverflowError, TypeError):
        return None


def determine_age(
    *,
    date_listed_text: str,
    date_updated_text: str,
    date_first_seen: date,
    today: date,
) -> Tuple[Optional[date], Optional[int], str]:
    """Return ``(date_listed, days_on_market, age_confidence)``.

    ``date_first_seen`` must already be resolved from the DB before calling.
    """
    # 1. Stated date.
    stated = _parse_date_text(date_listed_text, today)
    if stated and stated <= today:
        return stated, (today - stated).days, "stated"

    # 2. First-seen tracking. Only trustworthy once it predates today; on the
    #    very first run first_seen == today, which we still report but flag as
    #    weak by comparing to updated text below.
    first_seen_age = (today - date_first_seen).days
    if first_seen_age > 0:
        return date_first_seen, first_seen_age, "first_seen"

    # 3. Inference fallback from an "updated"/"refreshed" date.
    inferred = _parse_date_text(date_updated_text, today)
    if inferred and inferred <= today:
        return inferred, (today - inferred).days, "inferred"

    # First run and no stated/updated date at all: we saw it today for the first
    # time. days_on_market is 0 but we cannot vouch for it -> unknown.
    return None, None, "unknown"
