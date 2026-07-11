from app.services.document_audit_store import InMemoryDocumentAuditStore


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
