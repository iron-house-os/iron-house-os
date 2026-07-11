from __future__ import annotations

from app.schemas.cost_code import (
    CostCode,
    CostCodeGroup,
    CostCodeLibrary,
    CostCodeResolveRequest,
    CostCodeResolveResponse,
)
from app.schemas.estimate import EstimateItemType, EstimateUnit


LIBRARY_VERSION = "2026.07"

COST_CODES: tuple[CostCode, ...] = (
    CostCode(code="01-100", name="Mobilization", group=CostCodeGroup.general, default_item_type=EstimateItemType.indirect, default_unit=EstimateUnit.lump_sum, tags=["mobilization", "startup", "demobilization"]),
    CostCode(code="01-200", name="Site supervision", group=CostCodeGroup.general, default_item_type=EstimateItemType.indirect, default_unit=EstimateUnit.day, tags=["supervision", "foreman", "project management"]),
    CostCode(code="02-100", name="Clearing and grubbing", group=CostCodeGroup.earthworks, default_item_type=EstimateItemType.self_perform, default_unit=EstimateUnit.square_metre, tags=["clearing", "grubbing", "brush"]),
    CostCode(code="02-200", name="Common excavation", group=CostCodeGroup.earthworks, default_item_type=EstimateItemType.self_perform, default_unit=EstimateUnit.cubic_metre, tags=["excavation", "dig", "soil"]),
    CostCode(code="02-300", name="Trench backfill and compaction", group=CostCodeGroup.earthworks, default_item_type=EstimateItemType.self_perform, default_unit=EstimateUnit.cubic_metre, tags=["backfill", "compaction", "trench"]),
    CostCode(code="02-400", name="Granular base and subbase", group=CostCodeGroup.earthworks, default_item_type=EstimateItemType.material, default_unit=EstimateUnit.tonne, tags=["aggregate", "road base", "subbase", "granular"]),
    CostCode(code="03-100", name="PVC sewer and drain pipe", group=CostCodeGroup.utilities, default_item_type=EstimateItemType.material, default_unit=EstimateUnit.metre, tags=["pvc", "storm", "sanitary", "pipe"]),
    CostCode(code="03-200", name="Watermain pipe", group=CostCodeGroup.utilities, default_item_type=EstimateItemType.material, default_unit=EstimateUnit.metre, tags=["watermain", "ductile iron", "pvc", "pipe"]),
    CostCode(code="03-300", name="Manholes", group=CostCodeGroup.structures, default_item_type=EstimateItemType.material, default_unit=EstimateUnit.each, tags=["manhole", "precast", "structure"]),
    CostCode(code="03-400", name="Catch basins", group=CostCodeGroup.structures, default_item_type=EstimateItemType.material, default_unit=EstimateUnit.each, tags=["catch basin", "cb", "drainage"]),
    CostCode(code="04-100", name="Concrete curb", group=CostCodeGroup.concrete, default_item_type=EstimateItemType.subcontract, default_unit=EstimateUnit.metre, tags=["curb", "concrete"]),
    CostCode(code="04-200", name="Concrete sidewalk", group=CostCodeGroup.concrete, default_item_type=EstimateItemType.subcontract, default_unit=EstimateUnit.square_metre, tags=["sidewalk", "concrete", "flatwork"]),
    CostCode(code="05-100", name="Asphalt paving", group=CostCodeGroup.asphalt, default_item_type=EstimateItemType.subcontract, default_unit=EstimateUnit.tonne, tags=["asphalt", "paving", "blacktop"]),
    CostCode(code="05-200", name="Asphalt removal and disposal", group=CostCodeGroup.asphalt, default_item_type=EstimateItemType.self_perform, default_unit=EstimateUnit.square_metre, tags=["asphalt removal", "milling", "sawcut"]),
    CostCode(code="06-100", name="Traffic control", group=CostCodeGroup.traffic, default_item_type=EstimateItemType.subcontract, default_unit=EstimateUnit.day, tags=["traffic", "tcp", "lane closure"]),
    CostCode(code="06-200", name="Pavement markings", group=CostCodeGroup.traffic, default_item_type=EstimateItemType.subcontract, default_unit=EstimateUnit.lump_sum, tags=["paint", "markings", "thermoplastic"]),
    CostCode(code="07-100", name="Topsoil and landscape restoration", group=CostCodeGroup.landscaping, default_item_type=EstimateItemType.self_perform, default_unit=EstimateUnit.square_metre, tags=["topsoil", "landscape", "restoration"]),
    CostCode(code="08-100", name="Material and compaction testing", group=CostCodeGroup.testing, default_item_type=EstimateItemType.subcontract, default_unit=EstimateUnit.lump_sum, tags=["testing", "density", "compaction", "concrete"]),
    CostCode(code="09-100", name="Coring", group=CostCodeGroup.closeout, default_item_type=EstimateItemType.subcontract, default_unit=EstimateUnit.each, tags=["coring", "core drilling"]),
    CostCode(code="09-200", name="Cleanup and closeout", group=CostCodeGroup.closeout, default_item_type=EstimateItemType.self_perform, default_unit=EstimateUnit.lump_sum, tags=["cleanup", "closeout", "deficiency"]),
)


def get_cost_code_library() -> CostCodeLibrary:
    return CostCodeLibrary(version=LIBRARY_VERSION, items=list(COST_CODES))


def resolve_cost_code(payload: CostCodeResolveRequest) -> CostCodeResolveResponse:
    if payload.code:
        normalized = payload.code.strip().lower()
        exact = next((item for item in COST_CODES if item.code.lower() == normalized), None)
        if exact:
            return CostCodeResolveResponse(match=exact, confidence=1.0)

    query = (payload.description or "").strip().lower()
    if not query:
        return CostCodeResolveResponse(match=None, confidence=0.0)

    scored: list[tuple[float, CostCode]] = []
    query_tokens = set(query.replace("/", " ").replace("-", " ").split())
    for item in COST_CODES:
        haystack = " ".join([item.name, item.description or "", *item.tags]).lower()
        token_hits = sum(1 for token in query_tokens if token in haystack)
        phrase_hit = 1 if item.name.lower() in query or query in item.name.lower() else 0
        score = min(1.0, phrase_hit * 0.75 + token_hits / max(len(query_tokens), 1) * 0.7)
        if score:
            scored.append((score, item))

    scored.sort(key=lambda candidate: (-candidate[0], candidate[1].code))
    if not scored:
        return CostCodeResolveResponse(match=None, confidence=0.0)
    best_score, best = scored[0]
    return CostCodeResolveResponse(
        match=best,
        confidence=round(best_score, 2),
        alternatives=[item for _, item in scored[1:4]],
    )
