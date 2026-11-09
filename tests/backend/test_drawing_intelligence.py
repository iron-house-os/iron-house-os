from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services import drawing_intelligence, file_storage
from app.services.file_storage import LocalFileStorageProvider


client = TestClient(app)


class FakePage:
    def __init__(self, text: str) -> None:
        self.text = text

    def extract_text(self) -> str:
        return self.text


class FakeReader:
    def __init__(self, _: Path, texts: list[str]) -> None:
        self.pages = [FakePage(text) for text in texts]


@pytest.fixture
def project_id() -> str:
    response = client.post(
        "/api/v1/projects",
        json={"name": "King George Utility Upgrade", "municipality": "Surrey"},
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def drawing_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        file_storage,
        "storage_provider",
        LocalFileStorageProvider(root=tmp_path),
    )


def test_ingest_extract_and_persist_civil_pdf_findings(
    project_id: str,
    drawing_storage: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    texts = [
        """C-101 Utility Plan - City of Surrey - MMCD standard drawing
        Quantity Schedule: 120 m of 300 mm PVC storm pipe
        5 catch basins
        Field verify utility crossing. Dewatering and traffic control required.""",
        "C-201 Road profile. 450 m2 asphalt paving. Maintain access during construction.",
    ]
    monkeypatch.setattr(
        drawing_intelligence,
        "PdfReader",
        lambda path: FakeReader(path, texts),
    )

    response = client.post(
        "/api/v1/drawing-intelligence/ingest",
        data={
            "project_id": project_id,
            "title": "Issued for Tender Civil Drawings",
            "municipality": "Surrey",
        },
        files={"file": ("civil-ift.pdf", b"%PDF-1.7 fake", "application/pdf")},
    )

    payload = response.json()
    assert response.status_code == 201
    assert payload["analysis_version"] == "build-206-v1"
    assert payload["extraction_status"] == "completed"
    assert payload["source"]["project_id"] == project_id
    assert payload["source"]["original_filename"] == "civil-ift.pdf"
    assert len(payload["source"]["sha256_hash"]) == 64
    assert payload["source"]["page_count"] == 2
    assert all(item["requires_verification"] for item in payload["quantity_candidates"])
    assert any(
        item["quantity"] == 120 and item["unit"] == "m"
        for item in payload["quantity_candidates"]
    )
    assert any(
        item["quantity"] == 5 and item["unit"] == "ea"
        for item in payload["quantity_candidates"]
    )
    assert any(
        item["title"] == "Potential utility conflict"
        for item in payload["constructability_issues"]
    )
    assert payload["municipal_standard_issues"][0]["requires_review"] is True

    document_id = payload["source"]["document_id"]
    detail = client.get(f"/api/v1/drawing-intelligence/{document_id}")
    project_list = client.get(
        f"/api/v1/drawing-intelligence/projects/{project_id}"
    )
    document = client.get(f"/api/v1/documents/{document_id}")

    assert detail.status_code == 200
    assert detail.json()["source"] == payload["source"]
    assert project_list.status_code == 200
    assert project_list.json()["total"] == 1
    assert document.json()["drawing"]["discipline"] == "civil"
    assert document.json()["metadata"]["drawing_intelligence"]["extraction_status"] == (
        "completed"
    )


def test_reanalysis_flags_municipality_mismatch(
    project_id: str,
    drawing_storage: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    texts = ["City of Surrey standard drawing. 25 m storm pipe."]
    monkeypatch.setattr(
        drawing_intelligence,
        "PdfReader",
        lambda path: FakeReader(path, texts),
    )
    ingested = client.post(
        "/api/v1/drawing-intelligence/ingest",
        data={"project_id": project_id, "municipality": "Surrey"},
        files={"file": ("civil.pdf", b"%PDF fake", "application/pdf")},
    ).json()

    response = client.post(
        f"/api/v1/drawing-intelligence/{ingested['source']['document_id']}/reanalyze",
        json={"municipality": "Vancouver"},
    )

    assert response.status_code == 200
    assert response.json()["municipality"] == "Vancouver"
    assert any(
        item["title"] == "Possible municipality mismatch"
        and item["severity"] == "critical"
        for item in response.json()["municipal_standard_issues"]
    )


def test_scanned_pdf_reports_ocr_required_without_guessing_quantities(
    project_id: str,
    drawing_storage: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        drawing_intelligence,
        "PdfReader",
        lambda path: FakeReader(path, ["", ""]),
    )

    response = client.post(
        "/api/v1/drawing-intelligence/ingest",
        data={"project_id": project_id, "municipality": "Surrey"},
        files={"file": ("scanned.pdf", b"%PDF scan", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["extraction_status"] == "ocr_required"
    assert response.json()["quantity_candidates"] == []
    assert any("OCR" in warning for warning in response.json()["warnings"])
    assert response.json()["municipal_standard_issues"][0]["title"] == (
        "Standards review blocked by missing text"
    )


def test_ingest_rejects_non_pdf_before_storage(
    project_id: str,
    drawing_storage: None,
) -> None:
    response = client.post(
        "/api/v1/drawing-intelligence/ingest",
        data={"project_id": project_id},
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 422
