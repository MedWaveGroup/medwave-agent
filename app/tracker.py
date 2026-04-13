"""Core tracker — Facebook Ads performance vs GHL booked appointments."""

import logging
from datetime import datetime, timezone

from app.integrations.facebook_ads import fetch_adset_insights
from app.integrations.gohighlevel import fetch_appointments, match_appointments_to_adsets

logger = logging.getLogger(__name__)

_cache: dict = {}


def get_cached_data() -> dict:
    return _cache


async def refresh_data() -> dict:
    """Pull Facebook ad sets and GHL appointments, compute rankings."""
    global _cache
    logger.info("Refreshing data...")

    adsets = []
    appointments = []

    try:
        adsets = await fetch_adset_insights()
    except Exception as e:
        logger.error(f"Facebook Ads: {e}")

    try:
        appointments = await fetch_appointments()
    except Exception as e:
        logger.error(f"GHL: {e}")

    # Match appointments to ad sets
    appt_counts = match_appointments_to_adsets(appointments, adsets) if adsets else {}

    # Build performance table
    performance = []
    for ad in adsets:
        name = ad["adset_name"]
        booked = appt_counts.get(name, 0)
        spend = ad["spend"]
        cost_per_appt = round(spend / booked, 2) if booked > 0 else None

        performance.append({
            "adset_id": ad["adset_id"],
            "adset_name": name,
            "campaign_name": ad["campaign_name"],
            "spend": spend,
            "impressions": ad["impressions"],
            "clicks": ad["clicks"],
            "cpc": ad["cpc"],
            "ctr": ad["ctr"],
            "leads": ad["leads"],
            "booked_appointments": booked,
            "cost_per_appointment": cost_per_appt,
        })

    # Rank: most appointments first, lowest spend as tiebreaker
    sorted_by_appts = sorted(
        performance,
        key=lambda x: (-x["booked_appointments"], x["spend"]),
    )

    top_5 = sorted_by_appts[:5]

    # Bottom 3: spending money but fewest appointments
    with_spend = [p for p in sorted_by_appts if p["spend"] > 0]
    bottom_3 = list(reversed(with_spend))[:3] if with_spend else []

    total_spend = sum(a["spend"] for a in adsets)
    total_appts = sum(appt_counts.values())
    cost_per_appt = round(total_spend / total_appts, 2) if total_appts > 0 else None

    _cache = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_ad_sets": len(adsets),
            "total_spend": round(total_spend, 2),
            "total_appointments": total_appts,
            "total_leads": sum(a["leads"] for a in adsets),
            "cost_per_appointment": cost_per_appt,
        },
        "top_5": top_5,
        "bottom_3_switch_off": bottom_3,
        "all_adsets": sorted_by_appts,
    }

    logger.info(f"Done — {len(adsets)} ad sets, {total_appts} appointments")
    return _cache
