"""
Search Tools - Code Search with Ripgrep

Enables fast pattern matching across the codebase using ripgrep.
This is essential for codebase exploration - reading files one by one is too slow.

Requirements:
    - ripgrep (rg) must be installed and on PATH
    - On Windows: Install via `winget install BurntSushi.ripgrep.MSVC`
    - On Unix: Install via package manager or cargo install ripgrep
"""

import subprocess
import shutil
from typing import Tuple, Optional


def check_ripgrep_available() -> bool:
    """Check if ripgrep is installed and available."""
    return shutil.which('rg') is not None


def search_code(
    pattern: str,
    path: str = ".",
    file_type: Optional[str] = None,
    max_results: int = 50,
    context_lines: int = 0
) -> Tuple[bool, str]:
    """
    Search for a pattern in files using ripgrep.

    Args:
        pattern: Regex pattern to search for
        path: Directory or file to search in (default: current directory)
        file_type: Optional file type filter (e.g., 'py', 'js', 'ts')
        max_results: Maximum number of matches to return (default: 50)
        context_lines: Number of context lines around matches (default: 0)

    Returns:
        Tuple of (success: bool, results_or_error: str)
    """
    if not check_ripgrep_available():
        return False, "ripgrep (rg) not found. Install it with: winget install BurntSushi.ripgrep.MSVC"

    try:
        cmd = [
            'rg',
            '--line-number',      # Show line numbers
            '--no-heading',       # Don't group by file
            '--color', 'never',   # No ANSI colors
            '--max-count', str(max_results),  # Limit results
        ]

        # Add context lines if requested
        if context_lines > 0:
            cmd.extend(['--context', str(context_lines)])

        # Add file type filter if specified
        if file_type:
            cmd.extend(['--type', file_type])

        # Add pattern and path
        cmd.append(pattern)
        cmd.append(path)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 1 minute timeout
        )

        # ripgrep returns 0 for matches, 1 for no matches, 2+ for errors
        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                return True, output
            return True, "No matches found."
        elif result.returncode == 1:
            return True, "No matches found."
        else:
            error = result.stderr.strip() if result.stderr else "Unknown error"
            return False, f"Search error: {error}"

    except subprocess.TimeoutExpired:
        return False, "Search timed out after 60 seconds"
    except Exception as e:
        return False, f"Search error: {e}"


def search_files(
    pattern: str,
    path: str = ".",
    file_type: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Search for files matching a glob pattern.

    Args:
        pattern: Glob pattern for file names (e.g., '*.py', 'test_*')
        path: Directory to search in (default: current directory)
        file_type: Optional file type filter

    Returns:
        Tuple of (success: bool, file_list_or_error: str)
    """
    if not check_ripgrep_available():
        return False, "ripgrep (rg) not found. Install it with: winget install BurntSushi.ripgrep.MSVC"

    try:
        cmd = [
            'rg',
            '--files',           # List files only
            '--glob', pattern,   # Match file names
            '--color', 'never',
        ]

        if file_type:
            cmd.extend(['--type', file_type])

        cmd.append(path)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                files = output.split('\n')
                return True, f"Found {len(files)} files:\n{output}"
            return True, "No matching files found."
        elif result.returncode == 1:
            return True, "No matching files found."
        else:
            error = result.stderr.strip() if result.stderr else "Unknown error"
            return False, f"Search error: {error}"

    except subprocess.TimeoutExpired:
        return False, "Search timed out after 30 seconds"
    except Exception as e:
        return False, f"Search error: {e}"


def grep_count(pattern: str, path: str = ".") -> Tuple[bool, str]:
    """
    Count occurrences of a pattern across files.

    Args:
        pattern: Regex pattern to count
        path: Directory to search in

    Returns:
        Tuple of (success: bool, count_summary_or_error: str)
    """
    if not check_ripgrep_available():
        return False, "ripgrep (rg) not found."

    try:
        cmd = [
            'rg',
            '--count',           # Count matches per file
            '--color', 'never',
            pattern,
            path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                # Sum up the counts
                lines = output.split('\n')
                total = sum(int(line.split(':')[-1]) for line in lines if ':' in line)
                return True, f"Total matches: {total}\n\nPer file:\n{output}"
            return True, "No matches found."
        elif result.returncode == 1:
            return True, "No matches found."
        else:
            error = result.stderr.strip() if result.stderr else "Unknown error"
            return False, f"Count error: {error}"

    except subprocess.TimeoutExpired:
        return False, "Count timed out after 60 seconds"
    except Exception as e:
        return False, f"Count error: {e}"


# Tool registry entry point
SEARCH_TOOLS = {
    "search_code": search_code,
    "search_files": search_files,
    "grep_count": grep_count,
}
