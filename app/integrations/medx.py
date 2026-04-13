"""MedX system integration — pulls 7-day purchases (deposits taken + cash collected)."""

import httpx
from datetime import datetime, timedelta, timezone
from app.config import MEDX_API_BASE_URL, MEDX_API_KEY

# Both "deposit taken" and "cash collected" count as purchases
PURCHASE_TYPES = ("deposit_taken", "deposit", "cash_collected", "cash", "payment", "purchase")


async def fetch_purchases() -> list[dict]:
    """Fetch all purchases (deposits taken + cash collected) from the last 7 days."""
    if not MEDX_API_BASE_URL or not MEDX_API_KEY:
        return []

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)
    base = MEDX_API_BASE_URL.rstrip("/")

    headers = {
        "Authorization": f"Bearer {MEDX_API_KEY}",
        "Content-Type": "application/json",
    }
    date_params = {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": now.strftime("%Y-%m-%d"),
    }

    all_purchases = []

    async with httpx.AsyncClient(timeout=30) as client:
        # Try the /purchases endpoint first, fall back to /transactions
        for endpoint in ("/purchases", "/transactions", "/deposits"):
            try:
                resp = await client.get(
                    f"{base}{endpoint}", headers=headers, params=date_params
                )
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                data = resp.json()

                # Handle various response shapes
                items = (
                    data.get("purchases")
                    or data.get("transactions")
                    or data.get("deposits")
                    or data.get("data")
                    or data.get("results")
                    or []
                )

                for item in items:
                    record = _parse_purchase(item)
                    if record:
                        all_purchases.append(record)

                # If we got data, don't try other endpoints
                if all_purchases:
                    break

            except httpx.HTTPStatusError:
                continue

    return all_purchases


def _parse_purchase(item: dict) -> dict | None:
    """Parse a single purchase record from the MedX response."""
    # Determine the type — accept anything that looks like a deposit or cash collection
    item_type = (
        item.get("type", "")
        or item.get("transaction_type", "")
        or item.get("category", "")
        or "purchase"
    ).lower().replace(" ", "_")

    # Filter to only purchase types if the API returns mixed data
    if item_type and item_type not in PURCHASE_TYPES:
        # If we can't identify the type, include it anyway (be inclusive)
        if item_type not in ("refund", "void", "cancellation", "adjustment"):
            pass  # include unknown types
        else:
            return None

    return {
        "id": item.get("id", ""),
        "type": item_type,
        "amount": float(item.get("amount", item.get("total", 0))),
        "date": item.get("date", item.get("created_at", item.get("timestamp", ""))),
        "patient_name": item.get("patient_name", item.get("name", item.get("client_name", ""))),
        "patient_email": item.get("patient_email", item.get("email", "")),
        "source": item.get("source", item.get("channel", "")),
    }


def summarise_purchases(purchases: list[dict]) -> dict:
    """Return summary stats split by type."""
    deposits = [p for p in purchases if p["type"] in ("deposit_taken", "deposit")]
    cash = [p for p in purchases if p["type"] in ("cash_collected", "cash")]
    other = [p for p in purchases if p not in deposits and p not in cash]

    total_amount = sum(p["amount"] for p in purchases)
    deposit_amount = sum(p["amount"] for p in deposits)
    cash_amount = sum(p["amount"] for p in cash)

    return {
        "total_purchases": len(purchases),
        "total_amount": round(total_amount, 2),
        "deposits_taken": len(deposits),
        "deposits_amount": round(deposit_amount, 2),
        "cash_collected": len(cash),
        "cash_amount": round(cash_amount, 2),
        "other_purchases": len(other),
        "avg_purchase": round(total_amount / len(purchases), 2) if purchases else 0,
    }
