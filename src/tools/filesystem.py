"""
Filesystem Tools - Read, Write, List Operations

These are Gemini's "hands" for interacting with files.
Phase 1: Basic operations without security restrictions.
Phase 2: Add sandboxing, path validation, and access controls.

SECURITY WARNING:
    Phase 1 has NO security layer. Do not use on sensitive systems.
    See docs/BUILD_PLAN.md for Phase 2 security implementation.
"""

import os
from pathlib import Path
from typing import Tuple


def read_file(path: str) -> Tuple[bool, str]:
    """
    Read the contents of a file.

    Args:
        path: Path to the file to read

    Returns:
        Tuple of (success: bool, content_or_error: str)
    """
    try:
        file_path = Path(path).expanduser().resolve()

        if not file_path.exists():
            return False, f"File not found: {path}"

        if not file_path.is_file():
            return False, f"Not a file: {path}"

        # Read with UTF-8, fallback to latin-1 for binary-ish files
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = file_path.read_text(encoding='latin-1')

        return True, content

    except PermissionError:
        return False, f"Permission denied: {path}"
    except Exception as e:
        return False, f"Error reading file: {e}"


def write_file(path: str, content: str) -> Tuple[bool, str]:
    """
    Write content to a file, creating parent directories if needed.

    Args:
        path: Path to the file to write
        content: Content to write

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        file_path = Path(path).expanduser().resolve()

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        file_path.write_text(content, encoding='utf-8')

        return True, f"Successfully wrote {len(content)} bytes to {path}"

    except PermissionError:
        return False, f"Permission denied: {path}"
    except Exception as e:
        return False, f"Error writing file: {e}"


def list_directory(path: str = ".") -> Tuple[bool, str]:
    """
    List contents of a directory with type indicators.

    Args:
        path: Path to the directory (defaults to current directory)

    Returns:
        Tuple of (success: bool, listing_or_error: str)
    """
    try:
        dir_path = Path(path).expanduser().resolve()

        if not dir_path.exists():
            return False, f"Directory not found: {path}"

        if not dir_path.is_dir():
            return False, f"Not a directory: {path}"

        entries = []
        for item in sorted(dir_path.iterdir()):
            if item.is_dir():
                entries.append(f"{item.name}/ [dir]")
            elif item.is_file():
                # Include file size for context
                size = item.stat().st_size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size // 1024}KB"
                else:
                    size_str = f"{size // (1024 * 1024)}MB"
                entries.append(f"{item.name} [file, {size_str}]")
            else:
                entries.append(f"{item.name} [other]")

        if not entries:
            return True, "(empty directory)"

        return True, "\n".join(entries)

    except PermissionError:
        return False, f"Permission denied: {path}"
    except Exception as e:
        return False, f"Error listing directory: {e}"


def edit_file(path: str, old_text: str, new_text: str) -> Tuple[bool, str]:
    """
    Make a surgical edit to a file by replacing old_text with new_text.

    This is safer than write_file for modifications because it:
    1. Verifies the old_text exists (prevents blind overwrites)
    2. Only replaces the first occurrence (predictable behavior)
    3. Preserves the rest of the file exactly

    Args:
        path: Path to the file to edit
        old_text: The exact text to find and replace
        new_text: The text to replace it with

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        file_path = Path(path).expanduser().resolve()

        if not file_path.exists():
            return False, f"File not found: {path}"

        if not file_path.is_file():
            return False, f"Not a file: {path}"

        # Read current content
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = file_path.read_text(encoding='latin-1')

        # Check if old_text exists
        if old_text not in content:
            # Provide helpful context
            preview = content[:500] + "..." if len(content) > 500 else content
            return False, f"old_text not found in {path}. File preview:\n{preview}"

        # Check for multiple occurrences (warn but proceed)
        occurrences = content.count(old_text)
        warning = ""
        if occurrences > 1:
            warning = f" (Note: {occurrences} occurrences found, only first replaced)"

        # Replace first occurrence only
        new_content = content.replace(old_text, new_text, 1)

        # Write back
        file_path.write_text(new_content, encoding='utf-8')

        return True, f"Successfully edited {path}{warning}"

    except PermissionError:
        return False, f"Permission denied: {path}"
    except Exception as e:
        return False, f"Error editing file: {e}"


def file_exists(path: str) -> bool:
    """Check if a file exists."""
    try:
        return Path(path).expanduser().resolve().is_file()
    except Exception:
        return False


def directory_exists(path: str) -> bool:
    """Check if a directory exists."""
    try:
        return Path(path).expanduser().resolve().is_dir()
    except Exception:
        return False


# Tool registry entry point - maps tool names to functions
# Used by the orchestrator to dispatch tool calls
FILESYSTEM_TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_directory": list_directory,
}
