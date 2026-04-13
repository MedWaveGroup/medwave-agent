"""MedX system integration — pulls 7-day deposits/payments."""

import httpx
from datetime import datetime, timedelta, timezone
from app.config import MEDX_API_BASE_URL, MEDX_API_KEY


async def fetch_deposits() -> list[dict]:
    """Fetch deposits/payments from the last 7 days."""
    if not MEDX_API_BASE_URL or not MEDX_API_KEY:
        return []

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)

    url = f"{MEDX_API_BASE_URL.rstrip('/')}/deposits"
    headers = {
        "Authorization": f"Bearer {MEDX_API_KEY}",
        "Content-Type": "application/json",
    }
    params = {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": now.strftime("%Y-%m-%d"),
    }

    deposits = []
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("deposits", data.get("data", [])):
            deposits.append({
                "id": item.get("id", ""),
                "amount": float(item.get("amount", 0)),
                "date": item.get("date", item.get("created_at", "")),
                "patient_name": item.get("patient_name", item.get("name", "")),
                "patient_email": item.get("patient_email", item.get("email", "")),
                "source": item.get("source", ""),
            })

    return deposits


def summarise_deposits(deposits: list[dict]) -> dict:
    """Return summary stats for the deposit data."""
    total = sum(d["amount"] for d in deposits)
    return {
        "total_deposits": len(deposits),
        "total_amount": round(total, 2),
        "avg_deposit": round(total / len(deposits), 2) if deposits else 0,
    }
