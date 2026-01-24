"""erdos sync - unified problem data sync commands (SPEC-035).

This module provides CLI commands for synchronizing Erdős problem data
from multiple sources:

- `erdos sync submodule` - Update the teorth/erdosproblems submodule
- `erdos sync website <id>` - Fetch structured data from erdosproblems.com
- `erdos sync proof <id>` - Extract proof links from forum threads
- `erdos sync statements <id>` - Import Lean statements (wraps `erdos lean import`)
- `erdos sync all` - Run all sync operations
"""

import typer

from erdos.commands.sync.all_cmd import sync_all
from erdos.commands.sync.proof_cmd import proof
from erdos.commands.sync.statements_cmd import statements
from erdos.commands.sync.submodule_cmd import submodule
from erdos.commands.sync.website_cmd import website


app = typer.Typer(
    help="Sync problem data from multiple sources.",
    no_args_is_help=True,
)

# Register subcommands
app.command(name="submodule")(submodule)
app.command(name="website")(website)
app.command(name="proof")(proof)
app.command(name="statements")(statements)
app.command(name="all")(sync_all)
