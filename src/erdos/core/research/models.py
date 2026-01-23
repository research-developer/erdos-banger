"""Research record models (Spec 024)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - needed at runtime for Pydantic
from enum import Enum
from typing import Annotated

from pydantic import ConfigDict, Field

from erdos.core.models.base import ErdosBaseModel


class _FrozenModel(ErdosBaseModel):
    model_config = ConfigDict(frozen=True)


class LeadStatus(str, Enum):
    NEW = "new"
    INVESTIGATING = "investigating"
    PROMISING = "promising"
    DEAD_END = "dead_end"
    INCORPORATED = "incorporated"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class HypothesisStatus(str, Enum):
    ACTIVE = "active"
    REFUTED = "refuted"
    PROVEN = "proven"
    INCORPORATED = "incorporated"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, Enum):
    TODO = "todo"
    DOING = "doing"
    BLOCKED = "blocked"
    DONE = "done"


class AttemptKind(str, Enum):
    LEAN_LOOP = "lean_loop"
    MANUAL = "manual"


class AttemptResult(str, Enum):
    FAILED = "failed"
    PARTIAL = "partial"
    SUCCESS = "success"


class LeadSource(_FrozenModel):
    doi: Annotated[str | None, Field(default=None)] = None
    arxiv_id: Annotated[str | None, Field(default=None)] = None
    url: Annotated[str | None, Field(default=None)] = None


class LeadRecord(_FrozenModel):
    schema_version: Annotated[int, Field(default=1)] = 1
    problem_id: Annotated[int, Field(ge=1)]
    id: Annotated[str, Field(min_length=1)]

    title: Annotated[str, Field(min_length=1)]
    status: Annotated[LeadStatus, Field(default=LeadStatus.NEW)] = LeadStatus.NEW
    priority: Annotated[Priority, Field(default=Priority.MEDIUM)] = Priority.MEDIUM
    tags: Annotated[list[str], Field(default_factory=list)]
    source: Annotated[LeadSource, Field(default_factory=LeadSource)]
    notes: Annotated[str, Field(default="")] = ""
    created_at: datetime
    updated_at: datetime


class HypothesisRecord(_FrozenModel):
    schema_version: Annotated[int, Field(default=1)] = 1
    problem_id: Annotated[int, Field(ge=1)]
    id: Annotated[str, Field(min_length=1)]

    statement: Annotated[str, Field(min_length=1)]
    status: Annotated[HypothesisStatus, Field(default=HypothesisStatus.ACTIVE)] = (
        HypothesisStatus.ACTIVE
    )
    confidence: Annotated[Confidence, Field(default=Confidence.MEDIUM)] = (
        Confidence.MEDIUM
    )
    evidence: Annotated[list[str], Field(default_factory=list)]
    notes: Annotated[str, Field(default="")] = ""
    created_at: datetime
    updated_at: datetime


class TaskRecord(_FrozenModel):
    schema_version: Annotated[int, Field(default=1)] = 1
    problem_id: Annotated[int, Field(ge=1)]
    id: Annotated[str, Field(min_length=1)]

    title: Annotated[str, Field(min_length=1)]
    status: Annotated[TaskStatus, Field(default=TaskStatus.TODO)] = TaskStatus.TODO
    priority: Annotated[Priority, Field(default=Priority.MEDIUM)] = Priority.MEDIUM
    blocked_on: Annotated[list[str], Field(default_factory=list)]
    links: Annotated[list[str], Field(default_factory=list)]
    created_at: datetime
    updated_at: datetime


class AttemptArtifacts(_FrozenModel):
    lean_file: Annotated[str | None, Field(default=None)] = None
    loop_run_log: Annotated[str | None, Field(default=None)] = None


class AttemptRecord(_FrozenModel):
    """Append-only attempt record (immutable after creation)."""

    schema_version: Annotated[int, Field(default=1)] = 1
    problem_id: Annotated[int, Field(ge=1)]
    id: Annotated[str, Field(min_length=1)]

    kind: Annotated[AttemptKind, Field(default=AttemptKind.LEAN_LOOP)] = (
        AttemptKind.LEAN_LOOP
    )
    result: AttemptResult
    summary: Annotated[str, Field(min_length=1)]
    artifacts: Annotated[AttemptArtifacts, Field(default_factory=AttemptArtifacts)]
    created_at: datetime
