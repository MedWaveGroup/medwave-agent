"""Property24 adapter - priority source #1.

Access method: HTML pages of the public commercial/residential *to-rent* search
and listing detail pages. Property24 exposes no public API; it does publish a
sitemap and rich JSON-LD on detail pages, which we prefer over scraping visible
text. See SOURCES.md for the robots.txt assessment.

Search URL shape (commercial to-rent), e.g. East London:
    https://www.property24.com/commercial-property-to-rent/east-london/eastern-cape/<id>

Because Property24's URL slugs require an internal location id, the adapter
resolves the area to a search results page, then walks the result cards to detail
pages. Every step is defensive: a layout change degrades to "0 results" rather
than a crash, and the smoke test (tests/test_adapter_smoke.py) catches that.
"""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import quote_plus, urljoin

from ..logging_config import get_logger
from ..models import RawListing
from .base import BaseAdapter, SourceBlocked
from . import htmlutil as H

log = get_logger("adapter.property24")

BASE = "https://www.property24.com"


def _slug(area: str) -> str:
    # "East London, Eastern Cape" -> "east-london"
    town = area.split(",")[0].strip().lower()
    town = re.sub(r"[^a-z0-9\s-]", "", town)
    return re.sub(r"\s+", "-", town)


class Property24Adapter(BaseAdapter):
    name = "property24"
    display_name = "Property24"

    def search_urls(self, area: str, include_residential: bool) -> List[str]:
        """Candidate search result pages for the area.

        We try the commercial to-rent section first (the primary target) and add
        the residential to-rent section only when the toggle is on.
        """
        slug = _slug(area)
        urls = [
            f"{BASE}/commercial-property-to-rent/{slug}",
            f"{BASE}/to-rent/{slug}/commercial",
        ]
        if include_residential:
            urls.append(f"{BASE}/to-rent/{slug}")
        return urls

    def _result_detail_links(self, html: str) -> List[str]:
        """Extract detail-page URLs from a search results page."""
        s = H.soup(html)
        links = set()
        # Property24 result cards link to /to-rent/.../<numeric-id> or
        # /commercial-property-to-rent/.../<numeric-id>.
        for a in s.find_all("a", href=True):
            href = a["href"].split("?")[0].split("#")[0]
            if re.search(r"/(?:to-rent|commercial-property-to-rent)/.+/\d{5,}$", href):
                links.add(urljoin(BASE, href))
        return sorted(links)

    def parse_detail(self, url: str, html: str) -> Optional[RawListing]:
        """Parse a single Property24 detail page into a RawListing."""
        s = H.soup(html)
        blocks = H.json_ld_blocks(s)
        ld = H.find_ld_type(blocks, "RealEstateListing", "Product", "Offer", "Residence") or {}

        # id from the URL tail.
        m = re.search(r"/(\d{5,})$", url)
        source_id = m.group(1) if m else url.rsplit("/", 1)[-1]

        title = (
            (ld.get("name") if isinstance(ld.get("name"), str) else "")
            or H.meta_content(s, "og:title")
            or (s.title.get_text(strip=True) if s.title else "")
        )

        # Price: combine JSON-LD, visible price and og description so the VAT
        # basis (often only in the visible/og text) survives even when the clean
        # numeric price comes from JSON-LD. parse_price picks the figure.
        rent_text = " ".join(filter(None, [
            _ld_price(ld), _visible_price(s), H.meta_content(s, "og:description"),
        ]))

        # Size: dedicated feature nodes then whole-page text.
        size_text = _size_text(s)

        description = (
            (ld.get("description") if isinstance(ld.get("description"), str) else "")
            or H.meta_content(s, "og:description")
            or _description_text(s)
        )

        # Address / location.
        address_raw, suburb, city, province = _address(ld, s)

        # Dates - stated first (JSON-LD datePosted/datePublished, meta), else text.
        date_listed_text = _stated_date(ld, s, html)
        date_updated_text = _updated_date(s, html)

        # Availability.
        availability_text = " ".join(filter(None, [
            title, _status_text(s), description[:400],
        ]))

        # Agent / agency.
        agency_name, agent_name, agent_phone, agent_email = _contacts(ld, s)

        image_url = H.meta_content(s, "og:image") or None
        lat, lon = _geo(ld)

        raw = RawListing(
            source=self.name,
            source_listing_id=source_id,
            url=url,
            title=title,
            rent_text=rent_text,
            size_text=size_text,
            property_type_hint=title + " " + description[:200],
            address_raw=address_raw,
            suburb=suburb,
            city=city,
            province=province,
            agency_name=agency_name,
            agent_name=agent_name,
            agent_phone=agent_phone,
            agent_email=agent_email,
            description=description,
            image_url=image_url,
            date_listed_text=date_listed_text,
            date_updated_text=date_updated_text,
            availability_text=availability_text,
            latitude=lat,
            longitude=lon,
        )
        return raw

    def search(
        self,
        area: str,
        max_rent: int,
        min_size_sqm: int,
        radius_km: Optional[int] = None,
        include_residential: bool = False,
    ) -> List[RawListing]:
        results: List[RawListing] = []
        detail_links: List[str] = []

        for search_url in self.search_urls(area, include_residential):
            try:
                res = self.fetch(search_url)
            except SourceBlocked as exc:
                self.stats.blocked = True
                self.stats.errors.append(str(exc))
                log.warning("Property24 blocked/skip on %s: %s", search_url, exc)
                continue
            if res.status_code >= 400:
                continue
            found = self._result_detail_links(res.text)
            log.info("Property24 %s -> %d detail links", search_url, len(found))
            detail_links.extend(found)

        # Dedupe detail links; cap to a sane number per run.
        seen = set()
        for url in detail_links:
            if url in seen:
                continue
            seen.add(url)
            try:
                res = self.fetch(url)
            except SourceBlocked as exc:
                self.stats.blocked = True
                self.stats.errors.append(str(exc))
                continue
            if res.status_code in (404, 410):
                continue
            try:
                raw = self.parse_detail(res.url, res.text)
            except Exception as exc:  # never let one page kill the source
                self.stats.errors.append(f"parse {url}: {exc}")
                continue
            if raw:
                results.append(raw)

        self.stats.listings_found = len(results)
        return results


# --- field extractors -------------------------------------------------------

def _ld_price(ld: dict) -> str:
    offers = ld.get("offers") if isinstance(ld, dict) else None
    if isinstance(offers, list) and offers:
        offers = offers[0]
    if isinstance(offers, dict):
        price = offers.get("price") or offers.get("lowPrice")
        cur = offers.get("priceCurrency", "R")
        if price:
            return f"{cur} {price}"
    return ""


def _visible_price(s) -> str:
    node = s.find(attrs={"class": re.compile(r"p24_price|price", re.IGNORECASE)})
    if node:
        return node.get_text(" ", strip=True)
    m = re.search(r"R\s?\d[\d\s,]{2,}", s.get_text(" ", strip=True))
    return m.group(0) if m else ""


def _size_text(s) -> str:
    # Property24 lists floor size in feature blocks.
    for node in s.find_all(attrs={"class": re.compile(r"size|floor|area|feature", re.IGNORECASE)}):
        txt = node.get_text(" ", strip=True)
        if re.search(r"m\s*(?:2|²)|sqm|sq\s*m", txt, re.IGNORECASE):
            return txt
    # Fall back to whole page text; parser picks the largest single figure.
    return s.get_text(" ", strip=True)


def _description_text(s) -> str:
    node = s.find(attrs={"class": re.compile(r"description|listing-?desc", re.IGNORECASE)})
    return node.get_text(" ", strip=True) if node else ""


def _status_text(s) -> str:
    node = s.find(attrs={"class": re.compile(r"status|badge|ribbon|availability", re.IGNORECASE)})
    return node.get_text(" ", strip=True) if node else ""


def _address(ld: dict, s):
    address_raw = suburb = city = province = ""
    addr = ld.get("address") if isinstance(ld, dict) else None
    if isinstance(addr, dict):
        parts = [addr.get("streetAddress"), addr.get("addressLocality"),
                 addr.get("addressRegion")]
        address_raw = ", ".join(p for p in parts if p)
        suburb = addr.get("addressLocality", "") or ""
        province = addr.get("addressRegion", "") or ""
    if not address_raw:
        node = s.find(attrs={"class": re.compile(r"address|location", re.IGNORECASE)})
        if node:
            address_raw = node.get_text(" ", strip=True)
    return address_raw, suburb, city, province


def _stated_date(ld: dict, s, html: str) -> str:
    if isinstance(ld, dict):
        for key in ("datePosted", "datePublished", "dateCreated"):
            if ld.get(key):
                return str(ld[key])
    meta = (H.meta_content(s, "article:published_time")
            or H.meta_content(s, "datePosted"))
    if meta:
        return meta
    # Embedded state occasionally carries a createdDate.
    m = re.search(r'"(?:datePosted|listingDate|createdDate|firstPublished)"\s*:\s*"([^"]+)"', html)
    return m.group(1) if m else ""


def _updated_date(s, html: str) -> str:
    meta = H.meta_content(s, "article:modified_time")
    if meta:
        return meta
    m = re.search(r"(?:updated|modified|refreshed)\s*(?:on)?\s*[:\-]?\s*"
                  r"(\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2})", html, re.IGNORECASE)
    return m.group(1) if m else ""


def _contacts(ld: dict, s):
    agency_name = agent_name = ""
    agent_phone = agent_email = None
    if isinstance(ld, dict):
        broker = ld.get("realEstateAgent") or ld.get("provider") or ld.get("seller")
        if isinstance(broker, dict):
            agent_name = broker.get("name", "") or ""
            agent_phone = broker.get("telephone")
            agent_email = broker.get("email")
        org = ld.get("brand") or ld.get("agency")
        if isinstance(org, dict):
            agency_name = org.get("name", "") or ""

    text = s.get_text(" ", strip=True)
    agent_phone = agent_phone or H.tel_links(s) or H.first_phone(text)
    agent_email = agent_email or H.mailto_links(s) or H.first_email(text)
    if not agency_name:
        node = s.find(attrs={"class": re.compile(r"agency|branch|brand", re.IGNORECASE)})
        if node:
            agency_name = node.get_text(" ", strip=True)[:120]
    if not agent_name:
        node = s.find(attrs={"class": re.compile(r"agent-?name|agent", re.IGNORECASE)})
        if node:
            agent_name = node.get_text(" ", strip=True)[:120]
    return agency_name, agent_name or None, agent_phone, agent_email


def _geo(ld: dict):
    geo = ld.get("geo") if isinstance(ld, dict) else None
    if isinstance(geo, dict):
        try:
            return float(geo.get("latitude")), float(geo.get("longitude"))
        except (TypeError, ValueError):
            return None, None
    return None, None
