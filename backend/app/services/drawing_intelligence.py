from collections import Counter
import re

from app.schemas.drawing_intelligence import (
    DrawingDiscipline,
    DrawingSetAnalyzeRequest,
    DrawingSetAnalysisResponse,
    DrawingSheetAnalysis,
    DrawingSheetInput,
    DrawingSheetType,
)

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
