from collections import deque
from collections.abc import Iterable
from typing import Any, Protocol


class DocumentAuditStore(Protocol):
    """Append-only storage contract for serialized document audit events."""

    def append(self, event: dict[str, Any]) -> None: ...

    def recent(self, limit: int) -> list[dict[str, Any]]: ...

    def clear(self) -> None: ...


class InMemoryDocumentAuditStore:
    """Bounded process-local audit store used as the safe default."""

    def __init__(self, max_events: int = 200, events: Iterable[dict[str, Any]] | None = None) -> None:
        if max_events < 1:
            raise ValueError("max_events must be at least 1")
        self.max_events = max_events
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        for event in events or ():
            self.append(event)

    def append(self, event: dict[str, Any]) -> None:
        self._events.appendleft(dict(event))

    def recent(self, limit: int) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(limit, self.max_events))
        return [dict(event) for event in list(self._events)[:bounded_limit]]

    def clear(self) -> None:
        self._events.clear()
