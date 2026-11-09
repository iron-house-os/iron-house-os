from enum import StrEnum
from typing import TypeVar


WorkflowEnum = TypeVar("WorkflowEnum", bound=StrEnum)


def workflow_enum(
    enum_type: type[WorkflowEnum],
    raw_value: str | None,
    *,
    fallback: WorkflowEnum,
    aliases: dict[str, str] | None = None,
) -> WorkflowEnum:
    """Return a stable API enum for data written by an older workflow."""

    normalized = (raw_value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    if aliases:
        normalized = aliases.get(normalized, normalized)
    try:
        return enum_type(normalized)
    except ValueError:
        return fallback
