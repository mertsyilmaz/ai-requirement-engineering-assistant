from fastapi import APIRouter, HTTPException

from app.schemas.analyze_request import AnalyzeRequest
from app.schemas.analyze_response import AnalyzeResponse
from app.use_cases.analyze_requirement import AnalyzeRequirementUseCase


router = APIRouter(prefix="/api/v1/requirements", tags=["Requirements"])

analyze_requirement_use_case = AnalyzeRequirementUseCase()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    try:
        result = analyze_requirement_use_case.execute(request.text, request.provider)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")