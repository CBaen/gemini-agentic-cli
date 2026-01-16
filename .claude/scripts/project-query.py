#!/usr/bin/env python3
"""
project-query.py - Token-efficient project lookup

Usage:
    python project-query.py list              # All projects (one line each)
    python project-query.py list backlog      # Only backlog projects
    python project-query.py list active       # Only active projects
    python project-query.py show M01          # Full details for M01
    python project-query.py start M01 @claude # Mark M01 active, assign to @claude
    python project-query.py done M01          # Mark M01 complete

Returns minimal output - no token bloat.
"""

import argparse
import re
import sys
from pathlib import Path

PROJECTS_DIR = Path(__file__).parent.parent / "projects"
INDEX_FILE = PROJECTS_DIR / "INDEX.md"


def parse_index():
    """Parse INDEX.md into list of dicts."""
    if not INDEX_FILE.exists():
        return []

    projects = []
    lines = INDEX_FILE.read_text().split("\n")

    for line in lines:
        # Match table rows: | ID | Title | Status | Owner |
        match = re.match(r'\|\s*([MC]\d+)\s*\|\s*(.+?)\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|', line)
        if match:
            projects.append({
                "id": match.group(1),
                "title": match.group(2).strip(),
                "status": match.group(3).strip(),
                "owner": match.group(4).strip()
            })

    return projects


def update_index(project_id: str, status: str = None, owner: str = None):
    """Update a project's status/owner in INDEX.md."""
    content = INDEX_FILE.read_text()
    lines = content.split("\n")

    for i, line in enumerate(lines):
        if f"| {project_id} |" in line:
            parts = line.split("|")
            if len(parts) >= 5:
                if status:
                    parts[3] = f" {status} "
                if owner:
                    parts[4] = f" {owner} "
                lines[i] = "|".join(parts)
                break

    INDEX_FILE.write_text("\n".join(lines))


def cmd_list(status_filter: str = None):
    """List projects (optionally filtered by status)."""
    projects = parse_index()

    if status_filter:
        projects = [p for p in projects if p["status"] == status_filter]

    if not projects:
        print(f"No projects with status: {status_filter}" if status_filter else "No projects found")
        return

    # Compact output
    for p in projects:
        owner = p["owner"] if p["owner"] != "-" else ""
        print(f"{p['id']}: {p['title']} [{p['status']}] {owner}".strip())


def cmd_show(project_id: str):
    """Show full details for a project."""
    project_file = PROJECTS_DIR / f"{project_id}.md"

    if not project_file.exists():
        print(f"No project file: {project_id}.md")
        print(f"Create with: .claude/projects/{project_id}.md")
        return

    print(project_file.read_text())


def cmd_start(project_id: str, owner: str):
    """Mark project as active and assign owner."""
    update_index(project_id, status="active", owner=owner)
    print(f"{project_id}: active, assigned to {owner}")


def cmd_done(project_id: str):
    """Mark project as complete."""
    update_index(project_id, status="done")
    print(f"{project_id}: done")


def main():
    parser = argparse.ArgumentParser(description="Token-efficient project lookup")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    list_parser = subparsers.add_parser("list", help="List projects")
    list_parser.add_argument("status", nargs="?", help="Filter by status")

    # show
    show_parser = subparsers.add_parser("show", help="Show project details")
    show_parser.add_argument("id", help="Project ID (e.g., M01)")

    # start
    start_parser = subparsers.add_parser("start", help="Mark project active")
    start_parser.add_argument("id", help="Project ID")
    start_parser.add_argument("owner", help="Owner (e.g., @claude)")

    # done
    done_parser = subparsers.add_parser("done", help="Mark project complete")
    done_parser.add_argument("id", help="Project ID")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args.status)
    elif args.command == "show":
        cmd_show(args.id)
    elif args.command == "start":
        cmd_start(args.id, args.owner)
    elif args.command == "done":
        cmd_done(args.id)


if __name__ == "__main__":
    main()
