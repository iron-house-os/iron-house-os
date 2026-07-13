from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
import re
from uuid import UUID

from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.document import Document
from app.models.project import Project
from app.schemas.drawing_intelligence import (
    CivilDrawingAnalysis,
    CivilDrawingAnalysisList,
    DrawingAnalysisSource,
    DrawingDiscipline,
    DrawingIssue,
    DrawingPageExtraction,
    DrawingQuantityCandidate,
    DrawingSetAnalyzeRequest,
    DrawingSetAnalysisResponse,
    DrawingSheetAnalysis,
    DrawingSheetInput,
    DrawingSheetType,
)
from app.schemas.document import DocumentCategory
from app.services import documents
from app.services.file_storage import resolve_storage_path

MUNICIPALITY_HINTS = [
    "surrey",
    "vancouver",
    "burnaby",
    "richmond",
    "coquitlam",
    "delta",
    "langley",
    "abbotsford",
    "chilliwack",
    "sechelt",
    "new westminster",
    "maple ridge",
]

DISCIPLINE_KEYWORDS: dict[DrawingDiscipline, list[str]] = {
    "civil": ["civil", "watermain", "sanitary", "storm", "roadworks", "grading", "servicing"],
    "traffic": ["traffic", "tcp", "detour", "signal", "pavement marking"],
    "structural": ["structural", "rebar", "foundation", "retaining wall"],
    "electrical": ["electrical", "lighting", "streetlight", "duct", "hydro"],
    "landscape": ["landscape", "planting", "irrigation", "boulevard", "topsoil"],
    "environmental": ["esc", "erosion", "sediment", "environmental", "tree protection"],
    "unknown": [],
}

SHEET_TYPE_KEYWORDS: dict[DrawingSheetType, list[str]] = {
    "cover": ["cover", "title sheet"],
    "general_notes": ["general notes", "notes", "legend", "abbreviations"],
    "civil_plan": ["plan", "site plan", "roadworks", "servicing", "utility plan"],
    "profile": ["profile", "plan and profile"],
    "cross_section": ["cross section", "section"],
    "traffic_control": ["traffic control", "tcp", "detour"],
    "esc": ["erosion", "sediment", "esc"],
    "landscape": ["landscape", "planting", "irrigation"],
    "details": ["detail", "standard detail"],
    "specification": ["specification", "spec"],
    "addenda": ["addenda", "addendum"],
    "unknown": [],
}

ANALYSIS_METADATA_KEY = "drawing_intelligence"
MAX_PAGE_TEXT_CHARS = 200_000
MAX_QUANTITY_CANDIDATES = 100
CIVIL_QUANTITY_KEYWORDS = (
    "aggregate",
    "asphalt",
    "catch basin",
    "concrete",
    "culvert",
    "curb",
    "excavation",
    "hydrant",
    "manhole",
    "pipe",
    "road",
    "sanitary",
    "sewer",
    "sidewalk",
    "storm",
    "topsoil",
    "valve",
    "watermain",
)
MEASURED_QUANTITY_PATTERN = re.compile(
    r"(?P<quantity>\d{1,7}(?:,\d{3})*(?:\.\d+)?)\s*"
    r"(?P<unit>m²|m2|sq\.?\s*m|m³|m3|cu\.?\s*m|lm|m|ea|each)\b",
    re.IGNORECASE,
)
COUNT_QUANTITY_PATTERN = re.compile(
    r"\b(?P<quantity>\d{1,5})\s+(?P<asset>catch basins?|manholes?|hydrants?|valves?|service connections?)\b",
    re.IGNORECASE,
)
CONSTRUCTABILITY_RULES = (
    (
        re.compile(r"\b(conflict|clash|utility crossing)\b", re.IGNORECASE),
        "critical",
        "Potential utility conflict",
        "A possible conflict is called out and needs coordinated field/design review.",
    ),
    (
        re.compile(r"\b(field verify|verify in field|confirm location|location unknown)\b", re.IGNORECASE),
        "warning",
        "Field verification required",
        "The drawing requires an existing condition or utility location to be confirmed in the field.",
    ),
    (
        re.compile(r"\b(shoring|trench box|deep excavation)\b", re.IGNORECASE),
        "warning",
        "Excavation support review",
        "Excavation support language was detected; review access, soil, depth, and safety assumptions.",
    ),
    (
        re.compile(r"\b(dewatering|groundwater|water table)\b", re.IGNORECASE),
        "warning",
        "Groundwater or dewatering review",
        "Groundwater language was detected and may affect production, disposal, and temporary works.",
    ),
    (
        re.compile(r"\b(live traffic|maintain access|traffic control|staged construction)\b", re.IGNORECASE),
        "warning",
        "Traffic and access constraint",
        "Traffic, staging, or access requirements may constrain sequencing and production rates.",
    ),
    (
        re.compile(r"\b(contaminated|hazardous material|environmental monitor)\b", re.IGNORECASE),
        "warning",
        "Environmental handling review",
        "Potential environmental handling or monitoring requirements were detected.",
    ),
)


async def ingest_civil_pdf(
    db: Session,
    *,
    file: UploadFile,
    project_id: UUID,
    title: str | None = None,
    municipality: str | None = None,
) -> CivilDrawingAnalysis:
    filename = file.filename or "upload"
    if Path(filename).suffix.casefold() != ".pdf":
        raise AppError("Drawing intelligence accepts PDF files only.", status_code=422)
    if db.get(Project, project_id) is None:
        raise AppError("Project not found", status_code=404)

    uploaded = await documents.upload_document(
        db,
        file=file,
        title=title,
        category=DocumentCategory.drawing.value,
        project_id=project_id,
        description="Civil PDF ingested for drawing intelligence.",
    )
    document = _load_document(db, uploaded.document.id)
    return _analyze_and_persist(db, document, municipality)


def get_civil_pdf_analysis(db: Session, document_id: UUID) -> CivilDrawingAnalysis:
    document = _load_document(db, document_id)
    payload = (document.metadata_json or {}).get(ANALYSIS_METADATA_KEY)
    if not isinstance(payload, dict):
        raise AppError("Drawing analysis not found", status_code=404)
    return CivilDrawingAnalysis.model_validate(payload)


def list_project_civil_pdf_analyses(
    db: Session,
    project_id: UUID,
) -> CivilDrawingAnalysisList:
    if db.get(Project, project_id) is None:
        raise AppError("Project not found", status_code=404)
    rows = db.scalars(
        select(Document)
        .where(
            Document.project_id == project_id,
            Document.category == DocumentCategory.drawing.value,
        )
        .order_by(Document.created_at.desc())
    ).all()
    items = []
    for document in rows:
        payload = (document.metadata_json or {}).get(ANALYSIS_METADATA_KEY)
        if isinstance(payload, dict):
            items.append(CivilDrawingAnalysis.model_validate(payload))
    return CivilDrawingAnalysisList(items=items, total=len(items))


def reanalyze_civil_pdf(
    db: Session,
    document_id: UUID,
    municipality: str | None = None,
) -> CivilDrawingAnalysis:
    document = _load_document(db, document_id)
    if document.category != DocumentCategory.drawing.value:
        raise AppError("Document is not registered as a drawing", status_code=422)
    return _analyze_and_persist(db, document, municipality)


def _analyze_and_persist(
    db: Session,
    document: Document,
    municipality: str | None,
) -> CivilDrawingAnalysis:
    metadata = dict(document.metadata_json or {})
    required_source_fields = ("original_filename", "sha256_hash", "size_bytes")
    if not document.project_id or not document.storage_uri:
        raise AppError("Drawing is missing its project or stored PDF reference.", status_code=422)
    if any(not metadata.get(field) for field in required_source_fields):
        raise AppError("Drawing is missing immutable upload metadata.", status_code=422)

    path = resolve_storage_path(document.storage_uri)
    page_texts: list[tuple[int, str]] = []
    pages: list[DrawingPageExtraction] = []
    warnings = [
        "Automated drawing findings are candidates only and require estimator or engineer verification."
    ]
    extraction_status = "completed"
    page_count = 0

    try:
        reader = PdfReader(path)
        page_count = len(reader.pages)
        for page_number, page in enumerate(reader.pages, start=1):
            extraction_warning = None
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
                extraction_warning = "Text extraction failed for this page."
            if len(text) > MAX_PAGE_TEXT_CHARS:
                text = text[:MAX_PAGE_TEXT_CHARS]
                extraction_warning = "Extracted text was truncated for safe analysis."
            normalized = _normalize_text(text)
            if not normalized and extraction_warning is None:
                extraction_warning = "No embedded text found; OCR may be required."
            page_texts.append((page_number, normalized))
            pages.append(
                DrawingPageExtraction(
                    page_number=page_number,
                    character_count=len(normalized),
                    text_preview=normalized[:500] or None,
                    extraction_warning=extraction_warning,
                )
            )
    except Exception:
        extraction_status = "failed"
        warnings.append("The PDF could not be parsed. Confirm that it is valid and not password protected.")

    total_characters = sum(len(text) for _, text in page_texts)
    if extraction_status != "failed":
        pages_without_text = sum(1 for page in pages if page.character_count == 0)
        if total_characters == 0:
            extraction_status = "ocr_required"
            warnings.append("No embedded PDF text was found; OCR is required before quantity review.")
        elif pages_without_text:
            extraction_status = "partial"
            warnings.append(
                f"{pages_without_text} page(s) had no embedded text and may require OCR."
            )

    quantity_candidates = _extract_quantity_candidates(page_texts)
    constructability_issues = _constructability_issues(page_texts)
    municipal_issues = _municipal_standard_issues(page_texts, municipality)
    report = CivilDrawingAnalysis(
        source=DrawingAnalysisSource(
            document_id=document.id,
            project_id=document.project_id,
            storage_uri=document.storage_uri,
            original_filename=str(metadata["original_filename"]),
            sha256_hash=str(metadata["sha256_hash"]),
            size_bytes=int(metadata["size_bytes"]),
            page_count=page_count,
        ),
        title=document.title,
        municipality=(municipality or "").strip() or None,
        extraction_status=extraction_status,
        analyzed_at=datetime.now(UTC),
        text_character_count=total_characters,
        pages=pages,
        quantity_candidates=quantity_candidates,
        constructability_issues=constructability_issues,
        municipal_standard_issues=municipal_issues,
        warnings=warnings,
    )
    metadata[ANALYSIS_METADATA_KEY] = report.model_dump(mode="json")
    document.metadata_json = metadata
    document.discipline = "civil"
    document.drawing_title = document.title
    db.commit()
    return report


def _load_document(db: Session, document_id: UUID) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise AppError("Document not found", status_code=404)
    return document


def _normalize_text(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.replace("\x00", " ").splitlines()]
    return "\n".join(line for line in lines if line)


def _extract_quantity_candidates(
    page_texts: list[tuple[int, str]],
) -> list[DrawingQuantityCandidate]:
    candidates: list[DrawingQuantityCandidate] = []
    seen: set[tuple[int, float, str, str]] = set()
    for page_number, text in page_texts:
        for line in text.splitlines():
            normalized_line = " ".join(line.split())
            lowered = normalized_line.casefold()
            if not any(keyword in lowered for keyword in CIVIL_QUANTITY_KEYWORDS):
                continue
            for match in MEASURED_QUANTITY_PATTERN.finditer(normalized_line):
                quantity = float(match.group("quantity").replace(",", ""))
                unit = _normalize_unit(match.group("unit"))
                key = (page_number, quantity, unit, lowered)
                if quantity <= 0 or key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    DrawingQuantityCandidate(
                        description=normalized_line[:180],
                        quantity=quantity,
                        unit=unit,
                        page_number=page_number,
                        source_text=normalized_line[:240],
                        confidence=(
                            "high"
                            if any(word in lowered for word in ("quantity", "total", "schedule"))
                            else "medium"
                        ),
                    )
                )
            for match in COUNT_QUANTITY_PATTERN.finditer(normalized_line):
                quantity = float(match.group("quantity"))
                key = (page_number, quantity, "ea", lowered)
                if quantity <= 0 or key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    DrawingQuantityCandidate(
                        description=match.group("asset").title(),
                        quantity=quantity,
                        unit="ea",
                        page_number=page_number,
                        source_text=normalized_line[:240],
                        confidence="low",
                    )
                )
            if len(candidates) >= MAX_QUANTITY_CANDIDATES:
                return candidates
    return candidates


def _normalize_unit(unit: str) -> str:
    normalized = unit.casefold().replace(".", "").replace(" ", "")
    return {
        "m²": "m2",
        "sqm": "m2",
        "m³": "m3",
        "cum": "m3",
        "lm": "m",
        "each": "ea",
    }.get(normalized, normalized)


def _constructability_issues(
    page_texts: list[tuple[int, str]],
) -> list[DrawingIssue]:
    issues: list[DrawingIssue] = []
    seen: set[tuple[str, int]] = set()
    for page_number, text in page_texts:
        for line in text.splitlines():
            for pattern, severity, title, detail in CONSTRUCTABILITY_RULES:
                if not pattern.search(line) or (title, page_number) in seen:
                    continue
                seen.add((title, page_number))
                issues.append(
                    DrawingIssue(
                        issue_type="constructability",
                        severity=severity,
                        title=title,
                        detail=detail,
                        page_number=page_number,
                        evidence=line[:240],
                    )
                )
    return issues


def _municipal_standard_issues(
    page_texts: list[tuple[int, str]],
    municipality: str | None,
) -> list[DrawingIssue]:
    issues: list[DrawingIssue] = []
    all_text = "\n".join(text for _, text in page_texts).casefold()
    reference_lines = [
        (page_number, line)
        for page_number, text in page_texts
        for line in text.splitlines()
        if any(
            keyword in line.casefold()
            for keyword in ("mmcd", "standard drawing", "municipal standard", "city standard")
        )
    ]
    if not all_text:
        issues.append(
            DrawingIssue(
                issue_type="municipal_standard",
                severity="warning",
                title="Standards review blocked by missing text",
                detail="OCR or manual review is required before municipal references can be checked.",
            )
        )
        return issues

    if not reference_lines:
        issues.append(
            DrawingIssue(
                issue_type="municipal_standard",
                severity="warning",
                title="No municipal standard reference detected",
                detail="Confirm the governing municipality, standard drawings, specifications, and applicable edition manually.",
            )
        )
    else:
        page_number, evidence = reference_lines[0]
        issues.append(
            DrawingIssue(
                issue_type="municipal_standard",
                severity="info",
                title="Municipal standard edition requires verification",
                detail="A standards reference was detected, but this build does not validate its edition or compliance.",
                page_number=page_number,
                evidence=evidence[:240],
            )
        )

    expected = (municipality or "").strip().casefold()
    detected = [hint for hint in MUNICIPALITY_HINTS if hint in all_text]
    if expected and expected not in all_text:
        issues.append(
            DrawingIssue(
                issue_type="municipal_standard",
                severity="warning",
                title="Selected municipality not named in extracted text",
                detail=f"Confirm that the drawing set is governed by {municipality} and uses its current requirements.",
            )
        )
    conflicting = [hint.title() for hint in detected if expected and hint not in expected]
    if conflicting:
        issues.append(
            DrawingIssue(
                issue_type="municipal_standard",
                severity="critical",
                title="Possible municipality mismatch",
                detail=f"The set references {', '.join(conflicting)} while the selected municipality is {municipality}.",
            )
        )
    return issues


def analyze_drawing_set(payload: DrawingSetAnalyzeRequest) -> DrawingSetAnalysisResponse:
    sheets = [_analyze_sheet(sheet) for sheet in payload.sheets]
    discipline_counts = Counter(sheet.discipline for sheet in sheets)
    type_counts = Counter(sheet.sheet_type for sheet in sheets)
    revision_counts = Counter(sheet.revision or "unrevised" for sheet in sheets)
    municipality_hints = sorted({hint for sheet in sheets for hint in sheet.municipality_hints})
    warnings = _set_warnings(sheets)
    return DrawingSetAnalysisResponse(
        project_name=payload.project_name,
        municipality=payload.municipality,
        sheet_count=len(sheets),
        disciplines=dict(discipline_counts),
        sheet_types=dict(type_counts),
        revisions=dict(revision_counts),
        municipality_hints=municipality_hints,
        warnings=warnings,
        sheets=sheets,
    )


def _analyze_sheet(sheet: DrawingSheetInput) -> DrawingSheetAnalysis:
    text = _combined_text(sheet)
    keywords = _detected_keywords(text)
    revision = sheet.revision or _detect_revision(text)
    scale = sheet.scale or _detect_scale(text)
    municipality_hints = [hint.title() for hint in MUNICIPALITY_HINTS if hint in text]
    warnings: list[str] = []
    if not sheet.sheet_number:
        warnings.append("Missing sheet number")
    if not revision:
        warnings.append("No revision detected")
    if not scale and _classify_sheet_type(text) in {"civil_plan", "profile", "cross_section"}:
        warnings.append("No scale detected")
    return DrawingSheetAnalysis(
        sheet_number=sheet.sheet_number,
        title=sheet.title,
        filename=sheet.filename,
        discipline=_classify_discipline(text),
        sheet_type=_classify_sheet_type(text),
        revision=revision,
        scale=scale,
        municipality_hints=municipality_hints,
        detected_keywords=keywords,
        warnings=warnings,
    )


def _combined_text(sheet: DrawingSheetInput) -> str:
    return " ".join([sheet.sheet_number or "", sheet.title, sheet.filename or "", sheet.raw_text or ""]).lower()


def _classify_discipline(text: str) -> DrawingDiscipline:
    scores = {name: sum(1 for keyword in keywords if keyword in text) for name, keywords in DISCIPLINE_KEYWORDS.items()}
    best, score = max(scores.items(), key=lambda item: item[1])
    return best if score else "unknown"


def _classify_sheet_type(text: str) -> DrawingSheetType:
    scores = {name: sum(1 for keyword in keywords if keyword in text) for name, keywords in SHEET_TYPE_KEYWORDS.items()}
    best, score = max(scores.items(), key=lambda item: item[1])
    return best if score else "unknown"


def _detected_keywords(text: str) -> list[str]:
    keywords = sorted({keyword for values in [*DISCIPLINE_KEYWORDS.values(), *SHEET_TYPE_KEYWORDS.values()] for keyword in values if keyword in text})
    return keywords[:20]


def _detect_revision(text: str) -> str | None:
    match = re.search(r"(?:rev(?:ision)?\.?\s*)([a-z0-9]+)", text)
    if match:
        return match.group(1).upper()
    match = re.search(r"\bissued for (tender|construction|review)\b", text)
    return match.group(1).title() if match else None


def _detect_scale(text: str) -> str | None:
    match = re.search(r"\b1\s*[:=]\s*\d{2,5}\b", text)
    return match.group(0).replace("=", ":").replace(" ", "") if match else None


def _set_warnings(sheets: list[DrawingSheetAnalysis]) -> list[str]:
    warnings: list[str] = []
    sheet_numbers = [sheet.sheet_number for sheet in sheets if sheet.sheet_number]
    duplicates = sorted(number for number, count in Counter(sheet_numbers).items() if count > 1)
    if duplicates:
        warnings.append(f"Duplicate sheet numbers: {', '.join(duplicates)}")
    if not any(sheet.sheet_type == "cover" for sheet in sheets):
        warnings.append("No cover sheet detected")
    if not any(sheet.sheet_type == "general_notes" for sheet in sheets):
        warnings.append("No general notes sheet detected")
    return warnings
