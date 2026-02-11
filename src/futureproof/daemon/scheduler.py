"""Background scheduler for periodic intelligence gathering.

Uses APScheduler 4 AsyncScheduler to run jobs on a schedule:
- Daily job market scans (6 AM)
- Weekly tech trends analysis (Monday 7 AM)
- Periodic career data refresh (every 3 days)

All discoveries are queued as insights for the next chat session.
"""

import logging
from typing import Any

from apscheduler import AsyncScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from futureproof.memory.profile import load_profile

from .insights import (
    Insight,
    InsightPriority,
    InsightsQueue,
    create_job_insight,
    create_trend_insight,
)

logger = logging.getLogger(__name__)


class DaemonScheduler:
    """Manages scheduled background jobs for intelligence gathering.

    Jobs run asynchronously and store their results in the insights queue.
    The scheduler can be started/stopped and persists job state.
    """

    def __init__(self, insights_queue: InsightsQueue | None = None) -> None:
        """Initialize the scheduler.

        Args:
            insights_queue: Queue for storing insights. Creates new one if not provided.
        """
        self.insights = insights_queue or InsightsQueue()
        self._scheduler: AsyncScheduler | None = None
        self._running = False

    async def start(self) -> None:
        """Start the scheduler and register all jobs."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        logger.info("Starting daemon scheduler...")

        self._scheduler = AsyncScheduler()

        # Register scheduled jobs
        await self._register_jobs()

        # Start the scheduler
        await self._scheduler.start_in_background()
        self._running = True

        logger.info("Daemon scheduler started")

    async def _register_jobs(self) -> None:
        """Register all scheduled jobs."""
        if not self._scheduler:
            return

        # Daily job market scan at 6 AM
        await self._scheduler.add_schedule(
            self._job_market_scan,
            CronTrigger(hour=6, minute=0),
            id="daily-job-scan",
        )
        logger.info("Registered: daily-job-scan (6:00 AM)")

        # Weekly tech trends on Monday at 7 AM
        await self._scheduler.add_schedule(
            self._tech_trends_scan,
            CronTrigger(day_of_week="mon", hour=7, minute=0),
            id="weekly-trends",
        )
        logger.info("Registered: weekly-trends (Monday 7:00 AM)")

        # Career data refresh every 3 days
        await self._scheduler.add_schedule(
            self._career_data_refresh,
            IntervalTrigger(days=3),
            id="career-refresh",
        )
        logger.info("Registered: career-refresh (every 3 days)")

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._running or not self._scheduler:
            return

        logger.info("Stopping daemon scheduler...")
        await self._scheduler.stop()
        self._running = False
        logger.info("Daemon scheduler stopped")

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    async def run_job_now(self, job_id: str) -> dict[str, Any]:
        """Run a specific job immediately.

        Args:
            job_id: The job ID to run

        Returns:
            Result of the job execution
        """
        job_map = {
            "daily-job-scan": self._job_market_scan,
            "weekly-trends": self._tech_trends_scan,
            "career-refresh": self._career_data_refresh,
        }

        if job_id not in job_map:
            return {"error": f"Unknown job: {job_id}"}

        logger.info(f"Running job manually: {job_id}")
        try:
            await job_map[job_id]()
            return {"status": "completed", "job_id": job_id}
        except Exception as e:
            logger.exception(f"Job {job_id} failed")
            return {"error": str(e), "job_id": job_id}

    async def get_job_info(self) -> list[dict[str, Any]]:
        """Get information about registered jobs.

        Returns:
            List of job information dictionaries
        """
        jobs = [
            {
                "id": "daily-job-scan",
                "description": "Scan job market for matching positions",
                "schedule": "Daily at 6:00 AM",
            },
            {
                "id": "weekly-trends",
                "description": "Analyze tech trends from Hacker News",
                "schedule": "Monday at 7:00 AM",
            },
            {
                "id": "career-refresh",
                "description": "Refresh career data from all sources",
                "schedule": "Every 3 days",
            },
        ]
        return jobs

    # =========================================================================
    # Job Implementations
    # =========================================================================

    async def _job_market_scan(self) -> None:
        """Scan job market for positions matching user profile."""
        logger.info("Running job market scan...")

        try:
            # Load user profile to get target roles
            profile = load_profile()
            target_roles = profile.target_roles or ["Software Developer"]

            from futureproof.gatherers.market import JobMarketGatherer

            gatherer = JobMarketGatherer()

            total_jobs = 0
            all_highlights: list[dict[str, Any]] = []

            for role in target_roles[:3]:  # Limit to 3 roles
                logger.info(f"Scanning for: {role}")

                try:
                    data = await gatherer.gather(
                        role=role,
                        location="remote",
                        limit=20,
                    )

                    jobs = data.get("job_listings", [])
                    total_jobs += len(jobs)

                    # Collect highlights (first 2 from each role)
                    for job in jobs[:2]:
                        all_highlights.append(
                            {
                                "title": job.get("title", role),
                                "company": job.get("company", "Unknown"),
                                "location": job.get("location", "Remote"),
                                "role_searched": role,
                            }
                        )

                except Exception as e:
                    logger.warning(f"Failed to scan for {role}: {e}")

            # Create insight if we found jobs
            if total_jobs > 0:
                insight = create_job_insight(
                    title=f"Found {total_jobs} new job opportunities",
                    jobs_found=total_jobs,
                    role=", ".join(target_roles[:3]),
                    location="remote",
                    highlights=all_highlights,
                )
                self.insights.add(insight)
                logger.info(f"Job scan complete: {total_jobs} jobs found")
            else:
                logger.info("Job scan complete: no new jobs found")

        except Exception as e:
            logger.exception("Job market scan failed")
            # Still create an insight about the failure
            self.insights.add(
                Insight(
                    id=None,
                    category="system",
                    title="Job market scan encountered issues",
                    content=f"The scheduled job scan had problems: {e}",
                    priority=InsightPriority.LOW,
                )
            )

    async def _tech_trends_scan(self) -> None:
        """Analyze tech trends from Hacker News."""
        logger.info("Running tech trends scan...")

        try:
            from futureproof.gatherers.market import TechTrendsGatherer

            gatherer = TechTrendsGatherer()

            # Get general trends
            data = await gatherer.gather()

            hiring = data.get("hiring_trends", {})
            stories = data.get("trending_stories", [])

            content_parts = []

            # Top technologies
            if hiring.get("top_technologies"):
                top_tech = [t[0] for t in hiring["top_technologies"][:5]]
                content_parts.append(f"Top technologies this week: {', '.join(top_tech)}")

            # Remote percentage
            if hiring.get("remote_percentage"):
                content_parts.append(f"Remote-friendly positions: {hiring['remote_percentage']}%")

            # Trending topics
            if stories:
                trending = [s.get("title", "") for s in stories[:3]]
                content_parts.append("\nTrending discussions:")
                for title in trending:
                    content_parts.append(f"  - {title[:60]}...")

            if content_parts:
                insight = create_trend_insight(
                    title="Weekly Tech Trends Update",
                    content="\n".join(content_parts),
                    technologies=hiring.get("top_technologies", [])[:10],
                )
                self.insights.add(insight)
                logger.info("Tech trends scan complete")
            else:
                logger.info("Tech trends scan complete: no significant trends")

        except Exception as e:
            logger.exception("Tech trends scan failed")
            self.insights.add(
                Insight(
                    id=None,
                    category="system",
                    title="Tech trends scan encountered issues",
                    content=f"The weekly trends scan had problems: {e}",
                    priority=InsightPriority.LOW,
                )
            )

    async def _career_data_refresh(self) -> None:
        """Refresh career data from all sources."""
        logger.info("Running career data refresh...")

        try:
            from futureproof.services import GathererService

            service = GathererService()
            results = service.gather_all()

            successful = sum(1 for s in results.values() if s)
            total = len(results)

            if successful > 0:
                sources = [k for k, v in results.items() if v]
                self.insights.add(
                    Insight(
                        id=None,
                        category="career_update",
                        title=f"Career data refreshed ({successful}/{total} sources)",
                        content=f"Successfully updated: {', '.join(sources)}",
                        priority=InsightPriority.LOW,
                    )
                )
                logger.info(f"Career refresh complete: {successful}/{total} sources updated")
            else:
                logger.warning("Career refresh complete: no sources updated")

        except Exception:
            logger.exception("Career data refresh failed")


# Convenience function for one-off scans
async def run_all_scans() -> dict[str, Any]:
    """Run all scans immediately (useful for testing or manual refresh).

    Returns:
        Results from all scans
    """
    scheduler = DaemonScheduler()
    results = {}

    for job_id in ["daily-job-scan", "weekly-trends", "career-refresh"]:
        result = await scheduler.run_job_now(job_id)
        results[job_id] = result

    return results
