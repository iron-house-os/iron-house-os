from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.errors import AppError
from app.schemas.rfq_package import (
    RFQPackageCreate,
    RFQPackageDocumentCreate,
    RFQPackageDocumentRead,
    RFQPackageRead,
    RFQPackageReadiness,
    RFQPackageStatus,
    RFQPackageUpdateStatus,
    RFQReadinessItem,
    SupplierRecipientCreate,
    SupplierRecipientRead,
)


class RFQPackageStore:
    def __init__(self) -> None:
        self._packages: dict[UUID, RFQPackageRead] = {}

    def reset(self) -> None:
        self._packages.clear()

    def create(self, payload: RFQPackageCreate) -> RFQPackageRead:
        now = datetime.now(UTC)
        rfq_package = RFQPackageRead(
            id=uuid4(),
            title=payload.title,
            project_name=payload.project_name,
            scope_summary=payload.scope_summary,
            due_at=payload.due_at,
            status=RFQPackageStatus.draft,
            supplier_category_targets=payload.supplier_category_targets,
            metadata=payload.metadata,
            recipients=[],
            documents=[],
            created_at=now,
            updated_at=now,
        )
        self._packages[rfq_package.id] = rfq_package
        return rfq_package

    def list(self) -> list[RFQPackageRead]:
        return sorted(self._packages.values(), key=lambda item: item.created_at, reverse=True)

    def get(self, rfq_package_id: UUID) -> RFQPackageRead:
        rfq_package = self._packages.get(rfq_package_id)
        if rfq_package is None:
            raise AppError("RFQ package not found", status_code=404)
        return rfq_package

    def update_status(
        self,
        rfq_package_id: UUID,
        payload: RFQPackageUpdateStatus,
    ) -> RFQPackageRead:
        rfq_package = self.get(rfq_package_id)
        updated = rfq_package.model_copy(
            update={"status": payload.status, "updated_at": datetime.now(UTC)}
        )
        self._packages[rfq_package_id] = updated
        return updated

    def select_suppliers(
        self,
        rfq_package_id: UUID,
        payload: list[SupplierRecipientCreate],
    ) -> RFQPackageRead:
        rfq_package = self.get(rfq_package_id)
        recipients = [
            SupplierRecipientRead(
                id=uuid4(),
                supplier_id=item.supplier_id,
                supplier_name=item.supplier_name,
                category=item.category,
                status="selected",
            )
            for item in payload
        ]
        updated = rfq_package.model_copy(
            update={"recipients": recipients, "updated_at": datetime.now(UTC)}
        )
        self._packages[rfq_package_id] = updated
        return updated

    def register_documents(
        self,
        rfq_package_id: UUID,
        payload: list[RFQPackageDocumentCreate],
    ) -> RFQPackageRead:
        rfq_package = self.get(rfq_package_id)
        documents = [
            RFQPackageDocumentRead(
                id=uuid4(),
                document_type=item.document_type,
                title=item.title,
                required=item.required,
                storage_uri=item.storage_uri,
                metadata=item.metadata,
                status="registered",
            )
            for item in payload
        ]
        updated = rfq_package.model_copy(
            update={"documents": documents, "updated_at": datetime.now(UTC)}
        )
        self._packages[rfq_package_id] = updated
        return updated

    def readiness(self, rfq_package_id: UUID) -> RFQPackageReadiness:
        rfq_package = self.get(rfq_package_id)
        required_documents = [document for document in rfq_package.documents if document.required]
        required_documents_registered = bool(required_documents) and all(
            document.status == "registered" for document in required_documents
        )
        items = [
            RFQReadinessItem(
                key="scope",
                label="Scope summary",
                ready=bool(rfq_package.scope_summary),
                detail="Scope summary is present."
                if rfq_package.scope_summary
                else "Add a scope summary before issuing.",
            ),
            RFQReadinessItem(
                key="suppliers",
                label="Supplier recipients",
                ready=bool(rfq_package.recipients),
                detail=f"{len(rfq_package.recipients)} supplier recipients selected.",
            ),
            RFQReadinessItem(
                key="documents",
                label="Required bid documents",
                ready=required_documents_registered,
                detail=f"{len(required_documents)} required documents registered.",
            ),
        ]
        ready_count = sum(1 for item in items if item.ready)
        return RFQPackageReadiness(
            rfq_package_id=rfq_package.id,
            status=rfq_package.status,
            ready=ready_count == len(items),
            score=round((ready_count / len(items)) * 100),
            items=items,
        )


rfq_package_store = RFQPackageStore()
