from app.application.ports.ambiguity_knowledge_repository import (
    AmbiguityKnowledgeRepositoryPort,
)
from app.application.ports.nlp_processor import NlpProcessorPort
from app.application.pre_analysis.known_ambiguity_detector import (
    KnownAmbiguityDetector,
)
from app.application.pre_analysis.measurement_ambiguity_detector import (
    MeasurementAmbiguityDetector,
)
from app.application.pre_analysis.reference_ambiguity_detector import (
    ReferenceAmbiguityDetector,
)
from app.domain.pre_analysis import (
    ConfirmedAmbiguity,
    MeasurementAmbiguity,
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
        known_ambiguity_detector: KnownAmbiguityDetector | None = None,
    ):
        self.nlp_processor = nlp_processor
        self.measurement_ambiguity_detector = (
            measurement_ambiguity_detector or MeasurementAmbiguityDetector()
        )
        self.known_ambiguity_detector = (
            known_ambiguity_detector
            or KnownAmbiguityDetector(ambiguity_repository)
        )
        self.reference_ambiguity_detector = reference_ambiguity_detector

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
        (
            ambiguity_candidates,
            confirmed_ambiguities,
            rejected_ambiguity_candidates,
        ) = self.known_ambiguity_detector.detect(
            cleaned_text,
            analyzed_text,
            measurable_expressions,
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
            prompt_guidance=self._build_prompt_guidance(
                confirmed_ambiguities,
                rejected_ambiguity_candidates,
                reference_ambiguities,
                measurement_ambiguities,
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

        return guidance
