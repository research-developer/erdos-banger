# ADR-002: Bounded Contexts + Composition Root (Clean Architecture)

**Status:** Accepted
**Date:** 2026-01-25
**Related:** `docs/_specs/master-vision.md`, `src/erdos/core/context.py`, `src/erdos/core/ports.py`

## Context

`erdos-banger` is a CLI-first system. Historically, CLI command modules can
accumulate orchestration and cross-cutting concerns (configuration reads,
network clients, filesystem paths), leading to:

- "god command" modules that are hard to test and review
- duplicated wiring (constructing the same clients/services in multiple places)
- tight coupling between domain policy and infrastructure adapters

We want the codebase to remain:

- **local-first** (works with minimal setup; derived stores are regenerable)
- **testable** (fast unit tests; explicit `requires_network` tests for IO)
- **extensible** without constant refactors

## Decision

Adopt a **bounded-context** organization under `src/erdos/core/` and a single
**composition root** for dependency wiring:

1. **Bounded core contexts:** group domain logic into subpackages by responsibility
   (e.g., `core/ingest/`, `core/search/`, `core/loop/`, `core/research/`).
2. **Stable contracts:** define dependency-inversion interfaces as `typing.Protocol`
   ports in `src/erdos/core/ports.py` (prefer narrow ports over monolithic ones).
3. **Single wiring point:** construct concrete dependencies in `AppContext`
   (`src/erdos/core/context.py`) and have CLI commands request dependencies
   from the context instead of constructing them directly.
4. **Centralized configuration:** prefer `AppConfig.from_env()` as the SSOT for
   configuration reads and thread configuration through the composition root.

## Options Considered

### Option A (Chosen): Bounded Contexts + Ports + Composition Root

#### Pros

- Supports SRP: each subpackage has a narrow responsibility
- Improves DIP: policy depends on ports, not concrete adapters
- Improves testability: unit tests can inject fakes via ports/context constructors
- Keeps CLI code thin and consistent

#### Cons

- Adds a small amount of structure/indirection
- Requires discipline to avoid re-introducing "core root" module sprawl

### Option B: Keep Logic in Command Modules

#### Pros

- Fewer files and layers

#### Cons

- Tends to produce large, coupled modules over time
- Forces tests to monkeypatch boundaries instead of injecting dependencies

### Option C: Service Locator / Global Singletons

#### Pros

- Easy access to shared dependencies

#### Cons

- Hidden dependencies, harder tests, and unclear lifecycle

## Consequences

- New core logic should live in an existing bounded context (or a new subpackage
  if a truly new domain emerges), not as new `core/*.py` top-level modules.
- CLI commands should be thin adapters that:
  - parse flags/args
  - call a core service/use-case
  - emit output via shared presenter helpers
- Ports should remain stable and narrow; prefer adding new ports over growing
  one mega-interface.
