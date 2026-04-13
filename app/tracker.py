"""Core tracker — aggregates data from all sources and ranks ad sets."""

import logging
from datetime import datetime, timezone

from app.integrations.facebook_ads import fetch_adset_insights
from app.integrations.gohighlevel import fetch_appointments, match_appointments_to_adsets
from app.integrations.medx import fetch_purchases, summarise_purchases

logger = logging.getLogger(__name__)

# In-memory cache of the latest dashboard data
_cache: dict = {}


def get_cached_data() -> dict:
    return _cache


async def refresh_data() -> dict:
    """Pull fresh data from all three sources and compute rankings."""
    global _cache
    logger.info("Refreshing data from all sources...")

    # --- 1. Fetch from all APIs ---
    adsets = []
    appointments = []
    purchases = []
    errors = []

    try:
        adsets = await fetch_adset_insights()
    except Exception as e:
        logger.error(f"Facebook Ads fetch failed: {e}")
        errors.append(f"Facebook Ads: {e}")

    try:
        appointments = await fetch_appointments()
    except Exception as e:
        logger.error(f"GHL fetch failed: {e}")
        errors.append(f"Go High Level: {e}")

    try:
        purchases = await fetch_purchases()
    except Exception as e:
        logger.error(f"MedX fetch failed: {e}")
        errors.append(f"MedX: {e}")

    # --- 2. Match appointments to ad sets ---
    appt_counts = match_appointments_to_adsets(appointments, adsets) if adsets else {}

    # --- 3. Build unified ad set performance table ---
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

    # --- 4. Rank by booked appointments (desc), then by spend (asc) as tiebreaker ---
    sorted_by_appts = sorted(
        performance,
        key=lambda x: (-x["booked_appointments"], x["spend"]),
    )

    top_5 = sorted_by_appts[:5]

    # Bottom 3: ad sets with spend > 0 but fewest appointments
    with_spend = [p for p in sorted_by_appts if p["spend"] > 0]
    bottom_3 = list(reversed(with_spend))[:3] if with_spend else []

    # --- 5. Purchase summary (deposits taken + cash collected) ---
    purchase_summary = summarise_purchases(purchases)

    # --- 6. Totals ---
    total_spend = sum(a["spend"] for a in adsets)
    total_appointments = sum(appt_counts.values())
    overall_cost_per_appt = round(total_spend / total_appointments, 2) if total_appointments > 0 else None
    total_purchases = purchase_summary["total_purchases"]
    cost_per_purchase = round(total_spend / total_purchases, 2) if total_purchases > 0 else None

    _cache = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_ad_sets": len(adsets),
            "total_spend": round(total_spend, 2),
            "total_appointments": total_appointments,
            "total_leads": sum(a["leads"] for a in adsets),
            "cost_per_appointment": overall_cost_per_appt,
            "cost_per_purchase": cost_per_purchase,
            "purchases": purchase_summary,
        },
        "top_5": top_5,
        "bottom_3_switch_off": bottom_3,
        "all_adsets": sorted_by_appts,
        "errors": errors,
    }

    logger.info(
        f"Refresh complete — {len(adsets)} ad sets, "
        f"{total_appointments} appointments, "
        f"{purchase_summary['total_purchases']} purchases"
    )
    return _cache
