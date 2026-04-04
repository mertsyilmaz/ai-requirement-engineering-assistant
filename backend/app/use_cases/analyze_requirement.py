from app.services.analysis_service import AnalysisService


class AnalyzeRequirementUseCase:
    def __init__(self):
        self.analysis_service = AnalysisService()

    def execute(self, text: str, provider: str) -> dict:
        return self.analysis_service.analyze(text, provider)