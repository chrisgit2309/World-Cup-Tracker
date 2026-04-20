from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TicketListing:
    source: str          # "stubhub" | "seatgeek"
    match: str           # e.g. "USA vs Mexico"
    venue: str
    match_date: datetime
    section: str
    row: str
    quantity: int
    price_usd: float
    url: str
    scraped_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MatchSummary:
    match: str
    match_date: datetime
    venue: str
    cheapest_listings: list[TicketListing]
