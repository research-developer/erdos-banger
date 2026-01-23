"""Generate Lean skeletons from problem statements."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, PackageLoader, select_autoescape


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.models import ProblemRecord


class FormalizerError(Exception):
    """Raised when skeleton generation fails."""


_env = Environment(
    loader=PackageLoader("erdos", "templates"),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)


def generate_skeleton(
    problem: ProblemRecord,
    project_path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """
    Generate a Lean skeleton file for a problem.

    Args:
        problem: The problem to formalize
        project_path: Path to Lean project
        overwrite: If True, overwrite existing file

    Returns:
        Path to the generated file

    Raises:
        FormalizerError: If generation fails
    """
    output_dir = project_path / "Erdos"
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"Problem{problem.id:03d}.lean"
    output_path = output_dir / filename

    if output_path.exists() and not overwrite:
        raise FormalizerError(
            f"File already exists: {output_path}. Use --force to overwrite."
        )

    try:
        template = _env.get_template("lean_skeleton.j2")
        content = template.render(
            problem=problem,
            problem_id_padded=f"{problem.id:03d}",
        )
        output_path.write_text(content, encoding="utf-8")
        _update_root_module(project_path, problem.id)
    except Exception as exc:
        raise FormalizerError(
            f"Failed to generate skeleton for Problem {problem.id}: {exc}"
        ) from exc

    return output_path


def _update_root_module(project_path: Path, problem_id: int) -> None:
    """Add import for new problem to Erdos.lean."""
    root_lean = project_path / "Erdos.lean"
    if not root_lean.exists():
        return

    import_line = f"import Erdos.Problem{problem_id:03d}"
    content = root_lean.read_text(encoding="utf-8")

    if import_line not in content:
        lines = content.rstrip().split("\n")
        lines.append(import_line)
        root_lean.write_text("\n".join(lines) + "\n", encoding="utf-8")
