"""Lean 4 runner (stub)."""

from pathlib import Path

from erdos.core.models import LeanCheckResult


class LeanRunner:
    """Run Lean commands inside a project."""

    def __init__(self, project_path: Path) -> None:
        self._project_path = project_path

    def init(self) -> None:
        raise NotImplementedError("Feature not yet implemented (requires Spec 007)")

    def check(self, file_path: Path) -> LeanCheckResult:
        raise NotImplementedError("Feature not yet implemented (requires Spec 007)")
