"""erdos research - filesystem research workspace and state (v3)."""

from __future__ import annotations

import typer

from . import attempt, hypothesis, lead, task, workspace


app = typer.Typer(help="Manage per-problem research workspace and state.")

workspace.register(app)
app.add_typer(lead.app, name="lead")
app.add_typer(hypothesis.app, name="hypothesis")
app.add_typer(task.app, name="task")
app.add_typer(attempt.app, name="attempt")
