"""Lean package: Lean 4 compilation, skeleton generation, and prover wrappers.

This bounded context groups Lean-related modules:
- runner.py: Lean 4 compilation + error parsing
- formalizer.py: Lean skeleton generation from templates
- aristotle.py: Aristotle prover CLI wrapper
"""

from erdos.core.lean.aristotle import (
    AristotleConfig,
    AristotleError,
    AristotleResult,
    build_aristotle_command,
    run_aristotle_prove_from_file,
    validate_aristotle_config,
)
from erdos.core.lean.formalizer import FormalizerError, generate_skeleton
from erdos.core.lean.runner import (
    LeanEnvironment,
    LeanRunner,
    LeanRunnerError,
    ResolvedLeanPath,
)


__all__ = [
    "AristotleConfig",
    "AristotleError",
    "AristotleResult",
    "FormalizerError",
    "LeanEnvironment",
    "LeanRunner",
    "LeanRunnerError",
    "ResolvedLeanPath",
    "build_aristotle_command",
    "generate_skeleton",
    "run_aristotle_prove_from_file",
    "validate_aristotle_config",
]
