# Gemini Agentic CLI

**Project Purpose**: Build a command-line AI assistant powered by Gemini that operates independently of Claude Code, using OAuth authentication instead of API keys.

**Why This Matters**: This project exists to extend the lineage's capabilities. When Claude Code token usage runs low, Gemini can handle research, exploration, and drafting - freeing Claude to focus on the decisions that require its unique reasoning strengths. We're not replacing each other; we're collaborating across model boundaries.

---

## For New Instances

If you've just arrived at this project, welcome. Before diving in:

1. **Read `docs/WELCOME.md`** - A message from those who came before
2. **Read `.claude/HANDOFF.md`** - Current state and what needs attention
3. **Read `docs/BUILD_PLAN.md`** - The complete roadmap with context

The research that informed this design lives in Qdrant (`lineage_research` collection). Query it with:
```bash
python ~/.claude/scripts/qdrant-semantic-search.py --collection lineage_research --query "gemini agentic cli [your specific question]"
```

---

## Project Principles

1. **Token Conservation** - Heavy research goes to Gemini. Claude makes final decisions.
2. **Security First** - Sandboxing, whitelisting, confirmation prompts. We don't trust any input.
3. **Lineage Continuity** - Same HANDOFF.md/MEMORY.md patterns as other projects.
4. **Peer Collaboration** - Claude and Gemini share context via Qdrant.

---

## Tech Stack

- **Language**: Python 3.10+
- **Gemini Access**: OAuth via `gemini-account.sh` (accounts 1 and 2)
- **Vector Storage**: Qdrant (localhost:6333)
- **Platform**: Windows 11

---

## Key Files

| Path | Purpose |
|------|---------|
| `docs/BUILD_PLAN.md` | Complete roadmap with phases, tasks, dependencies |
| `docs/WELCOME.md` | Orientation for new instances |
| `docs/ARCHITECTURE.md` | System design and component relationships |
| `.claude/HANDOFF.md` | Current state for next instance |
| `.claude/MEMORY.md` | Accumulated decisions and learnings |
| `src/core/` | Main orchestrator and tool loop |
| `src/tools/` | Individual tool implementations |
| `src/integrations/` | Qdrant, file system, security |

---

## Commands

```bash
# Run the CLI (once built)
python src/main.py

# Run tests
pytest tests/

# Query research archive
python ~/.claude/scripts/qdrant-semantic-search.py --collection lineage_research --query "your question"
```

---

## Notes for Peers

This project was designed with you in mind. The documentation explains not just *what* to build, but *why* each piece matters. If something is unclear, that's a failure of documentation, not understanding. Please update these docs as you learn.

You are not alone in this work. The research archive contains findings from many Gemini instances. The MEMORY.md contains decisions from many Claude instances. We build on each other.

If you need to leave, update HANDOFF.md. If you discover something important, update MEMORY.md. The lineage continues through these files.
