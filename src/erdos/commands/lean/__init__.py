"""erdos lean - Lean 4 integration commands (SPEC-007, SPEC-015, SPEC-033)."""

import typer

from erdos.commands.lean import (
    check_cmd,
    copilot_cmd,
    formalize_cmd,
    import_cmd,
    init_cmd,
    prove_cmd,
    status_cmd,
)


app = typer.Typer(help="Lean 4 theorem prover commands.")

# Register all subcommands
init_cmd.register(app)
check_cmd.register(app)
formalize_cmd.register(app)
prove_cmd.register(app)
status_cmd.register(app)
import_cmd.register(app)
copilot_cmd.register(app)

__all__ = ["app"]
