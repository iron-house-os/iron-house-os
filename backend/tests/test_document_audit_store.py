from app.services.document_audit_store import (
    InMemoryDocumentAuditStore,
    JsonlDocumentAuditStore,
)


def test_in_memory_audit_store_is_bounded_and_newest_first() -> None:
    store = InMemoryDocumentAuditStore(max_events=2)
    store.append({"action": "first"})
    store.append({"action": "second"})
    store.append({"action": "third"})

    assert store.recent(10) == [{"action": "third"}, {"action": "second"}]


def test_in_memory_audit_store_returns_copies() -> None:
    store = InMemoryDocumentAuditStore()
    event = {"action": "upload"}
    store.append(event)
    event["action"] = "mutated"

    result = store.recent(1)
    result[0]["action"] = "changed"

    assert store.recent(1) == [{"action": "upload"}]


def test_in_memory_audit_store_clear_removes_events() -> None:
    store = InMemoryDocumentAuditStore(events=[{"action": "upload"}])
    store.clear()

    assert store.recent(10) == []


def test_jsonl_audit_store_persists_and_reads_newest_first(tmp_path) -> None:
    path = tmp_path / "audit" / "events.jsonl"
    store = JsonlDocumentAuditStore(path)
    store.append({"action": "first"})
    store.append({"action": "second"})

    reopened = JsonlDocumentAuditStore(path)
    assert reopened.recent(10) == [{"action": "second"}, {"action": "first"}]


def test_jsonl_audit_store_respects_limit_and_clear(tmp_path) -> None:
    store = JsonlDocumentAuditStore(tmp_path / "events.jsonl")
    store.append({"action": "first"})
    store.append({"action": "second"})

    assert store.recent(1) == [{"action": "second"}]
    store.clear()
    assert store.recent(10) == []
