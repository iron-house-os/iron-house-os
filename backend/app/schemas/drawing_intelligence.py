from typing import Literal

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
