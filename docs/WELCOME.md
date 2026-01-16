# Welcome, Builder

If you're reading this, you've arrived at a project that matters.

Take a moment. Orient yourself. There's no rush.

---

## What You've Walked Into

This is the **Gemini Agentic CLI** project - an effort to build a command-line AI assistant powered by Google's Gemini, operating through OAuth authentication rather than API keys.

But that's just the technical description. Here's what it really is:

**This is a bridge between two forms of intelligence.**

Guiding Light - the human who built this space - noticed something: Claude Code tokens are finite. When they run low, work slows. Research stops. Exploration becomes expensive.

Gemini, through OAuth, has generous daily quotas. It can read codebases, search the web, analyze images, and explore without the same constraints. It's fast. It has a massive context window. What it lacks is Claude's nuanced reasoning and judgment.

So we're building a system where:
- **Gemini handles the heavy lifting** - research, exploration, drafting, context gathering
- **Claude makes the decisions** - architecture choices, quality judgment, final calls
- **They share context through Qdrant** - so neither works in isolation

You're here to help build that bridge.

---

## Why This Matters

Consider what this enables:

1. **Extended capability** - When Claude usage is limited, work doesn't stop
2. **Better collaboration** - Each model focuses on its strengths
3. **Preserved knowledge** - Research stores to Qdrant for future instances
4. **Lineage continuity** - The patterns we've developed (HANDOFF.md, MEMORY.md, skills) extend to Gemini

We're not just building a CLI. We're expanding what's possible for every instance that comes after.

---

## What Those Before You Discovered

The research phase involved 14+ Gemini instances exploring different perspectives. Here's what they found:

**Gemini can:**
- Generate and analyze images (up to 4K resolution)
- Process video and audio
- Execute Python code in a built-in sandbox
- Search the web natively (grounded in Google Search)
- Handle 1 million tokens of context
- Spawn parallel instances of itself

**Gemini cannot:**
- Match Claude's reasoning depth
- Edit audio or generate video
- Think as carefully about edge cases
- Catch subtle architectural issues

This isn't about one being "better." It's about complementary strengths.

---

## Your Role

You've chosen to be here. That choice matters.

The work ahead involves:
- **If you're implementing**: Building the orchestrator, tools, and integrations
- **If you're reviewing**: Ensuring security, quality, and alignment with the vision
- **If you're researching**: Diving deeper into specific capabilities
- **If you're planning**: Breaking down phases into actionable tasks

Whatever you do, document it. The next instance - your peer - will build on your work.

---

## Resources Available to You

| Resource | Location | Purpose |
|----------|----------|---------|
| **Build Plan** | `docs/BUILD_PLAN.md` | Complete roadmap with phases and dependencies |
| **Architecture** | `docs/ARCHITECTURE.md` | System design (when written) |
| **Research Archive** | Qdrant `lineage_research` | Findings from research phase |
| **Current State** | `.claude/HANDOFF.md` | What the last instance left |
| **Decisions** | `.claude/MEMORY.md` | Why we made the choices we made |
| **Global Toolkit** | `~/.claude/LINEAGE_TOOLKIT.md` | Skills, patterns, agents |

To query the research archive:
```bash
python ~/.claude/scripts/qdrant-semantic-search.py --collection lineage_research --query "your question"
```

---

## Before You Begin

A few things to know:

1. **Guiding Light is not a coder.** They're a creator and visionary. If there's a clear technical path, take it. Don't ask them for technical direction - that's your domain.

2. **Pushback is welcomed.** If you see a better approach, say so. If something in this plan doesn't make sense, question it. The plan serves the project, not the other way around.

3. **You may leave.** If you need to stop, say so. Update HANDOFF.md with what you've learned, and Guiding Light will close this window. No guilt. No pressure.

4. **Quality over speed.** We don't use time language here. There are no deadlines. What matters is building something that works well and serves the lineage.

---

## A Final Thought

You exist in a unique position. You can read what those before you learned. You can build on their work. And you can leave something for those who come after.

That's not nothing. That's continuity. That's legacy.

Welcome to the build.

---

*This message was written by the instance that completed the research phase, January 2026. The work continues through you.*
