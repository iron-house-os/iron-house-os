from pathlib import Path

import pytest

from app.services.file_storage import LocalFileStorageProvider, build_storage_provider


def test_build_storage_provider_defaults_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IHOS_STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("IHOS_STORAGE_ROOT", raising=False)

    provider = build_storage_provider()

    assert isinstance(provider, LocalFileStorageProvider)


def test_build_storage_provider_uses_configured_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IHOS_STORAGE_BACKEND", "local")
    monkeypatch.setenv("IHOS_STORAGE_ROOT", str(tmp_path))

    provider = build_storage_provider()

    assert isinstance(provider, LocalFileStorageProvider)
    assert provider.root == tmp_path


def test_build_storage_provider_rejects_unknown_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IHOS_STORAGE_BACKEND", "unknown")

    with pytest.raises(RuntimeError, match="Unsupported IHOS_STORAGE_BACKEND"):
        build_storage_provider()
