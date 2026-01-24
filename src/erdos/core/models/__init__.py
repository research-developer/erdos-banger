"""Core domain models for erdos-banger.

This package provides a curated export surface for domain models.
Import from here (e.g., `from erdos.core.models import ProblemRecord`)
or from specific submodules for reduced import overhead.
"""

# Base models and utilities
from erdos.core.models.base import ErdosBaseModel, utc_now

# Lean compiler models
from erdos.core.models.lean import LeanCheckResult, LeanError

# CLI output model
from erdos.core.models.output import CLIOutput

# Problem domain models
from erdos.core.models.problem import ProblemRecord, ProblemStatus, ReferenceEntry

# Reference/manifest models
from erdos.core.models.reference import (
    ManifestEntry,
    OpenAccessStatus,
    ProblemManifest,
    ReferenceRecord,
)

# Search models
from erdos.core.models.search import ChunkSource, TextChunk


__all__ = [
    "CLIOutput",
    "ChunkSource",
    "ErdosBaseModel",
    "LeanCheckResult",
    "LeanError",
    "ManifestEntry",
    "OpenAccessStatus",
    "ProblemManifest",
    "ProblemRecord",
    "ProblemStatus",
    "ReferenceEntry",
    "ReferenceRecord",
    "TextChunk",
    "utc_now",
]
