"""Index research artifacts into the SQLite search DB (Spec 025)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter, ValidationError

from erdos.core.constants import PREVIEW_LENGTH
from erdos.core.models import ChunkSource, TextChunk
from erdos.core.research.models import (
    AttemptRecord,
    HypothesisRecord,
    LeadRecord,
    TaskRecord,
)
from erdos.core.research.paths import get_problem_dir, get_research_root
from erdos.core.research.render import (
    render_attempt,
    render_hypothesis,
    render_lead,
    render_task,
)
from erdos.core.research.yaml_io import load_yaml


if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from erdos.core.ports import ProblemRepository, SearchIndexWritePort


logger = logging.getLogger(__name__)


def _chunk_preview(text: str) -> str:
    if len(text) <= PREVIEW_LENGTH:
        return text
    if PREVIEW_LENGTH <= 3:
        return text[:PREVIEW_LENGTH]
    return text[: PREVIEW_LENGTH - 3] + "..."


def _try_parse_record(
    path: Path, adapter: TypeAdapter[Any]
) -> tuple[Any | None, str | None]:
    try:
        raw = load_yaml(path)
        return adapter.validate_python(raw, strict=False), None
    except (OSError, ValueError, ValidationError) as e:
        return None, str(e)


def _index_record_dir(
    *,
    problem_id: int,
    dir_path: Path,
    adapter: TypeAdapter[Any],
    source: ChunkSource,
    render: Callable[[Any], str],
    index: SearchIndexWritePort,
) -> int:
    if not dir_path.exists():
        return 0
    count = 0
    paths = sorted(p for p in dir_path.iterdir() if p.is_file() and p.suffix == ".yaml")
    for path in paths:
        rec, err = _try_parse_record(path, adapter)
        if rec is None:
            logger.warning("Skipping invalid research record %s: %s", path, err)
            continue
        # TypeAdapter guarantees fields, but we still ensure file/id consistency.
        rec_id = getattr(rec, "id", None)
        rec_problem_id = getattr(rec, "problem_id", None)
        if rec_problem_id != problem_id:
            logger.warning(
                "Skipping research record with mismatched problem_id (%s): %s",
                rec_problem_id,
                path,
            )
            continue
        if rec_id != path.stem:
            logger.warning(
                "Skipping research record with mismatched id (%s != %s): %s",
                rec_id,
                path.stem,
                path,
            )
            continue

        text = render(rec)
        chunk = TextChunk(
            id=f"research_{problem_id}_{source.value}_{rec_id}",
            text=text,
            source=source,
            problem_id=problem_id,
            preview=_chunk_preview(text),
        )
        index.index_chunk(chunk)
        count += 1
    return count


def index_research_artifacts(
    *,
    repo: ProblemRepository,
    index: SearchIndexWritePort,
    repo_root: Path | None,
) -> int:
    """Index research artifacts for all known problems.

    This is best-effort: malformed research YAML is skipped with warnings.
    """
    research_root = get_research_root(repo_root)
    problems_root = research_root / "problems"
    if not problems_root.exists():
        return 0

    total = 0
    lead_adapter: TypeAdapter[LeadRecord] = TypeAdapter(LeadRecord)
    attempt_adapter: TypeAdapter[AttemptRecord] = TypeAdapter(AttemptRecord)
    hypothesis_adapter: TypeAdapter[HypothesisRecord] = TypeAdapter(HypothesisRecord)
    task_adapter: TypeAdapter[TaskRecord] = TypeAdapter(TaskRecord)

    for problem in repo.iter_problems():
        problem_id = problem.id
        problem_dir = get_problem_dir(repo_root, problem_id)
        if not problem_dir.exists():
            continue

        synthesis_path = problem_dir / "SYNTHESIS.md"
        if synthesis_path.exists():
            try:
                text = synthesis_path.read_text(encoding="utf-8").strip()
                if not text:
                    logger.warning(
                        "Skipping empty synthesis for problem %s: %s",
                        problem_id,
                        synthesis_path,
                    )
                else:
                    chunk = TextChunk(
                        id=f"research_{problem_id}_synthesis",
                        text=text,
                        source=ChunkSource.RESEARCH_SYNTHESIS,
                        problem_id=problem_id,
                        preview=_chunk_preview(text),
                    )
                    index.index_chunk(chunk)
                    total += 1
            except (OSError, ValidationError) as e:
                logger.warning(
                    "Skipping synthesis for problem %s (%s): %s",
                    problem_id,
                    synthesis_path,
                    e,
                )

        total += _index_record_dir(
            problem_id=problem_id,
            dir_path=problem_dir / "leads",
            adapter=lead_adapter,
            source=ChunkSource.RESEARCH_LEAD,
            render=render_lead,
            index=index,
        )
        total += _index_record_dir(
            problem_id=problem_id,
            dir_path=problem_dir / "attempts",
            adapter=attempt_adapter,
            source=ChunkSource.RESEARCH_ATTEMPT,
            render=render_attempt,
            index=index,
        )
        total += _index_record_dir(
            problem_id=problem_id,
            dir_path=problem_dir / "hypotheses",
            adapter=hypothesis_adapter,
            source=ChunkSource.RESEARCH_HYPOTHESIS,
            render=render_hypothesis,
            index=index,
        )
        total += _index_record_dir(
            problem_id=problem_id,
            dir_path=problem_dir / "tasks",
            adapter=task_adapter,
            source=ChunkSource.RESEARCH_TASK,
            render=render_task,
            index=index,
        )

    return total
