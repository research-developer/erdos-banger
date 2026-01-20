"""CLI output domain models."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - needed at runtime for Pydantic
from typing import Annotated, Any

from pydantic import Field, model_validator

from erdos.core.models.base import ErdosBaseModel, utc_now


class CLIOutput(ErdosBaseModel):
    """
    Standard wrapper for CLI JSON output.

    All --json output uses this structure for consistency.
    """

    schema_version: Annotated[int, Field(default=1)] = 1
    command: Annotated[str, Field(description="Command that produced this output")]
    success: Annotated[bool, Field(default=True)] = True
    data: Annotated[Any, Field(description="Command-specific output data")]
    error: Annotated[dict[str, Any] | None, Field(default=None)] = None

    # Metadata
    timestamp: Annotated[datetime, Field(default_factory=utc_now)] = Field(
        default_factory=utc_now
    )
    duration_ms: Annotated[int | None, Field(default=None)] = None

    @model_validator(mode="after")
    def _check_invariants(self) -> CLIOutput:
        """Ensure success/data/error consistency."""
        if self.success:
            if self.error is not None:
                raise ValueError("CLIOutput: success=True but error is set")
            return self

        # Failure case
        if self.error is None:
            raise ValueError("CLIOutput: success=False but error is None")
        if self.data is not None:
            raise ValueError("CLIOutput: success=False but data is not None")

        required_keys = {"type", "message", "code"}
        missing = required_keys.difference(self.error.keys())
        if missing:
            raise ValueError(f"CLIOutput: error missing keys: {sorted(missing)}")

        if not isinstance(self.error.get("type"), str) or not self.error["type"]:
            raise ValueError("CLIOutput: error.type must be a non-empty string")
        if not isinstance(self.error.get("message"), str) or not self.error["message"]:
            raise ValueError("CLIOutput: error.message must be a non-empty string")
        if not isinstance(self.error.get("code"), int):
            raise ValueError("CLIOutput: error.code must be an int")
        return self

    @classmethod
    def ok(cls, command: str, data: Any, duration_ms: int | None = None) -> CLIOutput:
        """Create a successful output."""
        return cls(command=command, success=True, data=data, duration_ms=duration_ms)

    @classmethod
    def err(
        cls,
        command: str,
        error_type: str,
        message: str,
        code: int = 1,
    ) -> CLIOutput:
        """Create an error output."""
        return cls(
            command=command,
            success=False,
            data=None,
            error={"type": error_type, "message": message, "code": code},
        )
