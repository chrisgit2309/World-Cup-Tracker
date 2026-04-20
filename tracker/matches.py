"""
Static registry of World Cup 2026 matches to track.
Add or remove entries here as the schedule is confirmed.
Each entry maps a human-readable match name to source-specific IDs/URLs.
"""
from __future__ import annotations
from datetime import datetime, timezone

MATCHES: list[dict] = [
    {
        "name": "USA vs Bolivia",
        "venue": "SoFi Stadium, Los Angeles",
        "date": datetime(2026, 6, 22, 18, 0, tzinfo=timezone.utc),
        "stubhub_url": "https://www.stubhub.com/fifa-world-cup-2026-tickets/",
        "seatgeek_event_id": "",  # fill in when SeatGeek lists the event
    },
    {
        "name": "Mexico vs ???",
        "venue": "Estadio Azteca, Mexico City",
        "date": datetime(2026, 6, 21, 20, 0, tzinfo=timezone.utc),
        "stubhub_url": "https://www.stubhub.com/fifa-world-cup-2026-tickets/",
        "seatgeek_event_id": "",
    },
    {
        "name": "Canada vs ???",
        "venue": "BC Place, Vancouver",
        "date": datetime(2026, 6, 23, 15, 0, tzinfo=timezone.utc),
        "stubhub_url": "https://www.stubhub.com/fifa-world-cup-2026-tickets/",
        "seatgeek_event_id": "",
    },
    {
        "name": "World Cup Final",
        "venue": "MetLife Stadium, New York/New Jersey",
        "date": datetime(2026, 7, 19, 18, 0, tzinfo=timezone.utc),
        "stubhub_url": "https://www.stubhub.com/fifa-world-cup-2026-tickets/",
        "seatgeek_event_id": "",
    },
]
