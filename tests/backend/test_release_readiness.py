from app.services import system_readiness


def test_runtime_readiness_probes_database_and_storage(monkeypatch) -> None:
    monkeypatch.setattr(system_readiness, "_database_readiness", lambda: (True, "ready"))
    monkeypatch.setattr(system_readiness, "_storage_readiness", lambda: (True, "ready"))

    readiness = system_readiness.get_system_readiness(probe_runtime=True)

    assert readiness["status"] == "ready"
    assert readiness["checks"]["database"] == "ready"
    assert readiness["checks"]["document_storage"] == "ready"


def test_runtime_readiness_fails_when_a_dependency_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        system_readiness,
        "_database_readiness",
        lambda: (False, "unavailable"),
    )
    monkeypatch.setattr(system_readiness, "_storage_readiness", lambda: (True, "ready"))

    readiness = system_readiness.get_system_readiness(probe_runtime=True)

    assert readiness["status"] == "not_ready"
    assert readiness["checks"]["database"] == "unavailable"
