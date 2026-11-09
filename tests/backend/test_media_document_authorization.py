"""Document-route authorization regression coverage for media evidence."""

import json
from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

import app.services.file_storage as file_storage
from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.services.auth import AuthenticatedUser
from app.services.file_storage import LocalFileStorageProvider


client = TestClient(app)


def principal(user_id: str, role: str, email: str):
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID(user_id),
            email=email,
            display_name=email,
            role=role,
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    return override


def upload_asset() -> dict:
    response = client.post(
        "/api/v1/media",
        data={"category": "job_photo", "caption": "Private evidence"},
        files=[
            (
                "files",
                ("evidence.jpg", BytesIO(b"immutable-original-photo"), "image/jpeg"),
            )
        ],
    )
    assert response.status_code == 201, response.text
    return response.json()[0]


def test_media_documents_inherit_owner_policy_across_every_documents_read_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(file_storage, "storage_provider", LocalFileStorageProvider(tmp_path))
    ordinary = client.post(
        "/api/v1/documents",
        json={"title": "Visible ordinary document", "category": "specification"},
    ).json()

    app.dependency_overrides[require_authenticated_user] = principal(
        "00000000-0000-0000-0000-000000000010",
        "viewer",
        "photo-owner@ironhousecontracting.com",
    )
    asset = upload_asset()
    edited = client.post(
        f"/api/v1/media/{asset['id']}/versions",
        data={
            "action": "edit",
            "operations": json.dumps([{"type": "rotate", "values": {"degrees": 90}}]),
        },
        files={"file": ("edit.png", BytesIO(b"private-edited-version"), "image/png")},
    )
    assert edited.status_code == 200, edited.text
    edit_version = edited.json()["versions"][0]
    replaced = client.post(
        f"/api/v1/media/{asset['id']}/versions",
        data={"action": "replacement", "operations": "[]"},
        files={"file": ("replacement.jpg", BytesIO(b"private-replacement"), "image/jpeg")},
    )
    assert replaced.status_code == 200, replaced.text
    replacement_version = replaced.json()["versions"][0]
    restored = client.post(
        f"/api/v1/media/{asset['id']}/restore",
        json={"version_id": edit_version["id"]},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["versions"][0]["document_id"] == edit_version["document_id"]

    app.dependency_overrides[require_authenticated_user] = principal(
        "00000000-0000-0000-0000-000000000010",
        "estimator",
        "photo-owner@ironhousecontracting.com",
    )
    media_document_ids = {
        asset["original_document_id"],
        edit_version["document_id"],
        replacement_version["document_id"],
    }
    owner_tokens: dict[str, str] = {}
    owner_photo_list = client.get("/api/v1/documents?category=photo")
    assert owner_photo_list.status_code == 200
    assert media_document_ids <= {item["id"] for item in owner_photo_list.json()["items"]}
    for document_id in media_document_ids:
        assert client.get(f"/api/v1/documents/{document_id}").status_code == 200
        assert client.get(f"/api/v1/documents/{document_id}/download").status_code == 200
        token_response = client.get(f"/api/v1/documents/{document_id}/download-token")
        assert token_response.status_code == 200
        owner_tokens[document_id] = token_response.json()["token"]
        assert client.get(
            "/api/v1/documents/signed-download",
            params={"token": owner_tokens[document_id]},
        ).status_code == 200
        assert client.get(f"/api/v1/documents/{document_id}/integrity").status_code == 200
        manifest = client.post(
            "/api/v1/documents/attachment-manifest",
            json={"document_ids": [document_id]},
        )
        assert manifest.status_code == 200
        assert manifest.json()["items"][0]["document_id"] == document_id

    app.dependency_overrides[require_authenticated_user] = principal(
        "00000000-0000-0000-0000-000000000099",
        "estimator",
        "other-estimator@ironhousecontracting.com",
    )
    general_list = client.get("/api/v1/documents")
    assert general_list.status_code == 200
    assert {item["id"] for item in general_list.json()["items"]} == {ordinary["id"]}
    assert client.get("/api/v1/documents?category=photo").json() == {"items": [], "total": 0}

    for document_id in media_document_ids:
        assert client.get(f"/api/v1/documents/{document_id}").status_code == 404
        assert client.get(f"/api/v1/documents/{document_id}/download").status_code == 404
        assert client.get(f"/api/v1/documents/{document_id}/download-token").status_code == 404
        assert client.get(
            "/api/v1/documents/signed-download",
            params={"token": owner_tokens[document_id]},
        ).status_code == 404
        assert client.get(f"/api/v1/documents/{document_id}/integrity").status_code == 404
        assert client.patch(
            f"/api/v1/documents/{document_id}",
            json={"title": "Unauthorized mutation"},
        ).status_code == 404
        assert client.patch(
            f"/api/v1/documents/{document_id}/status",
            json={"status": "active"},
        ).status_code == 404
        assert client.post(
            "/api/v1/documents/attachment-manifest",
            json={"document_ids": [document_id]},
        ).status_code == 404

    duplicate_upload = client.post(
        "/api/v1/documents/upload",
        data={"category": "photo"},
        files={
            "file": (
                "duplicate.jpg",
                BytesIO(b"immutable-original-photo"),
                "image/jpeg",
            )
        },
    )
    assert duplicate_upload.status_code == 201, duplicate_upload.text
    assert not media_document_ids.intersection(duplicate_upload.json()["duplicate_document_ids"])

    app.dependency_overrides[require_authenticated_user] = principal(
        "00000000-0000-0000-0000-000000000020",
        "operations_manager",
        "operations@ironhousecontracting.com",
    )
    management_photo_ids = {
        item["id"] for item in client.get("/api/v1/documents?category=photo").json()["items"]
    }
    assert media_document_ids <= management_photo_ids
    for document_id in media_document_ids:
        assert client.get(f"/api/v1/documents/{document_id}").status_code == 200
