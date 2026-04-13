"""Facebook Ads API integration — pulls 7-day ad set performance."""

import httpx
from datetime import datetime, timedelta
from app.config import FB_ACCESS_TOKEN, FB_AD_ACCOUNT_ID

API_BASE = "https://graph.facebook.com/v19.0"


async def fetch_adset_insights() -> list[dict]:
    """Fetch last 7 days of ad set level insights from Facebook Ads API."""
    if not FB_ACCESS_TOKEN or not FB_AD_ACCOUNT_ID:
        return []

    today = datetime.utcnow().date()
    since = (today - timedelta(days=7)).isoformat()
    until = today.isoformat()

    url = f"{API_BASE}/{FB_AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": FB_ACCESS_TOKEN,
        "level": "adset",
        "fields": ",".join([
            "adset_id",
            "adset_name",
            "campaign_name",
            "spend",
            "impressions",
            "clicks",
            "cpc",
            "cpm",
            "ctr",
            "actions",
        ]),
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "limit": 100,
    }

    adsets = []
    async with httpx.AsyncClient(timeout=30) as client:
        while url:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            for row in data.get("data", []):
                leads = 0
                if row.get("actions"):
                    for action in row["actions"]:
                        if action["action_type"] in ("lead", "offsite_conversion.fb_pixel_lead"):
                            leads += int(action["value"])

                adsets.append({
                    "adset_id": row["adset_id"],
                    "adset_name": row["adset_name"],
                    "campaign_name": row.get("campaign_name", ""),
                    "spend": float(row.get("spend", 0)),
                    "impressions": int(row.get("impressions", 0)),
                    "clicks": int(row.get("clicks", 0)),
                    "cpc": float(row.get("cpc", 0)),
                    "cpm": float(row.get("cpm", 0)),
                    "ctr": float(row.get("ctr", 0)),
                    "leads": leads,
                })

            # Handle pagination
            paging = data.get("paging", {})
            url = paging.get("next")
            params = {}  # next URL includes params

    return adsets
