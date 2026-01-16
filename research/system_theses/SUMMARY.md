# System Improvement Theses - Summary

Research conducted 2026-01-16 via Gemini. All theses specific to OUR system.

## Quick Wins (Do These First)

### 1. Enable GPU for Ollama
```bash
set OLLAMA_NUM_GPU=1
# Restart Ollama
```
**Expected:** 5-10x faster embeddings (2.4s → <500ms)

### 2. Use ThreadPoolExecutor for Batch Embedding
```python
from concurrent.futures import ThreadPoolExecutor

def embed_chunk(chunk):
    return embed_function(chunk)

with ThreadPoolExecutor(max_workers=8) as executor:
    embeddings = list(executor.map(embed_chunk, chunks))
```
**Expected:** Up to 8x speedup on embedding

### 3. Pre-Check Qdrant Before Research
```python
# Threshold: 0.9 = already researched, 0.75 = partial match
hits = client.search(collection, query_vector, score_threshold=0.75)
if hits[0].score > 0.9:
    return "FOUND_EXISTING"
```
**Expected:** Avoid duplicate research, save rate limits

### 4. Track RPM to Avoid Rate Limits
```python
class RateLimitTracker:
    def __init__(self, rpm_limit=60):
        self.count = 0
        self.start_time = time.time()

    def increment(self):
        if time.time() - self.start_time >= 60:
            self.reset()
        if self.count >= 50:  # Warn at 83%
            print("WARNING: Approaching rate limit")
        self.count += 1
```

---

## Thesis Summaries

### L01: Ollama Embedding Optimization
**Problem:** 2.4s per embedding = 24s for 10 chunks

**Root Causes:**
- CPU only (no GPU acceleration)
- Single-threaded calls
- No batch embedding

**Solutions:**
1. Set `OLLAMA_NUM_GPU=1` environment variable
2. Implement batch embedding API calls
3. Consider `all-minilm` (384d, much faster) for non-critical content
4. Target: <500ms per embedding

### L02: Gemini Prompt Engineering
**Problem:** Inconsistent JSON output, markdown wrapping

**Key Finding:** Gemini 2.0 Flash does NOT have JSON mode

**Best Patterns:**
- Schema definition: "Return JSON conforming to this schema: [...]"
- Explicit instruction: "Return ONLY valid JSON. No markdown. No explanation."
- Always include example output in prompt

**Anti-patterns:**
- Asking for conversational output
- Ambiguous instructions
- Not specifying format clearly

### L03: Qdrant Batch Operations
**Problem:** Sequential store = slow

**Solutions:**
- Batch upsert: `PUT /collections/{name}/points` with list of points
- ThreadPoolExecutor for parallel embedding
- Asyncio pipeline: embed chunk N while storing chunk N-1
- gRPC faster than REST

**Target:** 10 chunks in <5 seconds

### L04: Auto-Discovery Before Research
**Problem:** Re-researching existing topics

**Thresholds:**
- 0.9 = high confidence match (skip research)
- 0.75 = partial match (fill gaps only)
- Below 0.75 = proceed with new research

**Integration Point:** Immediately before Gemini call

**Gap Filling Prompt:** "Using existing research as context, address these aspects not covered: [gaps]"

### L05: Subagent Summary Validation
**Problem:** Haiku summaries lose implementation details

**Required Sections:**
1. Code Snippets (regex: `def `, `import `)
2. Commands (CLI patterns)
3. URLs (https?://...)
4. Numbers (specific values)

**Pattern:** Summary + point_ids for drill-down

**Minimum Viable Summary:** Overview + all code/commands/URLs/numbers required for action

### L06: Code Indexing for Qdrant
**What to Index:**
- Key functions with docstrings
- Common patterns
- NOT: entire codebase, generated code, dependencies

**Chunking:**
- Unit: Function or Class
- Max: 512 tokens
- Include: imports, module docstrings

**Embedding:** Code + docstring concatenated

**Freshness:** Trigger on git commit, track by commit hash

### L07: Embedding Model Comparison
**Models for 4GB VRAM:**
- `nomic-embed-text`: 768d, current (slow)
- `all-minilm`: 384d, very fast, lower quality
- `mxbai-embed-large`: 1024d, higher quality, needs more VRAM

**Recommendation:** Test `all-minilm` for speed-critical paths

### L08: Gemini Worker Health Monitoring
**Rate Limit Tracking:**
- Track RPM per account
- Warn at 50 RPM (83% of limit)
- Reset counter every 60s

**Circuit Breaker States:**
- CLOSED: Normal operation
- OPEN: Stop requests, wait timeout
- HALF_OPEN: Test with single request

**Account Rotation:**
- Failover strategy: Account 1 → Account 2 on circuit open
- Track success rates for smart weighting

**Logging:**
- Request timestamps
- Account in use, RPM
- Circuit breaker states
- Full request/response (scrubbed)

---

## Implementation Priority

1. **Immediate:** GPU for Ollama, batch embedding
2. **This Week:** Pre-check pattern, rate limit tracking
3. **Next:** Summary validation template, code indexing
4. **Later:** Full circuit breaker, gRPC migration

---

## Files

- `L01_Ollama_Embedding_Optimization.json`
- `L02_Gemini_Prompts.json`
- `L03_Qdrant_Batch_Operations.json`
- `L04_Auto_Discovery.json`
- `L05_Subagent_Summary_Validation.json`
- `L06_Code_Indexing.json`
- `L07_Embedding_Model_Comparison.json`
- `L08_Worker_Health.json`
