"""Daemon server for running FutureProof as a background process.

The daemon runs continuously and:
- Executes scheduled intelligence gathering jobs
- Maintains the insights queue
- Can be controlled via CLI commands (start/stop/status)

Usage:
    futureproof daemon start   # Start daemon in background
    futureproof daemon stop    # Stop daemon gracefully
    futureproof daemon status  # Show daemon status
"""

import asyncio
import logging
import os
import signal
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from futureproof.memory.checkpointer import get_data_dir

from .insights import InsightsQueue
from .scheduler import DaemonScheduler

logger = logging.getLogger(__name__)


class DaemonStatus(Enum):
    """Status of the daemon process."""

    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


@dataclass
class DaemonInfo:
    """Information about the daemon state."""

    status: DaemonStatus
    pid: int | None
    started_at: datetime | None
    uptime_seconds: float | None
    pending_insights: int
    jobs_registered: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "pid": self.pid,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "uptime_seconds": self.uptime_seconds,
            "pending_insights": self.pending_insights,
            "jobs_registered": self.jobs_registered,
        }


class DaemonServer:
    """Main daemon server process.

    Manages the scheduler and handles signals for graceful shutdown.
    """

    def __init__(self) -> None:
        """Initialize the daemon server."""
        self.data_dir = get_data_dir()
        self.pid_file = self.data_dir / "daemon.pid"
        self.log_file = self.data_dir / "daemon.log"
        self.started_at: datetime | None = None

        self.insights = InsightsQueue()
        self.scheduler = DaemonScheduler(self.insights)

        self._shutdown_event = asyncio.Event()

    def _setup_logging(self) -> None:
        """Configure logging to file for daemon mode."""
        # Create file handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)

    def _write_pid(self) -> None:
        """Write current PID to file."""
        self.pid_file.write_text(str(os.getpid()))
        logger.info(f"PID file written: {self.pid_file}")

    def _remove_pid(self) -> None:
        """Remove PID file."""
        if self.pid_file.exists():
            self.pid_file.unlink()
            logger.info("PID file removed")

    def _read_pid(self) -> int | None:
        """Read PID from file.

        Returns:
            PID if file exists and is valid, None otherwise
        """
        if not self.pid_file.exists():
            return None

        try:
            pid = int(self.pid_file.read_text().strip())
            return pid
        except (ValueError, OSError):
            return None

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running.

        Args:
            pid: Process ID to check

        Returns:
            True if process is running
        """
        try:
            os.kill(pid, 0)  # Signal 0 = check if process exists
            return True
        except OSError:
            return False

    def get_status(self) -> DaemonInfo:
        """Get current daemon status.

        Returns:
            DaemonInfo with current state
        """
        pid = self._read_pid()
        pending = self.insights.count_unread()

        if pid is None:
            return DaemonInfo(
                status=DaemonStatus.STOPPED,
                pid=None,
                started_at=None,
                uptime_seconds=None,
                pending_insights=pending,
                jobs_registered=0,
            )

        if not self._is_process_running(pid):
            # Stale PID file
            self._remove_pid()
            return DaemonInfo(
                status=DaemonStatus.STOPPED,
                pid=None,
                started_at=None,
                uptime_seconds=None,
                pending_insights=pending,
                jobs_registered=0,
            )

        # Process is running
        uptime = None
        if self.started_at:
            uptime = (datetime.now() - self.started_at).total_seconds()

        return DaemonInfo(
            status=DaemonStatus.RUNNING,
            pid=pid,
            started_at=self.started_at,
            uptime_seconds=uptime,
            pending_insights=pending,
            jobs_registered=3,  # We have 3 scheduled jobs
        )

    async def start(self, foreground: bool = False) -> None:
        """Start the daemon.

        Args:
            foreground: If True, run in foreground (don't daemonize)
        """
        # Check if already running
        existing_pid = self._read_pid()
        if existing_pid and self._is_process_running(existing_pid):
            logger.error(f"Daemon already running with PID {existing_pid}")
            return

        if not foreground:
            # Daemonize
            self._daemonize()

        self._setup_logging()
        logger.info("FutureProof daemon starting...")

        # Write PID file
        self._write_pid()
        self.started_at = datetime.now()

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_signal)

        try:
            # Start the scheduler
            await self.scheduler.start()

            logger.info("Daemon running. Waiting for shutdown signal...")

            # Wait for shutdown signal
            await self._shutdown_event.wait()

        except Exception as e:
            logger.exception(f"Daemon error: {e}")
        finally:
            await self._cleanup()

    def _daemonize(self) -> None:
        """Fork into a daemon process (Unix double-fork)."""
        # First fork
        try:
            pid = os.fork()
            if pid > 0:
                # Parent exits
                sys.exit(0)
        except OSError as e:
            logger.error(f"Fork #1 failed: {e}")
            sys.exit(1)

        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # Second fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            logger.error(f"Fork #2 failed: {e}")
            sys.exit(1)

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()

        with open("/dev/null") as devnull:
            os.dup2(devnull.fileno(), sys.stdin.fileno())

        # Redirect stdout/stderr to log file
        log_fd = os.open(str(self.log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND)
        os.dup2(log_fd, sys.stdout.fileno())
        os.dup2(log_fd, sys.stderr.fileno())

    def _handle_signal(self) -> None:
        """Handle shutdown signal."""
        logger.info("Received shutdown signal")
        self._shutdown_event.set()

    async def _cleanup(self) -> None:
        """Clean up resources on shutdown."""
        logger.info("Cleaning up...")

        # Stop scheduler
        await self.scheduler.stop()

        # Remove PID file
        self._remove_pid()

        logger.info("Daemon stopped")

    def stop(self) -> bool:
        """Stop a running daemon.

        Returns:
            True if daemon was stopped successfully
        """
        pid = self._read_pid()

        if pid is None:
            logger.info("Daemon is not running (no PID file)")
            return False

        if not self._is_process_running(pid):
            logger.info("Daemon is not running (stale PID file)")
            self._remove_pid()
            return False

        # Send SIGTERM
        logger.info(f"Stopping daemon (PID {pid})...")
        try:
            os.kill(pid, signal.SIGTERM)

            # Wait for process to exit (up to 10 seconds)
            for _ in range(20):
                if not self._is_process_running(pid):
                    logger.info("Daemon stopped successfully")
                    return True
                asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.5))

            # Force kill if still running
            logger.warning("Daemon not responding, sending SIGKILL")
            os.kill(pid, signal.SIGKILL)
            return True

        except OSError as e:
            logger.error(f"Failed to stop daemon: {e}")
            return False


def run_daemon(foreground: bool = False) -> None:
    """Run the daemon server.

    Args:
        foreground: If True, run in foreground mode
    """
    server = DaemonServer()
    asyncio.run(server.start(foreground=foreground))


def stop_daemon() -> bool:
    """Stop the daemon server.

    Returns:
        True if daemon was stopped
    """
    server = DaemonServer()
    return server.stop()


def get_daemon_status() -> DaemonInfo:
    """Get daemon status.

    Returns:
        DaemonInfo with current state
    """
    server = DaemonServer()
    return server.get_status()
