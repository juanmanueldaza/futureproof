"""Insights queue for storing background discoveries.

Insights are stored in SQLite and surfaced when the user opens a chat session.
This provides a non-intrusive notification system - discoveries are queued
rather than pushed as desktop notifications.

Example insights:
- "Found 5 new ML Engineer positions matching your profile"
- "Python demand increased 15% this month on HN hiring threads"
- "New company hiring in your target stack: Anthropic"
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from futureproof.memory.checkpointer import get_data_dir

logger = logging.getLogger(__name__)


class InsightPriority(Enum):
    """Priority levels for insights."""

    LOW = "low"  # Informational, can wait
    MEDIUM = "medium"  # Worth mentioning
    HIGH = "high"  # Important, surface first


@dataclass
class Insight:
    """A single insight from background processing."""

    id: int | None
    category: str  # e.g., "job_market", "tech_trends", "career_update"
    title: str
    content: str
    priority: InsightPriority = InsightPriority.MEDIUM
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    read: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "content": self.content,
            "priority": self.priority.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "read": self.read,
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Insight":
        """Create Insight from database row."""
        return cls(
            id=row["id"],
            category=row["category"],
            title=row["title"],
            content=row["content"],
            priority=InsightPriority(row["priority"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
            read=bool(row["read"]),
        )


class InsightsQueue:
    """SQLite-backed queue for storing and retrieving insights.

    Insights are stored persistently and can be retrieved when
    the user opens a chat session.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize the insights queue.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.futureproof/insights.db
        """
        if db_path is None:
            db_path = get_data_dir() / "insights.db"

        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'medium',
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    read INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_insights_read
                ON insights(read)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_insights_priority
                ON insights(priority)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_insights_created
                ON insights(created_at)
            """)
            conn.commit()

    def add(self, insight: Insight) -> int:
        """Add an insight to the queue.

        Args:
            insight: The insight to add

        Returns:
            The ID of the inserted insight
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO insights
                    (category, title, content, priority, metadata, created_at, read)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    insight.category,
                    insight.title,
                    insight.content,
                    insight.priority.value,
                    json.dumps(insight.metadata) if insight.metadata else None,
                    insight.created_at.isoformat(),
                    int(insight.read),
                ),
            )
            conn.commit()
            insight_id = cursor.lastrowid
            logger.info(f"Added insight: {insight.title} (id={insight_id})")
            return insight_id if insight_id else 0

    def get_unread(self, limit: int = 10) -> list[Insight]:
        """Get unread insights, ordered by priority and recency.

        Args:
            limit: Maximum number of insights to return

        Returns:
            List of unread insights
        """
        with self._get_connection() as conn:
            # Order by priority (high first) then by date (newest first)
            priority_order = "CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"
            cursor = conn.execute(
                f"""
                SELECT * FROM insights
                WHERE read = 0
                ORDER BY {priority_order}, created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [Insight.from_row(row) for row in cursor.fetchall()]

    def get_all(self, include_read: bool = False, limit: int = 50) -> list[Insight]:
        """Get all insights.

        Args:
            include_read: Whether to include already-read insights
            limit: Maximum number of insights to return

        Returns:
            List of insights
        """
        with self._get_connection() as conn:
            if include_read:
                cursor = conn.execute(
                    "SELECT * FROM insights ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM insights WHERE read = 0 ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
            return [Insight.from_row(row) for row in cursor.fetchall()]

    def mark_read(self, insight_id: int) -> None:
        """Mark an insight as read.

        Args:
            insight_id: The ID of the insight to mark as read
        """
        with self._get_connection() as conn:
            conn.execute("UPDATE insights SET read = 1 WHERE id = ?", (insight_id,))
            conn.commit()

    def mark_all_read(self) -> int:
        """Mark all insights as read.

        Returns:
            Number of insights marked as read
        """
        with self._get_connection() as conn:
            cursor = conn.execute("UPDATE insights SET read = 1 WHERE read = 0")
            conn.commit()
            count = cursor.rowcount
            logger.info(f"Marked {count} insights as read")
            return count

    def delete(self, insight_id: int) -> None:
        """Delete an insight.

        Args:
            insight_id: The ID of the insight to delete
        """
        with self._get_connection() as conn:
            conn.execute("DELETE FROM insights WHERE id = ?", (insight_id,))
            conn.commit()

    def clear_old(self, days: int = 30) -> int:
        """Clear insights older than specified days.

        Args:
            days: Delete insights older than this many days

        Returns:
            Number of insights deleted
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM insights WHERE created_at < ?",
                (cutoff.isoformat(),),
            )
            conn.commit()
            count = cursor.rowcount
            logger.info(f"Cleared {count} insights older than {days} days")
            return count

    def count_unread(self) -> int:
        """Get count of unread insights.

        Returns:
            Number of unread insights
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM insights WHERE read = 0")
            result = cursor.fetchone()
            return result[0] if result else 0

    def stats(self) -> dict[str, Any]:
        """Get statistics about the insights queue.

        Returns:
            Dictionary with queue statistics
        """
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM insights").fetchone()[0]
            unread = conn.execute("SELECT COUNT(*) FROM insights WHERE read = 0").fetchone()[0]

            # Count by category
            categories = {}
            for row in conn.execute(
                "SELECT category, COUNT(*) as cnt FROM insights GROUP BY category"
            ):
                categories[row["category"]] = row["cnt"]

            # Count by priority
            priorities = {}
            for row in conn.execute(
                "SELECT priority, COUNT(*) as cnt FROM insights WHERE read = 0 GROUP BY priority"
            ):
                priorities[row["priority"]] = row["cnt"]

            return {
                "total": total,
                "unread": unread,
                "read": total - unread,
                "by_category": categories,
                "unread_by_priority": priorities,
            }


# Convenience functions for creating common insights


def create_job_insight(
    title: str,
    jobs_found: int,
    role: str,
    location: str,
    highlights: list[dict[str, Any]] | None = None,
) -> Insight:
    """Create a job market insight.

    Args:
        title: Insight title
        jobs_found: Number of jobs found
        role: Role searched for
        location: Location searched
        highlights: Notable job listings

    Returns:
        Insight object ready to be queued
    """
    content_parts = [f"Found {jobs_found} positions for {role} in {location}."]

    if highlights:
        content_parts.append("\nHighlights:")
        for job in highlights[:3]:
            company = job.get("company", "Unknown")
            job_title = job.get("title", role)
            content_parts.append(f"  - {job_title} at {company}")

    return Insight(
        id=None,
        category="job_market",
        title=title,
        content="\n".join(content_parts),
        priority=InsightPriority.MEDIUM if jobs_found > 0 else InsightPriority.LOW,
        metadata={
            "jobs_found": jobs_found,
            "role": role,
            "location": location,
            "highlights": highlights or [],
        },
    )


def create_trend_insight(
    title: str,
    content: str,
    technologies: list[str] | None = None,
    priority: InsightPriority = InsightPriority.MEDIUM,
) -> Insight:
    """Create a tech trends insight.

    Args:
        title: Insight title
        content: Trend description
        technologies: Related technologies
        priority: Insight priority

    Returns:
        Insight object ready to be queued
    """
    return Insight(
        id=None,
        category="tech_trends",
        title=title,
        content=content,
        priority=priority,
        metadata={"technologies": technologies or []},
    )


def create_career_insight(
    title: str,
    content: str,
    action_suggested: str | None = None,
    priority: InsightPriority = InsightPriority.MEDIUM,
) -> Insight:
    """Create a career-related insight.

    Args:
        title: Insight title
        content: Insight content
        action_suggested: Suggested action for the user
        priority: Insight priority

    Returns:
        Insight object ready to be queued
    """
    return Insight(
        id=None,
        category="career_update",
        title=title,
        content=content,
        priority=priority,
        metadata={"action_suggested": action_suggested},
    )
