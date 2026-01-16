"""
Task Queue - SQLite-backed Persistent Task Queue

Based on doctoral thesis research for 24/7 Gemini daemon operation.

Features:
- ACID-compliant persistence (survives crashes/restarts)
- Priority levels (0=Critical, 100=Low)
- Dead letter queue for failed tasks
- Exponential backoff for retries
- Stuck task recovery

Schema:
- id: UUID
- priority: Integer (lower = higher priority)
- model_pref: Model tier preference
- payload: JSON task data
- status: PENDING, PROCESSING, COMPLETED, FAILED, DEAD_LETTER
- created_at: Timestamp
- execute_after: Timestamp (for scheduling/backoff)
- attempts: Retry counter
"""

import sqlite3
import json
import uuid
import time
import os
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path


class TaskStatus(Enum):
    """Task status states."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class TaskQueue:
    """
    SQLite-backed persistent task queue for 24/7 daemon operation.

    Provides ACID-compliant task storage that survives crashes and restarts.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the task queue.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.gemini/tasks.db
        """
        if db_path is None:
            db_path = os.path.expanduser("~/.gemini/tasks.db")

        self.db_path = db_path

        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    priority INTEGER DEFAULT 100,
                    model_pref TEXT,
                    payload TEXT,
                    status TEXT,
                    result TEXT,
                    created_at REAL,
                    execute_after REAL DEFAULT 0,
                    attempts INTEGER DEFAULT 0,
                    error_message TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status_prio ON tasks (status, priority)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_execute_after ON tasks (execute_after)")

            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")

    def add_task(
        self,
        model_pref: str,
        payload: Dict[str, Any],
        priority: int = 100,
        execute_after: float = 0
    ) -> str:
        """
        Add a new task to the queue.

        Args:
            model_pref: Preferred model tier (flash-lite, flash-3, pro-3)
            payload: Task data as dictionary
            priority: Priority level (0=Critical, 100=Low)
            execute_after: Unix timestamp for delayed execution

        Returns:
            Task ID (UUID)
        """
        task_id = str(uuid.uuid4())

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO tasks
                   (id, priority, model_pref, payload, status, created_at, execute_after)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (task_id, priority, model_pref, json.dumps(payload),
                 TaskStatus.PENDING.value, time.time(), execute_after)
            )

        return task_id

    def add_batch(
        self,
        tasks: List[Dict[str, Any]],
        model_pref: str = "flash-lite",
        base_priority: int = 100
    ) -> List[str]:
        """
        Add multiple tasks at once.

        Args:
            tasks: List of task payloads
            model_pref: Model tier for all tasks
            base_priority: Base priority (increments by 1 per task)

        Returns:
            List of task IDs
        """
        task_ids = []

        with sqlite3.connect(self.db_path) as conn:
            for i, payload in enumerate(tasks):
                task_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO tasks
                       (id, priority, model_pref, payload, status, created_at, execute_after)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (task_id, base_priority + i, model_pref, json.dumps(payload),
                     TaskStatus.PENDING.value, time.time(), 0)
                )
                task_ids.append(task_id)

        return task_ids

    def claim_task(self) -> Optional[Tuple[str, int, str, Dict]]:
        """
        Atomically claim the highest priority pending task.

        Returns:
            Tuple of (task_id, priority, model_pref, payload) or None
        """
        with sqlite3.connect(self.db_path) as conn:
            # Find candidate
            cursor = conn.execute("""
                SELECT id, priority, model_pref, payload
                FROM tasks
                WHERE status = ? AND execute_after <= ?
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
            """, (TaskStatus.PENDING.value, time.time()))

            row = cursor.fetchone()

            if row:
                task_id = row[0]
                conn.execute(
                    "UPDATE tasks SET status = ? WHERE id = ?",
                    (TaskStatus.PROCESSING.value, task_id)
                )
                return (row[0], row[1], row[2], json.loads(row[3]))

        return None

    def complete_task(self, task_id: str, result: Dict[str, Any]):
        """
        Mark a task as completed with its result.

        Args:
            task_id: The task ID
            result: Result data to store
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, result = ? WHERE id = ?",
                (TaskStatus.COMPLETED.value, json.dumps(result), task_id)
            )

    def fail_task(self, task_id: str, error_msg: str, max_attempts: int = 3):
        """
        Handle a failed task with retry logic.

        Args:
            task_id: The task ID
            error_msg: Error message to record
            max_attempts: Maximum retry attempts before dead letter
        """
        with sqlite3.connect(self.db_path) as conn:
            # Fetch current attempts
            cursor = conn.execute(
                "SELECT attempts FROM tasks WHERE id = ?", (task_id,)
            )
            row = cursor.fetchone()

            if not row:
                return

            attempts = row[0]

            if attempts >= max_attempts:
                status = TaskStatus.DEAD_LETTER.value
                next_try = 0
            else:
                status = TaskStatus.PENDING.value
                # Exponential backoff: 5s, 10s, 20s, 40s...
                next_try = time.time() + (2 ** attempts * 5)

            conn.execute(
                """UPDATE tasks
                   SET status = ?, attempts = attempts + 1,
                       error_message = ?, execute_after = ?
                   WHERE id = ?""",
                (status, error_msg, next_try, task_id)
            )

    def release_task(self, task_id: str, delay_seconds: float = 0):
        """
        Release a claimed task back to pending (e.g., on rate limit).

        Args:
            task_id: The task ID
            delay_seconds: Delay before task can be claimed again
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE tasks SET status = 'PENDING', execute_after = ? WHERE id = ?",
                (time.time() + delay_seconds, task_id)
            )

    def reset_stuck_tasks(self, timeout_seconds: int = 300):
        """
        Reset tasks that have been PROCESSING too long (crashed daemon).

        Args:
            timeout_seconds: Time after which a processing task is considered stuck
        """
        cutoff = time.time() - timeout_seconds

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE tasks
                SET status = 'PENDING', attempts = attempts + 1
                WHERE status = 'PROCESSING' AND created_at < ?
            """, (cutoff,))

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            )
            row = cursor.fetchone()

            if row:
                return {
                    "id": row[0],
                    "priority": row[1],
                    "model_pref": row[2],
                    "payload": json.loads(row[3]) if row[3] else None,
                    "status": row[4],
                    "result": json.loads(row[5]) if row[5] else None,
                    "created_at": row[6],
                    "execute_after": row[7],
                    "attempts": row[8],
                    "error_message": row[9]
                }

        return None

    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics by status."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) FROM tasks GROUP BY status
            """)

            stats = {status.value: 0 for status in TaskStatus}
            for row in cursor:
                stats[row[0]] = row[1]

            return stats

    def get_pending_count(self) -> int:
        """Get count of pending tasks."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status = ?",
                (TaskStatus.PENDING.value,)
            )
            return cursor.fetchone()[0]

    def clear_completed(self, older_than_hours: int = 24):
        """
        Clear completed tasks older than specified hours.

        Args:
            older_than_hours: Age threshold for cleanup
        """
        cutoff = time.time() - (older_than_hours * 3600)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM tasks WHERE status = ? AND created_at < ?",
                (TaskStatus.COMPLETED.value, cutoff)
            )

    def get_dead_letters(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tasks in the dead letter queue for manual review."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, payload, error_message, created_at, attempts
                FROM tasks
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (TaskStatus.DEAD_LETTER.value, limit))

            return [
                {
                    "id": row[0],
                    "payload": json.loads(row[1]) if row[1] else None,
                    "error_message": row[2],
                    "created_at": row[3],
                    "attempts": row[4]
                }
                for row in cursor
            ]
