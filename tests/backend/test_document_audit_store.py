import pytest

from app.services.document_audit_store import (
    InMemoryDocumentAuditStore,
    JsonlDocumentAuditStore,
    create_document_audit_store_from_environment,
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


def test_environment_factory_defaults_to_memory(monkeypatch) -> None:
    monkeypatch.delenv("DOCUMENT_AUDIT_STORE", raising=False)
    monkeypatch.setenv("DOCUMENT_AUDIT_MAX_EVENTS", "7")

    store = create_document_audit_store_from_environment()

    assert isinstance(store, InMemoryDocumentAuditStore)
    assert store.max_events == 7


def test_environment_factory_selects_jsonl(monkeypatch, tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    monkeypatch.setenv("DOCUMENT_AUDIT_STORE", "jsonl")
    monkeypatch.setenv("DOCUMENT_AUDIT_JSONL_PATH", str(path))

    store = create_document_audit_store_from_environment()

    assert isinstance(store, JsonlDocumentAuditStore)
    assert store.path == path


def test_environment_factory_rejects_unknown_provider(monkeypatch) -> None:
    monkeypatch.setenv("DOCUMENT_AUDIT_STORE", "unknown")

    with pytest.raises(ValueError, match="Unsupported document audit store"):
        create_document_audit_store_from_environment()
