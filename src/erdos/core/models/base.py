"""Base model configuration shared across all domain models."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class ErdosBaseModel(BaseModel):
    """Base model with shared configuration."""

    model_config = ConfigDict(
        # Validation
        strict=True,  # Strict type coercion
        validate_assignment=True,  # Validate on attribute assignment
        validate_default=True,  # Validate default values
        # Serialization
        ser_json_bytes="base64",  # How to serialize bytes
        ser_json_timedelta="float",  # Timedelta as seconds
        # Immutability (where desired)
        frozen=False,  # Subclasses can override
        # Extra fields
        extra="forbid",  # Reject unknown fields
        # JSON schema
        json_schema_extra={
            "examples": []  # Subclasses add examples
        },
    )
