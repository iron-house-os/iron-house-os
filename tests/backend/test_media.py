import json
from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.services.auth import AuthenticatedUser
from app.services.file_storage import LocalFileStorageProvider
import app.services.file_storage as file_storage


client = TestClient(app)
ADMIN_ID = UUID("00000000-0000-0000-0000-000000000001")


def photo(name: str = "evidence.jpg") -> tuple[str, BytesIO, str]:
    return (name, BytesIO(b"immutable-original-photo"), "image/jpeg")


def upload_asset(*, category: str = "job_photo", location: str = "Restricted GPS") -> dict:
    response = client.post(
        "/api/v1/media",
        data={"category": category, "caption": "Pipe installation", "location": location},
        files=[("files", photo())],
    )
    assert response.status_code == 201, response.text
    return response.json()[0]


def test_original_is_immutable_and_versions_link_editor_parent_and_operations(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(file_storage, "storage_provider", LocalFileStorageProvider(tmp_path))
    asset = upload_asset()
    original_version = asset["versions"][0]

    edit = client.post(
        f"/api/v1/media/{asset['id']}/versions",
        data={
            "action": "edit",
            "operations": json.dumps([
                {"type": "rotate", "values": {"degrees": 90}},
                {"type": "crop", "values": {"x": 5, "y": 5, "width": 90, "height": 90}},
                {"type": "arrow", "values": {}},
                {"type": "text", "values": {"text": "Deficiency"}},
            ]),
            "change_summary": "Rotated, cropped and annotated.",
        },
        files={"file": ("edit.png", BytesIO(b"explicit-edited-version"), "image/png")},
    )

    assert edit.status_code == 200, edit.text
    edited = edit.json()
    current = edited["versions"][0]
    assert current["version_number"] == 2
    assert current["parent_version_id"] == original_version["id"]
    assert current["editor_id"] == str(ADMIN_ID)
    assert {operation["type"] for operation in current["operations"]} == {
        "rotate", "crop", "arrow", "text"
    }

    immutable = client.patch(
        f"/api/v1/documents/{asset['original_document_id']}",
        json={"storage_uri": "elsewhere/replaced.jpg"},
    )
    assert immutable.status_code == 409

    restored = client.post(
        f"/api/v1/media/{asset['id']}/restore",
        json={"version_id": original_version["id"]},
    )
    assert restored.status_code == 200
    restored_version = restored.json()["versions"][0]
    assert restored_version["action"] == "restore"
    assert restored_version["parent_version_id"] == current["id"]
    assert restored_version["document_id"] == original_version["document_id"]


def test_replacement_and_restore_require_reasons_for_controlled_records(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(file_storage, "storage_provider", LocalFileStorageProvider(tmp_path))
    asset = upload_asset(category="incident")

    denied = client.post(
        f"/api/v1/media/{asset['id']}/versions",
        data={"action": "replacement", "operations": "[]"},
        files={"file": ("replacement.jpg", BytesIO(b"replacement"), "image/jpeg")},
    )
    assert denied.status_code == 422

    replaced = client.post(
        f"/api/v1/media/{asset['id']}/versions",
        data={
            "action": "replacement",
            "operations": "[]",
            "amendment_reason": "Wrong incident photo selected on site.",
        },
        files={"file": ("replacement.jpg", BytesIO(b"replacement"), "image/jpeg")},
    )
    assert replaced.status_code == 200
    assert replaced.json()["versions"][0]["action"] == "replacement"
    assert replaced.json()["versions"][0]["amendment_reason"]


def test_record_links_and_content_are_authorized_and_location_is_role_restricted(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(file_storage, "storage_provider", LocalFileStorageProvider(tmp_path))
    asset = upload_asset()
    equipment = client.post(
        "/api/v1/equipment",
        json={"name": "Excavator", "identifier": "EX-01"},
    ).json()
    link = client.post(
        f"/api/v1/media/{asset['id']}/links",
        json={"record_type": "equipment", "record_id": equipment["id"]},
    )
    assert link.status_code == 200
    linked = client.get(
        f"/api/v1/media?record_type=equipment&record_id={equipment['id']}"
    )
    assert linked.status_code == 200
    assert linked.json()[0]["links"][0]["record_id"] == equipment["id"]
    assert client.get(f"/api/v1/media/{asset['id']}/content").content == b"immutable-original-photo"

    def viewer(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            email="viewer@ironhousecontracting.com",
            display_name="Viewer",
            role="viewer",
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = viewer
    restricted = client.get(f"/api/v1/media/{asset['id']}")
    assert restricted.status_code == 200
    assert restricted.json()["location"] is None
    denied_edit = client.patch(f"/api/v1/media/{asset['id']}", json={"caption": "Changed"})
    assert denied_edit.status_code == 403


def test_annotation_and_transform_validation_rejects_unsafe_payloads(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(file_storage, "storage_provider", LocalFileStorageProvider(tmp_path))
    asset = upload_asset()
    invalid = client.post(
        f"/api/v1/media/{asset['id']}/versions",
        data={
            "action": "edit",
            "operations": json.dumps([{"type": "rotate", "values": {"degrees": 47}}]),
        },
        files={"file": ("edit.png", BytesIO(b"bad-operation"), "image/png")},
    )
    assert invalid.status_code == 422
