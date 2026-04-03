from pydantic import BaseModel


class AmbiguityItem(BaseModel):
    phrase: str
    reason: str
    severity: str


class SuggestionItem(BaseModel):
    originalPart: str
    suggestedPart: str
    reason: str


class AnalyzeResponse(BaseModel):
    originalText: str
    userStory: str
    requirementType: str
    ambiguities: list[AmbiguityItem]
    suggestions: list[SuggestionItem]
    improvedText: str