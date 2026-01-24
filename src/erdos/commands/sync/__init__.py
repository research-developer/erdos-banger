"""erdos sync - unified problem data sync commands (SPEC-035).

This module provides CLI commands for synchronizing Erdős problem data
from multiple sources:

- `erdos sync website <id>` - Fetch structured data from erdosproblems.com
- `erdos sync submodule` - Update the teorth/erdosproblems submodule
- `erdos sync proof <id>` - Extract proof links from forum threads
- `erdos sync statements <id>` - Import Lean statements (wraps `erdos lean import`)
- `erdos sync all` - Run all sync operations
"""

import typer

from erdos.commands.sync.submodule_cmd import submodule
from erdos.commands.sync.website_cmd import website


app = typer.Typer(
    help="Sync problem data from multiple sources.",
    no_args_is_help=True,
)

# Register subcommands
app.command(name="submodule")(submodule)
app.command(name="website")(website)
