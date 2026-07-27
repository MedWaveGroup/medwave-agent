"""Deduplication of the same physical unit listed by several agents/portals.

Match rule (spec): normalised street address equal AND size within 5% AND rent
within 10%. The surviving record is the one with the most complete agent contact
details; the others' agency names are folded into ``also_listed_by`` and each is
marked ``duplicate_of`` the survivor.
"""
from __future__ import annotations

from typing import List

from .models import Listing
from .parsers import normalise_address


def _size_close(a: float | None, b: float | None, tol: float = 0.05) -> bool:
    if a is None or b is None:
        return False
    if a == 0 or b == 0:
        return a == b
    return abs(a - b) / max(a, b) <= tol


def _rent_close(a: int | None, b: int | None, tol: float = 0.10) -> bool:
    if a is None or b is None:
        return False
    if a == 0 or b == 0:
        return a == b
    return abs(a - b) / max(a, b) <= tol


def _contact_score(l: Listing) -> int:
    """More complete contact details rank higher."""
    score = 0
    if l.agent_phone:
        score += 3
    if l.agent_email:
        score += 2
    if l.agent_name:
        score += 1
    if l.agency_name:
        score += 1
    # Break ties toward richer records.
    if l.description:
        score += 1
    if l.image_url:
        score += 1
    return score


def _same_unit(a: Listing, b: Listing) -> bool:
    na, nb = normalise_address(a.address_raw), normalise_address(b.address_raw)
    if not na or not nb or na != nb:
        return False
    return _size_close(a.size_sqm, b.size_sqm) and _rent_close(a.monthly_rent, b.monthly_rent)


def deduplicate(listings: List[Listing]) -> List[Listing]:
    """Collapse duplicates in place and return the surviving records.

    Returns only survivors; duplicates keep their row (with ``duplicate_of`` set)
    so they can still be persisted, but they are excluded from the returned list
    used for exports.
    """
    survivors: List[Listing] = []
    groups: List[List[Listing]] = []

    for listing in listings:
        placed = False
        for group in groups:
            if _same_unit(group[0], listing):
                group.append(listing)
                placed = True
                break
        if not placed:
            groups.append([listing])

    for group in groups:
        if len(group) == 1:
            survivors.append(group[0])
            continue
        # Choose survivor with the richest contact details.
        group.sort(key=_contact_score, reverse=True)
        survivor = group[0]
        others = group[1:]
        also = [o.agency_name for o in others if o.agency_name]
        # Preserve any already-known also_listed_by entries.
        existing = [x for x in survivor.also_listed_by.split(";") if x]
        survivor.also_listed_by = ";".join(dict.fromkeys(existing + also))
        if "deduplicated" not in survivor.flags:
            survivor.flags.append("deduplicated")
        for o in others:
            o.duplicate_of = survivor.id
        survivors.append(survivor)

    return survivors
