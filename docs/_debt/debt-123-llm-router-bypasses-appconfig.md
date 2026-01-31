# DEBT-123: LLM Router Bypasses AppConfig for Task-Specific Commands

**Priority:** P2
**Status:** Open
**Found:** 2026-01-31
**Component:** `src/erdos/core/llm/router.py`

## Summary

The LLM router reads task-specific environment variables (`ERDOS_LLM_COMMAND_MATH`, `ERDOS_LLM_COMMAND_CODE`, `ERDOS_LLM_COMMAND_COPILOT`) directly from `os.environ` rather than through `AppConfig`, violating the centralized configuration pattern.

## Evidence

In `src/erdos/core/llm/router.py` lines 52-59:

```python
environ = env if env is not None else dict(os.environ)
chain = get_env_var_chain(task)
for var_name in chain:
    value = environ.get(var_name, "").strip()
```

The router defaults to `os.environ` when no `env` dict is passed. Commands like `ask` and `loop` call it without passing AppConfig's environment context.

## Impact

- Task-specific LLM command selection doesn't go through centralized AppConfig
- Testing is harder - tests need to mock `os.environ` directly
- Inconsistent with other config patterns (Exa, S2, zbMATH all use AppConfig)

## Recommended Fix

1. Add task-routing fields to `AppConfig`:
```python
llm_command_math: str = ""
llm_command_code: str = ""
llm_command_copilot: str = ""
```

2. Update router to accept AppConfig or pass env dict from caller

3. Have commands pass AppConfig's values

## Related

- DEBT-055: Configuration scattered env deps (archived - mostly fixed)
- DEBT-075: Remove remaining env fallbacks (archived - this was missed)
