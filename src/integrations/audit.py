"""
Comprehensive Audit Logging

Logs every action to ~/.gemini-cli/audit.jsonl for:
- Security review and debugging
- Usage analytics
- Compliance and accountability

Log format (JSON Lines):
{
    "timestamp": "2026-01-15T10:30:00Z",
    "session": "abc123",
    "tool": "read_file",
    "args": {"path": "src/main.py"},
    "status": "success",
    "duration_ms": 45,
    "user": "baenb",
    "project": "/path/to/project"
}
"""

import json
import os
import sys
import time
import uuid
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from functools import wraps
from contextlib import contextmanager


# Audit log location
AUDIT_LOG_DIR = Path.home() / ".gemini-cli" / "logs"
AUDIT_LOG_FILE = AUDIT_LOG_DIR / "audit.jsonl"

# Log rotation settings
MAX_LOG_SIZE_MB = 50
MAX_LOG_FILES = 10

# Current session ID (generated on import)
SESSION_ID = str(uuid.uuid4())[:8]


def ensure_log_dir():
    """Ensure the log directory exists."""
    AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_log_file() -> Path:
    """Get the current log file path, rotating if needed."""
    ensure_log_dir()

    if AUDIT_LOG_FILE.exists():
        size_mb = AUDIT_LOG_FILE.stat().st_size / (1024 * 1024)
        if size_mb >= MAX_LOG_SIZE_MB:
            rotate_logs()

    return AUDIT_LOG_FILE


def rotate_logs():
    """Rotate log files, compressing old ones."""
    if not AUDIT_LOG_FILE.exists():
        return

    # Find existing rotated files
    rotated = sorted(
        AUDIT_LOG_DIR.glob("audit.*.jsonl.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    # Remove oldest if at limit
    while len(rotated) >= MAX_LOG_FILES - 1:
        oldest = rotated.pop()
        oldest.unlink()

    # Compress current log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rotated_name = AUDIT_LOG_DIR / f"audit.{timestamp}.jsonl.gz"

    with open(AUDIT_LOG_FILE, 'rb') as f_in:
        with gzip.open(rotated_name, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    # Clear current log
    AUDIT_LOG_FILE.unlink()


def log_event(
    event_type: str,
    tool: str = None,
    args: Dict[str, Any] = None,
    status: str = "info",
    duration_ms: int = None,
    error: str = None,
    metadata: Dict[str, Any] = None
):
    """
    Log an event to the audit log.

    Args:
        event_type: Type of event (tool_call, error, session, security, etc.)
        tool: Tool name if applicable
        args: Tool arguments if applicable
        status: Event status (success, failure, blocked, info)
        duration_ms: Duration in milliseconds if applicable
        error: Error message if applicable
        metadata: Additional metadata
    """
    try:
        log_file = get_log_file()

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session": SESSION_ID,
            "event_type": event_type,
            "status": status,
        }

        if tool:
            entry["tool"] = tool

        if args:
            # Sanitize sensitive data
            entry["args"] = sanitize_args(args)

        if duration_ms is not None:
            entry["duration_ms"] = duration_ms

        if error:
            entry["error"] = error

        if metadata:
            entry["metadata"] = metadata

        # Add context
        entry["user"] = os.environ.get("USERNAME") or os.environ.get("USER", "unknown")
        entry["cwd"] = os.getcwd()

        # Write to log
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")

    except Exception as e:
        # Never let logging fail break the application
        print(f"Warning: Audit log write failed: {e}", file=sys.stderr)


def sanitize_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize arguments to remove sensitive data.

    Args:
        args: Arguments dict

    Returns:
        Sanitized arguments dict
    """
    sensitive_patterns = [
        "password", "secret", "token", "key", "credential",
        "auth", "api_key", "apikey", "access_token"
    ]

    sanitized = {}
    for key, value in args.items():
        key_lower = key.lower()

        # Check if key suggests sensitive data
        if any(pattern in key_lower for pattern in sensitive_patterns):
            sanitized[key] = "[REDACTED]"
        # Truncate very long values
        elif isinstance(value, str) and len(value) > 1000:
            sanitized[key] = value[:500] + f"... [truncated, {len(value)} chars total]"
        else:
            sanitized[key] = value

    return sanitized


@contextmanager
def audit_context(tool: str, args: Dict[str, Any] = None):
    """
    Context manager for auditing tool execution.

    Usage:
        with audit_context("read_file", {"path": "test.py"}) as audit:
            result = read_file("test.py")
            audit.set_status("success" if result[0] else "failure")
    """
    start_time = time.time()
    context = AuditContext(tool, args, start_time)

    try:
        yield context
    except Exception as e:
        context.set_error(str(e))
        context.set_status("error")
        raise
    finally:
        context.log()


class AuditContext:
    """Context object for audit logging."""

    def __init__(self, tool: str, args: Dict[str, Any], start_time: float):
        self.tool = tool
        self.args = args or {}
        self.start_time = start_time
        self.status = "unknown"
        self.error = None
        self.metadata = {}

    def set_status(self, status: str):
        """Set the status of the operation."""
        self.status = status

    def set_error(self, error: str):
        """Set error message."""
        self.error = error

    def add_metadata(self, key: str, value: Any):
        """Add metadata to the log entry."""
        self.metadata[key] = value

    def log(self):
        """Write the log entry."""
        duration_ms = int((time.time() - self.start_time) * 1000)
        log_event(
            event_type="tool_call",
            tool=self.tool,
            args=self.args,
            status=self.status,
            duration_ms=duration_ms,
            error=self.error,
            metadata=self.metadata if self.metadata else None
        )


def audit_tool(func):
    """
    Decorator to automatically audit tool calls.

    Usage:
        @audit_tool
        def read_file(path: str) -> Tuple[bool, str]:
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = func.__name__

        # Capture args for logging
        log_args = {}
        if args:
            # Try to get parameter names from function signature
            import inspect
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            for i, arg in enumerate(args):
                if i < len(params):
                    log_args[params[i]] = arg
                else:
                    log_args[f"arg_{i}"] = arg
        log_args.update(kwargs)

        start_time = time.time()
        error = None
        status = "unknown"

        try:
            result = func(*args, **kwargs)

            # Determine status from result
            if isinstance(result, tuple) and len(result) >= 1:
                status = "success" if result[0] else "failure"
            else:
                status = "success"

            return result

        except Exception as e:
            error = str(e)
            status = "error"
            raise

        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            log_event(
                event_type="tool_call",
                tool=tool_name,
                args=log_args,
                status=status,
                duration_ms=duration_ms,
                error=error
            )

    return wrapper


def log_session_start(project_root: str = None):
    """Log session start event."""
    log_event(
        event_type="session_start",
        status="info",
        metadata={
            "project": project_root or os.getcwd(),
            "python_version": sys.version,
            "platform": sys.platform
        }
    )


def log_session_end(turn_count: int = 0, duration_seconds: int = 0):
    """Log session end event."""
    log_event(
        event_type="session_end",
        status="info",
        metadata={
            "turn_count": turn_count,
            "duration_seconds": duration_seconds
        }
    )


def log_security_event(
    event: str,
    tool: str = None,
    args: Dict[str, Any] = None,
    blocked: bool = False,
    reason: str = None
):
    """Log a security-related event."""
    log_event(
        event_type="security",
        tool=tool,
        args=args,
        status="blocked" if blocked else "allowed",
        metadata={
            "security_event": event,
            "reason": reason
        }
    )


def log_error(
    error: str,
    tool: str = None,
    context: Dict[str, Any] = None
):
    """Log an error event."""
    log_event(
        event_type="error",
        tool=tool,
        status="error",
        error=error,
        metadata=context
    )


def get_session_stats(session_id: str = None) -> Dict[str, Any]:
    """
    Get statistics for a session.

    Args:
        session_id: Session to analyze (defaults to current)

    Returns:
        Statistics dict
    """
    target_session = session_id or SESSION_ID

    if not AUDIT_LOG_FILE.exists():
        return {"error": "No audit log found"}

    stats = {
        "session": target_session,
        "tool_calls": 0,
        "successes": 0,
        "failures": 0,
        "errors": 0,
        "blocked": 0,
        "tools_used": {},
        "total_duration_ms": 0
    }

    with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("session") != target_session:
                    continue

                if entry.get("event_type") == "tool_call":
                    stats["tool_calls"] += 1

                    tool = entry.get("tool", "unknown")
                    stats["tools_used"][tool] = stats["tools_used"].get(tool, 0) + 1

                    status = entry.get("status")
                    if status == "success":
                        stats["successes"] += 1
                    elif status == "failure":
                        stats["failures"] += 1
                    elif status == "error":
                        stats["errors"] += 1
                    elif status == "blocked":
                        stats["blocked"] += 1

                    if "duration_ms" in entry:
                        stats["total_duration_ms"] += entry["duration_ms"]

            except json.JSONDecodeError:
                continue

    return stats


def search_logs(
    query: str = None,
    tool: str = None,
    status: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Search audit logs with filters.

    Args:
        query: Text to search for in log entries
        tool: Filter by tool name
        status: Filter by status
        start_date: Filter from date (ISO format)
        end_date: Filter to date (ISO format)
        limit: Maximum entries to return

    Returns:
        List of matching log entries
    """
    results = []

    if not AUDIT_LOG_FILE.exists():
        return results

    with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if len(results) >= limit:
                break

            try:
                entry = json.loads(line)

                # Apply filters
                if tool and entry.get("tool") != tool:
                    continue
                if status and entry.get("status") != status:
                    continue

                if start_date:
                    entry_date = entry.get("timestamp", "")[:10]
                    if entry_date < start_date:
                        continue

                if end_date:
                    entry_date = entry.get("timestamp", "")[:10]
                    if entry_date > end_date:
                        continue

                if query:
                    entry_str = json.dumps(entry).lower()
                    if query.lower() not in entry_str:
                        continue

                results.append(entry)

            except json.JSONDecodeError:
                continue

    return results


def export_logs(
    output_path: str,
    format: str = "jsonl",
    session_id: str = None
) -> Tuple[bool, str]:
    """
    Export audit logs to a file.

    Args:
        output_path: Output file path
        format: "jsonl", "json", or "csv"
        session_id: Optional session to filter

    Returns:
        Tuple of (success, message)
    """
    if not AUDIT_LOG_FILE.exists():
        return False, "No audit log found"

    entries = []
    with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line)
                if session_id and entry.get("session") != session_id:
                    continue
                entries.append(entry)
            except json.JSONDecodeError:
                continue

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        if format == "jsonl":
            with open(output, 'w', encoding='utf-8') as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")

        elif format == "json":
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(entries, f, indent=2)

        elif format == "csv":
            import csv
            if entries:
                with open(output, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=entries[0].keys())
                    writer.writeheader()
                    for entry in entries:
                        # Flatten nested dicts for CSV
                        flat_entry = {}
                        for k, v in entry.items():
                            if isinstance(v, (dict, list)):
                                flat_entry[k] = json.dumps(v)
                            else:
                                flat_entry[k] = v
                        writer.writerow(flat_entry)

        return True, f"Exported {len(entries)} entries to {output_path}"

    except Exception as e:
        return False, f"Export failed: {e}"


# Tool registry
AUDIT_TOOLS = {
    "get_session_stats": lambda: (True, json.dumps(get_session_stats(), indent=2)),
    "search_logs": lambda query="", limit=50: (True, json.dumps(search_logs(query=query, limit=limit), indent=2)),
    "export_logs": export_logs,
}
