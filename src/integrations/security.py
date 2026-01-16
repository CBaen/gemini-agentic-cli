"""
Security Layer - Sandboxing, Whitelisting, and Protection

This module provides the security guardrails that make the CLI safe:
1. Path sandboxing - restrict file access to project root
2. Command whitelisting - only allow approved commands
3. Sensitive file protection - block access to credentials
4. Confirmation prompts - ask before destructive operations

IMPORTANT: All file/command operations should go through this layer.
"""

import os
import re
from pathlib import Path
from typing import Tuple, Optional, Callable
from dataclasses import dataclass


@dataclass
class SecurityConfig:
    """Configuration for security layer."""
    project_root: Path
    require_confirmations: bool = True
    strict_mode: bool = True  # If True, block on any security concern


# Global configuration - set during initialization
_config: Optional[SecurityConfig] = None


def initialize_security(project_root: str, require_confirmations: bool = True):
    """
    Initialize the security layer with a project root.

    Args:
        project_root: The root directory for sandboxing
        require_confirmations: Whether to require user confirmation for destructive ops
    """
    global _config
    _config = SecurityConfig(
        project_root=Path(project_root).resolve(),
        require_confirmations=require_confirmations
    )


def get_project_root() -> Path:
    """Get the configured project root."""
    if _config is None:
        # Default to current working directory if not initialized
        return Path.cwd().resolve()
    return _config.project_root


# ============================================================================
# PATH SANDBOXING
# ============================================================================

# Patterns for sensitive files that should never be accessed
SENSITIVE_PATTERNS = [
    r'\.env$',                    # Environment files
    r'\.env\.',                   # .env.local, .env.production, etc.
    r'credentials.*\.json$',      # Credential files
    r'secrets.*\.json$',          # Secret files
    r'oauth.*\.json$',            # OAuth credentials
    r'\.ssh/',                    # SSH directory
    r'\.gnupg/',                  # GPG directory
    r'\.aws/',                    # AWS credentials
    r'\.gcloud/',                 # Google Cloud credentials
    r'id_rsa',                    # SSH private keys
    r'id_ed25519',                # SSH private keys
    r'\.pem$',                    # Certificate files
    r'\.key$',                    # Key files
    r'password',                  # Password files
    r'secret',                    # Secret files
    r'token',                     # Token files
]

# Windows reserved names (cannot be used as filenames)
WINDOWS_RESERVED = [
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
]


def validate_path(requested_path: str) -> Tuple[bool, str, Optional[Path]]:
    """
    Validate that a path is safe to access.

    Checks:
    1. Path is within project root (no traversal)
    2. Path doesn't match sensitive patterns
    3. Path doesn't use Windows reserved names

    Args:
        requested_path: The path to validate

    Returns:
        Tuple of (is_valid: bool, message: str, canonical_path: Path or None)
    """
    project_root = get_project_root()

    try:
        # Expand user (~) and resolve to absolute path
        expanded = Path(requested_path).expanduser()

        # If relative, make it relative to project root
        if not expanded.is_absolute():
            expanded = project_root / expanded

        # Resolve to canonical path (resolves .., symlinks, etc.)
        canonical = expanded.resolve()

        # Check if within project root
        try:
            canonical.relative_to(project_root)
        except ValueError:
            return False, f"Path outside project root: {requested_path} -> {canonical}", None

        # Check for sensitive patterns
        path_str = str(canonical).replace('\\', '/')
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern, path_str, re.IGNORECASE):
                return False, f"Access to sensitive file blocked: {requested_path}", None

        # Check Windows reserved names
        for part in canonical.parts:
            name_upper = part.upper().split('.')[0]  # CON.txt -> CON
            if name_upper in WINDOWS_RESERVED:
                return False, f"Windows reserved name not allowed: {part}", None

        return True, "Path validated", canonical

    except Exception as e:
        return False, f"Path validation error: {e}", None


# ============================================================================
# COMMAND WHITELISTING
# ============================================================================

# Allowed command patterns (regex)
# Each pattern should match the START of the command
ALLOWED_COMMANDS = [
    # Git operations (read-only and basic writes)
    r'^git\s+(status|diff|log|branch|show|blame|rev-parse|ls-files)',
    r'^git\s+(add|commit|checkout|switch|merge|rebase|pull|push|fetch)',
    r'^git\s+(stash|tag|remote|config\s+--get)',

    # Python
    r'^python\s+',
    r'^python3\s+',
    r'^pip\s+(install|list|show|freeze)',
    r'^pip3\s+(install|list|show|freeze)',
    r'^pytest',
    r'^mypy\s+',
    r'^black\s+',
    r'^ruff\s+',

    # Node.js
    r'^node\s+',
    r'^npm\s+(install|test|run|start|build|ci|audit)',
    r'^npx\s+',
    r'^yarn\s+(install|test|run|start|build)',
    r'^pnpm\s+(install|test|run|start|build)',
    r'^bun\s+(install|test|run|start|build)',

    # Common dev tools
    r'^ls(\s|$)',
    r'^dir(\s|$)',
    r'^cat\s+',
    r'^head\s+',
    r'^tail\s+',
    r'^grep\s+',
    r'^rg\s+',       # ripgrep
    r'^find\s+',
    r'^wc\s+',
    r'^sort\s+',
    r'^uniq\s+',
    r'^diff\s+',
    r'^echo\s+',
    r'^pwd$',
    r'^whoami$',
    r'^date$',
    r'^which\s+',
    r'^where\s+',

    # Build tools
    r'^make(\s|$)',
    r'^cmake\s+',
    r'^cargo\s+',
    r'^go\s+(build|run|test|mod|get)',
    r'^docker\s+(ps|images|build|run|logs)',
    r'^docker-compose\s+',
]

# Explicitly blocked commands (these override allowed patterns)
BLOCKED_COMMANDS = [
    r'rm\s+-rf\s+/',           # Recursive delete from root
    r'rm\s+-rf\s+\*',          # Recursive delete all
    r'rm\s+-rf\s+~',           # Recursive delete home
    r'rmdir\s+/s\s+',          # Windows recursive delete
    r'del\s+/s\s+/q',          # Windows quiet delete
    r'format\s+',              # Disk format
    r'mkfs\.',                 # Make filesystem
    r'dd\s+if=',               # Disk dump (can destroy data)
    r'chmod\s+777',            # Overly permissive
    r'chmod\s+-R\s+777',       # Recursive overly permissive
    r':\(\)\{',                # Fork bomb
    r'>\s*/dev/sd',            # Write to disk device
    r'curl.*\|\s*(ba)?sh',     # Piping curl to shell
    r'wget.*\|\s*(ba)?sh',     # Piping wget to shell
    r'eval\s+',                # Eval (code injection risk)
    r'\$\(',                   # Command substitution (in some contexts)
    r'`',                      # Backtick command substitution
    r';\s*rm\s+',              # Command chaining with rm
    r'&&\s*rm\s+',             # Command chaining with rm
    r'\|\s*rm\s+',             # Piping to rm
]


def validate_command(cmd: str) -> Tuple[bool, str]:
    """
    Validate that a command is safe to execute.

    Checks:
    1. Command matches at least one allowed pattern
    2. Command doesn't match any blocked patterns

    Args:
        cmd: The command to validate

    Returns:
        Tuple of (is_allowed: bool, message: str)
    """
    cmd_stripped = cmd.strip()

    # Check blocked patterns first (they override allowed)
    for pattern in BLOCKED_COMMANDS:
        if re.search(pattern, cmd_stripped, re.IGNORECASE):
            return False, f"Command blocked for safety: matches '{pattern}'"

    # Check if command matches any allowed pattern
    for pattern in ALLOWED_COMMANDS:
        if re.match(pattern, cmd_stripped, re.IGNORECASE):
            return True, "Command allowed"

    return False, f"Command not in whitelist. Allowed patterns: git, python, npm, etc."


# ============================================================================
# CONFIRMATION PROMPTS
# ============================================================================

# Operations that require user confirmation
OPERATIONS_REQUIRING_CONFIRMATION = [
    'write_file',           # Creating/overwriting files
    'edit_file',            # Modifying files
    'delete_file',          # Deleting files
    'delete_directory',     # Deleting directories
    'move_file',            # Moving/renaming files
    'copy_file',            # Copying files
    'create_directory',     # Creating directories
    'run_command',          # Any shell command
]

# Confirmation callback - set by orchestrator
_confirmation_callback: Optional[Callable[[str], bool]] = None


def set_confirmation_callback(callback: Callable[[str], bool]):
    """
    Set the callback function for confirmation prompts.

    Args:
        callback: Function that takes a message and returns True/False
    """
    global _confirmation_callback
    _confirmation_callback = callback


def request_confirmation(operation: str, details: str) -> bool:
    """
    Request user confirmation for a potentially destructive operation.

    Args:
        operation: The operation name (e.g., 'write_file')
        details: Details about the operation

    Returns:
        True if confirmed, False if denied
    """
    if _config and not _config.require_confirmations:
        return True

    if _confirmation_callback is None:
        # No callback set - default to allowing
        return True

    message = f"{operation}: {details}"
    return _confirmation_callback(message)


# ============================================================================
# COMBINED SECURITY CHECK
# ============================================================================

@dataclass
class SecurityCheckResult:
    """Result of a security check."""
    allowed: bool
    message: str
    requires_confirmation: bool = False
    canonical_path: Optional[Path] = None


def check_file_operation(
    operation: str,
    path: str,
    content: Optional[str] = None
) -> SecurityCheckResult:
    """
    Check if a file operation is allowed.

    Args:
        operation: 'read', 'write', 'edit', 'delete', 'move', 'copy', 'create', 'list'
        path: The file/directory path
        content: Optional content for write operations

    Returns:
        SecurityCheckResult with allowed status and details
    """
    # Validate path
    is_valid, message, canonical = validate_path(path)
    if not is_valid:
        return SecurityCheckResult(
            allowed=False,
            message=message,
            canonical_path=None
        )

    # Check if confirmation needed (all modifying operations)
    needs_confirm = operation in ['write', 'edit', 'delete', 'move', 'copy', 'create']

    return SecurityCheckResult(
        allowed=True,
        message="Operation allowed",
        requires_confirmation=needs_confirm,
        canonical_path=canonical
    )


def check_command(cmd: str) -> SecurityCheckResult:
    """
    Check if a shell command is allowed.

    Args:
        cmd: The command to check

    Returns:
        SecurityCheckResult with allowed status and details
    """
    is_allowed, message = validate_command(cmd)

    return SecurityCheckResult(
        allowed=is_allowed,
        message=message,
        requires_confirmation=is_allowed  # All allowed commands need confirmation
    )
