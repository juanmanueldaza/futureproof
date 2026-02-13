"""Daemon management tools for the career agent."""

import logging

from langchain_core.tools import tool
from langgraph.types import interrupt

from ._async import run_async

logger = logging.getLogger(__name__)


@tool
def get_daemon_status() -> str:
    """Get the status of the background intelligence daemon.

    Shows whether the daemon is running, its uptime, and how many
    pending insights are waiting to be reviewed.

    Use this when the user asks about the daemon or background processing status.
    """
    try:
        from futureproof.daemon.server import get_daemon_status as _get_status

        info = _get_status()

        parts = ["Daemon Status:"]
        if info.status.value == "running":
            parts.append(f"  Status: Running (PID {info.pid})")
            if info.uptime_seconds:
                hours = int(info.uptime_seconds // 3600)
                mins = int((info.uptime_seconds % 3600) // 60)
                parts.append(f"  Uptime: {hours}h {mins}m")
        else:
            parts.append("  Status: Stopped")

        parts.append(f"  Pending insights: {info.pending_insights}")
        parts.append(f"  Scheduled jobs: {info.jobs_registered}")

        if info.pending_insights > 0:
            parts.append("\nThere are pending insights. Ask me to show them.")

        return "\n".join(parts)

    except Exception as e:
        logger.exception("Error getting daemon status")
        return f"Error getting daemon status: {e}"


@tool
def get_pending_insights(show_all: bool = False) -> str:
    """Get insights discovered by the background daemon.

    Args:
        show_all: If True, include already-read insights. Default shows only unread.

    The daemon gathers market intelligence in the background and queues
    interesting discoveries as insights. Use this to review them.
    """
    try:
        from futureproof.daemon.insights import InsightsQueue

        queue = InsightsQueue()
        insights = queue.get_all(include_read=show_all)

        if not insights:
            return "No pending insights."

        parts = [f"Insights ({len(insights)}):"]
        for insight in insights:
            read_tag = " (read)" if insight.read else ""
            parts.append(f"\n**[{insight.priority.value.upper()}]{read_tag} {insight.title}**")
            parts.append(f"  {insight.content}")
            parts.append(
                f"  Category: {insight.category} | {insight.created_at.strftime('%Y-%m-%d %H:%M')}"
            )

        return "\n".join(parts)

    except Exception as e:
        logger.exception("Error getting insights")
        return f"Error getting insights: {e}"


@tool
def run_daemon_job(job: str) -> str:
    """Manually run a specific background intelligence job.

    Args:
        job: Job to run — "job-scan" (scan job market), "trends" (tech trends),
             or "refresh" (refresh career data from all sources)

    Use this when the user wants to manually trigger a background scan
    without waiting for the scheduled time.
    """
    job_map = {
        "job-scan": "daily-job-scan",
        "trends": "weekly-trends",
        "refresh": "career-refresh",
    }

    if job not in job_map:
        valid = ", ".join(job_map.keys())
        return f"Unknown job '{job}'. Available jobs: {valid}"

    job_id = job_map[job]

    approved = interrupt(
        {
            "question": f"Run daemon job '{job}' now?",
            "details": f"This will execute the '{job_id}' job immediately.",
        }
    )
    if not approved:
        return "Job cancelled."

    try:
        from futureproof.daemon.scheduler import DaemonScheduler

        scheduler = DaemonScheduler()
        result = run_async(scheduler.run_job_now(job_id))

        if result.get("success"):
            insights_count = result.get("insights_generated", 0)
            parts = [f"Job '{job}' completed successfully."]
            if insights_count:
                parts.append(f"Generated {insights_count} new insights.")
            return "\n".join(parts)

        error = result.get("error", "Unknown error")
        return f"Job '{job}' failed: {error}"

    except Exception as e:
        logger.exception("Error running daemon job")
        return f"Error running daemon job: {e}"
