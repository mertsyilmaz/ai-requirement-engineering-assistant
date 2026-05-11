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
    sentence: str
    source: str
    linguisticRole: str | None
    promptGuidance: str | None


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
    source: str
    linguisticRole: str | None
    promptGuidance: str | None


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
    source: str
    linguisticRole: str | None
    promptGuidance: str | None


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
# Summary: Structural measurement context sent as supporting pre-analysis information.
#---------- </Summary> ----------
class PreAnalysisMeasurementContextItem(BaseModel):

    sentence: str
    timeTarget: str | None
    percentageTarget: str | None
    percentageSubject: str | None
    countTarget: str | None
    loadContext: str | None
    statisticalTarget: str | None
    measuredItem: str | None
    nearbyAction: str | None
    condition: str | None


#---------- <Summary> ----------
# Summary: Measurable expression found in the requirement text.
#---------- </Summary> ----------
class PreAnalysisMeasurableExpressionItem(BaseModel):

    text: str
    category: str


#---------- <Summary> ----------
# Summary: Semantic similarity support produced by the NLP pre-analysis layer.
#---------- </Summary> ----------
class PreAnalysisSemanticFindingItem(BaseModel):

    phrase: str
    decision: str
    semanticLabel: str
    interpretation: str
    promptGuidance: str
    category: str
    sentence: str


#---------- <Summary> ----------
# Summary: Type-aware observation found by V3 semantic requirement type analysis.
#---------- </Summary> ----------
class PreAnalysisRequirementTypeObservationItem(BaseModel):

    checkpoint: str
    phrase: str
    similarityScore: float
    sentence: str


#---------- <Summary> ----------
# Summary: Secondary V3 requirement type candidate.
#---------- </Summary> ----------
class PreAnalysisSecondaryRequirementTypeItem(BaseModel):

    requirementType: str
    confidence: float
    description: str


#---------- <Summary> ----------
# Summary: V3 semantic requirement type analysis details.
#---------- </Summary> ----------
class PreAnalysisRequirementTypeAnalysisItem(BaseModel):

    requirementType: str
    confidence: float
    description: str
    secondaryTypes: list[PreAnalysisSecondaryRequirementTypeItem]
    observations: list[PreAnalysisRequirementTypeObservationItem]


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
    measurementContexts: list[PreAnalysisMeasurementContextItem]
    measurableExpressions: list[PreAnalysisMeasurableExpressionItem]
    semanticFindings: list[PreAnalysisSemanticFindingItem]
    requirementTypeAnalysis: PreAnalysisRequirementTypeAnalysisItem | None = None
    promptGuidance: list[str]


#---------- <Summary> ----------
# Summary: Timing metadata for analysis performance visibility.
#---------- </Summary> ----------
class AnalyzeTimingInfo(BaseModel):

    preAnalysisMs: int
    llmMs: int
    totalMs: int


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
    timings: AnalyzeTimingInfo
    promptUsed: str
    preAnalysis: PreAnalysisInfo | None
