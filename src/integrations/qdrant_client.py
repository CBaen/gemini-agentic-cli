"""
Qdrant Integration - Vector Storage for Collaboration

This module provides the bridge for Claude-Gemini collaboration.
Both models can store research findings and query each other's work.

Dependencies:
    - Qdrant running at localhost:6333
    - qdrant-semantic-search.py script at ~/.claude/scripts/
    - Ollama for embeddings (optional, falls back to simpler methods)

Collections:
    - lineage_research: Shared research findings
    - Project-specific collections for project data
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime


# Script locations
QDRANT_SEARCH_SCRIPT = Path.home() / ".claude" / "scripts" / "qdrant-semantic-search.py"
QDRANT_STORE_SCRIPT = Path.home() / ".claude" / "scripts" / "qdrant-store-gemini.py"

# Default collection
DEFAULT_COLLECTION = "lineage_research"


def check_qdrant_available() -> Tuple[bool, str]:
    """
    Check if Qdrant is running and accessible.

    Returns:
        Tuple of (available: bool, message: str)
    """
    try:
        import urllib.request
        req = urllib.request.urlopen("http://localhost:6333/collections", timeout=5)
        return True, "Qdrant is available"
    except Exception as e:
        return False, f"Qdrant not available: {e}"


def query_qdrant(
    query: str,
    collection: str = DEFAULT_COLLECTION,
    limit: int = 5,
    filters: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    Query Qdrant for semantically similar content.

    Uses the existing qdrant-semantic-search.py script for compatibility
    with the lineage's established patterns.

    Args:
        query: The search query
        collection: Qdrant collection to search (default: lineage_research)
        limit: Maximum results to return
        filters: Optional metadata filters

    Returns:
        Tuple of (success: bool, results_or_error: str)
    """
    if not QDRANT_SEARCH_SCRIPT.exists():
        return False, f"Qdrant search script not found at {QDRANT_SEARCH_SCRIPT}"

    try:
        cmd = [
            "python",
            str(QDRANT_SEARCH_SCRIPT),
            "--collection", collection,
            "--query", query,
            "--limit", str(limit)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(Path.home())
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                return True, output
            return True, "No matching results found."
        else:
            error = result.stderr.strip() if result.stderr else "Unknown error"
            return False, f"Query error: {error}"

    except subprocess.TimeoutExpired:
        return False, "Query timed out after 60 seconds"
    except Exception as e:
        return False, f"Query error: {e}"


def store_to_qdrant(
    content: str,
    collection: str = DEFAULT_COLLECTION,
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    Store content to Qdrant with metadata.

    Args:
        content: The content to store
        collection: Qdrant collection to store in
        metadata: Optional metadata (agent, project, type, etc.)

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Build metadata with defaults
    meta = {
        "agent": "gemini",
        "timestamp": int(datetime.now().timestamp()),
        "project": "gemini-agentic-cli",
    }
    if metadata:
        meta.update(metadata)

    # Use direct Qdrant API for storage (simpler than script)
    try:
        import urllib.request
        import uuid

        # Generate embedding (simplified - in production use Ollama)
        # For now, we'll use the script if available, or a placeholder
        if QDRANT_STORE_SCRIPT.exists():
            # Use existing script
            cmd = [
                "python",
                str(QDRANT_STORE_SCRIPT),
                "--collection", collection,
                "--content", content[:1000],  # Truncate for safety
            ]

            # Add metadata as JSON
            cmd.extend(["--metadata", json.dumps(meta)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return True, "Content stored successfully"
            else:
                # Fall through to direct API
                pass

        # Direct API approach (requires embeddings)
        # This is a simplified version - production should use proper embeddings
        return False, "Storage requires embedding generation. Use lineage-research skill for full functionality."

    except Exception as e:
        return False, f"Storage error: {e}"


def list_collections() -> Tuple[bool, List[str]]:
    """
    List available Qdrant collections.

    Returns:
        Tuple of (success: bool, collections_or_error: list/str)
    """
    try:
        import urllib.request
        import json

        req = urllib.request.urlopen("http://localhost:6333/collections", timeout=10)
        data = json.loads(req.read().decode())

        collections = [c["name"] for c in data.get("result", {}).get("collections", [])]
        return True, collections

    except Exception as e:
        return False, [f"Error listing collections: {e}"]


def get_collection_info(collection: str) -> Tuple[bool, str]:
    """
    Get information about a Qdrant collection.

    Args:
        collection: Collection name

    Returns:
        Tuple of (success: bool, info_or_error: str)
    """
    try:
        import urllib.request
        import json

        url = f"http://localhost:6333/collections/{collection}"
        req = urllib.request.urlopen(url, timeout=10)
        data = json.loads(req.read().decode())

        result = data.get("result", {})
        vectors_count = result.get("vectors_count", 0)
        points_count = result.get("points_count", 0)

        return True, f"Collection '{collection}': {points_count} points, {vectors_count} vectors"

    except Exception as e:
        return False, f"Error getting collection info: {e}"


# ============================================================================
# TOOL WRAPPERS FOR ORCHESTRATOR
# ============================================================================

def query_research(query: str, limit: int = 5) -> Tuple[bool, str]:
    """
    Query the lineage research archive.

    This is the main entry point for Gemini to access shared research.

    Args:
        query: What to search for
        limit: Maximum results

    Returns:
        Tuple of (success: bool, results: str)
    """
    return query_qdrant(query, collection=DEFAULT_COLLECTION, limit=limit)


def store_research(content: str, research_type: str = "general") -> Tuple[bool, str]:
    """
    Store research findings to the archive.

    Args:
        content: The research content
        research_type: Type of research (general, consultation, implementation)

    Returns:
        Tuple of (success: bool, message: str)
    """
    metadata = {
        "research_type": research_type,
        "agent": "gemini",
    }
    return store_to_qdrant(content, metadata=metadata)


# Tool registry entry point
QDRANT_TOOLS = {
    "query_research": query_research,
    "store_research": store_research,
}
