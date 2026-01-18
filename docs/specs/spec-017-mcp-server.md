# Spec 017: MCP Server

> Exposes erdos-banger functionality via Model Context Protocol for AI assistant integration.

**Status:** Pending
**Target:** v1.4
**Prerequisites (SSOT):**
- All CLI commands implemented (Specs 004-016)
- Search index: `docs/_archive/specs/spec-006-search-index.md`
- Lean integration: `docs/_archive/specs/spec-007-lean-integration.md`

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
python -m erdos.mcp
```

### Transport

- **stdio** (v1.4): JSON-RPC over stdin/stdout
- **HTTP** (future): REST API on localhost

---

## 2) Exposed Tools

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

**Output:** `ProblemRecord` as JSON

### 2.2 `list_problems`

List problems with optional filters.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "status": {"type": "string", "enum": ["open", "proved", "disproved"]},
    "prize_min": {"type": "integer"},
    "prize_max": {"type": "integer"},
    "tags": {"type": "array", "items": {"type": "string"}},
    "limit": {"type": "integer", "default": 50}
  }
}
```

**Output:** Array of `ProblemRecord` summaries

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

**Output:** Array of `ReferenceRecord`

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

**Output:** Array of search results with scores

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

**Output:** `LeanCheckResult` with errors array

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

**Output:** Path to generated file

### 2.7 `ask_question`

Ask a question about a problem (RAG).

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "problem_id": {"type": "integer"},
    "question": {"type": "string"},
    "no_llm": {"type": "boolean", "default": true, "description": "Return prompt only, don't call LLM"}
  },
  "required": ["problem_id", "question"]
}
```

**Output:** Prompt (if no_llm) or answer with sources

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

**Output:** Array of log entries

---

## 3) Claude Desktop Configuration

Add to Claude Desktop config (`~/.config/claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "erdos": {
      "command": "erdos-mcp",
      "args": [],
      "env": {
        "ERDOS_DATA_PATH": "/path/to/erdos-banger/data"
      }
    }
  }
}
```

Or with explicit Python path:

```json
{
  "mcpServers": {
    "erdos": {
      "command": "python",
      "args": ["-m", "erdos.mcp"],
      "cwd": "/path/to/erdos-banger"
    }
  }
}
```

---

## 4) Implementation

### 4.1 New Module: `src/erdos/mcp/__init__.py`

MCP server entry point using the `mcp` Python package.

```python
from mcp.server import Server
from mcp.types import Tool

server = Server("erdos")

@server.tool()
async def get_problem(problem_id: int) -> dict:
    """Get details for a specific Erdős problem."""
    loader = ProblemLoader.from_default()
    problem = loader.get_by_id(problem_id)
    return problem.model_dump()

# ... register all tools
```

### 4.2 Entry Point

Add to `pyproject.toml`:

```toml
[project.scripts]
erdos-mcp = "erdos.mcp:main"
```

### 4.3 Dependencies

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
mcp = [
    "mcp>=0.1.0",
]
```

**Install:** `pip install erdos-banger[mcp]`

---

## 5) Error Handling

### Tool Errors

Return structured errors that AI can understand:

```json
{
  "error": {
    "type": "not_found",
    "message": "Problem 9999 not found",
    "code": 404
  }
}
```

### Server Errors

MCP protocol handles transport errors. Tool-level errors should be returned as structured responses, not exceptions.

---

## 6) Verification: This Spec is Testable

### Vertical Slice Test

```bash
# Start MCP server (in background)
erdos-mcp &

# Test via MCP client (example using mcp-client-cli)
echo '{"method": "tools/call", "params": {"name": "get_problem", "arguments": {"problem_id": 6}}}' | mcp-client-cli

# Or test directly via Python
python -c "
from erdos.mcp import server
import asyncio
result = asyncio.run(server.call_tool('get_problem', {'problem_id': 6}))
print(result)
"
```

### Unit Tests

- `tests/unit/test_mcp_tools.py`
  - Each tool returns correct schema
  - Error handling for invalid inputs
  - Tool schemas match expected format

### Integration Tests

- `tests/integration/test_mcp_server.py`
  - Server starts and responds to tool list request
  - `get_problem` returns valid ProblemRecord
  - `search_index` returns results
  - `lean_check` with fixture file

### Acceptance Criteria

```bash
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

### No Network by Default

- `search_index` uses local index only
- `ingest` tool not exposed (requires explicit CLI invocation)

### No Secrets

- MCP server doesn't handle API keys
- LLM calls delegated to external command (Spec 011 pattern)

---

## References

- Model Context Protocol: `https://modelcontextprotocol.io/`
- MCP Python SDK: `https://github.com/anthropics/mcp`
- Master vision MCP section: `docs/specs/master-vision.md` (Section 8)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-18 | Initial spec |
