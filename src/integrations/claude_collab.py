"""
Claude Collaboration Protocol - Asynchronous Handoffs

This module enables asynchronous collaboration between Gemini and Claude:

1. Gemini does research, stores findings to Qdrant
2. Gemini writes summary to HANDOFF.md with CLAUDE_TURN: READY
3. Claude Code reads HANDOFF.md, queries Qdrant for context
4. Claude makes decisions, updates HANDOFF.md with GEMINI_TURN: READY

This allows the two models to work together on complex tasks,
each leveraging their strengths:
- Gemini: Research, exploration, drafting, image work
- Claude: Architecture decisions, complex reasoning, quality review

The protocol uses:
- HANDOFF.md for turn coordination
- Qdrant for shared context
- MEMORY.md for accumulated knowledge
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional, Dict, Any


# Turn markers
CLAUDE_TURN_MARKER = "CLAUDE_TURN: READY"
GEMINI_TURN_MARKER = "GEMINI_TURN: READY"


def get_project_handoff_path(project_root: Optional[str] = None) -> Path:
    """Get the HANDOFF.md path for a project."""
    root = Path(project_root or os.getcwd())
    return root / ".claude" / "HANDOFF.md"


def get_project_memory_path(project_root: Optional[str] = None) -> Path:
    """Get the MEMORY.md path for a project."""
    root = Path(project_root or os.getcwd())
    return root / ".claude" / "MEMORY.md"


def check_turn(project_root: Optional[str] = None) -> Tuple[bool, str]:
    """
    Check whose turn it is.

    Returns:
        Tuple of (success: bool, current_turn: str)
        current_turn is one of: "gemini", "claude", "none"
    """
    handoff_path = get_project_handoff_path(project_root)

    if not handoff_path.exists():
        return True, "none"

    try:
        content = handoff_path.read_text(encoding='utf-8')

        # Find the last marker
        claude_pos = content.rfind(CLAUDE_TURN_MARKER)
        gemini_pos = content.rfind(GEMINI_TURN_MARKER)

        if claude_pos > gemini_pos:
            return True, "claude"
        elif gemini_pos > claude_pos:
            return True, "gemini"
        else:
            return True, "none"

    except Exception as e:
        return False, f"Error reading handoff: {e}"


def signal_claude_turn(
    project_root: Optional[str] = None,
    summary: str = "",
    research_topics: list = None,
    questions: list = None
) -> Tuple[bool, str]:
    """
    Signal that Gemini is done and it's Claude's turn.

    Args:
        project_root: Project root directory
        summary: Summary of what Gemini accomplished
        research_topics: Topics stored to Qdrant for Claude to query
        questions: Questions for Claude to consider

    Returns:
        Tuple of (success: bool, message: str)
    """
    handoff_path = get_project_handoff_path(project_root)

    try:
        # Read existing content
        existing = ""
        if handoff_path.exists():
            existing = handoff_path.read_text(encoding='utf-8')

        # Build handoff section
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            "",
            "---",
            "",
            f"## Gemini Handoff - {timestamp}",
            "",
            CLAUDE_TURN_MARKER,
            "",
        ]

        if summary:
            lines.append("### Summary")
            lines.append(summary)
            lines.append("")

        if research_topics:
            lines.append("### Research Topics (stored in Qdrant)")
            for topic in research_topics:
                lines.append(f"- {topic}")
            lines.append("")
            lines.append("Query with: `python ~/.claude/scripts/qdrant-semantic-search.py --collection lineage_research --query \"your query\"`")
            lines.append("")

        if questions:
            lines.append("### Questions for Claude")
            for q in questions:
                lines.append(f"- [ ] {q}")
            lines.append("")

        # Append to file
        new_content = existing + "\n".join(lines)
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(new_content, encoding='utf-8')

        return True, f"Signaled Claude's turn. Handoff written to {handoff_path}"

    except Exception as e:
        return False, f"Error signaling Claude turn: {e}"


def signal_gemini_turn(
    project_root: Optional[str] = None,
    instructions: str = "",
    decisions: list = None,
    tasks: list = None
) -> Tuple[bool, str]:
    """
    Signal that Claude is done and it's Gemini's turn.

    This would typically be called by Claude Code, not this CLI,
    but included for completeness.

    Args:
        project_root: Project root directory
        instructions: Instructions for Gemini
        decisions: Decisions Claude made
        tasks: Tasks for Gemini to work on

    Returns:
        Tuple of (success: bool, message: str)
    """
    handoff_path = get_project_handoff_path(project_root)

    try:
        existing = ""
        if handoff_path.exists():
            existing = handoff_path.read_text(encoding='utf-8')

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            "",
            "---",
            "",
            f"## Claude Handoff - {timestamp}",
            "",
            GEMINI_TURN_MARKER,
            "",
        ]

        if instructions:
            lines.append("### Instructions")
            lines.append(instructions)
            lines.append("")

        if decisions:
            lines.append("### Decisions Made")
            for d in decisions:
                lines.append(f"- {d}")
            lines.append("")

        if tasks:
            lines.append("### Tasks for Gemini")
            for t in tasks:
                lines.append(f"- [ ] {t}")
            lines.append("")

        new_content = existing + "\n".join(lines)
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(new_content, encoding='utf-8')

        return True, f"Signaled Gemini's turn. Handoff written to {handoff_path}"

    except Exception as e:
        return False, f"Error signaling Gemini turn: {e}"


def read_handoff_context(project_root: Optional[str] = None) -> Tuple[bool, str]:
    """
    Read the current handoff context.

    Returns the last handoff section from HANDOFF.md.

    Returns:
        Tuple of (success: bool, context: str)
    """
    handoff_path = get_project_handoff_path(project_root)

    if not handoff_path.exists():
        return False, "No HANDOFF.md found"

    try:
        content = handoff_path.read_text(encoding='utf-8')

        # Find the last handoff section
        sections = content.split("---")
        if len(sections) > 1:
            return True, "---".join(sections[-2:])  # Last section with separator
        return True, content

    except Exception as e:
        return False, f"Error reading handoff: {e}"


def add_to_shared_memory(
    project_root: Optional[str] = None,
    category: str = "Learning",
    content: str = "",
    source: str = "gemini"
) -> Tuple[bool, str]:
    """
    Add an entry to shared MEMORY.md.

    Both Gemini and Claude can add learnings here.

    Args:
        project_root: Project root directory
        category: Category (Learning, Decision, Gotcha, etc.)
        content: The content to add
        source: Who added it (gemini or claude)

    Returns:
        Tuple of (success: bool, message: str)
    """
    memory_path = get_project_memory_path(project_root)

    try:
        existing = ""
        if memory_path.exists():
            existing = memory_path.read_text(encoding='utf-8')

        timestamp = datetime.now().strftime("%Y-%m-%d")
        entry = f"""
### {category}
**Date**: {timestamp}
**Source**: {source}

{content}

"""

        # Find insertion point (before final "---" if exists)
        if "\n---\n" in existing and existing.rstrip().endswith("---"):
            # Insert before final separator
            parts = existing.rsplit("\n---\n", 1)
            new_content = parts[0] + entry + "\n---\n" + parts[1]
        else:
            new_content = existing + entry

        memory_path.parent.mkdir(parents=True, exist_ok=True)
        memory_path.write_text(new_content, encoding='utf-8')

        return True, f"Added {category} to MEMORY.md"

    except Exception as e:
        return False, f"Error adding to memory: {e}"


def create_research_handoff(
    queries_completed: list,
    findings_summary: str,
    qdrant_collection: str = "lineage_research",
    next_steps: list = None,
    project_root: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Create a structured research handoff for Claude.

    This is a convenience function that:
    1. Documents the research done
    2. Points to Qdrant findings
    3. Signals Claude's turn

    Args:
        queries_completed: List of research queries completed
        findings_summary: Brief summary of findings
        qdrant_collection: Where findings are stored
        next_steps: Suggested next steps for Claude
        project_root: Project root directory

    Returns:
        Tuple of (success: bool, message: str)
    """
    summary = f"""### Research Completed

{findings_summary}

### Queries Executed
{chr(10).join(f'- {q}' for q in queries_completed)}

### How to Access Findings
```bash
python ~/.claude/scripts/qdrant-semantic-search.py --collection {qdrant_collection} --query "your specific question"
```
"""

    return signal_claude_turn(
        project_root=project_root,
        summary=summary,
        research_topics=queries_completed,
        questions=next_steps
    )


# Tool registry
COLLAB_TOOLS = {
    "check_turn": check_turn,
    "signal_claude_turn": signal_claude_turn,
    "read_handoff_context": read_handoff_context,
    "add_to_shared_memory": add_to_shared_memory,
    "create_research_handoff": create_research_handoff,
}
