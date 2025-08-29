"""Scheduler for periodic tasks."""

import asyncio
import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .alerts import run_alert_check
from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


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
        
        self.scheduler.start()
        logger.info(f"Scheduler started - checking alerts every {settings.alerts_check_interval_hours} hours")

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


# Global scheduler instance
scheduler = TaskScheduler()