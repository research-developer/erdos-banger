# Spec 017: MCP Server

> Exposes erdos-banger functionality via Model Context Protocol for AI assistant integration.

**Status:** Complete
**Implemented In:** c995379
**Target:** v1.4
**Prerequisites (SSOT):**
- CLI patterns: `docs/_archive/specs/spec-004-cli-architecture.md`
- Domain models + `CLIOutput`: `docs/_archive/specs/spec-003-domain-models.md`
- Presenter utilities (JSON routing): `docs/_archive/specs/spec-009-architecture-cleanup.md`
- Search index: `docs/_archive/specs/spec-006-search-index.md`
- Lean integration: `docs/_archive/specs/spec-007-lean-integration.md`
- Optional tools require their owning specs:
  - `ask_question`: `docs/_archive/specs/spec-011-ask-command.md`
  - `get_logs`: `docs/specs/spec-013-logging-evaluation.md`
  - semantic/hybrid modes: `docs/specs/spec-014-vector-embeddings.md`
  - formalization import/status: `docs/specs/spec-016-formal-conjectures.md`

---

## 0) Scope (v1.4)

### In scope

1. **MCP server** exposing core erdos-banger tools
2. **Claude Desktop integration** via config
3. **Tool schemas** with proper typing
4. **Stateless operation** (each call is independent)

### Out of scope

- Streaming responses
- Authentication/authorization
- Multi-user sessions
- Web-based MCP transport (stdio only for v1.4)

### Background

The Model Context Protocol (MCP) is an open standard by Anthropic for connecting AI assistants to external tools. Instead of the AI executing shell commands, it can call typed functions directly.

Benefits:
- Structured inputs/outputs (no shell parsing)
- Better error handling
- Faster execution (no subprocess overhead)
- Discoverable tool schemas

---

## 1) MCP Server Interface

### Launch Command

```bash
erdos-mcp
# or
python -m erdos.mcp.server
```

### Transport

- **stdio** (v1.4): JSON-RPC over stdin/stdout
- **HTTP** (future): REST API on localhost

---

## 2) Exposed Tools

### Tool Availability (Non-negotiable)

- Core v1 tools are always registered:
  - `get_problem`, `list_problems`, `get_references`, `search_index`, `lean_check`, `lean_formalize`
- Optional tools are registered **only if** their prerequisite spec is implemented and importable:
  - `ask_question` requires Spec 011 modules to exist
  - `get_logs` requires Spec 013 modules to exist
  - semantic/hybrid modes require Spec 014 modules to exist
  - formalization import/status requires Spec 016 modules to exist

If an optional tool is not registered, it must not appear in the MCP tool list.

### 2.1 `get_problem`

Get details for a specific Erdős problem.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "problem_id": {"type": "integer", "description": "Erdős problem ID"}
  },
  "required": ["problem_id"]
}
```

**Output:** `CLIOutput` where `data` is a `ProblemRecord` (or `error` on failure).

### 2.2 `list_problems`

List problems with optional filters.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "status": {"type": "string", "enum": ["open", "proved", "disproved", "partially_solved", "unknown"]},
    "prize_min": {"type": "integer"},
    "prize_max": {"type": "integer"},
    "tags": {"type": "array", "items": {"type": "string"}},
    "limit": {"type": "integer", "default": 50}
  }
}
```

**Output:** `CLIOutput` where `data` is an array of `ProblemRecord` summaries.

### 2.3 `get_references`

Get references for a problem.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "problem_id": {"type": "integer"}
  },
  "required": ["problem_id"]
}
```

**Output:** `CLIOutput` where `data` is an array of references.

Notes:
- If only `ProblemRecord.references` are available, return `ReferenceEntry` objects.
- If ingestion is implemented (Spec 010), this tool may return enriched `ReferenceRecord` entries instead.

### 2.4 `search_index`

Search the problem/literature index.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string", "description": "Search query"},
    "limit": {"type": "integer", "default": 10},
    "problem_id": {"type": "integer", "description": "Filter to specific problem"},
    "mode": {"type": "string", "enum": ["bm25", "semantic", "hybrid"], "default": "bm25"}
  },
  "required": ["query"]
}
```

**Output:** `CLIOutput` where `data` matches the `erdos search --json` schema (archived Spec 006).

### 2.5 `lean_check`

Compile a Lean file and return errors.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "file": {"type": "string", "description": "Lean file path relative to formal/lean/"}
  },
  "required": ["file"]
}
```

**Output:** `CLIOutput` where `data` is a `LeanCheckResult`.

### 2.6 `lean_formalize`

Generate a Lean skeleton for a problem.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "problem_id": {"type": "integer"},
    "force": {"type": "boolean", "default": false}
  },
  "required": ["problem_id"]
}
```

**Output:** `CLIOutput` where `data` matches the `erdos lean formalize --json` schema.

### 2.7 `ask_question`

Ask a question about a problem (RAG).

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "problem_id": {"type": "integer"},
    "question": {"type": "string"},
    "no_llm": {"type": "boolean", "default": true, "description": "Default true: return prompt/sources only (MCP server does not call an LLM by default)"}
  },
  "required": ["problem_id", "question"]
}
```

**Output:** `CLIOutput` where `data` matches the `erdos ask --json` schema (Spec 011).

### 2.8 `get_logs`

Query run logs.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "problem_id": {"type": "integer"},
    "command": {"type": "string"},
    "limit": {"type": "integer", "default": 20}
  }
}
```

**Output:** `CLIOutput` where `data` is an array of run log entries (Spec 013).

---

## 3) Claude Desktop Configuration

Preferred: use the MCP CLI installer (provided by `mcp[cli]`) to register the server with Claude Desktop:

```bash
# Install server into Claude Desktop
uv run mcp install src/erdos/mcp/server.py --name erdos

# Pass env vars
uv run mcp install src/erdos/mcp/server.py --name erdos -v ERDOS_DATA_PATH=/path/to/data
```

Alternative: manual Claude Desktop JSON config may be used, but is not SSOT (follow official MCP docs for current format).

---

## 4) Implementation

### 4.1 New Module: `src/erdos/mcp/server.py`

MCP server entry point using the MCP Python SDK (`mcp` on PyPI).

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("erdos-banger")

@mcp.tool()
def get_problem(problem_id: int) -> dict:
    """Get details for a specific Erdős problem."""
    # Call existing Python core logic (do NOT shell out to `erdos ...` via subprocess)
    # and return CLIOutput-compatible dicts.
    ...

# ... register all tools, then:
# def main(): mcp.run()
```

### 4.2 Entry Point

Add to `pyproject.toml`:

```toml
[project.scripts]
erdos-mcp = "erdos.mcp.server:main"
```

### 4.3 Dependencies

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
mcp = [
    "mcp[cli]>=1.25.0,<2",
]
```

**Install (uv):** `uv sync --extra mcp`

---

## 5) Error Handling

### Tool Errors

Return errors using `CLIOutput.err(...)` (SSOT: archived Spec 003) so the MCP surface matches the CLI `--json` surface.

If a tool depends on an optional spec that is not implemented/installed, return:

```json
{
  "schema_version": 1,
  "command": "<tool_name>",
  "success": false,
  "data": null,
  "error": {
    "type": "NotImplemented",
    "message": "Feature not yet implemented (requires SPEC-0XX)",
    "code": 1
  }
}
```

### Server Errors

MCP protocol handles transport errors. Tool-level errors should be returned as structured responses, not exceptions.

---

## 6) Verification: This Spec is Testable

### Vertical Slice Test

```bash
# Install MCP optional deps
uv sync --extra mcp

# Run the server in one terminal (stdio)
uv run erdos-mcp

# In another terminal, test with the MCP Inspector (manual):
#   npx -y @modelcontextprotocol/inspector
# Or write a small Python stdio client using mcp.client.stdio (SSOT: MCP Python SDK docs).
```

### Unit Tests

- `tests/unit/test_mcp_tools.py`
  - Each tool returns correct schema
  - Error handling for invalid inputs
  - Core tools (`get_problem`, `list_problems`, `get_references`, `search_index`) must be exercised against `tests/fixtures/sample_problems.yaml` (no network) and assert key fields (e.g., `get_problem(...).data.id == problem_id`)
  - Tool schemas match expected format
  - Tests must be guarded with `pytest.importorskip("mcp")` so the base test suite can run without the optional extra.

### Integration Tests

- `tests/integration/test_mcp_server.py`
  - Server starts and responds to tool list request
  - `get_problem` returns valid ProblemRecord
  - `search_index` returns results
  - `lean_check` with fixture file

### Acceptance Criteria

```bash
uv sync --extra mcp
uv run ruff check .
uv run mypy src/
uv run pytest -m "not requires_lean and not requires_network"
```

---

## 7) Security Considerations

### File System Access

- Tools only access files within the erdos-banger project directory
- No arbitrary file read/write
- Lean files restricted to `formal/lean/`
- Path traversal must be rejected (e.g., `../../etc/passwd`), returning `CLIOutput.err(...)` with `error.type="UsageError"` and `error.code=ExitCode.USAGE_ERROR` (SSOT: `src/erdos/core/exit_codes.py`).

### No Network by Default

- `search_index` uses local index only
- `ingest` is intentionally not exposed as an MCP tool (it can trigger network I/O and filesystem writes); it remains CLI-only

### No Secrets

- MCP server doesn't handle API keys
- LLM calls delegated to external command (Spec 011 pattern)

---

## References

- Model Context Protocol: `https://modelcontextprotocol.io/`
- MCP Python SDK (PyPI): `https://pypi.org/project/mcp/`
- MCP Python SDK (repo): `https://github.com/modelcontextprotocol/python-sdk`
- Master vision MCP section: `docs/specs/master-vision.md` (Section 8)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-18 | Initial spec |
