"""Unit tests for indexing research artifacts into the search index."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from erdos.core.models import ChunkSource, ProblemRecord, ProblemStatus, TextChunk
from erdos.core.search.research_indexing import index_research_artifacts


@dataclass(frozen=True)
class _Repo:
    problems: list[ProblemRecord]

    def get_by_id(self, problem_id: int) -> ProblemRecord | None:
        return next((p for p in self.problems if p.id == problem_id), None)

    def load_all(self, *, use_cache: bool = True) -> list[ProblemRecord]:
        _ = use_cache
        return list(self.problems)

    def iter_problems(self):
        yield from self.problems


class _Index:
    def __init__(self) -> None:
        self.chunks: list[TextChunk] = []

    def clear(self) -> None:
        self.chunks.clear()

    def index_problem(self, problem: ProblemRecord) -> None:
        _ = problem

    def index_chunk(self, chunk: TextChunk) -> None:
        self.chunks.append(chunk)


def test_index_research_artifacts_skips_empty_synthesis(tmp_path: Path, caplog) -> None:
    problem_id = 1
    problem_dir = tmp_path / "research" / "problems" / f"{problem_id:04d}"
    problem_dir.mkdir(parents=True)
    (problem_dir / "SYNTHESIS.md").write_text("", encoding="utf-8")

    repo = _Repo(
        problems=[
            ProblemRecord(
                id=problem_id,
                title="P1",
                statement="S1",
                status=ProblemStatus.OPEN,
            )
        ]
    )
    index = _Index()

    with caplog.at_level(logging.WARNING):
        total = index_research_artifacts(repo=repo, index=index, repo_root=tmp_path)

    assert total == 0
    assert not index.chunks
    assert "Skipping empty synthesis" in caplog.text


def test_index_research_artifacts_indexes_non_empty_synthesis(tmp_path: Path) -> None:
    problem_id = 1
    problem_dir = tmp_path / "research" / "problems" / f"{problem_id:04d}"
    problem_dir.mkdir(parents=True)
    (problem_dir / "SYNTHESIS.md").write_text("hello", encoding="utf-8")

    repo = _Repo(
        problems=[
            ProblemRecord(
                id=problem_id,
                title="P1",
                statement="S1",
                status=ProblemStatus.OPEN,
            )
        ]
    )
    index = _Index()

    total = index_research_artifacts(repo=repo, index=index, repo_root=tmp_path)

    assert total == 1
    assert len(index.chunks) == 1
    assert index.chunks[0].source == ChunkSource.RESEARCH_SYNTHESIS
