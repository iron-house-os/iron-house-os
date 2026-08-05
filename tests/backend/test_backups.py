import json
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.models.backups import BackupsIntake
from app.models.document import Document
from app.models.finance import Receipt
from app.models.media import MediaRecordLink
from app.models.user import Employee
from app.services import backups
from app.services.auth import AuthenticatedUser
from app.services.file_storage import LocalFileStorageProvider
import app.services.file_storage as file_storage
from conftest import TestingSessionLocal, override_authenticated_user

client = TestClient(app)


@pytest.fixture(autouse=True)
def backups_storage(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(file_storage, "storage_provider", LocalFileStorageProvider(tmp_path))


def _principal(
    user_id: str,
    email: str,
    role: str = "viewer",
) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=UUID(user_id),
        email=email,
        display_name=email.split("@")[0],
        role=role,
        session_version=1,
    )


def _use_user(user: AuthenticatedUser) -> None:
    def override(request: Request) -> AuthenticatedUser:
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


def _upload(content: bytes = b"backups-image", filename: str = "backup.jpg") -> dict:
    response = client.post(
        "/api/v1/media",
        data={"category": "backup", "caption": "Backups original"},
        files={"files": (filename, BytesIO(content), "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    assert len(response.json()) == 1
    return response.json()[0]


def _intake(asset: dict, **payload) -> dict:
    response = client.post(
        "/api/v1/backups",
        json={"media_id": asset["id"], **payload},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _run() -> dict:
    response = client.post("/api/v1/backups/controller/daily")
    assert response.status_code == 200, response.text
    return response.json()


def test_backups_requires_authentication() -> None:
    app.dependency_overrides.pop(require_authenticated_user)
    assert client.get("/api/v1/backups").status_code == 401


@pytest.mark.parametrize("role", ["admin", "operations_manager", "estimator", "viewer"])
def test_every_authenticated_account_role_can_submit_one_media_asset(role: str) -> None:
    user = _principal("00000000-0000-0000-0000-000000000010", f"{role}@example.com", role)
    _use_user(user)
    intake = _intake(_upload(content=role.encode()), note="One image", project_hint="Do not auto-select")
    assert intake["status"] == "pending"
    assert intake["uploader_role"] == ("employee" if role == "viewer" else role)
    assert intake["note"] == "One image"
    assert intake["project_hint"] == "Do not auto-select"
    assert intake["media_id"]
    assert intake["uploader_id"] == str(user.id)
    assert len(intake["media_hash"]) == 64
    assert intake["audit_history"][0]["action"] == "submitted"


def test_viewer_portal_role_is_recorded_and_visibility_and_private_media_are_scoped() -> None:
    submitter = _principal(
        "00000000-0000-0000-0000-000000000021",
        "foreman@example.com",
    )
    with TestingSessionLocal() as db:
        db.add(Employee(first_name="Fran", last_name="Foreman", email=submitter.email, portal_role="foreman"))
        db.commit()

    _use_user(submitter)
    asset = _upload()
    intake = _intake(asset)
    assert intake["uploader_role"] == "foreman"
    assert client.get("/api/v1/backups").json()["total"] == 1
    assert client.get(f"/api/v1/media/{asset['id']}/content").status_code == 200

    other = _principal(
        "00000000-0000-0000-0000-000000000022",
        "operator@example.com",
    )
    _use_user(other)
    assert client.get("/api/v1/backups").json()["items"] == []
    assert client.get(f"/api/v1/backups/{intake['id']}").status_code == 404
    assert client.get(f"/api/v1/media/{asset['id']}/content").status_code == 404

    manager = _principal(
        "00000000-0000-0000-0000-000000000023",
        "manager@example.com",
        "operations_manager",
    )
    _use_user(manager)
    assert client.get("/api/v1/backups").json()["total"] == 1
    assert client.get(f"/api/v1/media/{asset['id']}/content").status_code == 200


@pytest.mark.parametrize(
    ("ocr_text", "detected_type", "destination_type"),
    [
        ("STORE RECEIPT\nSUBTOTAL 10.00\nTOTAL 10.50\nTHANK YOU", "receipt", "receipt"),
        ("SUPPLIER INVOICE\nINVOICE NUMBER 100\nAMOUNT DUE 500.00", "supplier_invoice", "document"),
        ("PACKING SLIP\nDELIVERY TICKET 100\n2 PIPE FITTINGS", "packing_slip", "document"),
        ("A blurry unrecognized jobsite note", "other", None),
    ],
)
def test_daily_controller_routes_all_four_classifications_conservatively(
    monkeypatch,
    ocr_text: str,
    detected_type: str,
    destination_type: str | None,
) -> None:
    monkeypatch.setattr(backups, "extract_local_text", lambda _images: ocr_text)
    intake = _intake(_upload(content=ocr_text.encode()))
    result = _run()
    current = client.get(f"/api/v1/backups/{intake['id']}").json()

    assert result["claimed"] == 1
    assert current["detected_type"] == detected_type
    assert current["audit_history"][-1]["action"] in {"routed_for_review", "triage_required"}
    if destination_type is None:
        assert current["status"] == "needs_review"
        assert current["destination_record_id"] is None
        return

    assert current["status"] == "routed"
    assert current["destination_type"] == destination_type
    assert current["destination_record_id"]
    with TestingSessionLocal() as db:
        if destination_type == "receipt":
            receipt = db.get(Receipt, UUID(current["destination_record_id"]))
            assert receipt is not None
            assert receipt.status == "needs_review"
            assert receipt.treatment == "needs_review"
            assert receipt.approved_by is None
            assert receipt.exported_by is None
        else:
            document = db.get(Document, UUID(current["destination_record_id"]))
            assert document is not None
            assert document.status == "registered"
            assert document.metadata_json["workflow_status"] == "needs_review"
            assert document.metadata_json["posted"] is False
            assert document.metadata_json["approved"] is False
            assert document.metadata_json["accepted"] is False
            assert document.project_id is None


def test_low_confidence_is_kept_in_management_triage(monkeypatch) -> None:
    monkeypatch.setattr(backups, "extract_local_text", lambda _images: "maybe a receipt")
    monkeypatch.setattr(
        backups,
        "_classify",
        lambda _text: backups.Classification("receipt", 0.51, "test_classifier"),
    )
    intake = _intake(_upload(content=b"low-confidence"))
    _run()
    current = client.get(f"/api/v1/backups/{intake['id']}").json()
    assert current["status"] == "needs_review"
    assert current["detected_type"] == "other"
    assert current["confidence"] == 0.51
    assert current["destination_record_id"] is None


@pytest.mark.parametrize(
    "sensitive_text",
    [
        "BANK STATEMENT ACCOUNT NUMBER 123456789",
        "PAYROLL PAY STUB EMPLOYEE",
        "SOCIAL INSURANCE NUMBER 123 456 789",
        "MEDICAL REPORT DIAGNOSIS",
        "CARD NUMBER 4111 1111 1111 1111",
    ],
)
def test_obvious_sensitive_content_is_quarantined_before_external_ai(
    monkeypatch,
    sensitive_text: str,
) -> None:
    monkeypatch.setattr(backups, "extract_local_text", lambda _images: sensitive_text)
    monkeypatch.setattr(
        backups,
        "get_settings",
        lambda: SimpleNamespace(
            openai_api_key="configured-but-must-not-be-used",
            openai_chat_model="gpt-test",
            openai_api_base_url="https://api.openai.test/v1",
        ),
    )

    def forbidden_external_call(*_args, **_kwargs):
        raise AssertionError("Sensitive content was sent externally")

    monkeypatch.setattr(backups, "urlopen", forbidden_external_call)
    intake = _intake(_upload(content=sensitive_text.encode()))
    _run()
    current = client.get(f"/api/v1/backups/{intake['id']}").json()
    assert current["status"] == "needs_review"
    assert current["sensitive_quarantine"] is True
    assert current["classification_source"] == "local_sensitive_screen"
    assert current["destination_record_id"] is None
    assert current["audit_history"][-1]["action"] == "quarantined"


def test_configured_external_classifier_receives_only_screened_ocr_text(monkeypatch) -> None:
    ocr_text = "Vendor paperwork reference 4500"
    monkeypatch.setattr(backups, "extract_local_text", lambda _images: ocr_text)
    monkeypatch.setattr(
        backups,
        "get_settings",
        lambda: SimpleNamespace(
            openai_api_key="configured-test-key",
            openai_chat_model="gpt-test",
            openai_api_base_url="https://api.openai.test/v1",
        ),
    )
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(
                {
                    "output_text": json.dumps(
                        {"detected_type": "supplier_invoice", "confidence": 0.96}
                    )
                }
            ).encode()

    def external_call(request, *, timeout):
        requests.append((request, timeout))
        return Response()

    monkeypatch.setattr(backups, "urlopen", external_call)
    intake = _intake(_upload(content=b"not-sent-to-provider"))
    _run()
    current = client.get(f"/api/v1/backups/{intake['id']}").json()

    assert current["status"] == "routed"
    assert current["detected_type"] == "supplier_invoice"
    assert current["classification_source"] == "openai_api"
    assert len(requests) == 1
    request, timeout = requests[0]
    body = json.loads(request.data)
    assert timeout == 60
    assert request.full_url == "https://api.openai.test/v1/responses"
    assert body["input"] == ocr_text
    assert body["store"] is False
    assert "not-sent-to-provider" not in json.dumps(body)


def test_failure_retry_and_controller_idempotency(monkeypatch) -> None:
    def broken_ocr(_images):
        raise RuntimeError("OCR failure detail that must not be returned")

    monkeypatch.setattr(backups, "extract_local_text", broken_ocr)
    asset = _upload(content=b"retry-image")
    intake = _intake(asset)
    first = _run()
    failed = client.get(f"/api/v1/backups/{intake['id']}").json()
    assert first["failed"] == 1
    assert failed["status"] == "failed"
    assert "OCR failure detail" not in failed["error"]
    assert failed["attempt_count"] == 1

    retried = client.post(f"/api/v1/backups/{intake['id']}/retry")
    assert retried.status_code == 200
    assert retried.json()["status"] == "pending"
    monkeypatch.setattr(backups, "extract_local_text", lambda _images: "RECEIPT SUBTOTAL 10 TOTAL 10 THANK YOU")
    assert _run()["routed"] == 1
    routed = client.get(f"/api/v1/backups/{intake['id']}").json()
    assert routed["status"] == "routed"
    assert routed["attempt_count"] == 2

    assert _run() == {"claimed": 0, "routed": 0, "needs_review": 0, "failed": 0}
    duplicate_request = _intake(asset)
    assert duplicate_request["id"] == intake["id"]
    with TestingSessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(BackupsIntake)) == 1
        assert db.scalar(select(func.count()).select_from(Receipt)) == 1


def test_same_image_hash_reuses_one_destination_across_distinct_media(monkeypatch) -> None:
    monkeypatch.setattr(backups, "extract_local_text", lambda _images: "RECEIPT SUBTOTAL 10 TOTAL 10 THANK YOU")
    first = _intake(_upload(content=b"same-original", filename="first.jpg"))
    _run()
    first = client.get(f"/api/v1/backups/{first['id']}").json()

    second = _intake(_upload(content=b"same-original", filename="second.jpg"))
    _run()
    second = client.get(f"/api/v1/backups/{second['id']}").json()

    assert second["destination_record_id"] == first["destination_record_id"]
    with TestingSessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Receipt)) == 1
        links = list(
            db.scalars(
                select(MediaRecordLink).where(
                    MediaRecordLink.record_type == "receipt",
                    MediaRecordLink.record_id == UUID(first["destination_record_id"]),
                )
            )
        )
        assert len(links) == 2


def test_submitter_cannot_run_controller_or_retry_company_queue(monkeypatch) -> None:
    monkeypatch.setattr(backups, "extract_local_text", lambda _images: "other")
    intake = _intake(_upload())
    viewer = _principal(
        "00000000-0000-0000-0000-000000000001",
        "test-admin@ironhousecontracting.com",
        "viewer",
    )
    _use_user(viewer)
    assert client.post("/api/v1/backups/controller/daily").status_code == 403

    app.dependency_overrides[require_authenticated_user] = override_authenticated_user
    _run()
    assert client.post(f"/api/v1/backups/{intake['id']}/retry").status_code == 200
    _use_user(viewer)
    assert client.post(f"/api/v1/backups/{intake['id']}/retry").status_code == 403
