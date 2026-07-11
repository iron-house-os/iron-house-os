from collections import deque
from collections.abc import Iterable
import json
from pathlib import Path
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


class JsonlDocumentAuditStore:
    """Durable append-only JSON Lines store for single-node deployments."""

    def __init__(self, path: str | Path, max_read_events: int = 10_000) -> None:
        if max_read_events < 1:
            raise ValueError("max_read_events must be at least 1")
        self.path = Path(path)
        self.max_read_events = max_read_events
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
            stream.write("\n")

    def recent(self, limit: int) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        bounded_limit = max(1, min(limit, self.max_read_events))
        lines = self.path.read_text(encoding="utf-8").splitlines()
        events: list[dict[str, Any]] = []
        for line in reversed(lines[-self.max_read_events :]):
            if line.strip():
                events.append(json.loads(line))
            if len(events) >= bounded_limit:
                break
        return events

    def clear(self) -> None:
        self.path.write_text("", encoding="utf-8")
