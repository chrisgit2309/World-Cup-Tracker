"""Entry point.

Usage:
  python main.py             # run once immediately (scrape + send email)
  python main.py --schedule  # start the APScheduler daemon (runs on DIGEST_CRON)
  python main.py --no-email  # run once, print results only (no email sent)
"""
import argparse
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser(description="World Cup 2026 Ticket Price Tracker")
parser.add_argument("--schedule", action="store_true", help="Run as a scheduled daemon")
parser.add_argument("--no-email", action="store_true", help="Scrape and print, skip email")
args = parser.parse_args()

if args.schedule:
    from tracker.scheduler import start
    start()
else:
    from tracker.runner import run_once
    run_once(send_email=not args.no_email)
