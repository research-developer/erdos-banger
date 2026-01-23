"""Filesystem research store (Spec 024)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import TypeAdapter, ValidationError

from erdos.core.research.errors import (
    ResearchRecordInvalidError,
    ResearchRecordNotFoundError,
)
from erdos.core.research.ids import generate_record_id
from erdos.core.research.models import (
    AttemptArtifacts,
    AttemptKind,
    AttemptRecord,
    AttemptResult,
    Confidence,
    HypothesisRecord,
    HypothesisStatus,
    LeadRecord,
    LeadSource,
    LeadStatus,
    Priority,
    TaskRecord,
    TaskStatus,
)
from erdos.core.research.paths import get_problem_dir
from erdos.core.research.workspace import ensure_problem_workspace
from erdos.core.research.yaml_io import dump_yaml, load_yaml, write_text_atomic


if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def _utc_now(now: datetime | None = None) -> datetime:
    dt = now if now is not None else datetime.now(UTC)
    return dt.replace(microsecond=0)


_RECORD_ID_RE = re.compile(r"^[a-z][a-z0-9]*_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{6}$")


def _validate_record_id(record_id: str, kind: str) -> None:
    # Prevent path traversal and keep a stable filename contract.
    if not record_id:
        raise ResearchRecordInvalidError(f"Invalid {kind} id: empty")
    if record_id in {".", ".."}:
        raise ResearchRecordInvalidError(f"Invalid {kind} id: {record_id!r}")
    if PurePath(record_id).name != record_id:
        raise ResearchRecordInvalidError(f"Invalid {kind} id: {record_id!r}")
    if not record_id.startswith(f"{kind}_"):
        raise ResearchRecordInvalidError(f"Invalid {kind} id: {record_id!r}")
    if not _RECORD_ID_RE.match(record_id):
        raise ResearchRecordInvalidError(f"Invalid {kind} id: {record_id!r}")


T = TypeVar("T")


def _read_record(path: Path, adapter: TypeAdapter[T]) -> T:
    try:
        raw = load_yaml(path)
        return adapter.validate_python(raw, strict=False)
    except (OSError, ValueError, ValidationError) as e:
        raise ResearchRecordInvalidError(f"Invalid record at {path}: {e}") from e


def _write_record(path: Path, record: Any) -> None:
    yaml_text = dump_yaml(record)
    write_text_atomic(path, yaml_text)


def _iter_record_paths(dir_path: Path) -> Iterable[Path]:
    if not dir_path.exists():
        return []
    return sorted(
        [p for p in dir_path.iterdir() if p.is_file() and p.suffix == ".yaml"]
    )


@dataclass(frozen=True)
class FSResearchStore:
    repo_root: Path | None

    def _problem_dir(self, problem_id: int) -> Path:
        return get_problem_dir(self.repo_root, problem_id)

    # ---------------------------------------------------------------------
    # Leads
    # ---------------------------------------------------------------------

    def lead_add(
        self,
        problem_id: int,
        *,
        title: str,
        doi: str | None = None,
        arxiv_id: str | None = None,
        url: str | None = None,
        status: LeadStatus = LeadStatus.NEW,
        priority: Priority = Priority.MEDIUM,
        notes: str = "",
        tags: list[str] | None = None,
        now: datetime | None = None,
    ) -> tuple[LeadRecord, Path]:
        ensure_problem_workspace(problem_id, repo_root=self.repo_root)
        record_id = generate_record_id("lead", now=now)
        created = _utc_now(now)
        record = LeadRecord(
            problem_id=problem_id,
            id=record_id,
            title=title,
            status=status,
            priority=priority,
            tags=tags or [],
            source=LeadSource(doi=doi, arxiv_id=arxiv_id, url=url),
            notes=notes,
            created_at=created,
            updated_at=created,
        )
        path = self._problem_dir(problem_id) / "leads" / f"{record_id}.yaml"
        _write_record(path, record.model_dump(mode="json"))
        return record, path

    def lead_list(
        self,
        problem_id: int,
        *,
        status: LeadStatus | None = None,
        priority: Priority | None = None,
    ) -> list[LeadRecord]:
        adapter: TypeAdapter[LeadRecord] = TypeAdapter(LeadRecord)
        records: list[LeadRecord] = []
        for path in _iter_record_paths(self._problem_dir(problem_id) / "leads"):
            rec = _read_record(path, adapter)
            if rec.problem_id != problem_id:
                raise ResearchRecordInvalidError(
                    f"Lead {rec.id} has problem_id={rec.problem_id}, expected {problem_id}"
                )
            if rec.id != path.stem:
                raise ResearchRecordInvalidError(
                    f"Lead filename {path.name} does not match id={rec.id}"
                )
            if status is not None and rec.status != status:
                continue
            if priority is not None and rec.priority != priority:
                continue
            records.append(rec)
        return records

    def lead_update(
        self,
        problem_id: int,
        lead_id: str,
        *,
        status: LeadStatus | None = None,
        priority: Priority | None = None,
        notes: str | None = None,
        now: datetime | None = None,
    ) -> tuple[LeadRecord, Path]:
        _validate_record_id(lead_id, "lead")
        path = self._problem_dir(problem_id) / "leads" / f"{lead_id}.yaml"
        if not path.exists():
            raise ResearchRecordNotFoundError(f"Lead not found: {lead_id}")
        adapter: TypeAdapter[LeadRecord] = TypeAdapter(LeadRecord)
        rec = _read_record(path, adapter)
        if rec.problem_id != problem_id:
            raise ResearchRecordInvalidError(
                f"Lead {rec.id} has problem_id={rec.problem_id}, expected {problem_id}"
            )
        if rec.id != lead_id:
            raise ResearchRecordInvalidError(
                f"Lead filename {path.name} does not match id={rec.id}"
            )
        updated = _utc_now(now)
        new = rec.model_copy(
            update={
                **({"status": status} if status is not None else {}),
                **({"priority": priority} if priority is not None else {}),
                **({"notes": notes} if notes is not None else {}),
                "updated_at": updated,
            }
        )
        _write_record(path, new.model_dump(mode="json"))
        return new, path

    # ---------------------------------------------------------------------
    # Hypotheses
    # ---------------------------------------------------------------------

    def hypothesis_add(
        self,
        problem_id: int,
        *,
        statement: str,
        status: HypothesisStatus = HypothesisStatus.ACTIVE,
        confidence: Confidence = Confidence.MEDIUM,
        notes: str = "",
        evidence: list[str] | None = None,
        now: datetime | None = None,
    ) -> tuple[HypothesisRecord, Path]:
        ensure_problem_workspace(problem_id, repo_root=self.repo_root)
        record_id = generate_record_id("hyp", now=now)
        created = _utc_now(now)
        record = HypothesisRecord(
            problem_id=problem_id,
            id=record_id,
            statement=statement,
            status=status,
            confidence=confidence,
            evidence=evidence or [],
            notes=notes,
            created_at=created,
            updated_at=created,
        )
        path = self._problem_dir(problem_id) / "hypotheses" / f"{record_id}.yaml"
        _write_record(path, record.model_dump(mode="json"))
        return record, path

    def hypothesis_list(
        self,
        problem_id: int,
        *,
        status: HypothesisStatus | None = None,
    ) -> list[HypothesisRecord]:
        adapter: TypeAdapter[HypothesisRecord] = TypeAdapter(HypothesisRecord)
        records: list[HypothesisRecord] = []
        for path in _iter_record_paths(self._problem_dir(problem_id) / "hypotheses"):
            rec = _read_record(path, adapter)
            if rec.problem_id != problem_id:
                raise ResearchRecordInvalidError(
                    f"Hypothesis {rec.id} has problem_id={rec.problem_id}, expected {problem_id}"
                )
            if rec.id != path.stem:
                raise ResearchRecordInvalidError(
                    f"Hypothesis filename {path.name} does not match id={rec.id}"
                )
            if status is not None and rec.status != status:
                continue
            records.append(rec)
        return records

    def hypothesis_update(
        self,
        problem_id: int,
        hyp_id: str,
        *,
        status: HypothesisStatus | None = None,
        confidence: Confidence | None = None,
        notes: str | None = None,
        now: datetime | None = None,
    ) -> tuple[HypothesisRecord, Path]:
        _validate_record_id(hyp_id, "hyp")
        path = self._problem_dir(problem_id) / "hypotheses" / f"{hyp_id}.yaml"
        if not path.exists():
            raise ResearchRecordNotFoundError(f"Hypothesis not found: {hyp_id}")
        adapter: TypeAdapter[HypothesisRecord] = TypeAdapter(HypothesisRecord)
        rec = _read_record(path, adapter)
        if rec.problem_id != problem_id:
            raise ResearchRecordInvalidError(
                f"Hypothesis {rec.id} has problem_id={rec.problem_id}, expected {problem_id}"
            )
        if rec.id != hyp_id:
            raise ResearchRecordInvalidError(
                f"Hypothesis filename {path.name} does not match id={rec.id}"
            )
        updated = _utc_now(now)
        new = rec.model_copy(
            update={
                **({"status": status} if status is not None else {}),
                **({"confidence": confidence} if confidence is not None else {}),
                **({"notes": notes} if notes is not None else {}),
                "updated_at": updated,
            }
        )
        _write_record(path, new.model_dump(mode="json"))
        return new, path

    # ---------------------------------------------------------------------
    # Tasks
    # ---------------------------------------------------------------------

    def task_add(
        self,
        problem_id: int,
        *,
        title: str,
        status: TaskStatus = TaskStatus.TODO,
        priority: Priority = Priority.MEDIUM,
        blocked_on: list[str] | None = None,
        links: list[str] | None = None,
        now: datetime | None = None,
    ) -> tuple[TaskRecord, Path]:
        ensure_problem_workspace(problem_id, repo_root=self.repo_root)
        record_id = generate_record_id("task", now=now)
        created = _utc_now(now)
        record = TaskRecord(
            problem_id=problem_id,
            id=record_id,
            title=title,
            status=status,
            priority=priority,
            blocked_on=blocked_on or [],
            links=links or [],
            created_at=created,
            updated_at=created,
        )
        path = self._problem_dir(problem_id) / "tasks" / f"{record_id}.yaml"
        _write_record(path, record.model_dump(mode="json"))
        return record, path

    def task_list(
        self,
        problem_id: int,
        *,
        status: TaskStatus | None = None,
        priority: Priority | None = None,
    ) -> list[TaskRecord]:
        adapter: TypeAdapter[TaskRecord] = TypeAdapter(TaskRecord)
        records: list[TaskRecord] = []
        for path in _iter_record_paths(self._problem_dir(problem_id) / "tasks"):
            rec = _read_record(path, adapter)
            if rec.problem_id != problem_id:
                raise ResearchRecordInvalidError(
                    f"Task {rec.id} has problem_id={rec.problem_id}, expected {problem_id}"
                )
            if rec.id != path.stem:
                raise ResearchRecordInvalidError(
                    f"Task filename {path.name} does not match id={rec.id}"
                )
            if status is not None and rec.status != status:
                continue
            if priority is not None and rec.priority != priority:
                continue
            records.append(rec)
        return records

    def task_update(
        self,
        problem_id: int,
        task_id: str,
        *,
        status: TaskStatus | None = None,
        priority: Priority | None = None,
        now: datetime | None = None,
    ) -> tuple[TaskRecord, Path]:
        _validate_record_id(task_id, "task")
        path = self._problem_dir(problem_id) / "tasks" / f"{task_id}.yaml"
        if not path.exists():
            raise ResearchRecordNotFoundError(f"Task not found: {task_id}")
        adapter: TypeAdapter[TaskRecord] = TypeAdapter(TaskRecord)
        rec = _read_record(path, adapter)
        if rec.problem_id != problem_id:
            raise ResearchRecordInvalidError(
                f"Task {rec.id} has problem_id={rec.problem_id}, expected {problem_id}"
            )
        if rec.id != task_id:
            raise ResearchRecordInvalidError(
                f"Task filename {path.name} does not match id={rec.id}"
            )
        updated = _utc_now(now)
        new = rec.model_copy(
            update={
                **({"status": status} if status is not None else {}),
                **({"priority": priority} if priority is not None else {}),
                "updated_at": updated,
            }
        )
        _write_record(path, new.model_dump(mode="json"))
        return new, path

    # ---------------------------------------------------------------------
    # Attempts
    # ---------------------------------------------------------------------

    def attempt_log(
        self,
        problem_id: int,
        *,
        result: AttemptResult,
        summary: str,
        kind: AttemptKind = AttemptKind.LEAN_LOOP,
        lean_file: str | None = None,
        loop_log: str | None = None,
        now: datetime | None = None,
    ) -> tuple[AttemptRecord, Path]:
        ensure_problem_workspace(problem_id, repo_root=self.repo_root)
        record_id = generate_record_id("att", now=now)
        created = _utc_now(now)
        record = AttemptRecord(
            problem_id=problem_id,
            id=record_id,
            kind=kind,
            result=result,
            summary=summary,
            artifacts=AttemptArtifacts(lean_file=lean_file, loop_run_log=loop_log),
            created_at=created,
        )
        path = self._problem_dir(problem_id) / "attempts" / f"{record_id}.yaml"
        _write_record(path, record.model_dump(mode="json"))
        return record, path

    def attempt_list(
        self, problem_id: int, *, result: AttemptResult | None = None
    ) -> list[AttemptRecord]:
        adapter: TypeAdapter[AttemptRecord] = TypeAdapter(AttemptRecord)
        records: list[AttemptRecord] = []
        for path in _iter_record_paths(self._problem_dir(problem_id) / "attempts"):
            rec = _read_record(path, adapter)
            if rec.problem_id != problem_id:
                raise ResearchRecordInvalidError(
                    f"Attempt {rec.id} has problem_id={rec.problem_id}, expected {problem_id}"
                )
            if rec.id != path.stem:
                raise ResearchRecordInvalidError(
                    f"Attempt filename {path.name} does not match id={rec.id}"
                )
            if result is not None and rec.result != result:
                continue
            records.append(rec)
        return records


def validate_problem_workspace(problem_id: int, *, repo_root: Path | None) -> None:
    """Validate all records under a problem workspace, raising on first failure."""
    store = FSResearchStore(repo_root=repo_root)
    # Listing will validate ids and problem_id invariants.
    _ = store.lead_list(problem_id)
    _ = store.hypothesis_list(problem_id)
    _ = store.task_list(problem_id)
    _ = store.attempt_list(problem_id)


def fmt_problem_workspace(problem_id: int, *, repo_root: Path | None) -> int:
    """Canonicalize YAML formatting for all record files. Returns files rewritten."""
    ensure_problem_workspace(problem_id, repo_root=repo_root)

    rewritten = 0

    def _fmt_dir(dir_path: Path, adapter: TypeAdapter[Any]) -> int:
        changed = 0
        for path in _iter_record_paths(dir_path):
            rec = _read_record(path, adapter)
            # rec is a Pydantic model instance (validated by TypeAdapter)
            new_text = dump_yaml(rec.model_dump(mode="json"))
            old_text = path.read_text(encoding="utf-8")
            if old_text != new_text:
                write_text_atomic(path, new_text)
                changed += 1
        return changed

    base = get_problem_dir(repo_root, problem_id)
    rewritten += _fmt_dir(base / "leads", TypeAdapter(LeadRecord))
    rewritten += _fmt_dir(base / "hypotheses", TypeAdapter(HypothesisRecord))
    rewritten += _fmt_dir(base / "tasks", TypeAdapter(TaskRecord))
    rewritten += _fmt_dir(base / "attempts", TypeAdapter(AttemptRecord))

    return rewritten
