"""
Spawn Tools - Parallel Sub-Instance Spawning

Enables Gemini to spawn parallel copies of itself for research.
This is powerful for divide-and-conquer tasks:
- Research multiple topics simultaneously
- Explore different approaches in parallel
- Gather information from multiple angles

Architecture:
    Main Gemini instance spawns sub-instances via gemini-account.sh
    Sub-instances run in parallel (using both accounts)
    Results are aggregated and returned to main instance

Usage:
    TOOL_CALL: spawn_research | queries=["topic 1", "topic 2", "topic 3"]

The tool automatically distributes across accounts 1 and 2.
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Tuple, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import json


# Default gemini script location
GEMINI_SCRIPT = Path.home() / ".claude" / "scripts" / "gemini-account.sh"


def get_git_bash() -> Optional[Path]:
    """Find Git Bash on Windows."""
    if sys.platform != 'win32':
        return None

    paths = [
        Path("C:/Program Files/Git/usr/bin/bash.exe"),
        Path("C:/Program Files/Git/bin/bash.exe"),
    ]
    for p in paths:
        if p.exists():
            return p
    return None


def call_gemini_sync(query: str, account: int, timeout: int = 180) -> Tuple[bool, str]:
    """
    Call Gemini synchronously (for use in threads).

    Args:
        query: The query to send
        account: Account number (1 or 2)
        timeout: Timeout in seconds

    Returns:
        Tuple of (success: bool, response: str)
    """
    if not GEMINI_SCRIPT.exists():
        return False, f"gemini-account.sh not found at {GEMINI_SCRIPT}"

    try:
        if sys.platform == 'win32':
            git_bash = get_git_bash()
            if not git_bash:
                return False, "Git Bash not found"
            cmd = [str(git_bash), str(GEMINI_SCRIPT), str(account), query]
        else:
            cmd = ["bash", str(GEMINI_SCRIPT), str(account), query]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )

        if result.returncode != 0:
            error = result.stderr.strip() if result.stderr else "Unknown error"
            return False, f"Error (exit {result.returncode}): {error}"

        response = result.stdout.strip()
        if not response:
            return False, "Empty response (possibly rate limited)"

        return True, response

    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout}s"
    except Exception as e:
        return False, f"Error: {e}"


def spawn_research(queries: List[str], timeout: int = 180) -> Tuple[bool, str]:
    """
    Spawn parallel Gemini instances to research multiple topics.

    Args:
        queries: List of research queries (1-4 recommended)
        timeout: Timeout per query in seconds

    Returns:
        Tuple of (success: bool, aggregated_results: str)
    """
    if not queries:
        return False, "No queries provided"

    if len(queries) > 6:
        return False, "Too many queries (max 6 to avoid rate limits)"

    results = []
    errors = []

    # Use ThreadPoolExecutor for parallel execution
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit all queries, alternating accounts
        futures = {}
        for i, query in enumerate(queries):
            account = (i % 2) + 1  # Alternate: 1, 2, 1, 2...
            future = executor.submit(call_gemini_sync, query, account, timeout)
            futures[future] = (i, query, account)

        # Collect results as they complete
        for future in as_completed(futures):
            idx, query, account = futures[future]
            try:
                success, response = future.result()
                if success:
                    results.append({
                        "query": query,
                        "account": account,
                        "response": response
                    })
                else:
                    errors.append({
                        "query": query,
                        "account": account,
                        "error": response
                    })
            except Exception as e:
                errors.append({
                    "query": query,
                    "account": account,
                    "error": str(e)
                })

    # Format output
    output_lines = [f"Spawned {len(queries)} parallel research queries:"]
    output_lines.append("")

    for r in sorted(results, key=lambda x: queries.index(x["query"])):
        output_lines.append(f"=== Query: {r['query'][:50]}... (Account {r['account']}) ===")
        output_lines.append(r["response"])
        output_lines.append("")

    if errors:
        output_lines.append("=== Errors ===")
        for e in errors:
            output_lines.append(f"Query: {e['query'][:50]}...")
            output_lines.append(f"Error: {e['error']}")
            output_lines.append("")

    success = len(results) > 0
    return success, "\n".join(output_lines)


def spawn_single(query: str, account: Optional[int] = None) -> Tuple[bool, str]:
    """
    Spawn a single Gemini sub-instance for a specific query.

    Args:
        query: The query to research
        account: Optional account (1 or 2). If not specified, uses account 1.

    Returns:
        Tuple of (success: bool, response: str)
    """
    acc = account or 1
    if acc not in (1, 2):
        return False, "Account must be 1 or 2"

    return call_gemini_sync(query, acc)


def spawn_with_context(
    base_context: str,
    queries: List[str],
    timeout: int = 180
) -> Tuple[bool, str]:
    """
    Spawn parallel queries with shared context prepended.

    Useful when all sub-queries need the same background information.

    Args:
        base_context: Context to prepend to each query
        queries: List of specific questions
        timeout: Timeout per query

    Returns:
        Tuple of (success: bool, aggregated_results: str)
    """
    # Build full queries with context
    full_queries = [f"{base_context}\n\nQuestion: {q}" for q in queries]
    return spawn_research(full_queries, timeout)


# Tool registry entry point
SPAWN_TOOLS = {
    "spawn_research": spawn_research,
    "spawn_single": spawn_single,
    "spawn_with_context": spawn_with_context,
}
