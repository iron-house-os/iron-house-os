import json
from io import BytesIO
from pathlib import Path
from uuid import UUID

from types import SimpleNamespace
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.models.document import Document
from app.models.finance import Receipt
from app.models.media import BackupIntake, MediaAsset
from app.services import backups
from app.services.auth import AuthenticatedUser
from app.services.file_storage import LocalFileStorageProvider
import app.services.file_storage as file_storage
from conftest import TestingSessionLocal

client = TestClient(app)
ADMIN_ID = UUID("00000000-0000-0000-0000-000000000001")
VIEWER_ID = UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture(autouse=True)
def private_storage(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(file_storage, "storage_provider", LocalFileStorageProvider(tmp_path))


def principal(user_id: UUID, email: str, role: str):
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(id=user_id, email=email, display_name=email, role=role, session_version=1)
        request.state.authenticated_user = user
        return user
    return override


def upload(content: bytes, *, note: str = "Daily backup", project_hint: str = "Project 17") -> dict:
    response = client.post(
        "/api/v1/backups",
        data={"note": note, "project_hint": project_hint},
        files={"file": ("backup.jpg", BytesIO(content), "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def run_controller(classification: backups.Classification) -> dict:
    with TestingSessionLocal() as db:
        return backups.run_daily_controller(db, classifier=lambda _text: classification).model_dump()


def test_authentication_single_photo_and_retry_upload_idempotency() -> None:
    app.dependency_overrides.pop(require_authenticated_user)
    anonymous = client.post(
        "/api/v1/backups",
        files={"file": ("backup.jpg", BytesIO(b"anonymous"), "image/jpeg")},
    )
    assert anonymous.status_code == 401
    app.dependency_overrides[require_authenticated_user] = principal(ADMIN_ID, "admin@ironhousecontracting.com", "admin")

    multiple = client.post(
        "/api/v1/backups",
        files=[
            ("file", ("one.jpg", BytesIO(b"one"), "image/jpeg")),
            ("file", ("two.jpg", BytesIO(b"two"), "image/jpeg")),
        ],
    )
    assert multiple.status_code == 422
    first = upload(b"same-upload")
    retried = upload(b"same-upload")
    assert retried["id"] == first["id"]
    assert retried["media_asset_id"] == first["media_asset_id"]
    with TestingSessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(BackupIntake)) == 1


@pytest.mark.parametrize("role", ["viewer", "estimator", "operations_manager", "admin"])
def test_every_supported_account_role_can_submit(role: str) -> None:
    app.dependency_overrides[require_authenticated_user] = principal(
        VIEWER_ID, f"{role}@ironhousecontracting.com", role
    )
    assert upload(f"role-{role}".encode())["uploader_role"] == role


def test_submitter_company_visibility_and_private_original_access() -> None:
    admin_item = upload(b"admin-owned")
    app.dependency_overrides[require_authenticated_user] = principal(
        VIEWER_ID, "field@ironhousecontracting.com", "viewer"
    )
    viewer_item = upload(b"viewer-owned")
    own = client.get("/api/v1/backups")
    assert own.status_code == 200
    assert [item["id"] for item in own.json()["items"]] == [viewer_item["id"]]
    assert client.get(f"/api/v1/backups/{admin_item['id']}").status_code == 404
    assert client.get(f"/api/v1/media/{admin_item['media_asset_id']}/content").status_code == 404
    assert client.get(f"/api/v1/media/{viewer_item['media_asset_id']}/content").status_code == 200

    app.dependency_overrides[require_authenticated_user] = principal(
        ADMIN_ID, "admin@ironhousecontracting.com", "admin"
    )
    company = client.get("/api/v1/backups").json()
    assert {item["id"] for item in company["items"]} == {admin_item["id"], viewer_item["id"]}
    assert client.get(f"/api/v1/media/{viewer_item['media_asset_id']}/content").status_code == 200


@pytest.mark.parametrize(
    ("detected_type", "destination_type", "model"),
    [
        ("receipt", "receipt", Receipt),
        ("supplier_invoice", "finance_document", Document),
        ("packing_slip", "procurement_document", Document),
    ],
)
def test_controller_routes_review_only_and_is_idempotent(detected_type, destination_type, model, monkeypatch) -> None:
    monkeypatch.setattr(backups, "extract_local_text", lambda _images: "safe document text")
    item = upload(f"route-{detected_type}".encode())
    result = run_controller(backups.Classification(detected_type, 0.96, "test-classifier"))
    assert result == {"selected": 1, "routed": 1, "needs_review": 0, "failed": 0}
    routed = client.get(f"/api/v1/backups/{item['id']}").json()
    assert routed["status"] == "routed"
    assert routed["destination_type"] == destination_type
    audit_actions = {event["action"] for event in routed["audit_history"]}
    assert {"uploaded", "processing_started", "routed_for_review"}.issubset(audit_actions)
    with TestingSessionLocal() as db:
        destination = db.get(model, UUID(routed["destination_record_id"]))
        assert destination.status == "needs_review"
        if isinstance(destination, Receipt):
            assert destination.approved_by is None and destination.exported_at is None
        else:
            assert destination.metadata_json["unapproved"] is True
            assert destination.project_id is None
        destination_count = db.scalar(select(func.count()).select_from(model))
    second = run_controller(backups.Classification(detected_type, 0.96, "test-classifier"))
    assert second["selected"] == 0
    with TestingSessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(model)) == destination_count


def test_other_and_low_confidence_stay_in_management_triage(monkeypatch) -> None:
    monkeypatch.setattr(backups, "extract_local_text", lambda _images: "safe uncertain text")
    other = upload(b"other-route")
    assert run_controller(backups.Classification("other", 0.99, "test"))["needs_review"] == 1
    other_read = client.get(f"/api/v1/backups/{other['id']}").json()
    assert other_read["status"] == "needs_review" and other_read["destination_record_id"] is None

    low = upload(b"low-route")
    assert run_controller(backups.Classification("receipt", 0.40, "test"))["needs_review"] == 1
    low_read = client.get(f"/api/v1/backups/{low['id']}").json()
    assert low_read["status"] == "needs_review" and low_read["destination_record_id"] is None


def test_sensitive_content_is_quarantined_without_external_classifier(monkeypatch) -> None:
    monkeypatch.setattr(
        backups,
        "extract_local_text",
        lambda _images: "PAYROLL direct deposit card 4111 1111 1111 1111",
    )
    calls = []
    item = upload(b"sensitive-route")
    with TestingSessionLocal() as db:
        result = backups.run_daily_controller(
            db,
            classifier=lambda _text: calls.append("external") or backups.Classification("receipt", 0.99, "external"),
        )
    assert result.needs_review == 1 and calls == []
    quarantined = client.get(f"/api/v1/backups/{item['id']}").json()
    assert quarantined["sensitive_quarantine"] is True
    assert quarantined["status"] == "needs_review"
    assert quarantined["classifier"] == "local-sensitive-screen"
    assert quarantined["destination_record_id"] is None


def test_configured_openai_classifier_uses_ocr_text_and_strict_schema(monkeypatch) -> None:
    captured = {}

    class ProviderResponse:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self): return json.dumps({"output_text": '{"detected_type":"supplier_invoice","confidence":0.94}'}).encode()

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return ProviderResponse()

    monkeypatch.setattr(backups, "get_settings", lambda: SimpleNamespace(
        openai_api_key="server-only-key", openai_chat_model="gpt-test",
        openai_api_base_url="https://api.openai.test/v1",
    ))
    monkeypatch.setattr(backups, "urlopen", fake_urlopen)
    result = backups.classify_text("SUPPLIER INVOICE amount due 112.00")
    assert result == backups.Classification("supplier_invoice", 0.94, "gpt-test")
    assert captured["body"]["store"] is False
    assert captured["body"]["text"]["format"]["strict"] is True
    assert "SUPPLIER INVOICE" in captured["body"]["input"][0]["content"][0]["text"]
    assert captured["timeout"] == 60


def test_failure_retry_and_success_do_not_duplicate_destination(monkeypatch) -> None:
    item = upload(b"failure-route")
    monkeypatch.setattr(backups, "extract_local_text", lambda _images: (_ for _ in ()).throw(RuntimeError("OCR unavailable")))
    assert run_controller(backups.Classification("receipt", 0.99, "test"))["failed"] == 1
    failed = client.get(f"/api/v1/backups/{item['id']}").json()
    assert failed["status"] == "failed"
    assert failed["attempt_count"] == 1

    retried = client.post(f"/api/v1/backups/{item['id']}/retry", json={"reason": "OCR service recovered"})
    assert retried.status_code == 200
    assert retried.json()["status"] == "pending"
    monkeypatch.setattr(backups, "extract_local_text", lambda _images: "receipt subtotal gst total")
    assert run_controller(backups.Classification("receipt", 0.97, "test"))["routed"] == 1
    done = client.get(f"/api/v1/backups/{item['id']}").json()
    assert done["attempt_count"] == 2
    with TestingSessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Receipt)) == 1
        asset = db.get(MediaAsset, UUID(item["media_asset_id"]))
        assert asset.controlled is True and asset.category == "backups"
