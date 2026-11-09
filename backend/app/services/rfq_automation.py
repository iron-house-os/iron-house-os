from collections import defaultdict

from app.schemas.rfq_automation import (
    RFQAutomationInputItem,
    RFQAutomationRequest,
    RFQAutomationResponse,
    RFQScopeRecommendation,
)

SCOPE_MAP = {
    "pipe": "pipe_supply",
    "storm": "pipe_supply",
    "sanitary": "pipe_supply",
    "water": "pipe_supply",
    "structures": "structures_supply",
    "manhole": "structures_supply",
    "catch basin": "structures_supply",
    "asphalt": "asphalt_paving",
    "concrete": "concrete_subcontract",
    "traffic": "traffic_control",
    "landscape": "landscaping",
    "earthworks": "aggregate_supply",
    "disposal": "disposal",
    "testing": "testing",
}

SCOPE_DETAILS = {
    "pipe_supply": {
        "title": "Pipe and utility materials RFQ",
        "supplier_categories": ["pipe", "waterworks", "utility materials"],
        "required_documents": ["civil drawings", "specifications", "addenda", "municipal approved materials"],
        "priority": 10,
    },
    "structures_supply": {
        "title": "Precast structures RFQ",
        "supplier_categories": ["precast", "manholes", "catch basins"],
        "required_documents": ["civil drawings", "structure schedule", "standard details", "addenda"],
        "priority": 20,
    },
    "aggregate_supply": {
        "title": "Aggregates and granular materials RFQ",
        "supplier_categories": ["aggregate", "sand and gravel", "trucking"],
        "required_documents": ["typical sections", "specifications", "quantity summary"],
        "priority": 30,
    },
    "asphalt_paving": {
        "title": "Asphalt paving RFQ",
        "supplier_categories": ["asphalt", "paving", "milling"],
        "required_documents": ["roadworks drawings", "restoration details", "traffic staging", "addenda"],
        "priority": 40,
    },
    "concrete_subcontract": {
        "title": "Concrete works RFQ",
        "supplier_categories": ["concrete", "curb", "sidewalk", "flatwork"],
        "required_documents": ["civil drawings", "concrete details", "restoration drawings"],
        "priority": 50,
    },
    "testing": {
        "title": "Materials testing RFQ",
        "supplier_categories": ["testing", "geotechnical", "materials testing"],
        "required_documents": ["specifications", "municipal requirements", "expected schedule"],
        "priority": 60,
    },
    "traffic_control": {
        "title": "Traffic control RFQ",
        "supplier_categories": ["traffic control", "lane closure", "TCP"],
        "required_documents": ["traffic drawings", "site location", "schedule", "work windows"],
        "priority": 70,
    },
    "landscaping": {
        "title": "Landscape restoration RFQ",
        "supplier_categories": ["landscape", "topsoil", "sod", "irrigation"],
        "required_documents": ["landscape drawings", "restoration limits", "details"],
        "priority": 80,
    },
    "earthworks_support": {
        "title": "Earthworks support RFQ",
        "supplier_categories": ["excavation", "trucking", "equipment rental"],
        "required_documents": ["civil drawings", "geotechnical notes", "quantity summary"],
        "priority": 90,
    },
    "disposal": {
        "title": "Disposal and dump fees RFQ",
        "supplier_categories": ["disposal", "dump site", "trucking"],
        "required_documents": ["soil information", "quantity summary", "haul distance assumptions"],
        "priority": 95,
    },
    "misc": {
        "title": "Miscellaneous RFQ",
        "supplier_categories": ["misc"],
        "required_documents": ["scope summary", "drawings", "specifications"],
        "priority": 100,
    },
}

DEFAULT_SCOPES = ["pipe_supply", "structures_supply", "aggregate_supply", "asphalt_paving", "testing", "traffic_control"]


def recommend_rfq_scopes(payload: RFQAutomationRequest) -> RFQAutomationResponse:
    grouped: dict[str, list[RFQAutomationInputItem]] = defaultdict(list)
    if payload.include_default_civil_scopes:
        for scope in DEFAULT_SCOPES:
            grouped[scope]

    for item in payload.items:
        scope = _map_item_to_scope(item)
        grouped[scope].append(item)

    recommendations = [_build_recommendation(scope, items) for scope, items in grouped.items()]
    recommendations.sort(key=lambda item: item.priority)

    warnings: list[str] = []
    if not payload.items:
        warnings.append("No source quantities or municipal requirements supplied; showing default civil RFQ scopes only.")
    if payload.municipality:
        warnings.append("Municipality requirements should be attached to each issued RFQ for compliance confirmation.")

    return RFQAutomationResponse(
        project_name=payload.project_name,
        municipality=payload.municipality,
        recommendation_count=len(recommendations),
        high_priority_count=sum(1 for item in recommendations if item.priority <= 30),
        recommendations=recommendations,
        warnings=warnings,
    )


def _map_item_to_scope(item: RFQAutomationInputItem) -> str:
    text = f"{item.category} {item.description}".lower()
    for keyword, scope in SCOPE_MAP.items():
        if keyword in text:
            return scope
    return "misc"


def _build_recommendation(scope: str, items: list[RFQAutomationInputItem]) -> RFQScopeRecommendation:
    details = SCOPE_DETAILS[scope]
    source_signals = sorted({item.source for item in items}) or ["manual"]
    reasons = [f"{item.description} ({item.quantity or 0:g} {item.unit or ''})".strip() for item in items[:4]]
    reason = "; ".join(reasons) if reasons else "Default civil procurement scope for MVP bid setup."
    notes = []
    if not items:
        notes.append("Review whether this default RFQ scope applies before issuing.")
    if scope in {"pipe_supply", "structures_supply"}:
        notes.append("Ask suppliers to confirm municipal approved materials and current lead times.")
    if scope in {"asphalt_paving", "traffic_control"}:
        notes.append("Include staging, work windows, and restoration limits in RFQ package.")
    return RFQScopeRecommendation(
        scope=scope,
        title=details["title"],
        reason=reason,
        supplier_categories=details["supplier_categories"],
        required_documents=details["required_documents"],
        priority=details["priority"],
        source_signals=source_signals,
        review_notes=notes,
    )
