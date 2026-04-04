from fastapi import APIRouter

from app.schemas.analyze_request import AnalyzeRequest
from app.schemas.analyze_response import AnalyzeResponse
from app.use_cases.analyze_requirement import AnalyzeRequirementUseCase


router = APIRouter()

analyze_requirement_use_case = AnalyzeRequirementUseCase()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    result = analyze_requirement_use_case.execute(request.text, request.provider)
    return result