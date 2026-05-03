from fastapi import APIRouter, HTTPException

from app.api.v1.schemas.analyze_request import AnalyzeRequest
from app.api.v1.schemas.analyze_response import AnalyzeResponse
from app.application.services.analysis_service import AnalysisService


router = APIRouter(prefix="/api/v1/requirements", tags=["Requirements"])

analysis_service = AnalysisService()


@router.post("/analyze", response_model=AnalyzeResponse)
#---------- <Summary> ----------
# Summary: Analyzes a requirement with the selected provider and analysis version.
#---------- </Summary> ----------
def analyze(request: AnalyzeRequest):
    try:
        result = analysis_service.analyze(
            request.text,
            request.provider,
            request.analysisVersion,
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
