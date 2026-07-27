"""SQLite persistence.

Single-file DB, no server. Two responsibilities beyond plain CRUD:

* **First-seen tracking** - ``date_first_seen`` is the earliest run that ever
  saw a listing id, which becomes our most trustworthy age signal over time.
* **Availability history** - ``last_seen`` and ``availability_status`` let us
  detect listings that have dropped off since a previous export.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .models import Listing


SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id                  TEXT PRIMARY KEY,
    source              TEXT NOT NULL,
    source_listing_id   TEXT NOT NULL,
    url                 TEXT,
    title               TEXT,
    property_type       TEXT,
    monthly_rent        INTEGER,
    rent_basis          TEXT,
    additional_costs    TEXT,
    size_sqm            REAL,
    size_confidence     TEXT,
    address_raw         TEXT,
    suburb              TEXT,
    city                TEXT,
    province            TEXT,
    latitude            REAL,
    longitude           REAL,
    agency_name         TEXT,
    agent_name          TEXT,
    agent_phone         TEXT,
    agent_email         TEXT,
    date_listed         TEXT,
    date_first_seen     TEXT,
    days_on_market      INTEGER,
    age_confidence      TEXT,
    availability_status TEXT,
    last_seen           TEXT,
    date_scraped        TEXT,
    description         TEXT,
    image_url           TEXT,
    duplicate_of        TEXT,
    also_listed_by      TEXT,
    flags               TEXT
);

-- Every id ever seen and the first run date we saw it. This is the source of
-- truth for first-seen age inference and never gets rows deleted.
CREATE TABLE IF NOT EXISTS first_seen (
    id              TEXT PRIMARY KEY,
    date_first_seen TEXT NOT NULL
);

-- Which listing ids appeared in each export, so we can compute "dropped since
-- last run".
CREATE TABLE IF NOT EXISTS export_history (
    run_id      TEXT NOT NULL,
    listing_id  TEXT NOT NULL,
    area        TEXT,
    exported_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_listings_source ON listings(source);
CREATE INDEX IF NOT EXISTS idx_listings_avail ON listings(availability_status);
CREATE INDEX IF NOT EXISTS idx_export_area ON export_history(area);
"""


class Database:
    def __init__(self, path: Path | str):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    # --- first-seen ------------------------------------------------------
    def record_first_seen(self, listing_id: str, today: date) -> date:
        """Insert ``listing_id`` if new; return the stored first-seen date."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT date_first_seen FROM first_seen WHERE id = ?", (listing_id,)
            ).fetchone()
            if row:
                return date.fromisoformat(row["date_first_seen"])
            conn.execute(
                "INSERT INTO first_seen (id, date_first_seen) VALUES (?, ?)",
                (listing_id, today.isoformat()),
            )
            return today

    def get_first_seen(self, listing_id: str) -> Optional[date]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT date_first_seen FROM first_seen WHERE id = ?", (listing_id,)
            ).fetchone()
        return date.fromisoformat(row["date_first_seen"]) if row else None

    # --- listings --------------------------------------------------------
    def upsert_listing(self, listing: Listing) -> None:
        row = listing.to_row()
        cols = list(row.keys())
        placeholders = ",".join("?" for _ in cols)
        updates = ",".join(f"{c}=excluded.{c}" for c in cols if c != "id")
        sql = (
            f"INSERT INTO listings ({','.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}"
        )
        with self._conn() as conn:
            conn.execute(sql, [row[c] for c in cols])

    def upsert_many(self, listings: Iterable[Listing]) -> None:
        for l in listings:
            self.upsert_listing(l)

    def get_listing(self, listing_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM listings WHERE id = ?", (listing_id,)
            ).fetchone()
        return dict(row) if row else None

    def mark_status(self, listing_id: str, status: str, last_seen: datetime) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE listings SET availability_status = ?, last_seen = ? WHERE id = ?",
                (status, last_seen.isoformat(), listing_id),
            )

    # --- export history --------------------------------------------------
    def record_export(self, run_id: str, area: str, listing_ids: Iterable[str],
                      when: datetime) -> None:
        with self._conn() as conn:
            conn.executemany(
                "INSERT INTO export_history (run_id, listing_id, area, exported_at) "
                "VALUES (?, ?, ?, ?)",
                [(run_id, lid, area, when.isoformat()) for lid in listing_ids],
            )

    def previously_exported_ids(self, area: str) -> List[str]:
        """Ids exported in the most recent prior run for ``area``."""
        with self._conn() as conn:
            last = conn.execute(
                "SELECT run_id FROM export_history WHERE area = ? "
                "ORDER BY exported_at DESC LIMIT 1",
                (area,),
            ).fetchone()
            if not last:
                return []
            rows = conn.execute(
                "SELECT DISTINCT listing_id FROM export_history "
                "WHERE area = ? AND run_id = ?",
                (area, last["run_id"]),
            ).fetchall()
        return [r["listing_id"] for r in rows]
