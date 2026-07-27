"""Adapter base class and the polite HTTP fetcher every adapter shares.

Compliance behaviour lives here so no individual adapter can forget it:
  * robots.txt is fetched, cached and consulted before every request;
  * a minimum per-domain delay is enforced;
  * 429/503 trigger exponential backoff;
  * raw responses are cached on disk for ``cache_ttl_hours``;
  * an honest, contactable User-Agent is sent on every request.

Adapters subclass :class:`BaseAdapter` and implement ``search()``.
"""
from __future__ import annotations

import hashlib
import time
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx

from ..config import Config
from ..logging_config import get_logger
from ..models import RawListing

log = get_logger("adapter")


class SourceBlocked(Exception):
    """Raised when a source blocks the tool (bot detection / captcha / 403)."""


@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str
    from_cache: bool = False


@dataclass
class AdapterStats:
    """Per-source telemetry accumulated during a run, surfaced in the report."""

    source: str
    requests_made: int = 0
    listings_found: int = 0
    errors: List[str] = field(default_factory=list)
    blocked: bool = False
    skipped_paths: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class PoliteClient:
    """Shared HTTP client enforcing robots, rate limits, backoff and caching."""

    # Class-level so all adapters sharing one process honour one clock per host.
    _last_request_at: Dict[str, float] = {}

    def __init__(self, config: Config):
        self.config = config
        self.cache_dir = config.cache_path
        self.delay = float(config.request_delay_seconds)
        self.ttl = timedelta(hours=config.cache_ttl_hours)
        self._robots: Dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}
        self._client = httpx.Client(
            headers={"User-Agent": config.user_agent()},
            follow_redirects=True,
            timeout=30.0,
        )

    # --- robots ----------------------------------------------------------
    def _robots_for(self, url: str) -> Optional[urllib.robotparser.RobotFileParser]:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base in self._robots:
            return self._robots[base]
        rp = urllib.robotparser.RobotFileParser()
        robots_url = urljoin(base, "/robots.txt")
        try:
            resp = self._client.get(robots_url, timeout=15.0)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                rp = None  # No robots => allowed, but note we couldn't read it.
        except httpx.HTTPError as exc:
            log.warning("Could not fetch robots.txt for %s: %s", base, exc)
            rp = None
        self._robots[base] = rp
        return rp

    def allowed(self, url: str) -> bool:
        rp = self._robots_for(url)
        if rp is None:
            return True
        return rp.can_fetch(self.config.user_agent(), url)

    # --- caching ---------------------------------------------------------
    def _cache_file(self, url: str) -> Path:
        key = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.html"

    def _read_cache(self, url: str) -> Optional[str]:
        f = self._cache_file(url)
        if not f.exists():
            return None
        age = datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)
        if age > self.ttl:
            return None
        try:
            return f.read_text(encoding="utf-8")
        except OSError:
            return None

    def _write_cache(self, url: str, text: str) -> None:
        try:
            self._cache_file(url).write_text(text, encoding="utf-8")
        except OSError as exc:
            log.warning("Cache write failed for %s: %s", url, exc)

    # --- rate limiting ---------------------------------------------------
    def _respect_delay(self, host: str) -> None:
        last = PoliteClient._last_request_at.get(host)
        if last is not None:
            wait = self.delay - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        PoliteClient._last_request_at[host] = time.monotonic()

    # --- fetch -----------------------------------------------------------
    def get(self, url: str, stats: Optional[AdapterStats] = None,
            use_cache: bool = True) -> FetchResult:
        """Fetch ``url`` respecting robots, rate-limits, backoff and cache.

        Raises :class:`SourceBlocked` on 403/CAPTCHA-style responses so the
        adapter can mark itself BLOCKED and the run continues.
        """
        if use_cache:
            cached = self._read_cache(url)
            if cached is not None:
                log.debug("cache hit %s", url)
                return FetchResult(url=url, status_code=200, text=cached, from_cache=True)

        if not self.allowed(url):
            msg = f"robots.txt disallows {url}"
            log.info("SKIP (robots): %s", url)
            if stats is not None:
                stats.skipped_paths.append(url)
            raise SourceBlocked(msg)

        host = urlparse(url).netloc
        backoff = 2.0
        for attempt in range(5):
            self._respect_delay(host)
            try:
                resp = self._client.get(url)
            except httpx.HTTPError as exc:
                if stats is not None:
                    stats.requests_made += 1
                    stats.errors.append(f"{url}: {exc}")
                if attempt == 4:
                    raise
                time.sleep(backoff)
                backoff *= 2
                continue

            if stats is not None:
                stats.requests_made += 1

            if resp.status_code in (429, 503):
                log.warning("throttled %s (%s) - backing off %.0fs",
                            url, resp.status_code, backoff)
                time.sleep(backoff)
                backoff *= 2
                continue

            if resp.status_code == 403 or _looks_like_captcha(resp.text):
                raise SourceBlocked(f"{url} returned {resp.status_code} / bot wall")

            if resp.status_code in (404, 410):
                return FetchResult(url=url, status_code=resp.status_code, text=resp.text)

            if resp.status_code >= 400:
                if attempt == 4:
                    return FetchResult(url=url, status_code=resp.status_code, text=resp.text)
                time.sleep(backoff)
                backoff *= 2
                continue

            if use_cache:
                self._write_cache(url, resp.text)
            return FetchResult(url=str(resp.url), status_code=resp.status_code, text=resp.text)

        raise SourceBlocked(f"exhausted retries for {url}")

    def close(self) -> None:
        self._client.close()


def _looks_like_captcha(text: str) -> bool:
    if not text:
        return False
    low = text[:5000].lower()
    needles = ("captcha", "are you a robot", "verify you are human",
               "cf-browser-verification", "cloudflare", "access denied",
               "unusual traffic")
    return any(n in low for n in needles)


class BaseAdapter:
    """Interface every source adapter must implement."""

    #: Stable machine name matching the ``sources`` key in config.yaml.
    name: str = "base"
    #: Human-readable name for reports.
    display_name: str = "Base"

    def __init__(self, config: Config, client: Optional[PoliteClient] = None):
        self.config = config
        self.client = client or PoliteClient(config)
        self.stats = AdapterStats(source=self.name)

    def search(
        self,
        area: str,
        max_rent: int,
        min_size_sqm: int,
        radius_km: Optional[int] = None,
        include_residential: bool = False,
    ) -> List[RawListing]:
        """Return raw listings for ``area``. Must be implemented by subclasses."""
        raise NotImplementedError

    # Convenience used by adapters + the availability re-checker.
    def fetch(self, url: str, use_cache: bool = True) -> FetchResult:
        return self.client.get(url, stats=self.stats, use_cache=use_cache)
