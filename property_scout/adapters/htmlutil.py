"""Shared HTML/JSON extraction helpers used by adapters.

SA portals almost always embed structured data (JSON-LD ``RealEstateListing`` /
``Product`` / ``Offer``, Open Graph meta tags, and framework state blobs). The
build spec is explicit that the real listing date and price often live in the
markup even when not visibly rendered, so we always mine structured data before
falling back to visible text.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html or "", "lxml")


def json_ld_blocks(s: BeautifulSoup) -> List[Any]:
    """Return all parsed ``application/ld+json`` payloads (flattened @graph)."""
    blocks: List[Any] = []
    for tag in s.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            # Some sites emit multiple concatenated objects; try a lenient split.
            try:
                data = json.loads(raw.replace("}\n{", "},{").join(["[", "]"]))
            except (json.JSONDecodeError, ValueError):
                continue
        if isinstance(data, dict) and "@graph" in data:
            blocks.extend(data["@graph"])
        elif isinstance(data, list):
            blocks.extend(data)
        else:
            blocks.append(data)
    return blocks


def find_ld_type(blocks: List[Any], *types: str) -> Optional[Dict]:
    wanted = {t.lower() for t in types}
    for b in blocks:
        if not isinstance(b, dict):
            continue
        t = b.get("@type")
        if isinstance(t, list):
            if any(str(x).lower() in wanted for x in t):
                return b
        elif isinstance(t, str) and t.lower() in wanted:
            return b
    return None


def meta_content(s: BeautifulSoup, prop: str) -> str:
    """Return the content of an og:/twitter:/name meta tag, or ''."""
    for attr in ("property", "name", "itemprop"):
        tag = s.find("meta", attrs={attr: prop})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return ""


# Embedded framework-state blobs (Next.js __NEXT_DATA__, window.__STATE__, etc.).
_STATE_PATTERNS = [
    re.compile(r"__NEXT_DATA__\s*=\s*({.*?})\s*</script>", re.DOTALL),
    re.compile(r"window\.__(?:INITIAL_STATE|PRELOADED_STATE|STATE)__\s*=\s*({.*?});", re.DOTALL),
    re.compile(r"application/json\">({.*?})</script>", re.DOTALL),
]


def embedded_state(html: str) -> Optional[Dict]:
    for pat in _STATE_PATTERNS:
        m = pat.search(html or "")
        if m:
            try:
                return json.loads(m.group(1))
            except (json.JSONDecodeError, ValueError):
                continue
    return None


# Contact extraction ---------------------------------------------------------

_PHONE_RE = re.compile(
    r"(?:\+?27|0)\s*(?:\(0\))?\s*\d{2}[\s\-]?\d{3}[\s\-]?\d{4}"
)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def first_phone(*texts: str) -> Optional[str]:
    for t in texts:
        if not t:
            continue
        m = _PHONE_RE.search(t)
        if m:
            return re.sub(r"\s{2,}", " ", m.group(0)).strip()
    return None


def first_email(*texts: str) -> Optional[str]:
    for t in texts:
        if not t:
            continue
        m = _EMAIL_RE.search(t)
        if m:
            # Skip obvious asset/tracking addresses.
            addr = m.group(0)
            if not addr.lower().endswith((".png", ".jpg", ".gif")):
                return addr
    return None


def tel_links(s: BeautifulSoup) -> Optional[str]:
    tag = s.find("a", href=re.compile(r"^tel:", re.IGNORECASE))
    if tag:
        return tag["href"].split(":", 1)[1].strip()
    return None


def mailto_links(s: BeautifulSoup) -> Optional[str]:
    tag = s.find("a", href=re.compile(r"^mailto:", re.IGNORECASE))
    if tag:
        return tag["href"].split(":", 1)[1].split("?")[0].strip()
    return None
