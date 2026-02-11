"""FutureProof daemon module for background intelligence gathering.

This module provides:
- Background scheduler for periodic market scans and data refresh
- Insights queue for storing discoveries between sessions
- Daemon server for running as a background process

Architecture:
    ┌─────────────────────────────────────────────┐
    │              FutureProof Daemon             │
    │  ┌──────────────┐  ┌──────────────────────┐ │
    │  │  Scheduler   │  │    Insights Queue    │ │
    │  │ (APScheduler)│  │      (SQLite)        │ │
    │  └──────────────┘  └──────────────────────┘ │
    │           │                  │              │
    │           └────────┬─────────┘              │
    │                    ▼                        │
    │           ┌──────────────┐                  │
    │           │   Gatherers  │                  │
    │           │  (Market +   │                  │
    │           │   Career)    │                  │
    │           └──────────────┘                  │
    └─────────────────────────────────────────────┘
"""

from .insights import Insight, InsightPriority, InsightsQueue
from .scheduler import DaemonScheduler
from .server import DaemonServer, DaemonStatus

__all__ = [
    # Scheduler
    "DaemonScheduler",
    # Insights
    "InsightsQueue",
    "Insight",
    "InsightPriority",
    # Server
    "DaemonServer",
    "DaemonStatus",
]
