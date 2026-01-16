# Project Tracking

**MOVED**: Projects now use the token-efficient system.

## Quick Commands

```bash
# List all projects (one line each)
python .claude/scripts/project-query.py list

# List only backlog/active/done
python .claude/scripts/project-query.py list backlog
python .claude/scripts/project-query.py list active

# Show full details for one project
python .claude/scripts/project-query.py show M01

# Start a project (mark active, assign owner)
python .claude/scripts/project-query.py start M01 @claude

# Complete a project
python .claude/scripts/project-query.py done M01
```

## File Structure

```
.claude/projects/
├── INDEX.md       # Lightweight status table (scan this first)
├── M01.md         # Full project details
├── M06.md
├── C01.md
└── ...            # Create as needed from template
```

## Workflow

1. Run `list` to see what's available
2. Run `show [ID]` to load one project's details
3. Run `start [ID] @owner` when beginning
4. Update `[ID].md` with task progress and handoff notes
5. Run `done [ID]` when complete

**Token savings**: Only load what you need. Never read the whole backlog.

---

## Completed Infrastructure

| ID | Project | Completed | Date |
|----|---------|-----------|------|
| I01 | Direct-to-Qdrant Storage | @claude | 2026-01-16 |
| I02 | Unified Schema | @claude | 2026-01-16 |
| I03 | Rate Limit Optimization | @claude | 2026-01-16 |
