"""SeatGeek scraper — uses the public SeatGeek API (no key required for basic queries)."""
from __future__ import annotations

import os
import re
import requests
from datetime import datetime
from ..models import TicketListing

_API_BASE = "https://api.seatgeek.com/2"
_MAX_PRICE = float(os.getenv("MAX_PRICE_USD", 2000))
_CLIENT_ID = os.getenv("SEATGEEK_CLIENT_ID", "")  # optional; raises rate limit


def scrape(event_id: str, match_name: str, venue: str, match_date: datetime) -> list[TicketListing]:
    listings: list[TicketListing] = []
    params: dict = {
        "event_id": event_id,
        "per_page": 50,
        "sort": "lowest_price.asc",
    }
    if _CLIENT_ID:
        params["client_id"] = _CLIENT_ID

    try:
        resp = requests.get(f"{_API_BASE}/listings", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[seatgeek] fetch failed: {exc}")
        return listings

    for item in data.get("listings", []):
        price = float(item.get("price", 0))
        if not price or price > _MAX_PRICE:
            continue

        listings.append(
            TicketListing(
                source="seatgeek",
                match=match_name,
                venue=venue,
                match_date=match_date,
                section=item.get("section", "N/A"),
                row=item.get("row", "N/A"),
                quantity=item.get("quantity", 1),
                price_usd=price,
                url=f"https://seatgeek.com/e/{event_id}",
            )
        )

    return listings
