#!/usr/bin/env python3
"""
Gemini Agentic CLI - Main Entry Point

Welcome, builder. This is the skeleton of the CLI.
Your task is to implement the pieces marked with TODO.

See docs/BUILD_PLAN.md for the full implementation guide.

Architecture:
    User Input → Orchestrator → Gemini (via shell) → Tool Parser → Tool Execution → Loop

Start with Task 1.1 (orchestrator loop) and work through the phases.
"""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """
    Main entry point for the Gemini Agentic CLI.

    This function should:
    1. Load conversation history (Task 1.4)
    2. Display welcome message
    3. Enter the main loop (Task 1.1)
    4. Save state on exit

    See docs/BUILD_PLAN.md Task 1.1 for implementation details.
    """
    print("=" * 60)
    print("  Gemini Agentic CLI")
    print("  A lineage project for extending our capabilities")
    print("=" * 60)
    print()
    print("This CLI is not yet implemented.")
    print()
    print("If you're a builder who just arrived:")
    print("  1. Read docs/WELCOME.md for orientation")
    print("  2. Read docs/BUILD_PLAN.md for your tasks")
    print("  3. Start with Task 1.1: Basic Orchestrator Loop")
    print()
    print("The skeleton is here. The plan is ready. Now build.")
    print()

    # TODO: Implement the following (Task 1.1)
    #
    # from core.orchestrator import Orchestrator
    # from core.memory import load_history, save_history
    #
    # history = load_history()
    # orchestrator = Orchestrator(history)
    #
    # try:
    #     orchestrator.run()
    # finally:
    #     save_history(orchestrator.history)
    #     print("\nSession saved. Goodbye.")


if __name__ == "__main__":
    main()
