"""
Background job scheduler using APScheduler.

Provides scheduled tasks for:
- Daily TMDB data sync
- Daily popularity updates
- Weekly embedding regeneration
- Weekly vector index rebuild
"""

from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.utils.logger import get_logger


logger = get_logger(__name__)


class JobScheduler:
    """
    Background job scheduler for periodic tasks.

    Uses APScheduler with background scheduler for non-blocking execution.
    """

    def __init__(self) -> None:
        """Initialize job scheduler."""
        self.scheduler = BackgroundScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,  # Combine missed runs
                "max_instances": 1,  # Prevent overlapping runs
                "misfire_grace_time": 3600,  # 1 hour grace period
            },
        )
        self._jobs_registered = False

    def register_jobs(self) -> None:
        """Register all scheduled jobs."""
        if self._jobs_registered:
            logger.warning("Jobs already registered, skipping")
            return

        from app.jobs.pipeline_job import run_pipeline

        # Full pipeline: ingest → embed → index → enrich → score
        # Runs weekly on Sunday at 2 AM UTC.
        # Each stage is idempotent — safe to re-run; only processes rows that need work.
        self.scheduler.add_job(
            run_pipeline,
            trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
            id="weekly_pipeline",
            name="Weekly Data Pipeline (ingest → embed → index → enrich → score)",
            replace_existing=True,
        )

        self._jobs_registered = True
        logger.info("Registered 1 scheduled job: weekly_pipeline (Sun 02:00 UTC)")

    def start(self) -> None:
        """Start the scheduler."""
        if not self._jobs_registered:
            self.register_jobs()

        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Job scheduler started")
            self._log_next_runs()
        else:
            logger.warning("Scheduler already running")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Job scheduler stopped")

    def get_jobs(self) -> list[dict]:
        """
        Get list of all registered jobs.

        Returns:
            List of job information dicts
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                }
            )
        return jobs

    def run_job_now(self, job_id: str) -> bool:
        """
        Manually trigger a job to run immediately.

        Args:
            job_id: ID of the job to run

        Returns:
            True if job was triggered, False if not found
        """
        job = self.scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now(UTC))
            logger.info(f"Manually triggered job: {job_id}")
            return True
        logger.warning(f"Job not found: {job_id}")
        return False

    def _log_next_runs(self) -> None:
        """Log next run times for all jobs."""
        for job in self.scheduler.get_jobs():
            if job.next_run_time:
                logger.info(f"Job '{job.name}' next run: {job.next_run_time.isoformat()}")


# Global scheduler instance
_scheduler: JobScheduler | None = None


def get_scheduler() -> JobScheduler:
    """
    Get global scheduler instance (singleton pattern).

    Returns:
        JobScheduler instance
    """
    global _scheduler  # noqa: PLW0603
    if _scheduler is None:
        _scheduler = JobScheduler()
    return _scheduler


def start_scheduler() -> None:
    """Start the global scheduler if background jobs are enabled."""
    if settings.ENABLE_BACKGROUND_JOBS:
        scheduler = get_scheduler()
        scheduler.start()
        logger.info("Background jobs enabled and started")
    else:
        logger.info("Background jobs disabled in settings")


def stop_scheduler() -> None:
    """Stop the global scheduler."""
    if _scheduler:
        _scheduler.stop()
