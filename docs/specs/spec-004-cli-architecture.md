# Spec 004: CLI Architecture

> Defines the Typer-based CLI structure, command patterns, and how commands are tested end-to-end.

---

## Overview

The CLI is the primary interface for erdos-harness. It must be:
- **Consistent** - Same patterns across all commands
- **Testable** - Every command testable without mocking
- **Agent-friendly** - Clean JSON output for LLM agents
- **Ergonomic** - Good help text, sensible defaults

### Guiding Principles

1. **Non-interactive by default** - No prompts unless explicitly requested
2. **Fail fast, fail loud** - Clear error messages with actionable guidance
3. **JSON for machines, pretty for humans** - `--json` flag on every command
4. **Exit codes matter** - Distinct codes for different failure types

---

## 1) CLI Framework: Typer

We use [Typer](https://typer.tiangolo.com/) for the CLI, with [Rich](https://rich.readthedocs.io/) for formatting.

### Why Typer

- Built on Click (battle-tested)
- Auto-generates help from type hints
- Native Rich integration for beautiful output
- Less boilerplate than raw Click

### Entry Point

**pyproject.toml:**
```toml
[project.scripts]
erdos = "erdos.cli:app"
```

---

## 2) Application Structure

```python
# src/erdos/cli.py
"""Erdos CLI - main entry point."""

from typing import Annotated, Optional

import typer
from rich.console import Console

from erdos import __version__
from erdos.commands import lean, list_cmd, refs, search, show

# Create the main app
app = typer.Typer(
    name="erdos",
    help="CLI toolkit for Erdős problem research.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=True,
)

# Global state (shared across commands)
console = Console()
err_console = Console(stderr=True)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"erdos-harness {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON for machine consumption.",
        ),
    ] = False,
    no_network: Annotated[
        bool,
        typer.Option(
            "--no-network",
            help="Disable all network requests.",
        ),
    ] = False,
    config: Annotated[
        Optional[str],
        typer.Option(
            "--config",
            "-c",
            help="Path to config file.",
        ),
    ] = None,
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            help="Logging level: DEBUG, INFO, WARN, ERROR.",
        ),
    ] = "INFO",
) -> None:
    """
    Erdos CLI - toolkit for Erdős problem research.

    Run 'erdos COMMAND --help' for command-specific help.
    """
    # Store global options in context for commands to access
    ctx.ensure_object(dict)
    ctx.obj.update(
        {
            "json": json_output,
            "no_network": no_network,
            "config": config,
            "log_level": log_level,
        }
    )


# Register subcommands
app.add_typer(list_cmd.app, name="list")
app.add_typer(show.app, name="show")
app.add_typer(refs.app, name="refs")
app.add_typer(search.app, name="search")
app.add_typer(lean.app, name="lean")


if __name__ == "__main__":
    app()
```

---

## 3) Command Module Pattern

Each command lives in its own module under `src/erdos/commands/`.

### Standard Command Structure

```python
# src/erdos/commands/show.py
"""erdos show - display problem details."""

from typing import Annotated, Any, cast

import typer
from rich.console import Console
from rich.panel import Panel

from erdos.core.models import CLIOutput, ProblemRecord
from erdos.core.problem_loader import ProblemLoader

app = typer.Typer(
    help="Show detailed problem information.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()
err_console = Console(stderr=True)


def _output(ctx: typer.Context, data: CLIOutput) -> None:
    """Output result based on format preference."""
    if (ctx.obj or {}).get("json"):
        console.print_json(data.model_dump_json())
    elif data.success:
        _print_human(cast("dict[str, Any]", data.data))
    else:
        error = cast("dict[str, Any]", data.error)
        err_console.print(f"[red]Error:[/red] {error['message']}")


def _print_human(problem_data: dict[str, Any]) -> None:
    """Pretty-print problem for humans."""
    # `model_dump(mode="json")` turns enums into strings. With strict models
    # (Spec 003), re-validation needs `strict=False`.
    problem = ProblemRecord.model_validate(problem_data, strict=False)

    title = f"[bold]Problem {problem.id}:[/bold] {problem.title}"
    status_color = {
        "open": "yellow",
        "proved": "green",
        "disproved": "red",
    }.get(problem.status.value, "white")

    panel = Panel(
        f"""
[bold]Status:[/bold] [{status_color}]{problem.status.value}[/{status_color}]
[bold]Prize:[/bold] ${problem.prize}
[bold]Tags:[/bold] {', '.join(problem.tags) or 'None'}

[bold]Statement:[/bold]
{problem.statement}
        """.strip(),
        title=title,
        expand=False,
    )
    console.print(panel)


# ============================================================================
# Core Logic (testable independently)
# ============================================================================

def get_problem(problem_id: int, loader: ProblemLoader) -> CLIOutput:
    """
    Get a problem by ID.

    This is the core logic, separated from CLI concerns for testing.
    """
    try:
        problem = loader.get_by_id(problem_id)
        if problem is None:
            return CLIOutput.err(
                command="erdos show",
                error_type="NotFound",
                message=f"Problem {problem_id} not found",
                code=3,
            )
        return CLIOutput.ok(
            command="erdos show",
            data=problem.model_dump(mode="json"),
        )
    except Exception as e:
        return CLIOutput.err(
            command="erdos show",
            error_type="Error",
            message=str(e),
            code=1,
        )


# ============================================================================
# CLI Command
# ============================================================================

@app.callback(invoke_without_command=True)
def show(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(
            help="Problem ID to display.",
            min=1,
        ),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON for machine consumption.",
        ),
    ] = False,
) -> None:
    """
    Show detailed information about an Erdős problem.

    Example: erdos show 6
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    # Load configuration and create loader
    loader = ProblemLoader.from_default()  # Uses configured data path

    # Execute core logic
    result = get_problem(problem_id, loader)

    # Output based on format
    _output(ctx, result)

    # Exit with appropriate code
    if not result.success:
        error = cast("dict[str, Any]", result.error)
        raise typer.Exit(code=int(error.get("code", 1)))
```

---

## 4) Command Group Pattern (for `lean`)

Commands with subcommands use a Typer group.

```python
# src/erdos/commands/lean.py
"""erdos lean - Lean 4 integration commands."""

from pathlib import Path
from typing import Annotated, Any, Optional, cast

import typer
from rich.console import Console

from erdos.core.lean_runner import LeanRunner
from erdos.core.models import CLIOutput, LeanCheckResult

app = typer.Typer(help="Lean 4 theorem prover commands.")
console = Console()
err_console = Console(stderr=True)


def _output(ctx: typer.Context, data: CLIOutput) -> None:
    if (ctx.obj or {}).get("json"):
        console.print_json(data.model_dump_json())
    elif data.success:
        if isinstance(data.data, dict) and {"file", "success"}.issubset(
            data.data.keys()
        ):
            _print_human_check_result(cast("dict[str, Any]", data.data))
        else:
            console.print(data.data)
    else:
        error = cast("dict[str, Any]", data.error)
        err_console.print(f"[red]Error:[/red] {error['message']}")


def _print_human_check_result(result_data: dict) -> None:
    """Pretty-print Lean check result."""
    result = LeanCheckResult.model_validate(result_data, strict=False)

    if result.success:
        console.print(f"[green]✓[/green] {result.file} compiled successfully")
    else:
        console.print(f"[red]✗[/red] {result.file} has {result.error_count} error(s)")
        for error in result.errors:
            console.print(f"  {error}")


# ============================================================================
# Core Logic
# ============================================================================

def init_lean_project(project_path: Path) -> CLIOutput:
    """Initialize Lean project structure."""
    try:
        runner = LeanRunner(project_path)
        runner.init()
        return CLIOutput.ok(
            command="erdos lean init",
            data={"project_path": str(project_path), "initialized": True},
        )
    except NotImplementedError as e:
        return CLIOutput.err(
            command="erdos lean init",
            error_type="NotImplemented",
            message=str(e),
            code=1,
        )
    except Exception as e:
        return CLIOutput.err(
            command="erdos lean init",
            error_type="InitError",
            message=str(e),
            code=1,
        )


def check_lean_file(file_path: Path, project_path: Path) -> CLIOutput:
    """Check a Lean file for errors."""
    try:
        runner = LeanRunner(project_path)
        result = runner.check(file_path)
        return CLIOutput.ok(
            command="erdos lean check",
            data=result.model_dump(mode="json"),
        )
    except NotImplementedError as e:
        return CLIOutput.err(
            command="erdos lean check",
            error_type="NotImplemented",
            message=str(e),
            code=1,
        )
    except FileNotFoundError:
        return CLIOutput.err(
            command="erdos lean check",
            error_type="NotFound",
            message=f"File not found: {file_path}",
            code=3,
        )
    except Exception as e:
        return CLIOutput.err(
            command="erdos lean check",
            error_type="Error",
            message=str(e),
            code=1,
        )


# ============================================================================
# CLI Commands
# ============================================================================

@app.command()
def init(
    ctx: typer.Context,
    project_path: Annotated[
        Optional[Path],
        typer.Option(
            "--path",
            "-p",
            help="Path to Lean project (default: formal/lean/)",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON for machine consumption.",
        ),
    ] = False,
) -> None:
    """
    Initialize Lean 4 project with mathlib.

    Creates lakefile.lean, lean-toolchain, and directory structure.
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    path = project_path or Path("formal/lean")
    result = init_lean_project(path)
    _output(ctx, result)
    if not result.success:
        error = cast("dict[str, Any]", result.error)
        raise typer.Exit(code=int(error.get("code", 1)))


@app.command()
def check(
    ctx: typer.Context,
    file: Annotated[
        Path,
        typer.Argument(
            help="Lean file to check.",
            exists=True,
            readable=True,
        ),
    ],
    project_path: Annotated[
        Optional[Path],
        typer.Option(
            "--path",
            "-p",
            help="Path to Lean project (default: formal/lean/)",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON for machine consumption.",
        ),
    ] = False,
) -> None:
    """
    Check a Lean file for compilation errors.

    Example: erdos lean check Erdos/Problem006.lean
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    path = project_path or Path("formal/lean")
    result = check_lean_file(file, path)
    _output(ctx, result)

    # Exit with code 5 if Lean has errors
    if (
        result.success
        and isinstance(result.data, dict)
        and not result.data.get("success", True)
    ):
        raise typer.Exit(code=5)
    if not result.success:
        error = cast("dict[str, Any]", result.error)
        raise typer.Exit(code=int(error.get("code", 1)))


@app.command()
def formalize(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(
            help="Problem ID to formalize.",
            min=1,
        ),
    ],
    project_path: Annotated[
        Optional[Path],
        typer.Option(
            "--path",
            "-p",
            help="Path to Lean project (default: formal/lean/)",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON for machine consumption.",
        ),
    ] = False,
) -> None:
    """
    Generate a Lean skeleton for a problem.

    Creates Erdos/Problem<ID>.lean with theorem stub.
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    from erdos.core.formalizer import generate_skeleton
    from erdos.core.problem_loader import ProblemLoader

    path = project_path or Path("formal/lean")
    loader = ProblemLoader.from_default()

    problem = loader.get_by_id(problem_id)
    if problem is None:
        err_console.print(f"[red]Error:[/red] Problem {problem_id} not found")
        raise typer.Exit(code=3)

    try:
        output_file = generate_skeleton(problem, path)
    except NotImplementedError as e:
        result = CLIOutput.err(
            command="erdos lean formalize",
            error_type="NotImplemented",
            message=str(e),
            code=1,
        )
        _output(ctx, result)
        raise typer.Exit(code=1) from None

    if (ctx.obj or {}).get("json"):
        console.print_json(
            CLIOutput.ok(
                command="erdos lean formalize",
                data={"problem_id": problem_id, "file": str(output_file)},
            ).model_dump_json()
        )
    else:
        console.print(f"[green]✓[/green] Created {output_file}")
        console.print(f"  Run: erdos lean check {output_file}")
```

---

## 5) Exit Codes

Consistent exit codes across all commands:

| Code | Meaning | When Used |
|------|---------|-----------|
| 0 | Success | Command completed successfully |
| 1 | General error | Unexpected errors, exceptions |
| 2 | Usage error | Invalid arguments, missing required args |
| 3 | Not found | Requested resource doesn't exist |
| 4 | Network error | Network required but unavailable/failed |
| 5 | Lean error | Lean compilation failed (not a CLI error) |
| 10 | Config error | Invalid configuration |

```python
# src/erdos/core/exit_codes.py
"""Exit codes for CLI commands."""

from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    ERROR = 1
    USAGE_ERROR = 2
    NOT_FOUND = 3
    NETWORK_ERROR = 4
    LEAN_ERROR = 5
    CONFIG_ERROR = 10
```

---

## 6) JSON Output Schema

All `--json` output follows the `CLIOutput` schema:

```json
{
  "schema_version": 1,
  "command": "erdos show",
  "success": true,
  "data": { ... },
  "error": null,
  "timestamp": "2026-01-16T10:30:00+00:00",
  "duration_ms": 42
}
```

Error response:

```json
{
  "schema_version": 1,
  "command": "erdos show",
  "success": false,
  "data": null,
  "error": {
    "type": "NotFound",
    "message": "Problem 9999 not found",
    "code": 3
  },
  "timestamp": "2026-01-16T10:30:00+00:00",
  "duration_ms": 12
}
```

---

## 7) Testing CLI Commands

### Strategy: Three Levels

1. **Unit tests** - Test core logic functions directly
2. **Integration tests** - Test command functions with real data
3. **E2E tests** - Invoke CLI via subprocess, verify output

### Unit Test (Core Logic)

```python
# tests/unit/test_show_logic.py
"""Unit tests for show command logic."""

from erdos.commands.show import get_problem
from erdos.core.models import CLIOutput, ProblemStatus


class TestGetProblem:
    def test_found_problem(self, mock_loader_with_problem) -> None:
        """Returns CLIOutput with problem data when found."""
        result = get_problem(6, mock_loader_with_problem)

        assert result.success
        assert result.data["id"] == 6
        assert result.command == "erdos show"

    def test_not_found(self, mock_loader_empty) -> None:
        """Returns error CLIOutput when problem not found."""
        result = get_problem(9999, mock_loader_empty)

        assert not result.success
        assert result.error["type"] == "NotFound"
        assert result.error["code"] == 3
```

### Integration Test (Real Data)

```python
# tests/integration/test_show_command.py
"""Integration tests for show command."""

from pathlib import Path

from erdos.commands.show import get_problem
from erdos.core.problem_loader import ProblemLoader


def test_show_real_problem(sample_problems_yaml: Path) -> None:
    """show returns real problem from YAML file."""
    loader = ProblemLoader(sample_problems_yaml)
    result = get_problem(6, loader)

    assert result.success
    assert isinstance(result.data, dict)
    assert result.data["id"] == 6
    assert "title" in result.data


def test_show_missing_problem(sample_problems_yaml: Path) -> None:
    """show returns NotFound for non-existent problem."""
    loader = ProblemLoader(sample_problems_yaml)
    result = get_problem(99999, loader)

    assert not result.success
    assert isinstance(result.error, dict)
    assert result.error["type"] == "NotFound"
```

### E2E Test (Full CLI)

```python
# tests/e2e/test_cli_show.py
"""End-to-end tests for erdos show command."""

import json
import subprocess

import pytest


@pytest.mark.e2e
class TestErdosShow:
    def test_show_json_output(self, cli_runner) -> None:
        """erdos show --json outputs valid JSON."""
        result = cli_runner("show", "6", "--json")

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["command"] == "erdos show"
        assert data["data"]["id"] == 6

    def test_show_human_output(self, cli_runner) -> None:
        """erdos show outputs human-readable text by default."""
        result = cli_runner("show", "6")

        assert "Problem 6" in result.stdout
        assert result.returncode == 0

    def test_show_not_found(self, cli_runner) -> None:
        """erdos show returns code 3 for missing problem."""
        result = cli_runner("show", "99999", check=False)

        assert result.returncode == 3

    def test_show_json_not_found(self, cli_runner) -> None:
        """erdos show --json returns error object for missing problem."""
        result = cli_runner("show", "99999", "--json", check=False)

        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "NotFound"
        assert data["error"]["code"] == 3

    def test_show_invalid_id(self, cli_runner) -> None:
        """erdos show rejects invalid problem ID."""
        result = cli_runner("show", "abc", check=False)

        assert result.returncode == 2  # Usage error

    def test_show_help(self, cli_runner) -> None:
        """erdos show --help shows usage."""
        result = cli_runner("show", "--help")

        assert "Problem ID to display" in result.stdout
        assert result.returncode == 0
```

### CLI Runner Fixture

```python
# tests/e2e/conftest.py
"""E2E test fixtures."""

import os
import subprocess
from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture
def cli_runner(tmp_path: Path, sample_data_dir: Path) -> Iterator[callable]:
    """
    Run CLI commands in an isolated environment.

    Sets up required directory structure and environment.
    """
    # Copy sample data to temp directory
    data_dir = tmp_path / "data" / "erdosproblems"
    data_dir.mkdir(parents=True)
    # ... copy sample_problems.yaml

    def run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
        env = {
            "ERDOS_DATA_PATH": str(data_dir),
        }
        result = subprocess.run(
            ["uv", "run", "erdos", *args],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={**os.environ, **env},
        )
        if check and result.returncode not in (0,):
            raise AssertionError(
                f"CLI failed with code {result.returncode}:\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
        return result

    yield run
```

---

## 8) Help Text Quality

Every command has quality help text.

```python
@app.command()
def list_(
    status: Annotated[
        Optional[str],
        typer.Option(
            "--status",
            "-s",
            help="Filter by status: open, proved, disproved",
        ),
    ] = None,
    prize_min: Annotated[
        Optional[int],
        typer.Option(
            "--prize-min",
            help="Minimum prize amount in USD",
            min=0,
        ),
    ] = None,
    tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag",
            "-t",
            help="Filter by tag (can be repeated)",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-n",
            help="Maximum number of results",
            min=1,
            max=1000,
        ),
    ] = 100,
) -> None:
    """
    List Erdős problems with optional filters.

    [bold]Examples:[/bold]

        # List all open problems
        erdos list --status open

        # List problems with prize >= $1000
        erdos list --prize-min 1000

        # List number theory problems
        erdos list --tag "number theory"

        # Combine filters
        erdos list --status open --tag primes --limit 10
    """
    ...
```

### Help Output

```
$ erdos list --help
Usage: erdos list [OPTIONS]

  List Erdős problems with optional filters.

  Examples:

      # List all open problems
      erdos list --status open

      # List problems with prize >= $1000
      erdos list --prize-min 1000

      # List number theory problems
      erdos list --tag "number theory"

Options:
  -s, --status TEXT      Filter by status: open, proved, disproved
  --prize-min INTEGER    Minimum prize amount in USD  [x>=0]
  -t, --tag TEXT         Filter by tag (can be repeated)
  -n, --limit INTEGER    Maximum number of results  [1<=x<=1000; default: 100]
  --help                 Show this message and exit.
```

---

## 9) Command Reference

### v1.0 Commands

| Command | Description | Network |
|---------|-------------|---------|
| `erdos list` | List problems with filters | No |
| `erdos show <id>` | Show problem details | No |
| `erdos refs <id>` | List problem references | No |
| `erdos search <query>` | Search problem statements | No |
| `erdos lean init` | Initialize Lean project | Maybe* |
| `erdos lean check <file>` | Check Lean file | No |
| `erdos lean formalize <id>` | Generate Lean skeleton | No |

*`lean init` may fetch mathlib if not cached.

### v1.1 Commands (Planned)

| Command | Description | Network |
|---------|-------------|---------|
| `erdos ingest <id>` | Fetch reference metadata | Yes |
| `erdos ask <id> <question>` | RAG-powered Q&A | Yes |

---

## 10) Verification: This Spec is Testable

### Acceptance Criteria

```bash
# CLI is runnable
uv run erdos --version
# Output: erdos-harness 0.1.0

# Help works at all levels
uv run erdos --help
uv run erdos list --help
uv run erdos lean --help
uv run erdos lean check --help

# Commands execute without error (with sample data)
uv run erdos list --limit 5
uv run erdos show 6
uv run erdos show 6 --json
uv run erdos refs 6
uv run erdos search "prime"
uv run erdos lean init
uv run erdos lean formalize 6
uv run erdos lean check formal/lean/Erdos/Problem006.lean

# Exit codes are correct
uv run erdos show 99999 || echo "Exit code: $?"
# Exit code: 3 (not found)

# JSON output is valid
uv run erdos show 6 --json | python -m json.tool
# Valid JSON, no error
```

### Meta-Test: CLI Structure

```python
# tests/test_cli_structure.py
"""Verify CLI structure is correct."""

from typer.testing import CliRunner

from erdos.cli import app


runner = CliRunner()


def test_cli_has_version_flag() -> None:
    """CLI should have --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "erdos-harness" in result.stdout


def test_cli_has_json_flag() -> None:
    """CLI should have global --json flag."""
    result = runner.invoke(app, ["--help"])
    assert "--json" in result.stdout


def test_cli_has_required_commands() -> None:
    """CLI should have all v1 commands."""
    result = runner.invoke(app, ["--help"])

    required_commands = ["list", "show", "refs", "search", "lean"]
    for cmd in required_commands:
        assert cmd in result.stdout, f"Missing command: {cmd}"


def test_lean_has_subcommands() -> None:
    """lean command should have init, check, formalize subcommands."""
    result = runner.invoke(app, ["lean", "--help"])

    subcommands = ["init", "check", "formalize"]
    for cmd in subcommands:
        assert cmd in result.stdout, f"Missing lean subcommand: {cmd}"
```

---

## 11) References

- [Typer Documentation](https://typer.tiangolo.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [Click Documentation](https://click.palletsprojects.com/) (underlying library)
- [Typer Testing](https://typer.tiangolo.com/tutorial/testing/)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-16 | Initial spec |
