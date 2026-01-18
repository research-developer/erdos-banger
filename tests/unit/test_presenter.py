import io
from pathlib import Path

import click
import pytest
import typer
from rich.console import Console

from erdos.commands import presenter
from erdos.core.models import CLIOutput


def test_output_result_json_writes_only_to_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    test_console = Console(
        file=stdout,
        force_terminal=False,
        color_system=None,
        record=True,
    )
    test_err_console = Console(
        file=stderr,
        force_terminal=False,
        color_system=None,
        record=True,
    )

    monkeypatch.setattr(presenter, "console", test_console)
    monkeypatch.setattr(presenter, "err_console", test_err_console)

    ctx = typer.Context(click.Command("test"))
    ctx.obj = {"json": True}

    result = CLIOutput.ok(command="cmd", data={"ok": True})
    presenter.output_result(ctx, result)

    assert stdout.getvalue()
    assert not stderr.getvalue()


def test_output_result_json_error_writes_only_to_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    test_console = Console(
        file=stdout,
        force_terminal=False,
        color_system=None,
        record=True,
    )
    test_err_console = Console(
        file=stderr,
        force_terminal=False,
        color_system=None,
        record=True,
    )

    monkeypatch.setattr(presenter, "console", test_console)
    monkeypatch.setattr(presenter, "err_console", test_err_console)

    ctx = typer.Context(click.Command("test"))
    ctx.obj = {"json": True}

    result = CLIOutput.err(command="cmd", error_type="Error", message="boom", code=1)
    presenter.output_result(ctx, result)

    assert "boom" in stdout.getvalue()
    assert not stderr.getvalue()


def test_output_result_error_writes_only_to_err_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    test_console = Console(
        file=stdout,
        force_terminal=False,
        color_system=None,
        record=True,
    )
    test_err_console = Console(
        file=stderr,
        force_terminal=False,
        color_system=None,
        record=True,
    )

    monkeypatch.setattr(presenter, "console", test_console)
    monkeypatch.setattr(presenter, "err_console", test_err_console)

    ctx = typer.Context(click.Command("test"))
    ctx.obj = {"json": False}

    result = CLIOutput.err(command="cmd", error_type="Error", message="boom", code=1)
    presenter.output_result(ctx, result)

    assert not stdout.getvalue()
    assert "boom" in stderr.getvalue()


def test_exit_with_result_raises_typer_exit_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    test_console = Console(
        file=stdout,
        force_terminal=False,
        color_system=None,
        record=True,
    )
    test_err_console = Console(
        file=stderr,
        force_terminal=False,
        color_system=None,
        record=True,
    )

    monkeypatch.setattr(presenter, "console", test_console)
    monkeypatch.setattr(presenter, "err_console", test_err_console)

    ctx = typer.Context(click.Command("test"))
    ctx.obj = {"json": False}

    result = CLIOutput.err(command="cmd", error_type="Error", message="boom", code=7)
    with pytest.raises(typer.Exit) as exc_info:
        presenter.exit_with_result(ctx, result)

    assert exc_info.value.exit_code == 7


def test_no_duplicate_output_helpers() -> None:
    commands = Path("src/erdos/commands")
    offenders: list[str] = []
    for py_file in commands.glob("*.py"):
        if py_file.name in {"presenter.py", "__init__.py"}:
            continue
        if "def _output(" in py_file.read_text():
            offenders.append(py_file.name)
    assert not offenders, f"_output() should be removed from: {sorted(offenders)}"
