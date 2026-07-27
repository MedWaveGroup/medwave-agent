"""Generic portal/agency adapter.

Most SA property sites share the same anatomy: a search results page of cards
linking to detail pages, and detail pages carrying JSON-LD + Open Graph data.
This class implements that shape once; concrete sources declare only their base
URL, how to build a search URL, and how to recognise a detail-page link.

Property24 has its own bespoke adapter; everything else is configured here.
"""
from __future__ import annotations

import re
from typing import List, Optional, Pattern
from urllib.parse import urljoin

from ..logging_config import get_logger
from ..models import RawListing
from .base import BaseAdapter, SourceBlocked
from . import htmlutil as H
from .property24 import (
    _ld_price, _visible_price, _size_text, _description_text, _status_text,
    _address, _stated_date, _updated_date, _contacts, _geo,
)

log = get_logger("adapter.generic")


class GenericPortalAdapter(BaseAdapter):
    """Configure per source by setting the class attributes below."""

    base_url: str = ""
    #: Templates receive ``{slug}`` (and are tried in order until one yields links).
    commercial_search_templates: List[str] = []
    residential_search_templates: List[str] = []
    #: Regex a detail-page href must match.
    detail_link_re: Pattern = re.compile(r"$^")

    # --- helpers ---------------------------------------------------------
    @staticmethod
    def slug(area: str) -> str:
        town = area.split(",")[0].strip().lower()
        town = re.sub(r"[^a-z0-9\s-]", "", town)
        return re.sub(r"\s+", "-", town)

    def search_urls(self, area: str, include_residential: bool) -> List[str]:
        slug = self.slug(area)
        urls = [t.format(slug=slug, base=self.base_url) for t in self.commercial_search_templates]
        if include_residential:
            urls += [t.format(slug=slug, base=self.base_url) for t in self.residential_search_templates]
        return urls

    def _result_detail_links(self, html: str) -> List[str]:
        s = H.soup(html)
        links = set()
        for a in s.find_all("a", href=True):
            href = a["href"].split("?")[0].split("#")[0]
            full = urljoin(self.base_url, href)
            if self.detail_link_re.search(full):
                links.add(full)
        return sorted(links)

    def _source_id(self, url: str) -> str:
        m = re.search(r"(\d{4,})(?:/)?$", url.rstrip("/"))
        if m:
            return m.group(1)
        return url.rstrip("/").rsplit("/", 1)[-1]

    def parse_detail(self, url: str, html: str) -> Optional[RawListing]:
        s = H.soup(html)
        blocks = H.json_ld_blocks(s)
        ld = H.find_ld_type(blocks, "RealEstateListing", "Product", "Offer",
                            "Residence", "Apartment", "House") or {}

        title = (
            (ld.get("name") if isinstance(ld.get("name"), str) else "")
            or H.meta_content(s, "og:title")
            or (s.title.get_text(strip=True) if s.title else "")
        )
        rent_text = " ".join(filter(None, [
            _ld_price(ld), _visible_price(s), H.meta_content(s, "og:description"),
        ]))
        size_text = _size_text(s)
        description = (
            (ld.get("description") if isinstance(ld.get("description"), str) else "")
            or H.meta_content(s, "og:description")
            or _description_text(s)
        )
        address_raw, suburb, city, province = _address(ld, s)
        date_listed_text = _stated_date(ld, s, html)
        date_updated_text = _updated_date(s, html)
        availability_text = " ".join(filter(None, [title, _status_text(s), description[:400]]))
        agency_name, agent_name, agent_phone, agent_email = _contacts(ld, s)
        if not agency_name:
            agency_name = self.display_name  # at least attribute to the site
        image_url = H.meta_content(s, "og:image") or None
        lat, lon = _geo(ld)

        return RawListing(
            source=self.name,
            source_listing_id=self._source_id(url),
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
                log.warning("%s blocked/skip on %s: %s", self.name, search_url, exc)
                continue
            if res.status_code >= 400:
                continue
            found = self._result_detail_links(res.text)
            log.info("%s %s -> %d detail links", self.name, search_url, len(found))
            detail_links.extend(found)

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
            except Exception as exc:
                self.stats.errors.append(f"parse {url}: {exc}")
                continue
            if raw:
                results.append(raw)

        self.stats.listings_found = len(results)
        return results


# --- concrete sources -------------------------------------------------------

class PrivatePropertyAdapter(GenericPortalAdapter):
    name = "private_property"
    display_name = "Private Property"
    base_url = "https://www.privateproperty.co.za"
    commercial_search_templates = [
        "{base}/commercial-to-rent/eastern-cape/{slug}",
        "{base}/to-rent/{slug}",
    ]
    residential_search_templates = ["{base}/to-rent/{slug}"]
    detail_link_re = re.compile(r"/(?:to-rent|commercial-to-rent)/.+/\d{4,}")


class GumtreeAdapter(GenericPortalAdapter):
    name = "gumtree"
    display_name = "Gumtree Property"
    base_url = "https://www.gumtree.co.za"
    commercial_search_templates = [
        "{base}/s-commercial-property-to-rent/{slug}/v1c9227p1",
        "{base}/s-property-to-rent/{slug}/v1c9077p1",
    ]
    residential_search_templates = ["{base}/s-flats-apartments-to-rent/{slug}/v1c9078p1"]
    detail_link_re = re.compile(r"/a-[\w-]+/\d{4,}")


class PamGoldingAdapter(GenericPortalAdapter):
    name = "pamgolding"
    display_name = "Pam Golding"
    base_url = "https://www.pamgolding.co.za"
    commercial_search_templates = [
        "{base}/property-to-rent/commercial/{slug}",
        "{base}/property-to-rent/{slug}",
    ]
    residential_search_templates = ["{base}/property-to-rent/{slug}"]
    detail_link_re = re.compile(r"/property-details/[\w-]*?/\d{4,}|/results/rent/[\w-]+/\d{4,}")


class Century21Adapter(GenericPortalAdapter):
    name = "century21"
    display_name = "Century 21 South Africa"
    base_url = "https://www.century21.co.za"
    commercial_search_templates = [
        "{base}/results/to-let/commercial/{slug}",
        "{base}/results/to-let/{slug}",
    ]
    residential_search_templates = ["{base}/results/to-let/{slug}"]
    detail_link_re = re.compile(r"/results/[\w-]+/\d{4,}|/property/\d{4,}")


class SeeffAdapter(GenericPortalAdapter):
    name = "seeff"
    display_name = "Seeff"
    base_url = "https://www.seeff.com"
    commercial_search_templates = [
        "{base}/results/commercial/to-let/{slug}",
        "{base}/results/residential/to-let/{slug}",
    ]
    residential_search_templates = ["{base}/results/residential/to-let/{slug}"]
    detail_link_re = re.compile(r"/results/[\w-]+/to-let/[\w-]+/[\w-]+/\d{4,}|/details/\d{4,}")


class RemaxAdapter(GenericPortalAdapter):
    name = "remax"
    display_name = "RE/MAX South Africa"
    base_url = "https://www.remax.co.za"
    commercial_search_templates = [
        "{base}/commercial-property/to-let/{slug}",
        "{base}/property/to-let/{slug}",
    ]
    residential_search_templates = ["{base}/property/to-let/{slug}"]
    detail_link_re = re.compile(r"/property/[\w-]+/\d{4,}|/listing/\d{4,}")


class RawsonAdapter(GenericPortalAdapter):
    name = "rawson"
    display_name = "Rawson / Just Property"
    base_url = "https://www.rawson.co.za"
    commercial_search_templates = [
        "{base}/property-to-rent/commercial/south-africa/{slug}",
        "{base}/property-to-rent/south-africa/{slug}",
    ]
    residential_search_templates = ["{base}/property-to-rent/south-africa/{slug}"]
    detail_link_re = re.compile(r"/property-to-rent/[\w/-]+/\d{4,}|/property/\d{4,}")
