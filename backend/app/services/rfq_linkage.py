from app.schemas.rfq_automation import RFQAutomationRequest
from app.schemas.rfq_linkage import RFQLinkageRequest, RFQLinkageResponse, RFQPackageDraft
from app.services.rfq_automation import recommend_rfq_scopes


def build_rfq_package_drafts(payload: RFQLinkageRequest) -> RFQLinkageResponse:
    automation = recommend_rfq_scopes(
        RFQAutomationRequest(
            project_name=payload.project_name,
            municipality=payload.municipality,
            items=payload.source_items,
            include_default_civil_scopes=payload.include_default_civil_scopes,
        )
    )
    packages = [
        RFQPackageDraft(
            title=recommendation.title,
            scope_summary=_scope_summary(recommendation),
            supplier_category_targets=recommendation.supplier_categories,
            required_documents=recommendation.required_documents,
            source_scope=recommendation.scope,
            priority=recommendation.priority,
            review_notes=recommendation.review_notes,
        )
        for recommendation in automation.recommendations
    ]
    warnings = [*automation.warnings]
    if not packages:
        warnings.append("No RFQ package drafts were generated from the current source items.")

    return RFQLinkageResponse(
        project_id=payload.project_id,
        project_name=payload.project_name,
        package_count=len(packages),
        packages=packages,
        warnings=warnings,
        recommendations=automation.recommendations,
    )


def _scope_summary(recommendation) -> str:
    docs = ", ".join(recommendation.required_documents) if recommendation.required_documents else "standard project documents"
    return f"{recommendation.reason} Required RFQ attachments: {docs}."
