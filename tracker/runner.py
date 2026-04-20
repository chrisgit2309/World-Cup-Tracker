"""Orchestrates scraping → DB storage → digest email."""
from __future__ import annotations

from rich.console import Console
from rich.table import Table
from .matches import MATCHES
from .models import MatchSummary, TicketListing
from .db import upsert_listings, get_cheapest
from .scrapers import stubhub, seatgeek
from .digest import send_digest

console = Console()


def run_once(send_email: bool = True) -> None:
    all_summaries: list[MatchSummary] = []

    for match in MATCHES:
        name = match["name"]
        venue = match["venue"]
        date = match["date"]
        console.print(f"[bold cyan]Scraping:[/] {name}")

        listings: list[TicketListing] = []

        # StubHub
        if match.get("stubhub_url"):
            try:
                sh = stubhub.scrape(match["stubhub_url"], name, venue, date)
                listings.extend(sh)
                console.print(f"  StubHub: {len(sh)} listings")
            except Exception as exc:
                console.print(f"  [red]StubHub error:[/] {exc}")

        # SeatGeek
        if match.get("seatgeek_event_id"):
            try:
                sg = seatgeek.scrape(match["seatgeek_event_id"], name, venue, date)
                listings.extend(sg)
                console.print(f"  SeatGeek: {len(sg)} listings")
            except Exception as exc:
                console.print(f"  [red]SeatGeek error:[/] {exc}")

        if listings:
            upsert_listings(listings)

        cheapest_rows = get_cheapest(name, limit=5)
        cheapest = [
            TicketListing(
                source=r[1], match=r[2], venue=r[3],
                match_date=date, section=r[5], row=r[6],
                quantity=r[7], price_usd=r[8], url=r[9],
            )
            for r in cheapest_rows
        ]
        all_summaries.append(MatchSummary(match=name, match_date=date, venue=venue, cheapest_listings=cheapest))

    _print_summary(all_summaries)

    if send_email:
        send_digest(all_summaries)


def _print_summary(summaries: list[MatchSummary]) -> None:
    for s in summaries:
        table = Table(title=f"{s.match} — {s.venue}")
        table.add_column("Source")
        table.add_column("Section")
        table.add_column("Row")
        table.add_column("Qty", justify="right")
        table.add_column("Price (USD)", justify="right", style="green")
        for t in s.cheapest_listings:
            table.add_row(t.source, t.section, t.row, str(t.quantity), f"${t.price_usd:.2f}")
        console.print(table)
