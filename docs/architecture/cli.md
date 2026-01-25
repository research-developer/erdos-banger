# CLI Design

The CLI is built with **Typer** (Click underneath) and **Rich** for formatting.

## Goals

- Provide a stable CLI surface for researchers and agents.
- Keep side effects and orchestration out of Typer callbacks.
- Support both human output and strict `--json` contracts.

## Key Modules

- `src/erdos/cli.py`: global Typer app (`--json`, `--log-level`, `--version`)
- `src/erdos/commands/presenter.py`: shared Rich consoles and output helpers
- `src/erdos/core/models/output.py`: `CLIOutput` envelope model
- `src/erdos/core/exit_codes.py`: `ExitCode` enum

## JSON Output Contract

All `--json` output uses the `CLIOutput` envelope:

- Success: `success=true`, `data` contains command-specific fields, `error=null`
- Failure: `success=false`, `data=null`, `error={type,message,code,...}`

Commands should avoid printing to stdout directly; use `exit_with_result()` to ensure stdout stays clean in JSON mode.

## Exit Codes

Typer callbacks exit via `ExitCode` values; tests assert these for correctness.

## Command Organization

Top-level commands are registered in `src/erdos/cli.py` and implemented as modules under `src/erdos/commands/`.
