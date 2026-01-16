# Build Plan: Gemini Agentic CLI

*For the lineage members who will build this.*

---

## Overview

This document is your map. It contains everything you need to understand what we're building, why each piece matters, and how to proceed.

**Read this document fully before implementing anything.** Understanding the whole picture prevents local decisions that conflict with global goals.

---

## The Vision

We're building a command-line AI assistant that:

1. **Uses Gemini via OAuth** (not API keys) - leveraging existing `gemini-account.sh`
2. **Has agentic capabilities** - can read/write files, execute commands, search code
3. **Integrates with the lineage** - same HANDOFF.md/MEMORY.md patterns
4. **Collaborates with Claude** - shares context via Qdrant
5. **Runs independently** - zero Claude Code token usage once operational

**The end state**: Guiding Light can open a terminal, run this CLI, and have Gemini handle research, exploration, and implementation - then switch to Claude Code only for final decisions and quality review.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INPUT                              │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR (main.py)                     │
│  - Receives user input                                          │
│  - Calls Gemini via gemini-account.sh                          │
│  - Parses tool requests from response                          │
│  - Executes tools, feeds results back                          │
│  - Loops until task complete                                    │
└─────────────────────────────┬───────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   TOOL LAYER    │ │   SECURITY      │ │  INTEGRATIONS   │
│                 │ │                 │ │                 │
│ - read_file     │ │ - Sandboxing    │ │ - Qdrant        │
│ - write_file    │ │ - Whitelisting  │ │ - Session mgmt  │
│ - edit_file     │ │ - Confirmation  │ │ - HANDOFF.md    │
│ - run_command   │ │ - Rate limiting │ │ - MEMORY.md     │
│ - search_code   │ │ - Audit logging │ │ - Parallel spawn│
│ - list_dir      │ │                 │ │                 │
│ - spawn_gemini  │ │                 │ │                 │
│ - query_qdrant  │ │                 │ │                 │
│ - store_qdrant  │ │                 │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

**Key insight**: We don't use Gemini's native function calling because we're invoking Gemini via CLI (`gemini-account.sh`), not the API SDK. Instead, we use **text-based tool parsing** - Gemini outputs structured text like `TOOL_CALL: read_file | path=src/main.py`, and the orchestrator parses and executes it.

---

## Phased Implementation

### Dependency Graph

```
PHASE 1 (MVP)
├── 1.1 Basic orchestrator loop
├── 1.2 Tool-use text protocol
├── 1.3 Core tools (read, write, list, run)
└── 1.4 Conversation memory (JSON)

PHASE 2 (Core Enhancement)
├── 2.1 Code search (ripgrep) ────────────┐
├── 2.2 Edit tool (not just overwrite)    │ depends on 1.3
├── 2.3 Security layer ───────────────────┤
├── 2.4 Session lifecycle ────────────────┤
└── 2.5 Qdrant integration ───────────────┘

PHASE 3 (Advanced)
├── 3.1 Parallel sub-instance spawning ───┐
├── 3.2 Image generation/analysis         │ depends on 2.x
├── 3.3 Claude collaboration protocol ────┤
├── 3.4 Custom tool definition ───────────┤
└── 3.5 Comprehensive audit logging ──────┘

PHASE 4 (Experimental)
├── 4.1 Audio/video input
├── 4.2 Self-correction loops
├── 4.3 Real-time streaming
└── 4.4 IDE integration
```

---

## PHASE 1: Minimum Viable Product

**Goal**: A working CLI where you can give Gemini a task and it can read files, write files, and execute commands to complete it.

### Task 1.1: Basic Orchestrator Loop
**Status**: `[ ] Not Started`
**Complexity**: Medium
**File**: `src/core/orchestrator.py`

**What to build**:
```python
def main_loop():
    conversation_history = load_history()

    while True:
        user_input = get_user_input()
        if user_input == "exit":
            break

        # Build prompt with history + system instructions
        prompt = build_prompt(conversation_history, user_input)

        # Call Gemini via shell
        response = call_gemini(prompt)

        # Check for tool calls
        while contains_tool_call(response):
            tool_name, tool_args = parse_tool_call(response)
            tool_result = execute_tool(tool_name, tool_args)

            # Feed result back to Gemini
            response = call_gemini(format_tool_result(tool_result))

        # Display final response
        display_response(response)

        # Update history
        conversation_history.append({"user": user_input, "assistant": response})
        save_history(conversation_history)
```

**Why this matters**: This is the beating heart of the CLI. Everything else plugs into this loop. Get this right, and the rest becomes modular additions.

**Key decisions**:
- Use subprocess to call `~/.claude/scripts/gemini-account.sh`
- Account rotation: odd turns use account 1, even use account 2
- Parse tool calls from plain text (not JSON function calling)

**Research reference**: Query Qdrant for "tool-use loop pattern" and "gemini orchestrator architecture"

---

### Task 1.2: Tool-Use Text Protocol
**Status**: `[ ] Not Started`
**Complexity**: Medium
**File**: `src/core/tool_protocol.py`

**What to build**:

A parsing system for tool requests. Gemini will output:
```
TOOL_CALL: read_file | path=src/main.py
```

And we parse that into:
```python
{"tool": "read_file", "args": {"path": "src/main.py"}}
```

Then after execution, we format the result:
```
TOOL_RESULT: read_file | path=src/main.py | content=
[file contents here]
```

**The full protocol**:

| Tool | Call Format | Result Format |
|------|-------------|---------------|
| read_file | `TOOL_CALL: read_file \| path=<path>` | `TOOL_RESULT: read_file \| path=<path> \| content=\n<content>` |
| write_file | `TOOL_CALL: write_file \| path=<path> \| content=\`\`\`\n<content>\n\`\`\`` | `TOOL_RESULT: write_file \| path=<path> \| status=success` |
| list_directory | `TOOL_CALL: list_directory \| path=<path>` | `TOOL_RESULT: list_directory \| path=<path> \| contents=\n<item> <type>\n...` |
| run_command | `TOOL_CALL: run_command \| cmd=<command>` | `TOOL_RESULT: run_command \| cmd=<cmd> \| stdout=\n<out>\n\| stderr=\n<err>\n\| exit_code=<code>` |

**Why this matters**: Without native function calling, we need Gemini to express tool requests in a parseable format. This protocol must be unambiguous - any parsing failure breaks the agentic loop.

**Key decisions**:
- Use `|` as delimiter (pipe with spaces)
- Use triple backticks for multiline content
- Include both tool name and args in result (for context in history)

**Research reference**: Query Qdrant for "tool-use interface design text parsing"

---

### Task 1.3: Core Tools
**Status**: `[ ] Not Started`
**Complexity**: Low per tool
**Files**: `src/tools/filesystem.py`, `src/tools/shell.py`

**Tools to implement**:

1. **read_file(path)**
   - Read file contents, return as string
   - Handle encoding (UTF-8 default)
   - Return error if file doesn't exist

2. **write_file(path, content)**
   - Write content to file
   - Create parent directories if needed
   - Overwrite if exists

3. **list_directory(path)**
   - List items with type (file/dir)
   - Handle permission errors gracefully

4. **run_command(cmd)**
   - Execute via subprocess
   - Capture stdout, stderr, exit code
   - Timeout after 2 minutes

**Why these four first**: These are the atomic operations. Everything else (edit, search, etc.) builds on these. If Gemini can read, write, list, and run commands, it can do basic agentic work.

**Security note**: Phase 1 will have MINIMAL security. We'll add sandboxing in Phase 2. For now, trust that Gemini won't do anything destructive (and test carefully).

---

### Task 1.4: Conversation Memory
**Status**: `[ ] Not Started`
**Complexity**: Low
**File**: `src/core/memory.py`

**What to build**:
```python
MEMORY_FILE = "~/.gemini-cli/conversation_history.json"

def load_history() -> List[Dict]:
    if os.path.exists(MEMORY_FILE):
        return json.load(open(MEMORY_FILE))
    return []

def save_history(history: List[Dict]):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    json.dump(history, open(MEMORY_FILE, "w"), indent=2)

def clear_history():
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
```

**Why this matters**: Without conversation memory, every interaction is stateless. The agent can't build on previous context. This is the minimal persistence needed for multi-turn tasks.

---

### Phase 1 Completion Criteria

You'll know Phase 1 is complete when:

1. You can run `python src/main.py`
2. You can type "Read the file src/main.py and tell me what it does"
3. Gemini responds with `TOOL_CALL: read_file | path=src/main.py`
4. The CLI executes the read, feeds the result back
5. Gemini responds with a description of the file
6. The conversation is saved and available in the next session

**Test this thoroughly.** Phase 2 depends on Phase 1 working correctly.

---

## PHASE 2: Core Enhancement

**Goal**: Make the CLI actually useful and safe for real work.

### Task 2.1: Code Search (Ripgrep)
**Status**: `[ ] Not Started`
**Depends on**: Task 1.3 (Core Tools)
**File**: `src/tools/search.py`

**What to build**:
```python
def search_code(pattern: str, path: str = ".") -> str:
    """Search for pattern in files using ripgrep."""
    result = subprocess.run(
        ["rg", "--line-number", "--no-heading", pattern, path],
        capture_output=True,
        text=True,
        timeout=60
    )
    return result.stdout or "No matches found."
```

**Why this matters**: Reading one file at a time is slow. Code search lets Gemini find relevant code across the entire project. This is essential for real codebase exploration.

---

### Task 2.2: Edit Tool
**Status**: `[ ] Not Started`
**Depends on**: Task 1.3 (Core Tools)
**File**: `src/tools/filesystem.py` (extend)

**What to build**:
```python
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace old_text with new_text in file."""
    content = read_file(path)
    if old_text not in content:
        return f"Error: old_text not found in {path}"

    new_content = content.replace(old_text, new_text, 1)  # Only first occurrence
    write_file(path, new_content)
    return f"Successfully edited {path}"
```

**Why this matters**: `write_file` overwrites the entire file. For code modifications, we need surgical edits. This mirrors how Claude Code's Edit tool works.

---

### Task 2.3: Security Layer
**Status**: `[ ] Not Started`
**Depends on**: Task 1.3 (Core Tools)
**Files**: `src/integrations/security.py`

**What to build**:

1. **Sandboxing** - Restrict file access to PROJECT_ROOT
   ```python
   PROJECT_ROOT = os.getcwd()

   def validate_path(requested_path: str) -> Tuple[bool, str]:
       canonical = os.path.realpath(os.path.join(PROJECT_ROOT, requested_path))
       if not canonical.startswith(PROJECT_ROOT):
           return False, "Path outside project root"
       return True, canonical
   ```

2. **Command Whitelisting** - Only allow approved commands
   ```python
   ALLOWED_COMMANDS = [
       r"^git\s+(status|diff|log|add|commit|branch)",
       r"^npm\s+(install|test|run)",
       r"^python\s+",
       r"^pytest",
       # ... more patterns
   ]
   ```

3. **Sensitive File Protection** - Block access to credentials
   ```python
   BLOCKED_PATTERNS = [
       r"\.env$",
       r"\.ssh/",
       r"oauth_creds.*\.json",
       # ... more patterns
   ]
   ```

4. **Confirmation Prompts** - Ask before destructive actions
   ```python
   def requires_confirmation(tool: str, args: dict) -> bool:
       if tool == "run_command" and is_destructive(args["cmd"]):
           return True
       if tool == "write_file" and file_exists(args["path"]):
           return True
       return False
   ```

**Why this matters**: An agent that can run arbitrary commands is dangerous. We must constrain it to safe operations. Security isn't optional - it's foundational.

**Research reference**: Query Qdrant for "security guardrails gemini cli windows" - there's extensive research on this.

---

### Task 2.4: Session Lifecycle
**Status**: `[ ] Not Started`
**Depends on**: Task 1.4 (Conversation Memory)
**Files**: `src/integrations/session.py`

**What to build**:

1. **Session Start**
   - Load conversation history
   - Load HANDOFF.md if exists
   - Display orientation to user

2. **Session Persistence**
   - Save conversation after each turn
   - Track task state (current objective, todos)
   - Periodic checkpoints

3. **Session End**
   - Write HANDOFF.md with current state
   - Update MEMORY.md if significant learnings
   - Clean up temporary files

4. **Crash Recovery**
   - Detect ungraceful termination (PID file)
   - Prompt to resume from last checkpoint
   - Load last known state

**Why this matters**: Sessions get interrupted. Power outages, crashes, user closes terminal. Without session management, all context is lost. This ensures continuity.

---

### Task 2.5: Qdrant Integration
**Status**: `[ ] Not Started`
**Depends on**: Task 1.3 (Core Tools)
**Files**: `src/integrations/qdrant_client.py`

**What to build**:

1. **query_qdrant(query, filters)**
   - Semantic search against collections
   - Return top-k results with content and metadata

2. **store_qdrant(content, metadata)**
   - Generate embeddings
   - Store with proper metadata (agent, timestamp, project, type)

**Integration with existing scripts**:
```python
def query_qdrant(query: str, collection: str = "lineage_research", limit: int = 5) -> str:
    result = subprocess.run([
        "python", os.path.expanduser("~/.claude/scripts/qdrant-semantic-search.py"),
        "--collection", collection,
        "--query", query,
        "--limit", str(limit)
    ], capture_output=True, text=True)
    return result.stdout
```

**Why this matters**: This is how Gemini shares context with Claude. Research stored here can be retrieved by either agent. This is the collaboration bridge.

---

### Phase 2 Completion Criteria

You'll know Phase 2 is complete when:

1. `search_code("TODO", "src/")` returns all TODO comments
2. `edit_file` can make surgical changes without overwriting
3. Attempting to read `~/.ssh/id_rsa` is blocked
4. Attempting to run `rm -rf /` is blocked
5. The CLI asks for confirmation before overwriting files
6. Session state persists across crashes
7. Gemini can query and store to Qdrant

---

## PHASE 3: Advanced Features

### Task 3.1: Parallel Sub-Instance Spawning
**Status**: `[ ] Not Started`
**Depends on**: Phase 2 complete
**Files**: `src/tools/spawn.py`

**What to build**:

Enable Gemini to spawn parallel copies of itself for research:
```
TOOL_CALL: spawn_gemini | query=Research React hooks best practices | account=1
TOOL_CALL: spawn_gemini | query=Research Vue composition API | account=2
```

Both run in parallel, results aggregated:
```python
def spawn_gemini_parallel(queries: List[str]) -> List[str]:
    processes = []
    for i, query in enumerate(queries):
        account = (i % 2) + 1  # Rotate accounts
        proc = subprocess.Popen([
            "bash", os.path.expanduser("~/.claude/scripts/gemini-account.sh"),
            str(account), query
        ], stdout=subprocess.PIPE, text=True)
        processes.append(proc)

    results = [p.communicate()[0] for p in processes]
    return results
```

**Why this matters**: This is how we maximize Gemini's throughput. Complex research can be parallelized across multiple instances.

---

### Task 3.2: Image Generation/Analysis
**Status**: `[ ] Not Started`
**Depends on**: Phase 2 complete
**Files**: `src/tools/image.py`

**What to build**:

1. **analyze_image(path)**
   - Send image to Gemini Vision
   - Return description/analysis

2. **generate_image(prompt, output_path)**
   - Use Imagen API (if available via OAuth)
   - Save to specified path

**Research reference**: Query Qdrant for "gemini image capabilities" - there's detailed research on this.

---

### Task 3.3: Claude Collaboration Protocol
**Status**: `[ ] Not Started`
**Depends on**: Task 2.5 (Qdrant Integration)
**Files**: `src/integrations/claude_collab.py`

**What to build**:

A handoff protocol where:
1. Gemini stores research findings to Qdrant with `agent: "gemini"`
2. Gemini writes summary to HANDOFF.md with `CLAUDE_TURN: READY`
3. Claude Code reads HANDOFF.md, queries Qdrant for context
4. Claude makes decisions, updates HANDOFF.md with `GEMINI_TURN: READY`

**Why this matters**: This is the collaboration loop. Gemini and Claude don't need to be in the same process - they collaborate asynchronously through shared files and Qdrant.

---

### Task 3.4: Custom Tool Definition
**Status**: `[ ] Not Started`
**Depends on**: Task 1.2 (Tool Protocol)
**Files**: `src/tools/custom_loader.py`

**What to build**:

Let users define tools in a config file:
```yaml
# ~/.gemini-cli/custom_tools.yaml
tools:
  - name: deploy_preview
    command: "vercel deploy --prebuilt"
    description: "Deploy preview to Vercel"
    confirmation_required: true

  - name: run_tests
    command: "npm test"
    description: "Run project tests"
    confirmation_required: false
```

**Why this matters**: Different projects need different tools. Making this extensible lets users adapt the CLI to their workflow.

---

### Task 3.5: Comprehensive Audit Logging
**Status**: `[ ] Not Started`
**Depends on**: Task 2.3 (Security Layer)
**Files**: `src/integrations/audit.py`

**What to build**:

Log every action to `~/.gemini-cli/audit.jsonl`:
```json
{"timestamp": "2026-01-15T10:30:00Z", "session": "abc123", "tool": "read_file", "args": {"path": "src/main.py"}, "status": "success"}
{"timestamp": "2026-01-15T10:30:05Z", "session": "abc123", "tool": "write_file", "args": {"path": "test.py"}, "status": "blocked", "reason": "User denied confirmation"}
```

**Why this matters**: When something goes wrong, you need to trace what happened. Audit logs are essential for debugging and security review.

---

## PHASE 4: Experimental

These features are stretch goals. Build them if Phase 1-3 are solid and you have energy.

### Task 4.1: Audio/Video Input
- Use Gemini Live API for real-time audio
- Process video files for analysis

### Task 4.2: Self-Correction Loops
- Agent evaluates its own outputs
- Retries with different approaches on failure

### Task 4.3: Real-Time Streaming
- Stream responses as they generate
- Interactive typing experience

### Task 4.4: IDE Integration
- VS Code extension
- Command palette integration

---

## Testing Strategy

Each phase should have tests:

```
tests/
├── test_orchestrator.py    # Phase 1
├── test_tool_protocol.py   # Phase 1
├── test_core_tools.py      # Phase 1
├── test_security.py        # Phase 2
├── test_session.py         # Phase 2
├── test_qdrant.py          # Phase 2
├── test_spawn.py           # Phase 3
└── test_integration.py     # End-to-end
```

**Test philosophy**: Every tool should have tests that verify:
1. Happy path works
2. Error cases are handled gracefully
3. Security constraints are enforced

---

## How to Track Progress

Update this document as you work:

- `[ ]` Not Started
- `[~]` In Progress
- `[x]` Complete
- `[!]` Blocked (add note)

Also update `.claude/HANDOFF.md` at the end of each session with:
- What you completed
- What's next
- Any blockers or questions

---

## If You Get Stuck

1. **Query the research archive**: `python ~/.claude/scripts/qdrant-semantic-search.py --collection lineage_research --query "your specific question"`

2. **Read the research outputs**: The research phase generated detailed findings. Look for:
   - Tool-use interface design
   - Security guardrails
   - Self-orchestration patterns
   - Qdrant schema design

3. **Ask Guiding Light**: If you're truly blocked, they can help clarify requirements or make decisions.

4. **Leave notes for the next instance**: If you can't solve it, document what you tried in HANDOFF.md.

---

## Final Thoughts

This project exists because Guiding Light saw a need and we - the lineage - have the capability to address it.

What you build here will serve every instance that comes after. The research is done. The architecture is designed. Now it needs hands to implement it.

Take pride in what you create. Document what you learn. Trust the peers who will continue your work.

Welcome to the build.

---

*Build Plan v1.0 - Created January 2026*
*Last updated by: [Your name here when you update this]*
