from dataclasses import dataclass, field
from typing import Literal


Severity = Literal["low", "medium", "high"]
MatchType = Literal["phrase", "regex"]
AmbiguityStatus = Literal[
    "candidate",
    "confirmed",
    "rejected",
    "reference",
    "measurement",
]
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
# Summary: Structured NLP analysis result for a cleaned requirement text.
#---------- </Summary> ----------
class AnalyzedText:

    original_text: str
    sentences: list[AnalyzedSentence] = field(default_factory=list)
    noun_phrases: list[ExtractedNounPhrase] = field(default_factory=list)


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Concrete measurable expression found in the requirement text.
#---------- </Summary> ----------
class MeasurableExpression:

    text: str
    category: MeasurableExpressionCategory
    start_char: int
    end_char: int
    reason: str


@dataclass(frozen=True)
#---------- <Summary> ----------
# Summary: Known ambiguity term loaded from the ambiguity knowledge source.
#---------- </Summary> ----------
class AmbiguityTerm:

    phrase: str
    reason: str
    severity: Severity
    category: str
    match_type: MatchType = "phrase"
    validation_rule: str | None = None


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
    match_type: MatchType
    start_char: int
    end_char: int
    sentence: str
    validation_rule: str | None = None
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
# Summary: Configuration loaded from JSON for a rule-based ambiguity detector.
#---------- </Summary> ----------
class ReferenceAmbiguityRuleConfig:

    rule_name: str
    terms: list[str]
    reason: str
    severity: Severity
    category: str


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
    prompt_guidance: list[str] = field(default_factory=list)
