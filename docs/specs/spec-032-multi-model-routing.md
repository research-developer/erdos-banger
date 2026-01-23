# SPEC-032: Multi-Model Routing

> **Status:** Pending
>
> **Target:** v3.5
>
> **Resolves:** Single-model limitation; task-appropriate model selection
>
> **Prerequisites:** SPEC-028 (v3 verification), SPEC-029 (Exa)

---

## Summary

Implement **task-appropriate model routing** so different operations use the best-suited LLM:

- **GPT-5.2** for mathematical reasoning (tactic generation, proof search)
- **Claude Opus 4.5** for code generation (Lean skeletons, tooling)
- **Exa Research** for literature synthesis

This replaces the current single-model approach (`ERDOS_LLM_COMMAND`).

---

## Motivation

**Current state:** All LLM operations go through `ERDOS_LLM_COMMAND` — a single model for everything.

**Problem:** Different tasks have different optimal models:

| Task | Best Model | Why |
|------|------------|-----|
| Tactic generation | GPT-5.2 | 100% AIME 2025, best math reasoning |
| Proof strategy | GPT-5.2 | Abstract reasoning, multi-step math |
| Lean code generation | Claude Opus 4.5 | 80.9% SWE-bench, best code |
| Literature synthesis | Exa Research | Purpose-built, 94.9% SimpleQA |
| General reasoning | GPT-5.2 | Default to math-optimized |

**Solution:** Route tasks to appropriate models based on task type.

---

## Scope

### In Scope

1. **Model router** — Selects model based on task type
2. **Configuration** — Per-task model assignments
3. **CLI integration** — Existing commands use router transparently
4. **Fallback chain** — If primary unavailable, try secondary

### Out of Scope

- Dynamic model selection based on content analysis
- Cost optimization (future spec)
- Model fine-tuning or custom models
- Streaming responses (current batch mode sufficient)

---

## Configuration

### Environment Variables

```bash
# .env

# Primary models (task-specific)
ERDOS_MODEL_MATH=gpt-5.2              # Math reasoning, tactics
ERDOS_MODEL_CODE=claude-opus-4.5      # Code generation
ERDOS_MODEL_RESEARCH=exa-research     # Literature synthesis

# Fallback (if primary unavailable)
ERDOS_MODEL_FALLBACK=gpt-5.2

# API keys (existing)
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
EXA_API_KEY=...
```

### Configuration File (Optional)

```yaml
# config/models.yaml

models:
  math:
    provider: openai
    model: gpt-5.2
    temperature: 0.2
    max_tokens: 4096
    reasoning_effort: xhigh

  code:
    provider: anthropic
    model: claude-opus-4-5-20251101
    temperature: 0.1
    max_tokens: 8192

  research:
    provider: exa
    model: exa-research-pro

  fallback:
    provider: openai
    model: gpt-5.2
    temperature: 0.3

routing:
  tactic_generation: math
  proof_search: math
  lean_skeleton: code
  lean_repair: code
  literature_query: research
  ask_question: math
  general: math
```

---

## Architecture

### Module Structure

```
src/erdos/core/
  llm/
    __init__.py
    router.py           # Task → model routing
    providers/
      __init__.py
      openai.py         # OpenAI API adapter
      anthropic.py      # Anthropic API adapter
      exa.py           # Exa Research adapter
      base.py          # Protocol/ABC for providers
```

### Router Implementation

```python
# src/erdos/core/llm/router.py

from enum import Enum
from dataclasses import dataclass
from erdos.core.llm.providers.base import LLMProvider, LLMResponse

class TaskType(str, Enum):
    """Task types for model routing."""
    TACTIC_GENERATION = "tactic_generation"
    PROOF_SEARCH = "proof_search"
    LEAN_SKELETON = "lean_skeleton"
    LEAN_REPAIR = "lean_repair"
    LITERATURE_QUERY = "literature_query"
    ASK_QUESTION = "ask_question"
    GENERAL = "general"

@dataclass
class ModelConfig:
    """Configuration for a model."""
    provider: str  # openai, anthropic, exa
    model: str
    temperature: float = 0.2
    max_tokens: int = 4096
    reasoning_effort: str | None = None  # OpenAI only

class ModelRouter:
    """Routes tasks to appropriate LLM providers."""

    def __init__(
        self,
        providers: dict[str, LLMProvider],
        routing: dict[TaskType, str],
        fallback: str = "openai",
    ):
        self.providers = providers
        self.routing = routing
        self.fallback = fallback

    def route(self, task: TaskType) -> LLMProvider:
        """Get provider for task type."""
        provider_name = self.routing.get(task, self.fallback)
        if provider_name not in self.providers:
            provider_name = self.fallback
        return self.providers[provider_name]

    async def complete(
        self,
        task: TaskType,
        prompt: str,
        **kwargs,
    ) -> LLMResponse:
        """Route and execute completion."""
        provider = self.route(task)
        return await provider.complete(prompt, **kwargs)
```

### Provider Protocol

```python
# src/erdos/core/llm/providers/base.py

from typing import Protocol
from dataclasses import dataclass

@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    provider: str
    usage: dict | None = None  # tokens used
    cached: bool = False

class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    async def complete(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """Generate completion."""
        ...

    def is_available(self) -> bool:
        """Check if provider is configured and reachable."""
        ...
```

---

## CLI Integration

### Transparent Routing

Existing commands automatically use the router:

```bash
# Uses MATH model (GPT-5.2)
erdos ask 6 "What's the current best bound?"

# Uses CODE model (Claude)
erdos lean formalize 6

# Uses MATH model for tactics, CODE model for repairs
erdos loop 6 --max-iterations 10

# Uses RESEARCH model (Exa)
erdos research exa 6 "What approaches exist?"
```

### Explicit Override

Force a specific model:

```bash
erdos ask 6 "..." --model claude-opus-4.5
erdos loop 6 --tactic-model gpt-5.2 --repair-model claude-opus-4.5
```

---

## Fallback Chain

If primary model unavailable:

```
1. Try primary model for task type
2. If unavailable (no API key, rate limited, error):
   - Log warning
   - Try fallback model
3. If fallback unavailable:
   - Raise clear error with setup instructions
```

Example:

```
[WARN] Claude unavailable (ANTHROPIC_API_KEY not set)
[INFO] Falling back to GPT-5.2 for code generation
```

---

## Migration Path

### Phase 1: Parallel Support

Both old and new approaches work:

```bash
# Old way (still works)
ERDOS_LLM_COMMAND=./scripts/llm.sh erdos ask 6 "..."

# New way
ERDOS_MODEL_MATH=gpt-5.2 erdos ask 6 "..."
```

### Phase 2: Deprecation

```
[DEPRECATION] ERDOS_LLM_COMMAND is deprecated.
              Use ERDOS_MODEL_MATH, ERDOS_MODEL_CODE instead.
              Will be removed in v4.0.
```

### Phase 3: Removal (v4.0)

Remove `ERDOS_LLM_COMMAND` support entirely.

---

## Testing

### Unit Tests

```python
# tests/unit/llm/test_router.py

def test_router_selects_correct_provider():
    """Verify task → provider mapping."""
    ...

def test_router_falls_back_on_unavailable():
    """Verify fallback behavior."""
    ...

def test_router_raises_on_no_providers():
    """Clear error when nothing configured."""
    ...
```

### Integration Tests

```python
# tests/integration/test_multi_model.py

@pytest.mark.requires_network
@pytest.mark.requires_openai_key
def test_openai_provider():
    """End-to-end OpenAI completion."""
    ...

@pytest.mark.requires_network
@pytest.mark.requires_anthropic_key
def test_anthropic_provider():
    """End-to-end Anthropic completion."""
    ...
```

---

## Acceptance Criteria

1. [ ] `ModelRouter` selects provider based on task type
2. [ ] Configuration via environment variables works
3. [ ] Configuration via `config/models.yaml` works
4. [ ] Fallback chain executes on provider unavailability
5. [ ] `erdos ask` uses MATH model by default
6. [ ] `erdos lean formalize` uses CODE model by default
7. [ ] `--model` override works on all commands
8. [ ] Clear error messages when no providers configured
9. [ ] Deprecation warning for `ERDOS_LLM_COMMAND`
10. [ ] Unit and integration tests pass

---

## References

- [future-ideations.md](../future/future-ideations.md) — Model comparison table
- [OpenAI API](https://platform.openai.com/docs/api-reference)
- [Anthropic API](https://docs.anthropic.com/en/api)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-23 | Initial draft |
