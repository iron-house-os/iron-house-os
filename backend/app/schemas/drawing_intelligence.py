from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

DrawingDiscipline = Literal["civil", "traffic", "structural", "electrical", "landscape", "environmental", "unknown"]
DrawingSheetType = Literal[
    "cover",
    "general_notes",
    "civil_plan",
    "profile",
    "cross_section",
    "traffic_control",
    "esc",
    "landscape",
    "details",
    "specification",
    "addenda",
    "unknown",
]


class DrawingSheetInput(BaseModel):
    sheet_number: str | None = None
    title: str
    filename: str | None = None
    revision: str | None = None
    scale: str | None = None
    raw_text: str | None = None


class DrawingSetAnalyzeRequest(BaseModel):
    project_name: str | None = None
    municipality: str | None = None
    sheets: list[DrawingSheetInput] = Field(default_factory=list)


class DrawingSheetAnalysis(BaseModel):
    sheet_number: str | None
    title: str
    filename: str | None
    discipline: DrawingDiscipline
    sheet_type: DrawingSheetType
    revision: str | None
    scale: str | None
    municipality_hints: list[str]
    detected_keywords: list[str]
    warnings: list[str]


class DrawingSetAnalysisResponse(BaseModel):
    project_name: str | None
    municipality: str | None
    sheet_count: int
    disciplines: dict[str, int]
    sheet_types: dict[str, int]
    revisions: dict[str, int]
    municipality_hints: list[str]
    warnings: list[str]
    sheets: list[DrawingSheetAnalysis]


DrawingExtractionStatus = Literal["completed", "partial", "ocr_required", "failed"]
DrawingIssueSeverity = Literal["info", "warning", "critical"]
DrawingIssueType = Literal["constructability", "municipal_standard"]
QuantityConfidence = Literal["low", "medium", "high"]


class DrawingPageExtraction(BaseModel):
    page_number: int
    character_count: int
    text_preview: str | None = None
    extraction_warning: str | None = None


class DrawingQuantityCandidate(BaseModel):
    description: str
    quantity: float
    unit: str
    page_number: int
    source_text: str
    confidence: QuantityConfidence
    requires_verification: Literal[True] = True


class DrawingIssue(BaseModel):
    issue_type: DrawingIssueType
    severity: DrawingIssueSeverity
    title: str
    detail: str
    page_number: int | None = None
    evidence: str | None = None
    requires_review: Literal[True] = True


class DrawingAnalysisSource(BaseModel):
    document_id: UUID
    project_id: UUID
    storage_uri: str
    original_filename: str
    sha256_hash: str
    size_bytes: int
    page_count: int


class CivilDrawingAnalysis(BaseModel):
    analysis_version: Literal["build-206-v1"] = "build-206-v1"
    source: DrawingAnalysisSource
    title: str
    municipality: str | None = None
    extraction_status: DrawingExtractionStatus
    analyzed_at: datetime
    text_character_count: int
    pages: list[DrawingPageExtraction] = Field(default_factory=list)
    quantity_candidates: list[DrawingQuantityCandidate] = Field(default_factory=list)
    constructability_issues: list[DrawingIssue] = Field(default_factory=list)
    municipal_standard_issues: list[DrawingIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CivilDrawingAnalysisList(BaseModel):
    items: list[CivilDrawingAnalysis] = Field(default_factory=list)
    total: int


class CivilDrawingReanalyzeRequest(BaseModel):
    municipality: str | None = None
