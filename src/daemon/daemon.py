"""
Gemini Daemon - 24/7 Async Task Processor

Based on doctoral thesis research for continuous Gemini operation.

Features:
- Async task processing with concurrency limits
- Intelligent account/model routing via RateLimiter
- Graceful shutdown handling
- Crash recovery (stuck task reset)
- Configurable polling and pacing
- Logging with rotation support

Security Note:
- Uses asyncio.create_subprocess_exec (safe, no shell injection)
- Arguments passed as list, not interpolated into shell command

Usage:
    # Start the daemon
    python -m src.daemon.daemon

    # Or programmatically
    from src.daemon import GeminiDaemon
    daemon = GeminiDaemon()
    asyncio.run(daemon.run())
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from .task_queue import TaskQueue, TaskStatus
from .rate_limiter import RateLimiter, ModelTier


# Configuration
DEFAULT_LOG_FILE = os.path.expanduser("~/.gemini/daemon.log")
DEFAULT_DB_PATH = os.path.expanduser("~/.gemini/tasks.db")
GEMINI_SCRIPT = Path.home() / ".claude" / "scripts" / "gemini-account.sh"

# Set up logging
def setup_logging(log_file: str = DEFAULT_LOG_FILE) -> logging.Logger:
    """Configure daemon logging."""
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger('GeminiDaemon')
    logger.setLevel(logging.INFO)

    # File handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def get_git_bash() -> Optional[Path]:
    """Find Git Bash on Windows."""
    if sys.platform != 'win32':
        return None
    paths = [
        Path("C:/Program Files/Git/usr/bin/bash.exe"),
        Path("C:/Program Files/Git/bin/bash.exe"),
    ]
    for p in paths:
        if p.exists():
            return p
    return None


class GeminiDaemon:
    """
    24/7 Daemon for processing Gemini tasks.

    Continuously monitors the task queue and processes tasks
    using intelligent rate limiting and account rotation.
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        log_file: str = DEFAULT_LOG_FILE,
        max_concurrent: int = 20,
        poll_interval: float = 1.0,
        task_delay: float = 0.5
    ):
        """
        Initialize the daemon.

        Args:
            db_path: Path to task queue database
            log_file: Path to log file
            max_concurrent: Maximum concurrent task executions
            poll_interval: Seconds between queue polls when idle
            task_delay: Minimum seconds between task starts
        """
        self.running = True
        self.queue = TaskQueue(db_path)
        self.limiter = RateLimiter()
        self.logger = setup_logging(log_file)

        self.max_concurrent = max_concurrent
        self.poll_interval = poll_interval
        self.task_delay = task_delay

        self.active_tasks: set = set()
        self.stats = {
            "started_at": None,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_tokens": 0
        }

        # Custom task handlers (optional)
        self._handlers: Dict[str, Callable] = {}

        # Setup signal handling
        self._setup_signals()

    def _setup_signals(self):
        """Setup graceful shutdown signal handling."""
        def handle_shutdown(signum, frame):
            self.logger.info("Shutdown signal received. Finishing active tasks...")
            self.running = False

        # Windows and Unix compatible
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

    def register_handler(self, task_type: str, handler: Callable):
        """
        Register a custom handler for a task type.

        Args:
            task_type: The task type identifier
            handler: Async callable that processes the task payload
        """
        self._handlers[task_type] = handler

    async def _call_gemini(
        self,
        query: str,
        account: int,
        model: str,
        timeout: int = 120
    ) -> tuple[bool, str]:
        """
        Call Gemini asynchronously using subprocess (safe, no shell injection).

        Args:
            query: The prompt
            account: Account number (1 or 2)
            model: Model ID
            timeout: Request timeout

        Returns:
            Tuple of (success, response)
        """
        if not GEMINI_SCRIPT.exists():
            return False, f"gemini-account.sh not found at {GEMINI_SCRIPT}"

        try:
            if sys.platform == 'win32':
                git_bash = get_git_bash()
                if not git_bash:
                    return False, "Git Bash not found"
                cmd = [str(git_bash), str(GEMINI_SCRIPT), str(account), query, model]
            else:
                cmd = ["bash", str(GEMINI_SCRIPT), str(account), query, model]

            # Safe subprocess execution - arguments as list, no shell interpolation
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return False, "Timeout"

            if proc.returncode != 0:
                error = stderr.decode().strip() if stderr else "Unknown error"
                return False, f"Error: {error}"

            response = stdout.decode().strip()
            return bool(response), response or "Empty response"

        except Exception as e:
            return False, f"Error: {e}"

    async def _process_task(self, task: tuple):
        """
        Process a single task.

        Args:
            task: Tuple of (task_id, priority, model_pref, payload)
        """
        task_id, priority, model_pref, payload = task

        self.logger.info(f"Processing task {task_id[:8]}... (priority={priority})")

        # Get account slot
        account_id = self.limiter.acquire_slot(model_pref)

        if not account_id:
            # Rate limited, return to queue with backoff
            wait_time = self.limiter.get_wait_time(model_pref)
            self.logger.warning(
                f"Rate limited for {model_pref}. Re-queueing {task_id[:8]} "
                f"(wait {wait_time:.1f}s)"
            )
            self.queue.release_task(task_id, delay_seconds=max(10, wait_time))
            return

        try:
            # Check for custom handler
            task_type = payload.get("type", "default")

            if task_type in self._handlers:
                # Use custom handler
                result = await self._handlers[task_type](payload, account_id, model_pref)
            else:
                # Default: Send query to Gemini
                query = payload.get("query", payload.get("prompt", str(payload)))

                # Map model preference to actual model ID
                model_id = self._get_model_id(model_pref)

                success, response = await self._call_gemini(
                    query, account_id, model_id
                )

                if not success:
                    raise Exception(response)

                result = {"response": response, "account": account_id}

            # Success
            self.queue.complete_task(task_id, result)
            self.limiter.record_usage(account_id, model_pref)
            self.stats["tasks_completed"] += 1

            self.logger.info(f"Task {task_id[:8]} completed successfully")

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Task {task_id[:8]} failed: {error_msg}")

            # Check if it's a rate limit error
            if "429" in error_msg or "exhausted" in error_msg.lower():
                # Rate limit - release with longer delay
                self.queue.release_task(task_id, delay_seconds=60)
            else:
                # Other error - use retry logic
                self.queue.fail_task(task_id, error_msg)
                self.stats["tasks_failed"] += 1

    def _get_model_id(self, model_pref: str) -> str:
        """Map model preference to actual model ID."""
        mapping = {
            "flash-lite": "gemini-2.5-flash-lite",
            "flash-3": "gemini-3-flash-preview",
            "pro-3": "gemini-3-pro-preview",
            "pro-25": "gemini-2.5-pro",
            "image-pro": "gemini-3-pro-image-preview",
            "image-flash": "gemini-2.5-flash-image",
        }
        return mapping.get(model_pref, model_pref)

    async def run(self):
        """
        Main daemon loop.

        Continuously polls the queue and processes tasks.
        """
        self.stats["started_at"] = datetime.now().isoformat()
        self.logger.info("Gemini Daemon started. 24/7 monitoring active.")

        # Recover any stuck tasks from previous crash
        self.queue.reset_stuck_tasks()
        self.logger.info("Recovered stuck tasks from previous session")

        try:
            while self.running:
                # Check if we can accept more tasks
                if len(self.active_tasks) >= self.max_concurrent:
                    # Wait for a slot
                    done, _ = await asyncio.wait(
                        self.active_tasks,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    self.active_tasks -= done
                    continue

                # Try to claim a task
                task = self.queue.claim_task()

                if not task:
                    # Queue empty, idle poll
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Schedule task execution
                task_coro = self._process_task(task)
                task_future = asyncio.create_task(task_coro)
                self.active_tasks.add(task_future)
                task_future.add_done_callback(self.active_tasks.discard)

                # Pacing delay
                await asyncio.sleep(self.task_delay)

        except Exception as e:
            self.logger.error(f"Daemon error: {e}")

        finally:
            # Wait for active tasks to complete
            if self.active_tasks:
                self.logger.info(f"Waiting for {len(self.active_tasks)} active tasks...")
                await asyncio.gather(*self.active_tasks, return_exceptions=True)

            self.logger.info("Daemon stopped gracefully")
            self._print_summary()

    def _print_summary(self):
        """Print session summary."""
        self.logger.info("=== Session Summary ===")
        self.logger.info(f"Started: {self.stats['started_at']}")
        self.logger.info(f"Completed: {self.stats['tasks_completed']}")
        self.logger.info(f"Failed: {self.stats['tasks_failed']}")

    def add_task(
        self,
        query: str,
        model_pref: str = "flash-lite",
        priority: int = 100,
        task_type: str = "default",
        **kwargs
    ) -> str:
        """
        Add a task to the queue (convenience method).

        Args:
            query: The prompt/query
            model_pref: Model tier preference
            priority: Task priority (lower = higher)
            task_type: Task type for custom handlers
            **kwargs: Additional payload fields

        Returns:
            Task ID
        """
        payload = {
            "type": task_type,
            "query": query,
            **kwargs
        }
        return self.queue.add_task(model_pref, payload, priority)

    def get_status(self) -> Dict[str, Any]:
        """Get daemon and queue status."""
        return {
            "running": self.running,
            "active_tasks": len(self.active_tasks),
            "max_concurrent": self.max_concurrent,
            "queue_stats": self.queue.get_stats(),
            "rate_limiter": self.limiter.get_stats(),
            "session_stats": self.stats
        }


# CLI entry point
def main():
    """Run the daemon from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Gemini 24/7 Daemon")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Task database path")
    parser.add_argument("--log", default=DEFAULT_LOG_FILE, help="Log file path")
    parser.add_argument("--workers", type=int, default=20, help="Max concurrent tasks")
    parser.add_argument("--status", action="store_true", help="Show status and exit")

    args = parser.parse_args()

    daemon = GeminiDaemon(
        db_path=args.db,
        log_file=args.log,
        max_concurrent=args.workers
    )

    if args.status:
        daemon.limiter.print_status()
        print(f"\nQueue: {daemon.queue.get_stats()}")
        return

    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        print("\nDaemon stopped by user")


if __name__ == "__main__":
    main()
