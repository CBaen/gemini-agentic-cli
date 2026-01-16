"""
Shell Tool - Command Execution

Allows Gemini to execute shell commands and capture output.
Phase 1: Basic execution without security restrictions.
Phase 2: Add command whitelisting, timeouts, and audit logging.

SECURITY WARNING:
    Phase 1 has NO command restrictions. Do not use on sensitive systems.
    See docs/BUILD_PLAN.md for Phase 2 security implementation.
"""

import subprocess
import os
import sys
from typing import Tuple


# Default timeout for commands (2 minutes)
DEFAULT_TIMEOUT = 120


def run_command(cmd: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[bool, str]:
    """
    Execute a shell command and capture output.

    Args:
        cmd: The command to execute
        timeout: Maximum execution time in seconds (default: 120)

    Returns:
        Tuple of (success: bool, formatted_output: str)
    """
    try:
        # Determine shell based on platform
        if sys.platform == 'win32':
            # On Windows, use cmd.exe or PowerShell
            # Using shell=True allows running batch commands
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )
        else:
            # On Unix, use bash
            result = subprocess.run(
                cmd,
                shell=True,
                executable='/bin/bash',
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )

        # Format output
        output_parts = []

        if result.stdout.strip():
            output_parts.append(f"stdout:\n{result.stdout.strip()}")

        if result.stderr.strip():
            output_parts.append(f"stderr:\n{result.stderr.strip()}")

        output_parts.append(f"exit_code: {result.returncode}")

        output = "\n\n".join(output_parts)

        # Consider non-zero exit as failure, but still return the output
        success = result.returncode == 0

        return success, output

    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout} seconds"

    except FileNotFoundError:
        return False, f"Command not found or shell unavailable"

    except PermissionError:
        return False, f"Permission denied executing command"

    except Exception as e:
        return False, f"Error executing command: {e}"


def run_command_async(cmd: str) -> Tuple[bool, str, subprocess.Popen]:
    """
    Start a command asynchronously (for long-running processes).

    Args:
        cmd: The command to execute

    Returns:
        Tuple of (started: bool, message: str, process: Popen or None)

    Note:
        Caller is responsible for managing the process lifecycle.
        This is for Phase 3 parallel execution support.
    """
    try:
        if sys.platform == 'win32':
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.getcwd()
            )
        else:
            process = subprocess.Popen(
                cmd,
                shell=True,
                executable='/bin/bash',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.getcwd()
            )

        return True, f"Process started with PID {process.pid}", process

    except Exception as e:
        return False, f"Failed to start process: {e}", None


# Tool registry entry point
SHELL_TOOLS = {
    "run_command": run_command,
}
