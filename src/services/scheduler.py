"""Scheduler for periodic tasks."""

import asyncio
import logging
from datetime import time
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from .alerts import run_alert_check
from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


async def run_daily_summary_check() -> None:
    """Run daily summary check for new datasets."""
    logger.info("Starting daily summary check for new datasets")
    try:
        from datetime import date
        from .daily_summary import DailySummaryService
        
        daily_service = DailySummaryService()
        today = date.today()
        
        # Create daily summary for today
        result = await daily_service.discover_and_track_new_datasets(today)
        
        logger.info(
            f"Daily summary completed for {result['date']}: "
            f"{result['new_datasets_count']} new datasets discovered"
        )
        
        await daily_service.close()
        
    except Exception as e:
        logger.error(f"Error during daily summary check: {e}")


class TaskScheduler:
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None

    def start(self) -> None:
        """Start the scheduler with periodic tasks."""
        if not settings.alerts_enabled:
            logger.info("Alerts disabled, scheduler not starting")
            return

        self.scheduler = AsyncIOScheduler()
        
        # Add alert check job
        self.scheduler.add_job(
            run_alert_check,
            trigger=IntervalTrigger(hours=settings.alerts_check_interval_hours),
            id="check_alerts",
            name="Check for data changes and send alerts",
            misfire_grace_time=30,
            coalesce=True,
            max_instances=1
        )
        
        # Add daily summary job - runs every day at 9:00 AM
        self.scheduler.add_job(
            run_daily_summary_check,
            trigger=CronTrigger(hour=9, minute=0),
            id="daily_summary",
            name="Create daily summary of new datasets",
            misfire_grace_time=60,
            coalesce=True,
            max_instances=1
        )
        
        self.scheduler.start()
        logger.info(
            f"Scheduler started - checking alerts every {settings.alerts_check_interval_hours} hours, "
            f"daily summaries at 09:00"
        )

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.scheduler is not None and self.scheduler.running

    async def run_alert_check_now(self) -> None:
        """Manually trigger alert check."""
        logger.info("Manually triggering alert check")
        await run_alert_check()
    
    async def run_daily_summary_now(self) -> None:
        """Manually trigger daily summary check."""
        logger.info("Manually triggering daily summary check")
        await run_daily_summary_check()


# Global scheduler instance
scheduler = TaskScheduler()