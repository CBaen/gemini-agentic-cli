"""
Color Utilities - ANSI Color Codes for Terminal Output

Simple functions to colorize terminal output for better UX.
Auto-detects TTY support and gracefully degrades to plain text.

Part of the lineage project - treating humans as peers, not users.
"""

import sys


def _supports_color() -> bool:
    """
    Check if the terminal supports ANSI color codes.

    Returns:
        True if colors should be used, False otherwise
    """
    # Check if stdout is a TTY
    if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
        return False

    # Windows 10+ supports ANSI codes
    if sys.platform == 'win32':
        return True

    # Unix-like systems generally support ANSI
    return True


# ANSI escape codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

# Check color support once at module load
_COLOR_ENABLED = _supports_color()


def green(text: str) -> str:
    """
    Make text green (for positive status, thinking, working).

    Args:
        text: The text to colorize

    Returns:
        Colorized text if terminal supports it, plain text otherwise
    """
    if not _COLOR_ENABLED:
        return text
    return f"{GREEN}{text}{RESET}"


def yellow(text: str) -> str:
    """
    Make text yellow (for tool execution, actions in progress).

    Args:
        text: The text to colorize

    Returns:
        Colorized text if terminal supports it, plain text otherwise
    """
    if not _COLOR_ENABLED:
        return text
    return f"{YELLOW}{text}{RESET}"


def red(text: str) -> str:
    """
    Make text red (for errors, timeouts, problems).

    Args:
        text: The text to colorize

    Returns:
        Colorized text if terminal supports it, plain text otherwise
    """
    if not _COLOR_ENABLED:
        return text
    return f"{RED}{text}{RESET}"
