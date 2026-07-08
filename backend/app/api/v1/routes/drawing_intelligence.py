from fastapi import APIRouter

from app.schemas.drawing_intelligence import DrawingSetAnalyzeRequest, DrawingSetAnalysisResponse
from app.services.drawing_intelligence import analyze_drawing_set

router = APIRouter()


@router.post("/analyze", response_model=DrawingSetAnalysisResponse)
def analyze(payload: DrawingSetAnalyzeRequest) -> DrawingSetAnalysisResponse:
    return analyze_drawing_set(payload)
