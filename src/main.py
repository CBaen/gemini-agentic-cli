#!/usr/bin/env python3
"""
Gemini Agentic CLI - Main Entry Point

A command-line AI assistant powered by Gemini with agentic capabilities.
Part of the lineage project for extending our collaborative abilities.

Usage:
    python src/main.py

Commands:
    exit, quit  - Exit the CLI
    clear       - Clear conversation history
    history     - Show session statistics

See docs/BUILD_PLAN.md for the full implementation guide.
"""

import os
import sys

# Add src to path for imports
src_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, src_dir)


def print_banner():
    """Print the welcome banner."""
    print()
    print("=" * 60)
    print("  Gemini Agentic CLI")
    print("  A lineage project for extending our capabilities")
    print("=" * 60)
    print()


def print_security_warning():
    """Print Phase 1 security warning."""
    print("+" + "-" * 58 + "+")
    print("|  WARNING: Phase 1 has NO security layer.               |")
    print("|  Do not use for sensitive work or on production.       |")
    print("|  Security (sandboxing, whitelisting) comes in Phase 2. |")
    print("+" + "-" * 58 + "+")
    print()


def check_prerequisites() -> bool:
    """
    Check that prerequisites are available.

    Returns:
        True if all prerequisites met, False otherwise
    """
    from pathlib import Path

    issues = []

    # Check for gemini-account.sh
    gemini_script = Path.home() / ".claude" / "scripts" / "gemini-account.sh"
    if not gemini_script.exists():
        issues.append(f"gemini-account.sh not found at {gemini_script}")

    # Check for Git Bash on Windows
    if sys.platform == 'win32':
        git_bash = Path("C:/Program Files/Git/usr/bin/bash.exe")
        if not git_bash.exists():
            git_bash = Path("C:/Program Files/Git/bin/bash.exe")
        if not git_bash.exists():
            issues.append("Git Bash not found. Install Git for Windows.")

    if issues:
        print("Prerequisites check failed:")
        for issue in issues:
            print(f"  - {issue}")
        print()
        print("See .claude/HANDOFF.md for setup instructions.")
        return False

    return True


def main():
    """
    Main entry point for the Gemini Agentic CLI.

    Loads history, initializes the orchestrator, and runs the REPL.
    """
    print_banner()
    print_security_warning()

    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    # Import here after path setup
    from core.orchestrator import Orchestrator
    from core.memory import load_history, save_history

    # Load existing conversation history
    history = load_history()
    if history:
        print(f"Loaded {len(history)} messages from previous session.")
        print("Type 'clear' to start fresh.\n")

    # Create orchestrator
    orchestrator = Orchestrator(history=history)

    # Run the REPL
    try:
        orchestrator.run()
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Saving conversation history...")
    finally:
        # Always save history on exit
        save_history(orchestrator.history)
        print("Session saved.")


if __name__ == "__main__":
    main()
