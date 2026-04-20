"""APScheduler-based daily job runner."""
from __future__ import annotations

import os
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from .runner import run_once

_CRON = os.getenv("DIGEST_CRON", "0 8 * * *")  # default: 8 AM UTC daily


def start() -> None:
    scheduler = BlockingScheduler(timezone="UTC")
    trigger = CronTrigger.from_crontab(_CRON)
    scheduler.add_job(run_once, trigger, id="daily_digest", replace_existing=True)
    print(f"[scheduler] Daily digest scheduled with cron: '{_CRON}' (UTC)")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[scheduler] Shutting down.")
