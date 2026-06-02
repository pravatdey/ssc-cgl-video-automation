"""
Local scheduler - runs the SSC CGL pipeline twice a day.

    morning slot (Reasoning/Quant)  -> 05:00 IST
    evening slot (English/GA)        -> 17:00 IST

For unattended cloud runs use the GitHub Actions workflows instead
(.github/workflows/morning-video.yml and evening-video.yml).

Usage:
    python scheduler.py                 # run forever on the configured schedule
    python scheduler.py --now morning   # run one morning video immediately
    python scheduler.py --now evening   # run one evening video immediately
"""

import argparse
import asyncio
from datetime import datetime

import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from main import CGLVideoPipeline
from src.utils.logger import setup_logger, get_logger


def run_slot(slot: str):
    setup_logger(log_file="logs/scheduler.log")
    logger = get_logger("Scheduler")
    logger.info(f"=== [{slot}] pipeline started at {datetime.now()} ===")
    try:
        pipeline = CGLVideoPipeline()
        result = asyncio.run(pipeline.run(slot=slot))
        if result["success"]:
            logger.info(f"[{slot}] SUCCESS - Part {result.get('part')} {result.get('youtube_url', '')}")
        else:
            logger.error(f"[{slot}] FAILED: {result.get('error')}")
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)


def main():
    parser = argparse.ArgumentParser(description="SSC CGL Scheduler")
    parser.add_argument("--now", choices=["morning", "evening"],
                        help="Run one slot immediately and exit")
    args = parser.parse_args()

    if args.now:
        run_slot(args.now)
        return

    with open("config/settings.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    sched_cfg = cfg.get("schedule", {})
    tz = sched_cfg.get("timezone", "Asia/Kolkata")
    slots = sched_cfg.get("slots", {"morning": "05:00", "evening": "17:00"})

    scheduler = BlockingScheduler(timezone=tz)
    for slot, hhmm in slots.items():
        hour, minute = map(int, hhmm.split(":"))
        scheduler.add_job(run_slot, CronTrigger(hour=hour, minute=minute),
                          args=[slot], id=f"cgl_{slot}")
        print(f"Scheduled {slot} slot at {hhmm} {tz}")

    print("Scheduler running. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")


if __name__ == "__main__":
    main()
