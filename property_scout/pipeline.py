"""Search orchestration: run adapters, parse, filter, dedupe, persist, route.

This is the spine of the tool. It converts each source's ``RawListing`` into a
canonical :class:`Listing`, applies the hard filters, deduplicates across
sources, records first-seen / last-seen for age and availability tracking, and
sorts survivors into the four output buckets the call sheet needs:

    main               - qualifying listings
    age_unconfirmed    - pass everything else but age couldn't be established
    needs_verification - matched but unclear size or price
    dropped_since_last - previously exported, now let / withdrawn
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable, Dict, List, Optional

from .adapters import build_adapters
from .adapters.base import PoliteClient, SourceBlocked
from .age import determine_age
from .config import Config
from .db import Database
from .dedup import deduplicate
from .logging_config import get_logger
from .models import (
    DEFAULT_PROPERTY_TYPES,
    Listing,
    RawListing,
    make_listing_id,
)
from .parsers import (
    classify_property_type,
    detect_availability,
    detect_vat_basis,
    effective_rent_incl_vat,
    is_price_on_application,
    parse_price,
    parse_size_sqm,
)

log = get_logger("pipeline")

ProgressFn = Callable[[str, dict], None]

EXCLUDED_STATUSES = {"under_offer", "let", "coming_soon"}


@dataclass
class SourceReport:
    source: str
    display_name: str
    requests_made: int = 0
    listings_found: int = 0
    listings_passing: int = 0
    errors: List[str] = field(default_factory=list)
    blocked: bool = False
    skipped_paths: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    status: str = "ok"          # ok | blocked | error


@dataclass
class RunResult:
    area: str
    run_id: str
    started_at: datetime
    finished_at: Optional[datetime]
    filters: dict
    main: List[Listing] = field(default_factory=list)
    age_unconfirmed: List[Listing] = field(default_factory=list)
    needs_verification: List[Listing] = field(default_factory=list)
    dropped_since_last: List[dict] = field(default_factory=list)
    sources: List[SourceReport] = field(default_factory=list)
    inferred_dropped_count: int = 0
    stale_dropped_count: int = 0

    @property
    def sources_queried(self) -> List[str]:
        return [s.display_name for s in self.sources]

    @property
    def sources_blocked(self) -> List[str]:
        return [s.display_name for s in self.sources if s.blocked]

    def report_dict(self) -> dict:
        return {
            "area": self.area,
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "filters": self.filters,
            "totals": {
                "qualifying": len(self.main),
                "age_unconfirmed": len(self.age_unconfirmed),
                "needs_verification": len(self.needs_verification),
                "dropped_since_last_run": len(self.dropped_since_last),
                "stale_excluded": self.stale_dropped_count,
                "inferred_stale_excluded": self.inferred_dropped_count,
            },
            "sources": [
                {
                    "source": s.source,
                    "display_name": s.display_name,
                    "status": s.status,
                    "blocked": s.blocked,
                    "requests_made": s.requests_made,
                    "listings_found": s.listings_found,
                    "listings_passing": s.listings_passing,
                    "skipped_paths": s.skipped_paths,
                    "errors": s.errors,
                    "duration_seconds": round(s.duration_seconds, 2),
                }
                for s in self.sources
            ],
        }


class Pipeline:
    def __init__(self, config: Config, db: Optional[Database] = None,
                 today: Optional[date] = None):
        self.config = config
        self.db = db or Database(config.db_path)
        self.today = today or date.today()

    # --- raw -> canonical ------------------------------------------------
    def _to_listing(self, raw: RawListing) -> Listing:
        now = datetime.now()
        listing_id = make_listing_id(raw.source, raw.source_listing_id)

        size, size_conf = parse_size_sqm(raw.size_text or raw.description)
        poa = is_price_on_application(raw.rent_text)
        rent = None if poa else parse_price(raw.rent_text)
        vat_text = " ".join([raw.rent_text or "", raw.description or "",
                             raw.additional_costs or ""])
        rent_basis = detect_vat_basis(vat_text)
        ptype = classify_property_type(raw.property_type_hint, raw.title, raw.description)
        availability = detect_availability(raw.availability_text or raw.title)

        first_seen = self.db.record_first_seen(listing_id, self.today)
        date_listed, dom, age_conf = determine_age(
            date_listed_text=raw.date_listed_text,
            date_updated_text=raw.date_updated_text,
            date_first_seen=first_seen,
            today=self.today,
        )

        flags: List[str] = []
        if poa:
            flags.append("price_on_application")
        if size_conf in ("parsed_from_text",):
            flags.append("size_uncertain")
        if availability == "unknown":
            flags.append("availability_uncertain")

        # VAT gross-up flag: excl-VAT rent whose real cost exceeds the limit.
        eff = effective_rent_incl_vat(rent, rent_basis)
        if (rent is not None and rent_basis == "excl_vat"
                and eff is not None and eff > self.config.default_max_rent >= rent):
            flags.append("vat_pushes_over_limit")

        return Listing(
            id=listing_id,
            source=raw.source,
            source_listing_id=str(raw.source_listing_id),
            url=raw.url,
            title=raw.title,
            property_type=ptype,
            monthly_rent=rent,
            rent_basis=rent_basis,
            additional_costs=raw.additional_costs,
            size_sqm=size,
            size_confidence=size_conf,
            address_raw=raw.address_raw,
            suburb=raw.suburb,
            city=raw.city,
            province=raw.province,
            latitude=raw.latitude,
            longitude=raw.longitude,
            agency_name=raw.agency_name,
            agent_name=raw.agent_name,
            agent_phone=raw.agent_phone,
            agent_email=raw.agent_email,
            date_listed=date_listed,
            date_first_seen=first_seen,
            days_on_market=dom,
            age_confidence=age_conf,
            availability_status=availability,
            last_seen=now,
            date_scraped=now,
            description=raw.description,
            image_url=raw.image_url,
            flags=flags,
        )

    # --- filtering / routing --------------------------------------------
    def _route(self, listing: Listing, max_rent: int, min_size: int,
               allowed_types: set, result: RunResult) -> None:
        # 1. Availability - exclude anything not currently on the market.
        if listing.availability_status in EXCLUDED_STATUSES:
            return
        # 2. Property type.
        if listing.property_type not in allowed_types:
            return
        # 3. Unclear price -> Needs Verification.
        if listing.monthly_rent is None:
            result.needs_verification.append(listing)
            return
        # 4. Unclear size -> Needs Verification.
        if listing.size_sqm is None or listing.size_confidence == "unknown":
            result.needs_verification.append(listing)
            return
        # 5. Hard rent / size cut-offs.
        if listing.monthly_rent > max_rent:
            return
        if listing.size_sqm < min_size:
            return
        # 6. Age.
        max_age = self.config.max_listing_age_days
        conf = listing.age_confidence
        dom = listing.days_on_market
        if conf == "unknown":
            if self.config.include_unknown_age_in_separate_section:
                result.age_unconfirmed.append(listing)
            else:
                result.main.append(listing)
            return
        if dom is not None and dom > max_age:
            if conf in ("stated", "first_seen"):
                result.stale_dropped_count += 1
                return
            if conf == "inferred":
                if self.config.exclude_inferred_age_over_limit:
                    result.inferred_dropped_count += 1
                    return
        result.main.append(listing)

    # --- availability re-check of last run's exports --------------------
    def _recheck_dropped(self, area: str, client: PoliteClient,
                         current_ids: set, result: RunResult) -> None:
        if not self.config.recheck_previously_exported_listings:
            return
        prev_ids = self.db.previously_exported_ids(area)
        now = datetime.now()
        for lid in prev_ids:
            if lid in current_ids:
                continue  # still live, seen this run
            row = self.db.get_listing(lid)
            if not row or not row.get("url"):
                continue
            url = row["url"]
            try:
                res = client.get(url, use_cache=False)
            except SourceBlocked:
                continue
            gone = res.status_code in (404, 410)
            redirected_to_search = "/results" in res.url or "search" in res.url.lower()
            status = detect_availability(res.text[:4000]) if res.text else "unknown"
            if gone or redirected_to_search or status in EXCLUDED_STATUSES:
                self.db.mark_status(lid, "let", now)
                result.dropped_since_last.append({
                    "id": lid,
                    "title": row.get("title", ""),
                    "agency_name": row.get("agency_name", ""),
                    "suburb": row.get("suburb", ""),
                    "url": url,
                    "reason": "404/410" if gone else ("redirected" if redirected_to_search else status),
                })

    # --- main entry ------------------------------------------------------
    def run(
        self,
        area: str,
        max_rent: Optional[int] = None,
        min_size_sqm: Optional[int] = None,
        radius_km: Optional[int] = None,
        include_residential: bool = False,
        only_sources: Optional[List[str]] = None,
        progress: Optional[ProgressFn] = None,
    ) -> RunResult:
        max_rent = max_rent or self.config.default_max_rent
        min_size = min_size_sqm or self.config.default_min_size_sqm
        allowed_types = set(DEFAULT_PROPERTY_TYPES)
        if include_residential:
            allowed_types.add("residential")

        run_id = uuid.uuid4().hex[:12]
        result = RunResult(
            area=area, run_id=run_id, started_at=datetime.now(), finished_at=None,
            filters={
                "max_rent": max_rent, "min_size_sqm": min_size,
                "radius_km": radius_km, "include_residential": include_residential,
                "max_listing_age_days": self.config.max_listing_age_days,
            },
        )

        client = PoliteClient(self.config)
        adapters = build_adapters(self.config, only=only_sources, client=client)

        def emit(event: str, **data):
            if progress:
                progress(event, data)

        emit("run_start", area=area, sources=[a.display_name for a in adapters])

        all_candidates: List[Listing] = []
        for adapter in adapters:
            sr = SourceReport(source=adapter.name, display_name=adapter.display_name)
            emit("source_start", source=adapter.display_name)
            t0 = time.monotonic()
            try:
                raws = adapter.search(
                    area, max_rent, min_size, radius_km,
                    include_residential=include_residential,
                )
            except SourceBlocked as exc:
                sr.blocked = True
                sr.status = "blocked"
                sr.errors.append(str(exc))
                raws = []
            except Exception as exc:  # a broken source must never kill the run
                sr.status = "error"
                sr.errors.append(repr(exc))
                log.exception("Adapter %s crashed", adapter.name)
                raws = []

            sr.duration_seconds = time.monotonic() - t0
            sr.requests_made = adapter.stats.requests_made
            sr.skipped_paths = adapter.stats.skipped_paths
            sr.errors.extend(adapter.stats.errors)
            if adapter.stats.blocked:
                sr.blocked = True
                if sr.status == "ok":
                    sr.status = "blocked"
            sr.listings_found = len(raws)

            for raw in raws:
                try:
                    all_candidates.append(self._to_listing(raw))
                except Exception as exc:
                    sr.errors.append(f"convert: {exc}")

            result.sources.append(sr)
            emit("source_done", source=adapter.display_name,
                 found=sr.listings_found, blocked=sr.blocked, status=sr.status)

        # Persist every candidate (incl. eventual duplicates) before routing.
        for l in all_candidates:
            self.db.upsert_listing(l)

        # Deduplicate across all sources, then route survivors.
        survivors = deduplicate(all_candidates)
        # Persist dedup outcome (also_listed_by / duplicate_of).
        for l in all_candidates:
            self.db.upsert_listing(l)

        for listing in survivors:
            self._route(listing, max_rent, min_size, allowed_types, result)

        # Count passing per source (for the report).
        passing_ids = {l.id for l in (result.main + result.age_unconfirmed + result.needs_verification)}
        per_source_pass: Dict[str, int] = {}
        for l in survivors:
            if l.id in passing_ids:
                per_source_pass[l.source] = per_source_pass.get(l.source, 0) + 1
        for sr in result.sources:
            sr.listings_passing = per_source_pass.get(sr.source, 0)

        # Re-check previously exported listings for this area.
        current_ids = {l.id for l in all_candidates}
        emit("recheck_start")
        self._recheck_dropped(area, client, current_ids, result)

        # Record what we're exporting so next run can compute "dropped since".
        export_ids = list(passing_ids)
        if export_ids:
            self.db.record_export(run_id, area, export_ids, datetime.now())

        client.close()
        result.finished_at = datetime.now()
        emit("run_done", qualifying=len(result.main),
             age_unconfirmed=len(result.age_unconfirmed),
             needs_verification=len(result.needs_verification))
        return result
