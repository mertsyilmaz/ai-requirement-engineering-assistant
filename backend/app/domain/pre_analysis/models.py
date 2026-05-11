from dataclasses import dataclass, field
from typing import Literal


Severity = Literal["low", "medium", "high"]
FindingSource = Literal[
    "knownKnowledge",
    "linguisticAnalysis",
    "semanticValidation",
    "measurementAnalysis",
    "referenceAnalysis",
]
AmbiguityStatus = Literal[
    "candidate",
    "confirmed",
    "rejected",
    "reference",
    "measurement",
    "semantic",
]
SemanticDecision = Literal["confirmed", "excluded", "uncertain"]
MeasurableExpressionCategory = Literal[
    "time",
    "percentage",
    "count",
    "size",
    "frequency",
    "other",
]


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Single NLP token extracted from the requirement text.
#---------- </Summary> ----------
class AnalyzedToken:

    text: str
    lemma: str
    pos: str
    dependency: str
    start_char: int
    end_char: int
    morph: dict[str, str] = field(default_factory=dict)
    head_text: str | None = None
    head_lemma: str | None = None
    head_pos: str | None = None
    head_dependency: str | None = None


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Sentence-level NLP output with its tokens and character boundaries.
#---------- </Summary> ----------
class AnalyzedSentence:

    text: str
    start_char: int
    end_char: int
    tokens: list[AnalyzedToken] = field(default_factory=list)


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Noun phrase extracted by the NLP processor.
#---------- </Summary> ----------
class ExtractedNounPhrase:

    text: str
    root_text: str
    root_dependency: str
    start_char: int
    end_char: int


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Named entity extracted by spaCy NER from the requirement text.
#---------- </Summary> ----------
class ExtractedEntity:

    text: str
    label: str
    start_char: int
    end_char: int


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Structured NLP analysis result for a cleaned requirement text.
#---------- </Summary> ----------
class AnalyzedText:

    original_text: str
    sentences: list[AnalyzedSentence] = field(default_factory=list)
    noun_phrases: list[ExtractedNounPhrase] = field(default_factory=list)
    entities: list[ExtractedEntity] = field(default_factory=list)


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Concrete measurable expression found in the requirement text.
#---------- </Summary> ----------
class MeasurableExpression:

    text: str
    category: MeasurableExpressionCategory
    start_char: int
    end_char: int


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Known ambiguity term loaded from the ambiguity knowledge source.
#---------- </Summary> ----------
class AmbiguityTerm:

    phrase: str
    severity: Severity
    category: str


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Known ambiguity term matched in the requirement before final validation.
#---------- </Summary> ----------
class AmbiguityCandidate:

    phrase: str
    matched_text: str
    reason: str
    severity: Severity
    category: str
    start_char: int
    end_char: int
    sentence: str
    source: FindingSource = "knownKnowledge"
    linguistic_role: str | None = None
    prompt_guidance: str | None = None
    status: AmbiguityStatus = "candidate"


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Candidate ambiguity accepted as a real ambiguity by pre-analysis.
#---------- </Summary> ----------
class ConfirmedAmbiguity:

    phrase: str
    matched_text: str
    reason: str
    severity: Severity
    category: str
    start_char: int
    end_char: int
    sentence: str
    evidence: str
    source: FindingSource = "knownKnowledge"
    linguistic_role: str | None = None
    prompt_guidance: str | None = None
    status: AmbiguityStatus = "confirmed"


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Candidate ambiguity rejected because context makes it sufficiently clear.
#---------- </Summary> ----------
class RejectedAmbiguityCandidate:

    phrase: str
    matched_text: str
    reason: str
    category: str
    start_char: int
    end_char: int
    sentence: str
    rejection_reason: str
    supporting_expression: str | None = None
    source: FindingSource = "knownKnowledge"
    linguistic_role: str | None = None
    prompt_guidance: str | None = None
    status: AmbiguityStatus = "rejected"


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Ambiguity caused by unclear references such as it, this, or that.
#---------- </Summary> ----------
class ReferenceAmbiguity:

    phrase: str
    reason: str
    severity: Severity
    category: str
    start_char: int
    end_char: int
    sentence: str
    evidence: str
    status: AmbiguityStatus = "reference"


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Ambiguity caused by a measurable target missing important context.
#---------- </Summary> ----------
class MeasurementAmbiguity:

    phrase: str
    reason: str
    severity: Severity
    category: str
    missing_dimension: str
    start_char: int
    end_char: int
    sentence: str
    evidence: str
    status: AmbiguityStatus = "measurement"


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Structural measurement context extracted for LLM support, not as a direct ambiguity.
#---------- </Summary> ----------
class MeasurementContext:

    sentence: str
    time_target: str | None = None
    percentage_target: str | None = None
    percentage_subject: str | None = None
    count_target: str | None = None
    load_context: str | None = None
    statistical_target: str | None = None
    measured_item: str | None = None
    nearby_action: str | None = None
    condition: str | None = None


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Semantic interpretation used to support or exclude ambiguity candidates.
#---------- </Summary> ----------
class SemanticAmbiguityFinding:

    phrase: str
    decision: SemanticDecision
    semantic_label: str
    interpretation: str
    prompt_guidance: str
    category: str
    start_char: int
    end_char: int
    sentence: str
    source: FindingSource = "semanticValidation"
    status: AmbiguityStatus = "semantic"


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Requirement type definition loaded from semantic type knowledge.
#---------- </Summary> ----------
class RequirementTypeDefinition:

    requirement_type: str
    description: str
    checkpoints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Type-aware observation found by comparing text spans with type checkpoints.
#---------- </Summary> ----------
class RequirementTypeObservation:

    checkpoint: str
    phrase: str
    similarity_score: float
    sentence: str


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Secondary semantic requirement type candidate used by V3.
#---------- </Summary> ----------
class SecondaryRequirementType:

    requirement_type: str
    confidence: float
    description: str


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Semantic requirement type detection result used by V3.
#---------- </Summary> ----------
class RequirementTypeAnalysis:

    requirement_type: str
    confidence: float
    description: str
    secondary_types: list[SecondaryRequirementType] = field(default_factory=list)
    observations: list[RequirementTypeObservation] = field(default_factory=list)


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Complete output of pre-analysis used to enrich the LLM prompt.
#---------- </Summary> ----------
class PreAnalysisResult:

    original_text: str
    cleaned_text: str
    analyzed_text: AnalyzedText | None = None
    measurable_expressions: list[MeasurableExpression] = field(default_factory=list)
    ambiguity_candidates: list[AmbiguityCandidate] = field(default_factory=list)
    confirmed_ambiguities: list[ConfirmedAmbiguity] = field(default_factory=list)
    rejected_ambiguity_candidates: list[RejectedAmbiguityCandidate] = field(default_factory=list)
    reference_ambiguities: list[ReferenceAmbiguity] = field(default_factory=list)
    measurement_ambiguities: list[MeasurementAmbiguity] = field(default_factory=list)
    measurement_contexts: list[MeasurementContext] = field(default_factory=list)
    semantic_findings: list[SemanticAmbiguityFinding] = field(default_factory=list)
    requirement_type_analysis: RequirementTypeAnalysis | None = None
    prompt_guidance: list[str] = field(default_factory=list)
