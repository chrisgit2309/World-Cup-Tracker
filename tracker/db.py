"""Thin SQLite persistence layer using sqlite-utils."""
from __future__ import annotations

import sqlite_utils
from pathlib import Path
from .models import TicketListing

DB_PATH = Path(__file__).parent.parent / "data" / "tickets.db"


def get_db() -> sqlite_utils.Database:
    DB_PATH.parent.mkdir(exist_ok=True)
    db = sqlite_utils.Database(DB_PATH)
    if "listings" not in db.table_names():
        db["listings"].create(
            {
                "id": int,
                "source": str,
                "match": str,
                "venue": str,
                "match_date": str,
                "section": str,
                "row": str,
                "quantity": int,
                "price_usd": float,
                "url": str,
                "scraped_at": str,
            },
            pk="id",
        )
    return db


def upsert_listings(listings: list[TicketListing]) -> None:
    db = get_db()
    rows = [
        {
            "source": l.source,
            "match": l.match,
            "venue": l.venue,
            "match_date": l.match_date.isoformat(),
            "section": l.section,
            "row": l.row,
            "quantity": l.quantity,
            "price_usd": l.price_usd,
            "url": l.url,
            "scraped_at": l.scraped_at.isoformat(),
        }
        for l in listings
    ]
    db["listings"].insert_all(rows, ignore=True)


def get_cheapest(match: str, limit: int = 5) -> list[dict]:
    db = get_db()
    return list(
        db.execute(
            "SELECT * FROM listings WHERE match = ? ORDER BY price_usd ASC LIMIT ?",
            [match, limit],
        ).fetchall()
    )
