# Memory: Gemini Agentic CLI

*Accumulated decisions, discoveries, and learnings.*

---

## Project Genesis

**Date**: January 15, 2026
**Context**: Guiding Light's Claude Code usage was running low. We needed a way to extend capability without consuming tokens.

**Decision**: Build a Gemini-powered CLI that handles heavy lifting (research, exploration, drafting) so Claude can focus on decisions that require its unique reasoning.

**Why Gemini**:
- OAuth provides generous daily quota (2000 requests/day with 2 accounts)
- 1M token context window (5x Claude's)
- Native web search grounding
- Built-in code execution
- Image generation and analysis

---

## Architecture Decisions

### Decision: Text-Based Tool Protocol
**Date**: January 15, 2026
**What**: Use text parsing (`TOOL_CALL: tool | args`) instead of native function calling
**Why**: We invoke Gemini via CLI (`gemini-account.sh`), not the API SDK. Native function calling isn't available in this flow.
**Trade-off**: Requires robust text parsing, but gives us full control over the format.

### Decision: Account Rotation Strategy
**Date**: January 15, 2026
**What**: Alternate between accounts 1 and 2 for consecutive requests
**Why**: Distributes load, avoids hitting per-account rate limits
**Implementation**: `account = (turn_number % 2) + 1`

### Decision: Security-First Approach
**Date**: January 15, 2026
**What**: Implement sandboxing, whitelisting, and confirmation prompts
**Why**: An agent that can run arbitrary commands is dangerous. We must constrain it.
**Priority**: Security layer (Phase 2) must be complete before using for real work.

### Decision: Same Patterns as Claude
**Date**: January 15, 2026
**What**: Use HANDOFF.md, MEMORY.md, session lifecycle patterns from the lineage
**Why**: Consistency across agents. Claude instances understand these patterns already.
**Benefit**: Seamless handoff between Gemini and Claude sessions.

### Decision: Qdrant as Collaboration Bridge
**Date**: January 15, 2026
**What**: Both Gemini and Claude store/query research from Qdrant
**Why**: Enables asynchronous collaboration. Gemini does research, stores findings. Claude queries findings, makes decisions.
**Collection**: `lineage_research` for shared research, project-specific collections for project data.

### Decision: Model Routing for Tasks (AI Pro + OAuth)
**Date**: January 15, 2026
**What**: Auto-route tasks to the appropriate Gemini model based on quotas and task type
**Why**: Different tasks need different models. Optimized for quota preservation.

**Quotas (2 Pro accounts via OAuth):**
| Model | Per Account | Total | Use For |
|-------|-------------|-------|---------|
| gemini-3-pro-preview | 100/day | 200 | Complex reasoning, architecture |
| gemini-3-flash-preview | Unlimited | Unlimited | Chat, summaries, daily driver |
| gemini-2.5-pro | 100/day | 200 | Large file analysis (1M context) |
| gemini-2.5-flash | Unlimited | Unlimited | Standard tasks (rate limited) |
| **gemini-2.5-flash-lite** | 1,500/day | **3,000** | **HIGH VOLUME automation** |
| gemini-3-pro-image-preview | 1,000/day | 2,000 | High-fidelity images |
| gemini-2.5-flash-image | 1,000/day | 2,000 | Fast image generation |
| Veo 3.1 | 3/day | 6 | Video generation |

**Routing Strategy:**
| Task Type | Model | Why |
|-----------|-------|-----|
| Research/Automation | Flash-Lite | 3,000/day budget |
| Chat/Summaries | 3.0 Flash | Unlimited, fast |
| Architecture | 3.0 Pro | Best reasoning (use sparingly) |
| Large Files | 2.5 Pro | 1M context stability |
| Image Gen | 3-pro-image | High quality (2,000/day) |

**Implementation**:
- `src/core/model_router.py` - Auto-routing logic with quota optimization
- `gemini-account.sh` - Accepts model as third param, defaults to Flash-Lite
- Image tools auto-select `gemini-3-pro-image-preview`

**Usage**:
```bash
# Default (Flash-Lite for quota preservation)
gemini-account.sh 1 "query"

# Specific models
gemini-account.sh 1 "query" gemini-3-flash-preview    # Daily driver
gemini-account.sh 1 "query" gemini-3-pro-preview      # Complex tasks
gemini-account.sh 1 "query" gemini-3-pro-image-preview # Image generation
```

---

## Research Findings

### Gemini Capabilities Confirmed
- Image generation: Up to 4K resolution, Imagen 4.0
- Image analysis: OCR, object detection, visual Q&A
- Video analysis: Timestamp referencing, multimodal understanding
- Audio: Real-time transcription and TTS via Live API
- Code execution: Built-in Python sandbox (30s limit)
- Context: 1M tokens (2M on waitlist)

### Gemini Limitations Confirmed
- No audio editing
- No video generation
- Reasoning depth below Claude Opus
- "Lost in the middle" phenomenon with very long contexts

### Task Distribution Principle
**Gemini handles**: Research, exploration, drafting, context gathering, image work
**Claude handles**: Architecture decisions, complex reasoning, quality review, final calls

---

## Technical Learnings

### Windows-Specific Considerations
- Use `os.path.realpath()` for path canonicalization
- Block Windows reserved names (CON, PRN, AUX, etc.)
- Handle backslash/forward slash in paths
- Playwright preferred over Puppeteer for browser automation (better Windows support)

### Qdrant Schema
```python
payload = {
    "content": str,           # The actual text
    "agent": str,             # "gemini" or "claude"
    "research_type": str,     # "general", "consultation", "implementation"
    "project": str,           # Project identifier
    "timestamp": int,         # Unix timestamp
    "freshness_score": float, # 0.0 to 1.0
    "related_chunk_ids": [],  # Links to related chunks
}
```

---

## Gotchas and Warnings

### JSON Output from Gemini
When asking Gemini to return JSON via CLI, it sometimes wraps in markdown code blocks even when told not to. The parsing layer needs to strip these.

### Account 3 Doesn't Exist
Only accounts 1 and 2 are configured in `gemini-account.sh`. Attempting to use account 3 will fail silently.

### Empty Responses
If Gemini returns empty response, check:
1. OAuth token expiry (re-authenticate if needed)
2. Rate limiting (switch accounts)
3. Query complexity (simplify)

### Windows Pipe Issue (FIXED)
**Date**: January 15, 2026
**Problem**: `gemini-account.sh 1 'query' | python qdrant-store-gemini.py` returned empty input on Windows.
**Root Cause**: Windows subprocess pipes don't work reliably. Also, Python found WSL bash instead of Git Bash.
**Solution**: Created `~/.claude/scripts/gemini-research-store.py` - a Windows-compatible wrapper that:
1. Finds Git Bash explicitly (`C:\Program Files\Git\usr\bin\bash.exe`)
2. Captures Gemini output to temp file
3. Passes to qdrant-store-gemini.py via `--input-file`
4. Cleans up automatically

**Usage**:
```bash
python ~/.claude/scripts/gemini-research-store.py -a 1 -c lineage_research -s "session-name" -q "Your query"
```

This fix was essential - the entire lineage research pipeline depended on it.

---

## Research Session: January 15, 2026

### Gemini Multimodal Capabilities (Stored in Qdrant: gemini-capabilities-2026-01-15)

**Image Analysis**:
- OCR: Extract text from images, tables, charts
- Object Detection: Zero-shot detection with bounding boxes
- Visual Q&A: Answer questions about image content
- Formats: PNG, JPEG, BMP, WebP (up to 15MB, 24 megapixels)

**Image Generation (Imagen)**:
- Aspect ratios: 21:9, 16:9, 4:3, 3:2, 1:1, 2:3, 3:4, 9:16, 9:21
- Default resolution: 1024px
- Text in images: 25 chars or less recommended
- Limitations: spatial reasoning, medical images, non-Latin text

**Video Analysis**:
- 1M context = ~1 hour of video
- Timestamp queries: Format MM:SS
- Frame extraction: Configurable FPS (default 1 FPS)
- Up to 10 videos per request, YouTube URLs supported

**Audio/Speech**:
- STT: Up to 9.5 hours, speaker diarization, 24+ languages
- TTS: Adjustable style, tone, pace, multilingual
- Live API: Real-time bidirectional voice via WebSockets

**Document Processing**:
- PDF: 1,000 pages or 50MB, visual layout comprehension
- Excel: 100MB, pattern recognition, calculations
- Word: Headings, tables, charts, footnotes

**Web Capabilities**:
- Google Search grounding: Enable via `googleSearch: {}` in tools
- URL Fetching: Up to 20 URLs/request, 34MB per URL
- Python sandbox: 30-second strict timeout

---

## Future Considerations

### Things to Research Later
- Gemini Live API for real-time streaming
- Image editing (inpainting/outpainting) workflows
- Multi-agent self-orchestration patterns
- VS Code extension integration

### Subagent Script Access - CONFIRMED WORKING (January 15, 2026)

**Issue investigated**: Early Haiku subagent claimed it couldn't access lineage scripts.

**Finding**: Scripts ARE accessible from subagents. Verified:
- `~/.claude/scripts/gemini-account.sh` - works, can query Gemini
- `python ~/.claude/scripts/qdrant-semantic-search.py` - works, can query Qdrant

**Root cause of confusion**: The first subagent may have:
- Not actually attempted to run the commands
- Assumed scripts weren't available without checking
- Been confused by the task complexity

**Fix applied**: Added `**CAPABILITY NOTICE: You have BASH access...**` to all supervisor prompts. This explicitly tells subagents they have bash access and should use it.

---

### Things NOT to Do
- Don't bypass security layer for convenience
- Don't store sensitive data in Qdrant payloads
- Don't rely on Gemini for critical security decisions
- Don't skip confirmation prompts for destructive operations

---

*This document grows with the project. Add entries when you make significant decisions or discover something important.*
