"""Core data models for Property Scout.

Two record shapes exist:

* ``RawListing`` - what an adapter emits straight from a source page. Fields are
  best-effort and may be missing; the pipeline is responsible for parsing,
  normalising and enriching them.
* ``Listing`` - the canonical, fully-parsed record persisted to SQLite and used
  by exporters. Every field in the build spec lives here.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Optional


PROPERTY_TYPES = (
    "retail",
    "office",
    "commercial",
    "industrial",
    "medical",
    "residential",
    "other",
)

# Property types that qualify by default (residential is opt-in via a toggle).
DEFAULT_PROPERTY_TYPES = (
    "retail",
    "office",
    "commercial",
    "medical",
    "other",
)


def make_listing_id(source: str, source_listing_id: str) -> str:
    """Stable hash of ``source`` + ``source_listing_id``.

    Deterministic so the same physical listing keeps the same primary key across
    runs, which is what first-seen / last-seen tracking relies on.
    """
    raw = f"{source.strip().lower()}::{str(source_listing_id).strip()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class RawListing:
    """Loosely-typed output of an adapter's ``search()``.

    Adapters fill in whatever they can extract from the page. Text fields such as
    ``rent_text`` / ``size_text`` are handed to the parsers downstream, so an
    adapter never needs to understand SA rent/size formatting itself.
    """

    source: str
    source_listing_id: str
    url: str
    title: str = ""
    # Raw, unparsed strings straight off the page.
    rent_text: str = ""
    size_text: str = ""
    property_type_hint: str = ""
    address_raw: str = ""
    suburb: str = ""
    city: str = ""
    province: str = ""
    agency_name: str = ""
    agent_name: Optional[str] = None
    agent_phone: Optional[str] = None
    agent_email: Optional[str] = None
    description: str = ""
    image_url: Optional[str] = None
    # Age / availability signals as scraped.
    date_listed_text: str = ""          # visible or JSON-LD published date
    date_updated_text: str = ""         # "updated"/"refreshed" fallback
    availability_text: str = ""         # status words found on the page
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    additional_costs: str = ""
    # Free-form bag for anything an adapter wants to stash for debugging.
    extra: dict = field(default_factory=dict)


@dataclass
class Listing:
    """Canonical listing record - one row per physical unit per source."""

    id: str
    source: str
    source_listing_id: str
    url: str
    title: str
    property_type: str
    monthly_rent: Optional[int]
    rent_basis: str                     # "incl_vat" | "excl_vat" | "unknown"
    additional_costs: str
    size_sqm: Optional[float]
    size_confidence: str                # "stated" | "parsed_from_text" | "estimated" | "unknown"
    address_raw: str
    suburb: str
    city: str
    province: str
    latitude: Optional[float]
    longitude: Optional[float]
    agency_name: str
    agent_name: Optional[str]
    agent_phone: Optional[str]
    agent_email: Optional[str]
    date_listed: Optional[date]
    date_first_seen: date
    days_on_market: Optional[int]
    age_confidence: str                 # "stated" | "first_seen" | "inferred" | "unknown"
    availability_status: str            # "available" | "under_offer" | "let" | "unknown"
    last_seen: datetime
    date_scraped: datetime
    description: str
    image_url: Optional[str]
    duplicate_of: Optional[str] = None
    also_listed_by: str = ""            # semicolon-joined agency names of merged dups
    flags: list = field(default_factory=list)

    def to_row(self) -> dict:
        """Flat dict with ISO-formatted dates - used by exporters and the DB."""
        d = asdict(self)
        d["date_listed"] = self.date_listed.isoformat() if self.date_listed else None
        d["date_first_seen"] = self.date_first_seen.isoformat() if self.date_first_seen else None
        d["last_seen"] = self.last_seen.isoformat() if self.last_seen else None
        d["date_scraped"] = self.date_scraped.isoformat() if self.date_scraped else None
        d["flags"] = ";".join(self.flags) if self.flags else ""
        return d
