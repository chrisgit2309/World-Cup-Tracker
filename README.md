# World Cup 2026 Ticket Price Tracker

Monitors StubHub and SeatGeek for the cheapest World Cup 2026 tickets and sends a daily HTML email digest to subscribers.

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers (for StubHub scraping)
playwright install chromium

# 4. Configure secrets
cp .env.example .env
# Edit .env and fill in SENDGRID_API_KEY, FROM_EMAIL, SUBSCRIBERS
```

## Usage

```bash
# Scrape now and send the email digest
python main.py

# Scrape now but skip sending email (useful for testing)
python main.py --no-email

# Start the scheduler daemon (runs daily per DIGEST_CRON in .env)
python main.py --schedule
```

## Project structure

```
world-cup-tracker/
├── main.py                  # CLI entry point
├── requirements.txt
├── .env.example             # copy to .env and fill in secrets
├── data/                    # SQLite DB lives here (auto-created, git-ignored)
└── tracker/
    ├── matches.py           # list of matches to track (edit this!)
    ├── models.py            # TicketListing / MatchSummary dataclasses
    ├── db.py                # SQLite persistence (sqlite-utils)
    ├── runner.py            # orchestration: scrape → store → digest
    ├── scheduler.py         # APScheduler daemon
    ├── digest.py            # HTML email template + SendGrid sender
    └── scrapers/
        ├── stubhub.py       # Playwright-based StubHub scraper
        └── seatgeek.py      # SeatGeek public API client
```

## Adding matches

Edit `tracker/matches.py`. For each match provide:
- `stubhub_url` — the specific StubHub listing page URL
- `seatgeek_event_id` — from the SeatGeek event URL (e.g. `https://seatgeek.com/events/**12345678**`)

Leave `seatgeek_event_id` as `""` until the event appears on SeatGeek.

## Email delivery

Uses [SendGrid](https://sendgrid.com) (free tier: 100 emails/day). Set `SENDGRID_API_KEY` and verify your sender address in the SendGrid dashboard. Set `FROM_EMAIL` to that verified address.
