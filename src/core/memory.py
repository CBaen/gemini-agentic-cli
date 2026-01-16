"""
Conversation Memory - Persistent Session State

Manages conversation history persistence between sessions.
History is stored as JSON in ~/.gemini-cli/conversation_history.json

Structure:
    [
        {
            "role": "user" | "assistant" | "tool_result",
            "content": "message content",
            "timestamp": "ISO timestamp",
            "tool_calls": [...] (optional, for assistant messages with tool use)
        },
        ...
    ]
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


# Default storage location
DEFAULT_MEMORY_DIR = Path.home() / ".gemini-cli"
DEFAULT_HISTORY_FILE = DEFAULT_MEMORY_DIR / "conversation_history.json"


def get_memory_dir() -> Path:
    """Get the memory directory, creating it if needed."""
    memory_dir = DEFAULT_MEMORY_DIR
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


def get_history_file() -> Path:
    """Get the history file path."""
    return DEFAULT_HISTORY_FILE


def load_history(history_file: Optional[Path] = None) -> list[dict]:
    """
    Load conversation history from disk.

    Args:
        history_file: Optional custom path (defaults to ~/.gemini-cli/conversation_history.json)

    Returns:
        List of conversation entries (empty list if no history exists)
    """
    file_path = history_file or get_history_file()

    if not file_path.exists():
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            history = json.load(f)
            if isinstance(history, list):
                return history
            # Handle corrupted format
            return []
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load history ({e}). Starting fresh.")
        return []


def save_history(history: list[dict], history_file: Optional[Path] = None) -> bool:
    """
    Save conversation history to disk.

    Args:
        history: List of conversation entries
        history_file: Optional custom path

    Returns:
        True if save succeeded, False otherwise
    """
    file_path = history_file or get_history_file()

    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error saving history: {e}")
        return False


def clear_history(history_file: Optional[Path] = None) -> bool:
    """
    Clear all conversation history.

    Args:
        history_file: Optional custom path

    Returns:
        True if clear succeeded (or no file existed), False on error
    """
    file_path = history_file or get_history_file()

    if not file_path.exists():
        return True

    try:
        file_path.unlink()
        return True
    except IOError as e:
        print(f"Error clearing history: {e}")
        return False


def add_user_message(history: list[dict], content: str) -> list[dict]:
    """
    Add a user message to history.

    Args:
        history: Current conversation history
        content: User's message content

    Returns:
        Updated history (also modifies in place)
    """
    history.append({
        "role": "user",
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    return history


def add_assistant_message(
    history: list[dict],
    content: str,
    tool_calls: Optional[list] = None
) -> list[dict]:
    """
    Add an assistant message to history.

    Args:
        history: Current conversation history
        content: Assistant's response content
        tool_calls: Optional list of tool calls made

    Returns:
        Updated history (also modifies in place)
    """
    entry = {
        "role": "assistant",
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    if tool_calls:
        entry["tool_calls"] = tool_calls

    history.append(entry)
    return history


def add_tool_result(history: list[dict], tool_name: str, result: str) -> list[dict]:
    """
    Add a tool result to history.

    Args:
        history: Current conversation history
        tool_name: Name of the tool that was executed
        result: The formatted tool result

    Returns:
        Updated history (also modifies in place)
    """
    history.append({
        "role": "tool_result",
        "tool": tool_name,
        "content": result,
        "timestamp": datetime.now().isoformat()
    })
    return history


def format_history_for_prompt(history: list[dict], max_entries: int = 50) -> str:
    """
    Format conversation history for inclusion in Gemini prompt.

    Args:
        history: Conversation history
        max_entries: Maximum recent entries to include (to manage context length)

    Returns:
        Formatted string for prompt inclusion
    """
    if not history:
        return ""

    # Take most recent entries
    recent = history[-max_entries:]

    lines = []
    for entry in recent:
        role = entry.get("role", "unknown")
        content = entry.get("content", "")

        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")
        elif role == "tool_result":
            lines.append(f"[{content}]")

    return "\n\n".join(lines)


def get_session_info(history: list[dict]) -> dict:
    """
    Get summary information about the current session.

    Args:
        history: Conversation history

    Returns:
        Dict with session metadata
    """
    if not history:
        return {
            "message_count": 0,
            "first_message": None,
            "last_message": None,
            "tool_calls_count": 0
        }

    tool_calls = sum(
        len(entry.get("tool_calls", []))
        for entry in history
        if entry.get("role") == "assistant"
    )

    return {
        "message_count": len(history),
        "first_message": history[0].get("timestamp"),
        "last_message": history[-1].get("timestamp"),
        "tool_calls_count": tool_calls
    }
