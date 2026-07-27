"""Deduplication tests."""
from datetime import date, datetime

from property_scout.dedup import deduplicate
from property_scout.models import Listing


def _listing(**kw) -> Listing:
    base = dict(
        id=kw.get("id", "x"), source=kw.get("source", "s"),
        source_listing_id="1", url="http://x", title="t",
        property_type="retail", monthly_rent=10000, rent_basis="excl_vat",
        additional_costs="", size_sqm=45.0, size_confidence="stated",
        address_raw="21 Pearce Street, Vincent", suburb="Vincent", city="East London",
        province="EC", latitude=None, longitude=None,
        agency_name="Agency A", agent_name=None, agent_phone=None, agent_email=None,
        date_listed=None, date_first_seen=date(2026, 7, 1), days_on_market=5,
        age_confidence="stated", availability_status="available",
        last_seen=datetime(2026, 7, 27), date_scraped=datetime(2026, 7, 27),
        description="", image_url=None,
    )
    base.update(kw)
    return Listing(**base)


def test_duplicates_collapse_and_keep_richest_contact():
    a = _listing(id="a", source="property24", agency_name="Agency A",
                 agent_phone=None, agent_email=None)
    b = _listing(id="b", source="pamgolding", agency_name="Agency B",
                 address_raw="Shop 4, 21 Pearce St, Vincent",  # same door, diff label
                 agent_phone="043 726 1234", agent_email="x@y.co.za",
                 monthly_rent=10500, size_sqm=46.0)  # within 10% / 5%
    survivors = deduplicate([a, b])
    assert len(survivors) == 1
    winner = survivors[0]
    assert winner.id == "b"  # richer contact wins
    assert "Agency A" in winner.also_listed_by
    assert a.duplicate_of == "b"


def test_non_duplicates_survive():
    a = _listing(id="a", address_raw="21 Pearce Street")
    b = _listing(id="b", address_raw="99 Oxford Road")
    survivors = deduplicate([a, b])
    assert len(survivors) == 2


def test_same_address_but_different_rent_not_merged():
    a = _listing(id="a", monthly_rent=5000)
    b = _listing(id="b", monthly_rent=12000)  # >10% apart
    survivors = deduplicate([a, b])
    assert len(survivors) == 2
