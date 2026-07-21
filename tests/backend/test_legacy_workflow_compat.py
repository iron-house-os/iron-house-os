from fastapi.testclient import TestClient

from app.main import app
from app.models.document import Document
from app.models.equipment import Equipment
from app.models.project import Project
from app.models.rfq import RFQPackage, RFQPackageDocument, RFQPackageSupplierRecipient
from conftest import TestingSessionLocal


client = TestClient(app)


def test_every_list_serializer_tolerates_pre_workflow_values() -> None:
    with TestingSessionLocal() as session:
        project = Project(name="Legacy project", status="planning", metadata_json={})
        document = Document(
            title="Legacy plan",
            category="plans",
            status="indexed",
            metadata_json={},
        )
        equipment = Equipment(name="Legacy excavator", status="operational")
        rfq_package = RFQPackage(
            title="Legacy RFQ",
            status="planning",
            supplier_category_targets=[],
            metadata_json={},
        )
        rfq_package.recipients.append(
            RFQPackageSupplierRecipient(
                supplier_id="legacy-supplier",
                supplier_name="Legacy Supplier",
                status="selected",
            )
        )
        rfq_package.documents.append(
            RFQPackageDocument(
                document_type="drawing",
                title="Legacy attachment",
                required=True,
                status="registered",
                storage_uri="s3://legacy/attachment.pdf",
                metadata_json={},
            )
        )
        session.add_all([project, document, equipment, rfq_package])
        session.commit()

    projects = client.get("/api/v1/projects")
    documents = client.get("/api/v1/documents")
    equipment_response = client.get("/api/v1/equipment")
    rfqs = client.get("/api/v1/rfqs")

    assert projects.status_code == 200
    assert projects.json()["items"][0]["status"] == "opportunity"
    assert documents.status_code == 200
    assert documents.json()["items"][0]["category"] == "drawing"
    assert documents.json()["items"][0]["status"] == "registered"
    assert equipment_response.status_code == 200
    assert equipment_response.json()["items"][0]["status"] == "available"
    assert rfqs.status_code == 200
    assert rfqs.json()["items"][0]["status"] == "draft"
    assert rfqs.json()["items"][0]["recipients"][0]["status"] == "pending"
    assert rfqs.json()["items"][0]["documents"][0]["status"] == "attached"
