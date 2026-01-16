"""
Session Lifecycle - State Management and Recovery

Manages session state across the CLI lifecycle:
1. Session start - load history, check for crash recovery
2. Session persistence - save state after each turn
3. Session end - write HANDOFF.md, cleanup
4. Crash recovery - detect and recover from ungraceful termination

This follows the lineage patterns used in Claude Code projects.
"""

import os
import json
import atexit
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class SessionState:
    """Current session state."""
    session_id: str
    started_at: str
    project_root: str
    turn_count: int = 0
    last_activity: Optional[str] = None
    current_task: Optional[str] = None
    notes: list = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = []


# Session storage locations
def get_session_dir() -> Path:
    """Get the session storage directory."""
    session_dir = Path.home() / ".gemini-cli" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def get_pid_file() -> Path:
    """Get the PID file path for crash detection."""
    return get_session_dir() / "current.pid"


def get_state_file() -> Path:
    """Get the current session state file."""
    return get_session_dir() / "current_state.json"


# Global session state
_current_session: Optional[SessionState] = None


def generate_session_id() -> str:
    """Generate a unique session ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pid = os.getpid()
    return f"session_{timestamp}_{pid}"


def check_for_crash() -> Optional[Dict[str, Any]]:
    """
    Check if there was an ungraceful termination.

    Returns:
        Previous session state if crash detected, None otherwise
    """
    pid_file = get_pid_file()
    state_file = get_state_file()

    if not pid_file.exists():
        return None

    try:
        # Read the stored PID
        stored_pid = int(pid_file.read_text().strip())

        # Check if that process is still running
        try:
            os.kill(stored_pid, 0)  # Signal 0 checks existence
            # Process still running - not a crash
            return None
        except OSError:
            # Process not running - this was a crash
            pass

        # Load the saved state
        if state_file.exists():
            state_data = json.loads(state_file.read_text())
            return state_data

    except Exception:
        pass

    return None


def start_session(project_root: str) -> SessionState:
    """
    Start a new session.

    Args:
        project_root: The project root directory

    Returns:
        The new session state
    """
    global _current_session

    # Create session state
    _current_session = SessionState(
        session_id=generate_session_id(),
        started_at=datetime.now().isoformat(),
        project_root=str(Path(project_root).resolve()),
    )

    # Write PID file
    pid_file = get_pid_file()
    pid_file.write_text(str(os.getpid()))

    # Save initial state
    save_session_state()

    # Register cleanup on exit
    atexit.register(end_session)

    return _current_session


def save_session_state():
    """Save current session state to disk."""
    if _current_session is None:
        return

    state_file = get_state_file()
    state_data = asdict(_current_session)
    state_data['last_activity'] = datetime.now().isoformat()

    state_file.write_text(json.dumps(state_data, indent=2))


def update_session(turn_count: int = None, current_task: str = None, note: str = None):
    """
    Update session state.

    Args:
        turn_count: Update turn count
        current_task: Update current task description
        note: Add a note to the session
    """
    if _current_session is None:
        return

    if turn_count is not None:
        _current_session.turn_count = turn_count

    if current_task is not None:
        _current_session.current_task = current_task

    if note is not None:
        _current_session.notes.append({
            "timestamp": datetime.now().isoformat(),
            "note": note
        })

    save_session_state()


def end_session():
    """
    End the current session gracefully.

    Cleans up PID file and state file.
    """
    global _current_session

    # Clean up files
    try:
        pid_file = get_pid_file()
        if pid_file.exists():
            pid_file.unlink()
    except Exception:
        pass

    try:
        state_file = get_state_file()
        if state_file.exists():
            state_file.unlink()
    except Exception:
        pass

    _current_session = None


def get_current_session() -> Optional[SessionState]:
    """Get the current session state."""
    return _current_session


# ============================================================================
# HANDOFF.md INTEGRATION
# ============================================================================

def read_handoff(project_root: str) -> Optional[str]:
    """
    Read the HANDOFF.md file from a project.

    Args:
        project_root: The project root directory

    Returns:
        Content of HANDOFF.md or None if not found
    """
    handoff_path = Path(project_root) / ".claude" / "HANDOFF.md"

    if handoff_path.exists():
        try:
            return handoff_path.read_text(encoding='utf-8')
        except Exception:
            pass

    return None


def write_handoff(project_root: str, content: str) -> bool:
    """
    Write to the HANDOFF.md file.

    Args:
        project_root: The project root directory
        content: Content to write

    Returns:
        True if successful
    """
    handoff_path = Path(project_root) / ".claude" / "HANDOFF.md"

    try:
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(content, encoding='utf-8')
        return True
    except Exception:
        return False


def generate_handoff_update(
    session: SessionState,
    completed_tasks: list,
    next_steps: list,
    blockers: list = None,
    notes: list = None
) -> str:
    """
    Generate a HANDOFF.md update section.

    Args:
        session: Current session state
        completed_tasks: List of completed tasks
        next_steps: List of suggested next steps
        blockers: List of blockers (optional)
        notes: Additional notes (optional)

    Returns:
        Formatted markdown section
    """
    lines = [
        f"## Session Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"**Session ID**: {session.session_id}",
        f"**Turns**: {session.turn_count}",
        "",
    ]

    if completed_tasks:
        lines.append("### Completed")
        for task in completed_tasks:
            lines.append(f"- [x] {task}")
        lines.append("")

    if next_steps:
        lines.append("### Next Steps")
        for step in next_steps:
            lines.append(f"- [ ] {step}")
        lines.append("")

    if blockers:
        lines.append("### Blockers")
        for blocker in blockers:
            lines.append(f"- {blocker}")
        lines.append("")

    if notes:
        lines.append("### Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    lines.append("---")
    lines.append("")

    return "\n".join(lines)


# ============================================================================
# MEMORY.md INTEGRATION
# ============================================================================

def read_memory(project_root: str) -> Optional[str]:
    """
    Read the MEMORY.md file from a project.

    Args:
        project_root: The project root directory

    Returns:
        Content of MEMORY.md or None if not found
    """
    memory_path = Path(project_root) / ".claude" / "MEMORY.md"

    if memory_path.exists():
        try:
            return memory_path.read_text(encoding='utf-8')
        except Exception:
            pass

    return None


def append_to_memory(project_root: str, section: str, content: str) -> bool:
    """
    Append a new entry to MEMORY.md.

    Args:
        project_root: The project root directory
        section: Section header (e.g., "Decision", "Learning")
        content: Content to add

    Returns:
        True if successful
    """
    memory_path = Path(project_root) / ".claude" / "MEMORY.md"

    try:
        existing = ""
        if memory_path.exists():
            existing = memory_path.read_text(encoding='utf-8')

        entry = f"\n### {section}\n**Date**: {datetime.now().strftime('%Y-%m-%d')}\n{content}\n"

        # Find insertion point (before "---" separator or at end)
        if "\n---\n" in existing:
            parts = existing.rsplit("\n---\n", 1)
            new_content = parts[0] + entry + "\n---\n" + parts[1]
        else:
            new_content = existing + entry

        memory_path.parent.mkdir(parents=True, exist_ok=True)
        memory_path.write_text(new_content, encoding='utf-8')
        return True

    except Exception:
        return False
