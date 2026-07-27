"""Listing-age determination tests."""
from datetime import date

from property_scout.age import determine_age


TODAY = date(2026, 7, 27)


def test_stated_date_wins():
    d, dom, conf = determine_age(
        date_listed_text="2026-07-05", date_updated_text="2026-07-20",
        date_first_seen=TODAY, today=TODAY,
    )
    assert conf == "stated"
    assert d == date(2026, 7, 5)
    assert dom == 22


def test_first_seen_used_when_no_stated_date():
    d, dom, conf = determine_age(
        date_listed_text="", date_updated_text="",
        date_first_seen=date(2026, 6, 1), today=TODAY,
    )
    assert conf == "first_seen"
    assert dom == 56


def test_inferred_from_updated_date():
    d, dom, conf = determine_age(
        date_listed_text="", date_updated_text="updated 2026-07-10",
        date_first_seen=TODAY, today=TODAY,
    )
    assert conf == "inferred"
    assert d == date(2026, 7, 10)


def test_unknown_when_first_run_and_no_dates():
    d, dom, conf = determine_age(
        date_listed_text="", date_updated_text="",
        date_first_seen=TODAY, today=TODAY,
    )
    assert conf == "unknown"
    assert d is None and dom is None


def test_relative_date_parsing():
    d, dom, conf = determine_age(
        date_listed_text="Listed 3 days ago", date_updated_text="",
        date_first_seen=TODAY, today=TODAY,
    )
    assert conf == "stated"
    assert dom == 3
