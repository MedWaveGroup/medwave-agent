"""Tests for the size, price, VAT and address parsers - where the tool breaks."""
import pytest

from property_scout.parsers import (
    parse_size_sqm, parse_price, is_price_on_application,
    detect_vat_basis, effective_rent_incl_vat, normalise_address,
    classify_property_type, detect_availability,
)


# --- size -------------------------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("approx 45m2", 45.0),
    ("45 sqm", 45.0),
    ("45 m²", 45.0),
    ("45m² shop", 45.0),
    ("Floor Size: 45 m²", 45.0),
    ("1,250 m2 warehouse", 1250.0),
    ("45.5 square metres", 45.5),
    ("size 30 sq m", 30.0),
])
def test_size_extraction(text, expected):
    size, conf = parse_size_sqm(text)
    assert size == expected
    assert conf in ("stated", "parsed_from_text")


def test_size_never_sums_multiple_units():
    # Two 15 m² units must not be read as 30 m².
    size, _ = parse_size_sqm("Two units of 15 m2 and 15 m2 available")
    assert size == 15.0


def test_size_missing_returns_unknown():
    size, conf = parse_size_sqm("Lovely space, call for details")
    assert size is None and conf == "unknown"


def test_size_approx_is_parsed_not_stated():
    _, conf = parse_size_sqm("approx 45m2 in a long descriptive sentence here")
    assert conf == "parsed_from_text"


# --- price ------------------------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("R 12 000", 12000),
    ("R12,000", 12000),
    ("R12000 pm", 12000),
    ("R12 000 p/m excl VAT", 12000),
    ("R11 500 pm excl VAT", 11500),
    ("R8,750 per month", 8750),
])
def test_price_extraction(text, expected):
    assert parse_price(text) == expected


def test_price_on_application():
    assert is_price_on_application("Price on Application")
    assert is_price_on_application("Rental: POA")
    assert parse_price("Price on Application") is None


def test_price_picks_monthly_not_stray_small_number():
    assert parse_price("R12 000 pm, deposit R5") == 12000


# --- VAT --------------------------------------------------------------------
def test_vat_detection():
    assert detect_vat_basis("R11 500 excl VAT") == "excl_vat"
    assert detect_vat_basis("R11 500 plus VAT") == "excl_vat"
    assert detect_vat_basis("R11 500 incl VAT") == "incl_vat"
    assert detect_vat_basis("R11 500 pm") == "unknown"


def test_effective_rent_grosses_up_excl_vat():
    assert effective_rent_incl_vat(10000, "excl_vat") == 11500
    assert effective_rent_incl_vat(10000, "incl_vat") == 10000
    assert effective_rent_incl_vat(None, "excl_vat") is None


# --- address normalisation --------------------------------------------------
def test_address_normalisation_matches_variants():
    a = normalise_address("Shop 4, 21 Pearce Street, Vincent")
    b = normalise_address("Unit 4, 21 Pearce St., Vincent")
    assert a == b  # unit/shop prefix dropped, Street==St


def test_address_normalisation_abbreviates():
    assert normalise_address("10 Oxford Avenue") == "10 oxford ave"


# --- property type ----------------------------------------------------------
def test_property_type_classification():
    assert classify_property_type("Retail shop to let") == "retail"
    assert classify_property_type("Medical consulting room") == "medical"
    assert classify_property_type("Open plan office space") == "office"
    assert classify_property_type("2 bedroom apartment") == "residential"
    assert classify_property_type("Warehouse unit") == "industrial"


# --- availability -----------------------------------------------------------
def test_availability_detection():
    assert detect_availability("This property has been let") == "let"
    assert detect_availability("Under Offer") == "under_offer"
    assert detect_availability("Coming soon - register your interest") == "coming_soon"
    assert detect_availability("Retail shop to let, available now") == "available"
    assert detect_availability("") == "unknown"
