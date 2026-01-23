# SPEC-033: Lean Copilot Integration

> **Status:** Pending
>
> **Target:** v4.0
>
> **Resolves:** Manual tactic generation; no in-editor LLM assistance
>
> **Prerequisites:** SPEC-032 (multi-model routing)

---

## Summary

Integrate [Lean Copilot](https://github.com/lean-dojo/LeanCopilot) to provide **LLM-backed tactic suggestions** directly within Lean 4 proof development. This enables GPT-5.2 or other frontier models to suggest tactics in real-time.

---

## Motivation

**Current state:**
1. Write Lean code manually
2. Run `erdos loop` for automated iteration
3. No in-editor assistance

**Gap:** No real-time LLM suggestions during interactive proof development.

**Lean Copilot fills this gap:**
- `suggest_tactics` — LLM suggests next proof steps
- `search_proof` — LLM + aesop searches for multi-tactic proofs
- `select_premises` — Retrieves relevant lemmas/theorems

**Key feature:** Lean Copilot supports **external API mode** — no local GPU required.

---

## Scope

### In Scope

1. **External API server** — Python server implementing Lean Copilot's external model API
2. **Lean Copilot lakefile integration** — Add LeanCopilot dependency
3. **CLI command** — `erdos lean copilot serve` to start the API server
4. **Model routing** — Use GPT-5.2 for tactic generation via SPEC-032

### Out of Scope

- Local model inference (no GPU requirement)
- Training custom models
- Modifying Lean Copilot source
- VS Code extension integration (users install separately)

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Lean 4 Proof Environment                 │
│                    (VS Code + lean4 extension)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   theorem erdos_42 : ... := by                              │
│     suggest_tactics  -- Calls external API                  │
│                      -- GPT-5.2 suggests: "apply Nat.le"    │
│     search_proof     -- Orchestrates multi-step search      │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (localhost:8000)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              erdos lean copilot serve                       │
│           (implements external_model_api.yaml)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   FastAPI server:                                           │
│   POST /generate → calls ModelRouter(TACTIC_GENERATION)     │
│   POST /encode   → calls embedding model (for retrieval)    │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
   ┌─────────┐       ┌─────────┐       ┌─────────┐
   │ GPT-5.2 │       │ Claude  │       │  Local  │
   │ (math)  │       │ (code)  │       │ (embed) │
   └─────────┘       └─────────┘       └─────────┘
```

---

## External API Server

### API Specification

Lean Copilot expects an API server implementing:

```yaml
# Based on LeanCopilot external_model_api.yaml

openapi: 3.0.0
info:
  title: Lean Copilot External Model API
  version: 1.0.0

paths:
  /generate:
    post:
      summary: Generate tactic suggestions
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                prompt:
                  type: string
                  description: Proof state and context
                num_samples:
                  type: integer
                  default: 5
                temperature:
                  type: number
                  default: 0.2
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  tactics:
                    type: array
                    items:
                      type: string

  /encode:
    post:
      summary: Generate embeddings for premise retrieval
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                texts:
                  type: array
                  items:
                    type: string
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  embeddings:
                    type: array
                    items:
                      type: array
                      items:
                        type: number
```

### Server Implementation

```python
# src/erdos/lean_copilot/server.py

from fastapi import FastAPI
from pydantic import BaseModel
from erdos.core.llm.router import ModelRouter, TaskType

app = FastAPI(title="Erdos Lean Copilot API")

class GenerateRequest(BaseModel):
    prompt: str
    num_samples: int = 5
    temperature: float = 0.2

class GenerateResponse(BaseModel):
    tactics: list[str]

class EncodeRequest(BaseModel):
    texts: list[str]

class EncodeResponse(BaseModel):
    embeddings: list[list[float]]

@app.post("/generate", response_model=GenerateResponse)
async def generate_tactics(request: GenerateRequest) -> GenerateResponse:
    """Generate tactic suggestions using GPT-5.2."""
    router = get_model_router()

    # Build prompt for tactic generation
    system_prompt = """You are a Lean 4 theorem prover assistant.
Given a proof state, suggest tactics that could make progress.
Return only the tactic names/applications, one per line.
Do not include explanations."""

    full_prompt = f"{system_prompt}\n\nProof state:\n{request.prompt}"

    # Generate multiple samples
    tactics = []
    for _ in range(request.num_samples):
        response = await router.complete(
            TaskType.TACTIC_GENERATION,
            full_prompt,
            temperature=request.temperature,
        )
        # Parse tactics from response
        for line in response.content.strip().split("\n"):
            tactic = line.strip()
            if tactic and tactic not in tactics:
                tactics.append(tactic)

    return GenerateResponse(tactics=tactics[:request.num_samples])

@app.post("/encode", response_model=EncodeResponse)
async def encode_texts(request: EncodeRequest) -> EncodeResponse:
    """Generate embeddings for premise retrieval."""
    # Use OpenAI embeddings or local model
    embeddings = await get_embeddings(request.texts)
    return EncodeResponse(embeddings=embeddings)
```

---

## CLI Command

```bash
erdos lean copilot serve [OPTIONS]

# Examples:
erdos lean copilot serve                    # Default port 8000
erdos lean copilot serve --port 8080        # Custom port
erdos lean copilot serve --host 0.0.0.0     # Expose to network
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | 8000 | Server port |
| `--host` | 127.0.0.1 | Bind address |
| `--model` | gpt-5.2 | Model for tactic generation |
| `--log-level` | info | Logging verbosity |

---

## Lean Project Configuration

### lakefile.lean

```lean
-- formal/lean/lakefile.lean

import Lake
open Lake DSL

require LeanCopilot from git
  "https://github.com/lean-dojo/LeanCopilot.git" @ "v4.23.0"

package erdos where
  -- existing config...

-- Add Lean Copilot to default build
@[default_target]
lean_lib Erdos where
  globs := #[.submodules `Erdos]
```

### Lean Copilot Configuration

```lean
-- formal/lean/Erdos/Copilot.lean

import LeanCopilot

-- Configure external API endpoint
set_option LeanCopilot.externalApiUrl "http://localhost:8000"

-- Example usage in proof:
theorem example : 1 + 1 = 2 := by
  suggest_tactics  -- Calls external API
  -- GPT-5.2 suggests: "rfl", "simp", "norm_num"
```

---

## Prompt Engineering

### Tactic Generation Prompt

```
You are a Lean 4 theorem prover assistant specializing in combinatorics and number theory.

Given the following proof state:
- Goal: {goal}
- Hypotheses: {hypotheses}
- Context: {context}

Suggest tactics that could make progress toward the goal.

Guidelines:
1. Prefer simple tactics (rfl, simp, exact) when applicable
2. For induction, suggest the correct induction principle
3. For combinatorics, consider: Finset, Nat.card, Fintype
4. For number theory, consider: Nat.Prime, Nat.gcd, Nat.mod

Return only tactic names/applications, one per line.
Do not include explanations or comments.
```

### Response Parsing

```python
def parse_tactics(response: str) -> list[str]:
    """Parse tactic suggestions from LLM response."""
    tactics = []
    for line in response.strip().split("\n"):
        # Remove common prefixes
        line = line.strip()
        line = line.lstrip("- •·")
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("--") or line.startswith("#"):
            continue

        # Remove trailing punctuation
        line = line.rstrip(".,;:")

        if line:
            tactics.append(line)

    return tactics
```

---

## Testing

### Unit Tests

```python
# tests/unit/lean_copilot/test_server.py

def test_generate_parses_tactics():
    """Verify tactic parsing from LLM response."""
    ...

def test_generate_deduplicates():
    """No duplicate tactics in response."""
    ...

def test_encode_returns_correct_dimensions():
    """Embeddings have expected shape."""
    ...
```

### Integration Tests

```python
# tests/integration/test_lean_copilot.py

@pytest.mark.requires_network
@pytest.mark.requires_openai_key
def test_server_generate_endpoint():
    """End-to-end tactic generation."""
    ...

@pytest.mark.requires_lean
def test_lean_copilot_integration():
    """Verify Lean Copilot calls external API."""
    ...
```

---

## Acceptance Criteria

1. [ ] `erdos lean copilot serve` starts FastAPI server
2. [ ] `/generate` endpoint returns tactic suggestions
3. [ ] `/encode` endpoint returns embeddings
4. [ ] Server uses SPEC-032 model router for GPT-5.2
5. [ ] Lean Copilot lakefile integration documented
6. [ ] `suggest_tactics` works in Lean 4 proof
7. [ ] Latency < 2s for typical tactic generation
8. [ ] Clear error messages on API key issues
9. [ ] Unit and integration tests pass

---

## Future Enhancements

- **Premise retrieval** — Use research workspace for context
- **Multi-step search** — `search_proof` with beam search
- **Caching** — Cache common tactic suggestions
- **Streaming** — Return suggestions as they're generated

---

## References

- [Lean Copilot GitHub](https://github.com/lean-dojo/LeanCopilot)
- [Lean Copilot Paper](https://arxiv.org/abs/2404.12534)
- [LeanDojo Project](https://leandojo.org/)
- [future-ideations.md](../future/future-ideations.md) — Architecture diagram

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-23 | Initial draft |
