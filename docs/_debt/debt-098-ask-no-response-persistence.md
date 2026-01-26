# DEBT-098: `erdos ask` Does Not Persist LLM Responses

**Created:** 2026-01-26
**Priority:** High
**Component:** `erdos ask`, `erdos.core.ask`, `erdos.core.run_logger_summaries`

## Summary

The `erdos ask` command sends questions to GPT-5.2 Pro but does NOT persist the LLM responses. Only metadata (response length) is saved to the run log. This breaks iterative proof development workflows where you need to build upon previous LLM insights.

## Evidence

### Current Behavior

The `_summarize_ask` function in `src/erdos/core/run_logger_summaries.py`:

```python
def _summarize_ask(data: dict[str, Any]) -> dict[str, Any]:
    """Summarize 'erdos ask' command result."""
    sources = data.get("sources", [])
    answer = data.get("answer", "")
    return {
        "sources_retrieved": len(sources) if isinstance(sources, list) else 0,
        "llm_enabled": data.get("llm_enabled", False),
        "answer_length": len(answer) if isinstance(answer, str) else 0,  # <-- Only LENGTH!
    }
```

Run log entry shows only metadata:
```json
{
  "command": "erdos ask",
  "result": {
    "sources_retrieved": 2,
    "llm_enabled": true,
    "answer_length": 1523  // Response text is LOST
  }
}
```

### Contrast with `erdos loop`

The loop command DOES save full LLM interactions in `logs/loop/*.jsonl`:

```json
{"event": "llm_prompt", "data": {"prompt": "You are assisting..."}}
{"event": "llm_response", "data": {"response": "<<<<<<< SEARCH...", "exit_code": 0}}
```

## Impact

1. **Lost knowledge**: GPT-5.2 Pro responses cost money and contain valuable insights that disappear
2. **No iterative building**: Can't reference previous answers when formulating follow-up questions
3. **No audit trail**: Can't review what the LLM said to debug proof strategies
4. **Inconsistent design**: `erdos loop` saves responses, `erdos ask` doesn't

## Proposed Fix

### Option A: Save to dedicated ask log (like loop)

Create `logs/ask/` directory with per-session logs:

```python
# In erdos/core/ask/service.py or new ask/logging.py
def log_ask_interaction(problem_id: int, question: str, answer: str, sources: list):
    log_path = get_ask_log_path(problem_id)
    entry = {
        "timestamp": utc_now().isoformat(),
        "problem_id": problem_id,
        "question": question,
        "answer": answer,  # <-- Full response!
        "sources": sources,
    }
    append_jsonl(log_path, entry)
```

### Option B: Include full answer in run log

Update `_summarize_ask` to include the actual response:

```python
def _summarize_ask(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "sources_retrieved": len(sources),
        "llm_enabled": data.get("llm_enabled", False),
        "answer": data.get("answer", ""),  # <-- Full response
        "question": data.get("question", ""),
    }
```

### Option C: Both (recommended)

- Full responses in `logs/ask/*.jsonl` (detailed, per-problem)
- Summary in `logs/runs.jsonl` (quick overview)

## Acceptance Criteria

- [ ] `erdos ask` persists full LLM response somewhere retrievable
- [ ] Can query previous responses: `erdos logs ask --problem 848 --limit 5`
- [ ] Response format matches `erdos loop` pattern for consistency
- [ ] Tests verify response persistence

## Test Plan

```python
def test_ask_persists_llm_response(tmp_path, fake_llm):
    """Verify LLM responses are saved, not just their length."""
    result = runner.invoke(app, ["ask", "6", "What is known?"])

    # Check logs contain full response
    log_entries = load_ask_logs(problem_id=6)
    assert len(log_entries) == 1
    assert "answer" in log_entries[0]
    assert log_entries[0]["answer"] == fake_llm.last_response  # Full text!
```

## Related

- `erdos loop` logging: `src/erdos/core/loop/logging.py` (reference implementation)
- Run logger: `src/erdos/core/run_logger.py`
- Summarizers: `src/erdos/core/run_logger_summaries.py`
- BUG-039: Ingest cannot discover papers (related RAG gap)
