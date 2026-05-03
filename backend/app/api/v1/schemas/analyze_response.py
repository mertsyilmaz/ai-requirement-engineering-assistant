from pydantic import BaseModel


#---------- <Summary> ----------
# Summary: Ambiguity returned by the LLM.
#---------- </Summary> ----------
class AmbiguityItem(BaseModel):

    phrase: str
    reason: str
    severity: str


#---------- <Summary> ----------
# Summary: Suggestion returned by the LLM for improving part of the requirement.
#---------- </Summary> ----------
class SuggestionItem(BaseModel):

    originalPart: str
    suggestedPart: str
    reason: str


#---------- <Summary> ----------
# Summary: Alternative improved requirement returned by the LLM.
#---------- </Summary> ----------
class ImprovedTextOptionItem(BaseModel):

    label: str
    text: str
    reason: str


#---------- <Summary> ----------
# Summary: Known ambiguity candidate found before validation.
#---------- </Summary> ----------
class PreAnalysisAmbiguityCandidateItem(BaseModel):

    phrase: str
    matchedText: str
    reason: str
    severity: str
    category: str
    validationRule: str | None
    sentence: str


#---------- <Summary> ----------
# Summary: Known ambiguity candidate accepted by pre-analysis.
#---------- </Summary> ----------
class PreAnalysisConfirmedAmbiguityItem(BaseModel):

    phrase: str
    matchedText: str
    reason: str
    severity: str
    category: str
    evidence: str
    sentence: str


#---------- <Summary> ----------
# Summary: Known ambiguity candidate rejected because measurable context clarified it.
#---------- </Summary> ----------
class PreAnalysisRejectedAmbiguityCandidateItem(BaseModel):

    phrase: str
    matchedText: str
    reason: str
    category: str
    rejectionReason: str
    supportingExpression: str | None
    sentence: str


#---------- <Summary> ----------
# Summary: Reference ambiguity found by NLP pre-analysis.
#---------- </Summary> ----------
class PreAnalysisReferenceAmbiguityItem(BaseModel):

    phrase: str
    reason: str
    severity: str
    category: str
    evidence: str
    sentence: str


#---------- <Summary> ----------
# Summary: Measurement ambiguity found around a measurable expression.
#---------- </Summary> ----------
class PreAnalysisMeasurementAmbiguityItem(BaseModel):

    phrase: str
    reason: str
    severity: str
    category: str
    missingDimension: str
    evidence: str
    sentence: str


#---------- <Summary> ----------
# Summary: Measurable expression found in the requirement text.
#---------- </Summary> ----------
class PreAnalysisMeasurableExpressionItem(BaseModel):

    text: str
    category: str
    reason: str


#---------- <Summary> ----------
# Summary: Structured pre-analysis details returned for enhanced analysis versions.
#---------- </Summary> ----------
class PreAnalysisInfo(BaseModel):

    cleanedText: str
    ambiguityCandidates: list[PreAnalysisAmbiguityCandidateItem]
    confirmedAmbiguities: list[PreAnalysisConfirmedAmbiguityItem]
    rejectedAmbiguityCandidates: list[PreAnalysisRejectedAmbiguityCandidateItem]
    referenceAmbiguities: list[PreAnalysisReferenceAmbiguityItem]
    measurementAmbiguities: list[PreAnalysisMeasurementAmbiguityItem]
    measurableExpressions: list[PreAnalysisMeasurableExpressionItem]
    promptGuidance: list[str]


#---------- <Summary> ----------
# Summary: API response returned to the frontend after requirement analysis.
#---------- </Summary> ----------
class AnalyzeResponse(BaseModel):

    originalText: str
    userStory: str
    requirementType: str
    ambiguities: list[AmbiguityItem]
    suggestions: list[SuggestionItem]
    improvedText: str
    improvedTextOptions: list[ImprovedTextOptionItem]
    providerUsed: str
    isFallback: bool
    warnings: list[str]
    errors: list[str]
    promptUsed: str
    preAnalysis: PreAnalysisInfo | None
