"""Application wiring for erdos-banger.

This module is the composition root for CLI execution. It centralizes how
concrete dependencies are created from environment defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from erdos.core.problem_loader import ProblemLoader
from erdos.core.search_index import SearchIndex


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository, SearchIndexProtocol


@dataclass
class AppContext:
    """Dependency container for CLI commands."""

    problems: ProblemRepository
    index: SearchIndexProtocol | None = None

    @classmethod
    def from_environment(cls) -> AppContext:
        """Create context using environment defaults."""
        return cls(problems=ProblemLoader.from_default())

    def ensure_index(self) -> SearchIndexProtocol:
        """Ensure the search index dependency exists."""
        if self.index is None:
            self.index = SearchIndex.from_default()
        return self.index
