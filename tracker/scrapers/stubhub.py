"""StubHub scraper using Playwright for JS-rendered pages."""
from __future__ import annotations

import os
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from ..models import TicketListing

# World Cup 2026 StubHub search base URL
_BASE = "https://www.stubhub.com/world-cup-2026-tickets/grouping/15895/"

_MAX_PRICE = float(os.getenv("MAX_PRICE_USD", 2000))


def scrape(match_url: str, match_name: str, venue: str, match_date: datetime) -> list[TicketListing]:
    listings: list[TicketListing] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page.goto(match_url, wait_until="networkidle", timeout=30_000)

        cards = page.query_selector_all("[data-testid='listing-item']")
        for card in cards:
            try:
                price_text = card.query_selector("[data-testid='listing-price']").inner_text()
                price = float(re.sub(r"[^\d.]", "", price_text))
                if price > _MAX_PRICE:
                    continue

                section = (card.query_selector("[data-testid='listing-section']") or card).inner_text()
                row_el = card.query_selector("[data-testid='listing-row']")
                row = row_el.inner_text() if row_el else "N/A"
                qty_el = card.query_selector("[data-testid='listing-qty']")
                qty = int(re.search(r"\d+", qty_el.inner_text()).group()) if qty_el else 1
                link_el = card.query_selector("a")
                url = "https://www.stubhub.com" + link_el.get_attribute("href") if link_el else match_url

                listings.append(
                    TicketListing(
                        source="stubhub",
                        match=match_name,
                        venue=venue,
                        match_date=match_date,
                        section=section,
                        row=row,
                        quantity=qty,
                        price_usd=price,
                        url=url,
                    )
                )
            except Exception:
                continue

        browser.close()

    return listings
