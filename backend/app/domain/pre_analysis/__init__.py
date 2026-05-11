#---------- <Summary> ----------
# Summary: Domain models used by NLP pre-analysis.
#---------- </Summary> ----------

from app.domain.pre_analysis.models import (
    AmbiguityCandidate,
    AmbiguityStatus,
    AmbiguityTerm,
    AnalyzedSentence,
    AnalyzedText,
    AnalyzedToken,
    ConfirmedAmbiguity,
    ExtractedEntity,
    ExtractedNounPhrase,
    FindingSource,
    MeasurementAmbiguity,
    MeasurementContext,
    MeasurableExpression,
    MeasurableExpressionCategory,
    PreAnalysisResult,
    ReferenceAmbiguity,
    RejectedAmbiguityCandidate,
    RequirementTypeAnalysis,
    RequirementTypeDefinition,
    RequirementTypeObservation,
    SecondaryRequirementType,
    SemanticAmbiguityFinding,
    SemanticDecision,
    Severity,
)
