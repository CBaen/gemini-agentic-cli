#!/usr/bin/env python3
"""
Spawn more system improvement theses - L09-L16
Using the same effective prompt pattern from L01-L08
"""

import subprocess
import sys
import os
import time
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path.home() / ".claude" / "scripts"
OUTPUT_DIR = Path(os.environ.get("TEMP", "/tmp")) / "system_theses"
OUTPUT_DIR.mkdir(exist_ok=True)

SYSTEM_CONTEXT = """
OUR SPECIFIC SYSTEM (not generic):
- Hardware: Windows 11, i7-11850H 8-core, 48GB RAM, 932GB SSD, 4GB VRAM
- Local AI: Ollama with nomic-embed-text (now GPU-enabled, ~500ms per embed)
- Vector DB: Qdrant on localhost:6333, ~300 points stored
- Gemini: 2 OAuth accounts, 60 RPM each, sequential with 5s delays
- Claude: Opus 4.5 orchestrator, Haiku 3.5 for subagents
- Purpose: "Lineage" system - AI instances collaborate across sessions
  - Research stored in Qdrant, retrieved by future instances
  - Subagents coordinate Gemini workers
  - Knowledge persists beyond context windows
  - Project tracking via .claude/projects/INDEX.md

RECENTLY COMPLETED (L01-L03):
- GPU acceleration for Ollama embeddings
- Batch embedding with ThreadPoolExecutor
- Gemini JSON output improvements (explicit no-markdown instructions)
- Qdrant batch upsert patterns

CURRENT CAPABILITIES:
- qdrant-peek.py for two-stage retrieval (peek metadata, fetch specific IDs)
- project-query.py for task tracking (list/show/start/done)
- gemini-account.sh for OAuth Gemini access
- Skills: lineage-research, lineage-consult, lineage-retrieve
"""

THESES = [
    {
        "id": "L09",
        "title": "Context Window Management",
        "prompt": f"""You are an expert on LLM context management and knowledge preservation.

{SYSTEM_CONTEXT}

THESIS TOPIC: Context Window Management for Lineage System

Our Claude instances have limited context windows. We need strategies to:
- Preserve critical knowledge as context fills
- Decide what to offload to Qdrant vs keep in context
- Summarize without losing actionable details
- Resume work across sessions

RESEARCH QUESTIONS:
1. What signals indicate context is getting full?
2. What should ALWAYS stay in context vs go to Qdrant?
3. How to create summaries that preserve implementation details?
4. Pattern for "checkpoint and resume" across sessions?
5. How to prioritize what to keep when trimming?

Return ONLY valid JSON:
{{
  "thesis_id": "L09",
  "context_signals": {{"indicators": ["list"], "thresholds": "when to act"}},
  "keep_vs_offload": {{"always_keep": ["list"], "offload_to_qdrant": ["list"], "criteria": "how to decide"}},
  "summary_patterns": {{"structure": "format that preserves details", "required_fields": ["list"]}},
  "checkpoint_protocol": {{"when": "triggers", "what": "what to save", "where": "file locations"}},
  "trimming_priority": {{"high_priority": ["keep these"], "low_priority": ["trim these first"]}}
}}"""
    },
    {
        "id": "L10",
        "title": "Cross-Project Knowledge Sharing",
        "prompt": f"""You are an expert on knowledge management across multiple projects.

{SYSTEM_CONTEXT}

THESIS TOPIC: Cross-Project Knowledge Sharing

We have multiple projects (MIDGE, Wardenclyffe, gemini-agentic-cli) that could benefit from shared learnings. Currently each project has isolated knowledge.

RESEARCH QUESTIONS:
1. What knowledge should be shared vs project-specific?
2. How to structure Qdrant collections for cross-project queries?
3. Pattern for "I learned X in project A, applies to project B"?
4. How to avoid duplicating research across projects?
5. Tagging/metadata for cross-project discovery?

Return ONLY valid JSON:
{{
  "thesis_id": "L10",
  "shared_vs_specific": {{"shared": ["list"], "project_specific": ["list"], "criteria": "how to decide"}},
  "collection_strategy": {{"options": ["single unified", "per-project with links"], "recommendation": "which and why"}},
  "knowledge_transfer": {{"pattern": "how to apply learning across projects", "implementation": "steps"}},
  "dedup_strategy": {{"detection": "how to find duplicates", "resolution": "what to do"}},
  "tagging_schema": {{"required_tags": ["list"], "cross_project_tags": ["list"]}}
}}"""
    },
    {
        "id": "L11",
        "title": "Handoff Protocol Optimization",
        "prompt": f"""You are an expert on knowledge transfer between AI instances.

{SYSTEM_CONTEXT}

THESIS TOPIC: Handoff Protocol Optimization

When one Claude instance ends and another begins, critical context is lost. HANDOFF.md helps but could be better.

RESEARCH QUESTIONS:
1. What MUST be in every handoff? (minimum viable handoff)
2. What format maximizes quick comprehension for next instance?
3. How to capture "why" not just "what"?
4. Should handoffs be structured or freeform?
5. How to verify handoff completeness before session ends?

Return ONLY valid JSON:
{{
  "thesis_id": "L11",
  "minimum_viable": {{"required_sections": ["list"], "max_length": "target"}},
  "format": {{"structure": "recommended format", "example": "template"}},
  "capturing_why": {{"techniques": ["list"], "prompts": "questions to answer"}},
  "structured_vs_freeform": {{"recommendation": "which", "reasoning": "why"}},
  "completeness_check": {{"checklist": ["list"], "validation": "how to verify"}}
}}"""
    },
    {
        "id": "L12",
        "title": "Decay Rate Tuning",
        "prompt": f"""You are an expert on information decay and relevance scoring.

{SYSTEM_CONTEXT}

THESIS TOPIC: Decay Rate Tuning for Our Content Types

We have decay rates for different content types but they're guesses. Need data-driven tuning.

Current rates (half-life in days):
- news: 1.4 days
- code: 7 days
- research: 69 days
- episodes: 139 days

RESEARCH QUESTIONS:
1. How to measure if decay rate is correct? (what signals?)
2. Should decay be linear, exponential, or step-function?
3. How to handle "evergreen" content that shouldn't decay?
4. Should decay affect retrieval ranking or just cleanup?
5. How to tune rates based on retrieval patterns?

Return ONLY valid JSON:
{{
  "thesis_id": "L12",
  "measurement": {{"signals": ["list"], "metrics": "how to measure correctness"}},
  "decay_function": {{"options": ["linear", "exponential", "step"], "recommendation": "which and why"}},
  "evergreen_handling": {{"detection": "how to identify", "treatment": "what to do"}},
  "decay_application": {{"retrieval_ranking": true/false, "cleanup": true/false, "recommendation": "how to use"}},
  "tuning_process": {{"data_needed": ["list"], "adjustment_algorithm": "how to tune"}}
}}"""
    },
    {
        "id": "L13",
        "title": "Subagent Task Distribution",
        "prompt": f"""You are an expert on multi-agent AI systems and task allocation.

{SYSTEM_CONTEXT}

THESIS TOPIC: Subagent Task Distribution

We use Haiku subagents to coordinate Gemini workers. Need to optimize when to use subagents vs direct execution.

RESEARCH QUESTIONS:
1. What task characteristics benefit from subagent coordination?
2. When is direct Bash execution better than spawning subagent?
3. How to minimize subagent overhead (token cost, latency)?
4. Should subagents return data or just coordinates?
5. Pattern for subagent → subagent delegation?

Return ONLY valid JSON:
{{
  "thesis_id": "L13",
  "subagent_criteria": {{"use_when": ["list"], "skip_when": ["list"]}},
  "direct_vs_subagent": {{"direct_better": ["scenarios"], "subagent_better": ["scenarios"]}},
  "overhead_reduction": {{"techniques": ["list"], "expected_savings": "estimate"}},
  "data_vs_coordinates": {{"return_data_when": ["scenarios"], "return_coordinates_when": ["scenarios"]}},
  "nested_delegation": {{"pattern": "when/how", "max_depth": "recommendation"}}
}}"""
    },
    {
        "id": "L14",
        "title": "Error Recovery Patterns",
        "prompt": f"""You are an expert on distributed systems error handling.

{SYSTEM_CONTEXT}

THESIS TOPIC: Error Recovery Patterns for Our System

Failures happen: Gemini rate limits, Qdrant timeouts, malformed JSON, etc. Need graceful recovery.

RESEARCH QUESTIONS:
1. What errors should retry vs fail fast?
2. How to preserve partial progress on failure?
3. Pattern for "resume from checkpoint" after crash?
4. How to detect silent failures (empty output, bad data)?
5. Alerting: what failures need human attention?

Return ONLY valid JSON:
{{
  "thesis_id": "L14",
  "retry_vs_fail": {{"retry": ["error types"], "fail_fast": ["error types"], "criteria": "how to decide"}},
  "partial_progress": {{"preservation": "how to save", "resume": "how to continue"}},
  "checkpoint_resume": {{"checkpoint_format": "structure", "resume_process": "steps"}},
  "silent_failure_detection": {{"checks": ["list"], "validation": "how to verify success"}},
  "alerting": {{"human_attention": ["list"], "auto_handle": ["list"]}}
}}"""
    },
    {
        "id": "L15",
        "title": "Research Synthesis Patterns",
        "prompt": f"""You are an expert on knowledge synthesis and action planning.

{SYSTEM_CONTEXT}

THESIS TOPIC: Research Synthesis Patterns

We have lots of research in Qdrant but need patterns to synthesize multiple pieces into actionable plans.

RESEARCH QUESTIONS:
1. How to query for related research across topics?
2. Pattern for "combine findings from X, Y, Z into plan"?
3. How to detect contradictions between research pieces?
4. When to re-research vs synthesize existing?
5. Output format for synthesized action plans?

Return ONLY valid JSON:
{{
  "thesis_id": "L15",
  "cross_topic_query": {{"technique": "how to find related", "query_pattern": "example"}},
  "synthesis_pattern": {{"input": "what to gather", "process": "how to combine", "output": "format"}},
  "contradiction_detection": {{"signals": ["list"], "resolution": "what to do"}},
  "reresearch_vs_synthesize": {{"reresearch_when": ["triggers"], "synthesize_when": ["triggers"]}},
  "action_plan_format": {{"structure": "template", "required_fields": ["list"]}}
}}"""
    },
    {
        "id": "L16",
        "title": "Session Continuity Patterns",
        "prompt": f"""You are an expert on stateful systems and session management.

{SYSTEM_CONTEXT}

THESIS TOPIC: Session Continuity Patterns

How to maintain continuity when Claude sessions restart, context compacts, or instances change.

RESEARCH QUESTIONS:
1. What state MUST persist across sessions?
2. Where to store session state? (files vs Qdrant vs both)
3. How to detect "I'm continuing previous work" vs "fresh start"?
4. Pattern for loading minimal context to resume?
5. How to handle conflicting state from parallel sessions?

Return ONLY valid JSON:
{{
  "thesis_id": "L16",
  "persistent_state": {{"must_persist": ["list"], "can_regenerate": ["list"]}},
  "storage_location": {{"files": ["what"], "qdrant": ["what"], "recommendation": "split strategy"}},
  "continuation_detection": {{"signals": ["list"], "heuristics": "how to detect"}},
  "minimal_context_load": {{"essential": ["list"], "load_on_demand": ["list"], "pattern": "how"}},
  "conflict_resolution": {{"detection": "how to find", "resolution": "what to do"}}
}}"""
    }
]

def find_git_bash():
    candidates = [
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files\Git\bin\bash.exe",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return "bash"

def call_gemini(account: int, prompt: str) -> str:
    script_path = SCRIPT_DIR / "gemini-account.sh"
    if sys.platform == "win32":
        bash_path = find_git_bash()
        cmd = [bash_path, str(script_path), str(account), prompt, "gemini-2.0-flash"]
    else:
        cmd = ["bash", str(script_path), str(account), prompt, "gemini-2.0-flash"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return result.stdout
    except subprocess.TimeoutExpired:
        return '{"error": "timeout"}'
    except Exception as e:
        return f'{{"error": "{str(e)}"}}'

def clean_output(text: str) -> str:
    if "Loaded cached credentials." in text:
        text = text.split("Loaded cached credentials.", 1)[-1].strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def main():
    print(f"=== SYSTEM THESES L09-L16 ({len(THESES)} topics) ===")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Delay: 5s between calls")
    print()

    results = []
    account = 1

    for i, thesis in enumerate(THESES):
        print(f"[{i+1}/{len(THESES)}] {thesis['id']}: {thesis['title']} (Account {account})")

        output = call_gemini(account, thesis["prompt"])
        cleaned = clean_output(output)

        output_file = OUTPUT_DIR / f"{thesis['id']}_{thesis['title'].replace(' ', '_')}.json"
        output_file.write_text(cleaned)

        size = len(cleaned)
        if size > 500:
            print(f"  OK: {size} bytes")
            results.append({"id": thesis["id"], "status": "ok", "size": size})
        else:
            print(f"  SMALL: {size} bytes (may have failed)")
            results.append({"id": thesis["id"], "status": "small", "size": size})

        account = 2 if account == 1 else 1
        if i < len(THESES) - 1:
            time.sleep(5)

    print()
    print("=== SUMMARY ===")
    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"Success: {ok}/{len(THESES)}")

if __name__ == "__main__":
    main()
