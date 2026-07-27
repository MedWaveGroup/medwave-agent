"""Property24 adapter parsing test against a saved fixture.

Proves the adapter turns a real-shaped detail page into a fully-populated
RawListing without touching the network, and that the pipeline converts it into
a qualifying Listing.
"""
from datetime import date
from pathlib import Path

from property_scout.adapters.property24 import Property24Adapter
from property_scout.config import load_config
from property_scout.db import Database
from property_scout.pipeline import Pipeline

FIX = Path(__file__).parent / "fixtures"


def _adapter():
    cfg = load_config()
    return Property24Adapter(cfg)


def test_result_links_extracted():
    html = (FIX / "property24_results.html").read_text()
    links = _adapter()._result_detail_links(html)
    assert any(l.endswith("/12345") for l in links)
    assert any(l.endswith("/67890") for l in links)
    # pagination link must be ignored
    assert not any(l.endswith("/p2") for l in links)


def test_detail_parsing_populates_fields():
    html = (FIX / "property24_detail.html").read_text()
    url = "https://www.property24.com/commercial-property-to-rent/vincent/east-london/eastern-cape/12345"
    raw = _adapter().parse_detail(url, html)
    assert raw is not None
    assert raw.source_listing_id == "12345"
    assert "45" in raw.size_text
    assert "11" in raw.rent_text and "500" in raw.rent_text
    assert raw.agent_phone and "43" in raw.agent_phone
    assert raw.agent_email == "thabo@ecommercial.co.za"
    assert raw.agency_name == "EC Commercial Properties"
    assert "2026-07-05" in raw.date_listed_text
    assert "Vincent" in raw.address_raw


def test_pipeline_converts_fixture_to_qualifying(tmp_path):
    html = (FIX / "property24_detail.html").read_text()
    url = "https://www.property24.com/commercial-property-to-rent/vincent/east-london/eastern-cape/12345"
    raw = _adapter().parse_detail(url, html)

    cfg = load_config()
    db = Database(tmp_path / "t.db")
    pipe = Pipeline(cfg, db=db, today=date(2026, 7, 27))
    listing = pipe._to_listing(raw)

    assert listing.size_sqm == 45.0
    assert listing.monthly_rent == 11500
    assert listing.rent_basis == "excl_vat"
    assert listing.property_type in ("retail", "medical")
    assert listing.availability_status == "available"
    assert listing.age_confidence == "stated"
    assert listing.days_on_market == 22
    # excl VAT 11 500 -> 13 225 incl, over the 12 000 limit -> flagged.
    assert "vat_pushes_over_limit" in listing.flags
