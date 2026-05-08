from app.application.ports.ambiguity_knowledge_repository import (
    AmbiguityKnowledgeRepositoryPort,
)
from app.application.ports.nlp_processor import NlpProcessorPort
from app.application.pre_analysis.known_ambiguity_detector import (
    KnownAmbiguityDetector,
)
from app.application.pre_analysis.linguistic_ambiguity_detector import (
    LinguisticAmbiguityDetector,
)
from app.application.pre_analysis.measurement_ambiguity_detector import (
    MeasurementAmbiguityDetector,
)
from app.application.pre_analysis.measurement_context_extractor import (
    MeasurementContextExtractor,
)
from app.application.pre_analysis.reference_ambiguity_detector import (
    ReferenceAmbiguityDetector,
)
from app.application.pre_analysis.semantic_similarity_analyzer import (
    SemanticSimilarityAnalyzer,
)
from app.domain.pre_analysis import (
    ConfirmedAmbiguity,
    MeasurementAmbiguity,
    MeasurementContext,
    PreAnalysisResult,
    ReferenceAmbiguity,
    RejectedAmbiguityCandidate,
)


#---------- <Summary> ----------
# Summary: Runs the full LLM pre-analysis flow for enhanced analysis versions.
# 
# The service coordinates NLP analysis, known ambiguity detection, reference
# ambiguity detection, and measurement ambiguity detection. Text cleanup is done
# before this service is called by AnalysisService.
#---------- </Summary> ----------
class PreAnalysisService:

    def __init__(
        self,
        nlp_processor: NlpProcessorPort,
        ambiguity_repository: AmbiguityKnowledgeRepositoryPort,
        reference_ambiguity_detector: ReferenceAmbiguityDetector,
        measurement_ambiguity_detector: MeasurementAmbiguityDetector | None = None,
        measurement_context_extractor: MeasurementContextExtractor | None = None,
        known_ambiguity_detector: KnownAmbiguityDetector | None = None,
        linguistic_ambiguity_detector: LinguisticAmbiguityDetector | None = None,
        semantic_similarity_analyzer: SemanticSimilarityAnalyzer | None = None,
    ):
        self.nlp_processor = nlp_processor
        self.measurement_ambiguity_detector = (
            measurement_ambiguity_detector or MeasurementAmbiguityDetector()
        )
        self.measurement_context_extractor = (
            measurement_context_extractor or MeasurementContextExtractor()
        )
        self.known_ambiguity_detector = (
            known_ambiguity_detector
            or KnownAmbiguityDetector(ambiguity_repository)
        )
        self.linguistic_ambiguity_detector = (
            linguistic_ambiguity_detector or LinguisticAmbiguityDetector()
        )
        self.reference_ambiguity_detector = reference_ambiguity_detector
        self.semantic_similarity_analyzer = (
            semantic_similarity_analyzer
            or SemanticSimilarityAnalyzer(ambiguity_repository)
        )

    #---------- <Summary> ----------
    # Summary: Analyzes cleaned requirement text and returns structured pre-analysis findings.
    #---------- </Summary> ----------
    def analyze(self, cleaned_text: str) -> PreAnalysisResult:
        analyzed_text = self.nlp_processor.analyze(cleaned_text)
        measurable_expressions, measurement_ambiguities = (
            self.measurement_ambiguity_detector.detect(
                cleaned_text,
                analyzed_text,
            )
        )
        measurement_contexts = self.measurement_context_extractor.extract(
            analyzed_text,
            measurable_expressions,
        )
        (
            known_candidates,
            known_confirmed,
            known_rejected,
        ) = self.known_ambiguity_detector.detect(
            cleaned_text,
            analyzed_text,
            measurable_expressions,
        )
        (
            linguistic_candidates,
            linguistic_confirmed,
            linguistic_rejected,
        ) = self.linguistic_ambiguity_detector.detect(
            analyzed_text,
            measurable_expressions,
            known_candidates,
        )

        ambiguity_candidates = known_candidates + linguistic_candidates
        confirmed_ambiguities = known_confirmed + linguistic_confirmed
        rejected_ambiguity_candidates = known_rejected + linguistic_rejected

        (
            confirmed_ambiguities,
            rejected_ambiguity_candidates,
            semantic_findings,
        ) = self.semantic_similarity_analyzer.analyze(
            confirmed_ambiguities,
            rejected_ambiguity_candidates,
        )

        reference_ambiguities = self.reference_ambiguity_detector.detect(
            analyzed_text,
        )

        return PreAnalysisResult(
            original_text=cleaned_text,
            cleaned_text=cleaned_text,
            analyzed_text=analyzed_text,
            measurable_expressions=measurable_expressions,
            ambiguity_candidates=ambiguity_candidates,
            confirmed_ambiguities=confirmed_ambiguities,
            rejected_ambiguity_candidates=rejected_ambiguity_candidates,
            reference_ambiguities=reference_ambiguities,
            measurement_ambiguities=measurement_ambiguities,
            measurement_contexts=measurement_contexts,
            semantic_findings=semantic_findings,
            prompt_guidance=self._build_prompt_guidance(
                confirmed_ambiguities,
                rejected_ambiguity_candidates,
                reference_ambiguities,
                measurement_ambiguities,
                measurement_contexts,
                semantic_findings,
            ),
        )

    #---------- <Summary> ----------
    # Summary: Creates short guidance lines that tell the LLM how to use findings.
    #---------- </Summary> ----------
    def _build_prompt_guidance(
        self,
        confirmed_ambiguities: list[ConfirmedAmbiguity],
        rejected_ambiguity_candidates: list[RejectedAmbiguityCandidate],
        reference_ambiguities: list[ReferenceAmbiguity],
        measurement_ambiguities: list[MeasurementAmbiguity],
        measurement_contexts: list[MeasurementContext],
        semantic_findings,
    ) -> list[str]:
        guidance: list[str] = []

        if confirmed_ambiguities:
            guidance.append(
                "Use the confirmed ambiguities as validated pre-analysis findings."
            )

        if rejected_ambiguity_candidates:
            guidance.append(
                "Do not report rejected ambiguity candidates as ambiguities."
            )

        if reference_ambiguities:
            guidance.append(
                "Consider reference ambiguity findings if they are relevant to the requirement."
            )

        if measurement_ambiguities:
            guidance.append(
                "Use measurement ambiguity findings to clarify measurable targets that still lack scope, load, statistical target, or measurement boundaries."
            )

        if measurement_contexts:
            guidance.append(
                "Use measurement context observations as supporting context, not as mandatory ambiguity findings."
            )

        if semantic_findings:
            guidance.append(
                "Use semantic similarity findings as supporting evidence for NLP-derived ambiguity candidates."
            )

        return guidance
