from fastapi import FastAPI
from app.schemas.analyze_request import AnalyzeRequest
from app.schemas.analyze_response import AnalyzeResponse
from app.services.analysis_service import AnalysisService


app = FastAPI()
analysis_service = AnalysisService()


@app.get("/")
def root():
    return {"message" : "Backend is running."}

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    result = analysis_service.analyze(request.text, request.provider)
    return result