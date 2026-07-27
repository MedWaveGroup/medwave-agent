"""Text parsers for SA property listings.

These are the fragile heart of the tool: SA portals express rent, size and VAT
in wildly inconsistent free text. Every function here is pure and unit-tested
against saved fixtures. Keep them dependency-free.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Size extraction
# ---------------------------------------------------------------------------

# Matches: "45m2", "45 m²", "45 sqm", "45 sq m", "approx 45m²", "45m2 shop",
# "1,250 m2", "45.5 m²". The unit is required so we don't grab bedroom counts.
_SIZE_RE = re.compile(
    r"""
    (?P<num>\d{1,3}(?:[ ,]\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)   # 45 / 45.5 / 1,250
    \s*
    (?:m\s*(?:2|²|\^2)|sq\.?\s*m(?:etre?s?)?|square\s*met(?:er|re)s?)   # unit
    """,
    re.IGNORECASE | re.VERBOSE,
)

_APPROX_RE = re.compile(r"\b(approx|about|around|circa|~|from)\b", re.IGNORECASE)


def parse_size_sqm(text: str) -> Tuple[Optional[float], str]:
    """Extract a floor area in m² from free text.

    Returns ``(size, confidence)`` where confidence is one of
    ``"stated"`` (a clean single value), ``"parsed_from_text"`` (found amid
    prose / approximate), or ``"unknown"`` (nothing found).

    Only the *largest single* matched value is returned - we never sum multiple
    figures, because a listing that lists two 15 m² units must not be treated as
    a single 30 m² unit (spec: no summing to reach the threshold).
    """
    if not text:
        return None, "unknown"

    matches = []
    for m in _SIZE_RE.finditer(text):
        num = m.group("num").replace(" ", "").replace(",", "")
        try:
            val = float(num)
        except ValueError:
            continue
        # Ignore absurd values likely to be a typo or a plot size in hectares.
        if 0 < val <= 100000:
            matches.append(val)

    if not matches:
        return None, "unknown"

    # Largest single contiguous figure; never a sum.
    size = max(matches)

    # If prose contains approximation words, or the number sat inside a longer
    # description, mark it as parsed rather than cleanly stated.
    approximate = bool(_APPROX_RE.search(text))
    single_clean = len(matches) == 1 and len(text.strip()) <= 20
    confidence = "stated" if (single_clean and not approximate) else "parsed_from_text"
    return size, confidence


# ---------------------------------------------------------------------------
# Price extraction
# ---------------------------------------------------------------------------

_PRICE_RE = re.compile(
    r"""
    R\s*                                       # leading Rand symbol
    (?P<num>\d{1,3}(?:[ ,.]\d{3})+|\d+)        # 12 000 / 12,000 / 12.000 / 12000
    (?:\.\d{2})?                               # optional cents
    """,
    re.IGNORECASE | re.VERBOSE,
)

_POA_RE = re.compile(
    r"price\s*on\s*application|\bpoa\b|on\s*application|price\s*on\s*request",
    re.IGNORECASE,
)


def is_price_on_application(text: str) -> bool:
    return bool(_POA_RE.search(text or ""))


def parse_price(text: str) -> Optional[int]:
    """Extract a monthly rent in whole Rand from free text.

    Handles ``"R 12 000"``, ``"R12,000"``, ``"R12000 pm"``,
    ``"R12 000 p/m excl VAT"``. Returns ``None`` for Price-on-Application or
    when no Rand figure is present.
    """
    if not text or is_price_on_application(text):
        return None

    best = None
    for m in _PRICE_RE.finditer(text):
        raw = m.group("num")
        # Thousands separators in SA can be space, comma or full stop.
        digits = re.sub(r"[ ,.]", "", raw)
        if not digits.isdigit():
            continue
        val = int(digits)
        # Rents live in a sane band; ignore stray small numbers (e.g. "R5 deposit
        # per key") and huge sale prices when a per-month figure is present.
        if 100 <= val <= 100000000:
            # Prefer the first plausible monthly figure; keep the smallest
            # plausible one to avoid grabbing a sale price listed alongside.
            if best is None or val < best:
                best = val
    return best


# ---------------------------------------------------------------------------
# VAT detection
# ---------------------------------------------------------------------------

VAT_RATE = 0.15  # SA standard rate (informational; we do not invent numbers).

_EXCL_RE = re.compile(
    r"excl(?:uding|\.)?\s*vat|ex\s*vat|\bvat\s*excl|plus\s*vat|\+\s*vat|"
    r"vat\s*not\s*included",
    re.IGNORECASE,
)
_INCL_RE = re.compile(
    r"incl(?:uding|\.)?\s*vat|inc\s*vat|\bvat\s*incl|vat\s*included",
    re.IGNORECASE,
)


def detect_vat_basis(text: str) -> str:
    """Return ``"excl_vat"``, ``"incl_vat"`` or ``"unknown"``.

    "excluding" is checked first because "vat included in levies but rent excl
    vat" style text should read as excl.
    """
    if not text:
        return "unknown"
    if _EXCL_RE.search(text):
        return "excl_vat"
    if _INCL_RE.search(text):
        return "incl_vat"
    return "unknown"


def effective_rent_incl_vat(monthly_rent: Optional[int], rent_basis: str) -> Optional[int]:
    """The real number the team pays, grossing up excl-VAT rents by 15%."""
    if monthly_rent is None:
        return None
    if rent_basis == "excl_vat":
        return int(round(monthly_rent * (1 + VAT_RATE)))
    return monthly_rent


# ---------------------------------------------------------------------------
# Property type classification
# ---------------------------------------------------------------------------

_TYPE_KEYWORDS = [
    ("medical", (r"medical", r"consulting\s*room", r"treatment\s*room", r"clinic", r"surgery\b", r"doctor")),
    ("retail", (r"retail", r"shop", r"store\b", r"in\s*mall", r"shop-?in-?mall", r"boutique", r"showroom")),
    ("office", (r"office", r"business\s*park", r"co-?work")),
    ("industrial", (r"industrial", r"warehouse", r"factory", r"mini-?factory")),
    ("residential", (r"apartment", r"flat\b", r"cottage", r"garden\s*flat", r"bachelor", r"studio\b", r"townhouse", r"bedroom")),
    ("commercial", (r"commercial", r"premises", r"unit\b", r"space")),
]


def classify_property_type(*texts: str) -> str:
    """Best-effort property-type classification from title/description/hints."""
    blob = " ".join(t for t in texts if t).lower()
    if not blob.strip():
        return "other"
    for label, patterns in _TYPE_KEYWORDS:
        for pat in patterns:
            if re.search(pat, blob):
                return label
    return "other"


# ---------------------------------------------------------------------------
# Address normalisation (used by deduplication)
# ---------------------------------------------------------------------------

_STREET_ABBR = {
    "street": "st", "str": "st", "st.": "st",
    "avenue": "ave", "av": "ave", "ave.": "ave",
    "road": "rd", "rd.": "rd",
    "drive": "dr", "dr.": "dr",
    "boulevard": "blvd", "blvd.": "blvd",
    "crescent": "cres",
    "close": "cl",
    "lane": "ln",
    "place": "pl",
    "square": "sq",
    "highway": "hwy",
    "north": "n", "south": "s", "east": "e", "west": "w",
    "building": "bldg", "centre": "ctr", "center": "ctr",
}

_UNIT_PREFIX_RE = re.compile(
    r"\b(?:unit|shop|office|suite|door|no\.?|number|flat)\s*[:#]?\s*[0-9a-z]+\b",
    re.IGNORECASE,
)


def normalise_address(address: str) -> str:
    """Canonical form of a street address for fuzzy duplicate matching.

    Lower-cased, punctuation stripped, unit/shop numbers removed (two agents may
    label the same door "Shop 4" vs "Unit 4"), and common street-type words
    abbreviated to a single spelling.
    """
    if not address:
        return ""
    s = address.lower().strip()
    # Drop unit/shop/suite prefixes - they vary between agencies for one door.
    s = _UNIT_PREFIX_RE.sub(" ", s)
    # Strip punctuation to spaces.
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    tokens = []
    for tok in s.split():
        tokens.append(_STREET_ABBR.get(tok, tok))
    # Collapse and sort-independent? No - keep order but dedupe consecutive dups.
    out = []
    for t in tokens:
        if not out or out[-1] != t:
            out.append(t)
    return " ".join(out).strip()


# ---------------------------------------------------------------------------
# Availability status
# ---------------------------------------------------------------------------

_NOT_AVAILABLE_RE = re.compile(
    r"no\s*longer\s*available|has\s*been\s*let|now\s*let\b|already\s*let|"
    r"\bleased\b|(?<!to )(?<!to-)\blet\b|off\s*[- ]?market|withdrawn|"
    r"\bsold\b|not\s*available",
    re.IGNORECASE,
)
_UNDER_OFFER_RE = re.compile(
    r"under\s*offer|pending|sale\s*pending|offer\s*pending|deposit\s*taken",
    re.IGNORECASE,
)
_COMING_SOON_RE = re.compile(
    r"coming\s*soon|waitlist|wait\s*list|register\s*your\s*interest",
    re.IGNORECASE,
)
_AVAILABLE_RE = re.compile(
    r"to\s*let|to\s*rent|available|now\s*available|immediately\s*available",
    re.IGNORECASE,
)


def detect_availability(text: str) -> str:
    """Classify availability from status text on a listing page.

    Order matters: negative signals win over the generic "to let" boilerplate
    that most pages carry regardless of real status.
    """
    if not text:
        return "unknown"
    if _COMING_SOON_RE.search(text):
        return "coming_soon"
    if _UNDER_OFFER_RE.search(text):
        return "under_offer"
    if _NOT_AVAILABLE_RE.search(text):
        return "let"
    if _AVAILABLE_RE.search(text):
        return "available"
    return "unknown"
