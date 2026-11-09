from collections import Counter, deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from threading import Lock


@dataclass(frozen=True)
class RequestObservation:
    method: str
    path: str
    status_code: int
    duration_ms: float
    request_id: str
    occurred_at: str


_lock = Lock()
_recent: deque[RequestObservation] = deque(maxlen=100)
_started_at = datetime.now(UTC)


def observe_request(
    *, method: str, path: str, status_code: int, duration_ms: float, request_id: str
) -> None:
    observation = RequestObservation(
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
        request_id=request_id,
        occurred_at=datetime.now(UTC).isoformat(),
    )
    with _lock:
        _recent.appendleft(observation)


def operational_snapshot(*, recent_limit: int = 20) -> dict[str, object]:
    with _lock:
        observations = list(_recent)
    status_classes = Counter(f"{item.status_code // 100}xx" for item in observations)
    failures = [item for item in observations if item.status_code >= 500]
    durations = [item.duration_ms for item in observations]
    return {
        "started_at": _started_at.isoformat(),
        "observed_requests": len(observations),
        "status_classes": dict(status_classes),
        "server_error_count": len(failures),
        "max_duration_ms": max(durations, default=0.0),
        "recent": [asdict(item) for item in observations[: max(1, min(recent_limit, 100))]],
    }


def clear_operational_metrics() -> None:
    with _lock:
        _recent.clear()
