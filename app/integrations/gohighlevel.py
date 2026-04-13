"""Go High Level API integration — pulls 7-day booked appointments."""

import httpx
from datetime import datetime, timedelta, timezone
from app.config import GHL_API_KEY, GHL_LOCATION_ID

API_BASE = "https://services.leadconnectorhq.com"


async def fetch_appointments() -> list[dict]:
    """Fetch booked appointments from the last 7 days."""
    if not GHL_API_KEY or not GHL_LOCATION_ID:
        return []

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)

    url = f"{API_BASE}/calendars/events"
    headers = {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Version": "2021-04-15",
    }
    params = {
        "locationId": GHL_LOCATION_ID,
        "startTime": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "endTime": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    }

    appointments = []
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        for event in data.get("events", []):
            # Extract UTM source to correlate with Facebook ad sets
            contact = event.get("contact", {})
            utm_source = ""
            utm_content = ""
            adset_name = ""

            # GHL stores UTM data on the contact or in custom fields
            if contact:
                utm_source = contact.get("source", "")
                tags = contact.get("tags", [])
                custom_fields = contact.get("customFields", [])

                # Try to extract adset info from custom fields or tags
                for field in custom_fields:
                    if field.get("key", "").lower() in ("utm_content", "adset_name", "ad_set"):
                        adset_name = field.get("value", "")
                    if field.get("key", "").lower() == "utm_source":
                        utm_source = field.get("value", "")

            appointments.append({
                "id": event.get("id", ""),
                "status": event.get("status", ""),
                "start_time": event.get("startTime", ""),
                "contact_name": contact.get("name", ""),
                "contact_email": contact.get("email", ""),
                "utm_source": utm_source,
                "adset_name": adset_name,
            })

    return appointments


def match_appointments_to_adsets(appointments: list[dict], adsets: list[dict]) -> dict[str, int]:
    """Map booked appointments to ad set names. Returns {adset_name: count}."""
    adset_names = {a["adset_name"].lower(): a["adset_name"] for a in adsets}
    counts: dict[str, int] = {a["adset_name"]: 0 for a in adsets}

    for appt in appointments:
        matched_name = appt.get("adset_name", "").strip()

        # Try direct match
        if matched_name.lower() in adset_names:
            canonical = adset_names[matched_name.lower()]
            counts[canonical] = counts.get(canonical, 0) + 1
        # Try fuzzy: check if any adset name is contained in the UTM content
        elif matched_name:
            for key, canonical in adset_names.items():
                if key in matched_name.lower() or matched_name.lower() in key:
                    counts[canonical] = counts.get(canonical, 0) + 1
                    break

    return counts
