import json
import logging
from time import perf_counter
from dataclasses import replace

from app.application.pre_analysis.pre_analysis_service import PreAnalysisService
from app.application.pre_analysis.reference_ambiguity_detector import (
    ReferenceAmbiguityDetector,
)
from app.application.pre_analysis.requirement_type_analyzer import (
    RequirementTypeAnalyzer,
)
from app.application.prompts import PromptBuilder
from app.application.text_processing import TextProcessingPipeline
from app.infrastructure.llm.provider_factory import LlmProviderFactory
from app.infrastructure.nlp.spacy_nlp_processor import SpacyNlpProcessor
from app.infrastructure.repositories.json_ambiguity_repository import (
    JsonAmbiguityRepository,
)
from app.infrastructure.repositories.json_requirement_type_repository import (
    JsonRequirementTypeRepository,
)

logger = logging.getLogger(__name__)


#---------- <Summary> ----------
# Summary: Coordinates the complete requirement analysis request.
# 
# It cleans the input text, prepares version-specific analysis context, builds
# the prompt, calls the selected LLM provider, parses the model response, and
# serializes optional pre-analysis data for the API response.
#---------- </Summary> ----------
class AnalysisService:

    def __init__(self):
        self.text_processing_pipeline = TextProcessingPipeline()
        self.prompt_builder = PromptBuilder()
        self.pre_analysis_service: PreAnalysisService | None = None
        self.requirement_type_analyzer: RequirementTypeAnalyzer | None = None

    #---------- <Summary> ----------
    # Summary: Runs one requirement analysis with the selected provider and version.
    #---------- </Summary> ----------
    def analyze(self, text: str, provider: str, analysis_version: str) -> dict:
        analysis_start = perf_counter()
        logger.info(
            "Analyze request started. Provider: %s, Analysis version: %s",
            provider,
            analysis_version,
        )

        prepared_analysis = self._prepare_analysis(text, analysis_version)
        prompt = prepared_analysis["prompt"]
        pre_analysis = prepared_analysis["pre_analysis"]
        pre_analysis_duration_ms = prepared_analysis["pre_analysis_duration_ms"]

        try:
            llm_provider = LlmProviderFactory.create(provider)
            llm_start = perf_counter()
            raw_response = llm_provider.generate(prompt)
            llm_duration_ms = self._elapsed_ms(llm_start)

            logger.info(
                "Analyze request completed successfully. Provider: %s, Analysis version: %s",
                provider,
                analysis_version,
            )

            return self._build_response(
                text=text,
                provider_used=provider,
                raw_response=raw_response,
                prompt=prompt,
                pre_analysis=pre_analysis,
                is_fallback=False,
                warnings=[],
                errors=[],
                pre_analysis_duration_ms=pre_analysis_duration_ms,
                llm_duration_ms=llm_duration_ms,
                total_duration_ms=self._elapsed_ms(analysis_start),
            )

        except Exception as e:
            logger.error("Provider failed. Falling back to mock. Error: %s", str(e))

            mock_provider = LlmProviderFactory.create("mock")
            llm_start = perf_counter()
            raw_response = mock_provider.generate(prompt)
            llm_duration_ms = self._elapsed_ms(llm_start)
            provider_error = str(e)

            return self._build_response(
                text=text,
                provider_used=provider,
                raw_response=raw_response,
                prompt=prompt,
                pre_analysis=pre_analysis,
                is_fallback=True,
                warnings=self._build_fallback_warnings(provider, provider_error),
                errors=[provider_error],
                pre_analysis_duration_ms=pre_analysis_duration_ms,
                llm_duration_ms=llm_duration_ms,
                total_duration_ms=self._elapsed_ms(analysis_start),
            )

    #---------- <Summary> ----------
    # Summary: Prepares cleaned text, optional pre-analysis, and prompt by version.
    #---------- </Summary> ----------
    def _prepare_analysis(self, text: str, analysis_version: str) -> dict:
        normalized_version = analysis_version.lower().strip()
        cleaned_text = self.text_processing_pipeline.process(text)

        if normalized_version == "v1":
            return {
                "prompt": self.prompt_builder.build_v1_prompt(cleaned_text),
                "pre_analysis": None,
                "pre_analysis_duration_ms": 0,
            }

        if normalized_version == "v2":
            pre_analysis_start = perf_counter()
            pre_analysis = self._get_pre_analysis_service().analyze(cleaned_text)
            return {
                "prompt": self.prompt_builder.build_v2_prompt(pre_analysis),
                "pre_analysis": pre_analysis,
                "pre_analysis_duration_ms": self._elapsed_ms(pre_analysis_start),
            }

        if normalized_version == "v3":
            pre_analysis_start = perf_counter()
            pre_analysis = self._get_pre_analysis_service().analyze(cleaned_text)
            requirement_type_analysis = self._get_requirement_type_analyzer().analyze(
                cleaned_text,
                pre_analysis.analyzed_text,
                pre_analysis.measurable_expressions,
                pre_analysis.confirmed_ambiguities,
                pre_analysis.measurement_contexts,
            )
            pre_analysis = replace(
                pre_analysis,
                requirement_type_analysis=requirement_type_analysis,
            )
            return {
                "prompt": self.prompt_builder.build_v3_prompt(pre_analysis),
                "pre_analysis": pre_analysis,
                "pre_analysis_duration_ms": self._elapsed_ms(pre_analysis_start),
            }

        raise ValueError(f"Unsupported analysis version: {analysis_version}")

    #---------- <Summary> ----------
    # Summary: Lazily creates the heavier V2 pre-analysis service when V2 is requested.
    #---------- </Summary> ----------
    def _get_pre_analysis_service(self) -> PreAnalysisService:
        if not self.pre_analysis_service:
            self.pre_analysis_service = PreAnalysisService(
                nlp_processor=SpacyNlpProcessor(),
                ambiguity_repository=JsonAmbiguityRepository(),
                reference_ambiguity_detector=ReferenceAmbiguityDetector(),
            )

        return self.pre_analysis_service

    #---------- <Summary> ----------
    # Summary: Lazily creates the V3 semantic requirement type analyzer.
    #---------- </Summary> ----------
    def _get_requirement_type_analyzer(self) -> RequirementTypeAnalyzer:
        if not self.requirement_type_analyzer:
            self.requirement_type_analyzer = RequirementTypeAnalyzer(
                requirement_type_repository=JsonRequirementTypeRepository(),
            )

        return self.requirement_type_analyzer

    #---------- <Summary> ----------
    # Summary: Builds user-facing fallback warnings from provider failure details.
    #---------- </Summary> ----------
    def _build_fallback_warnings(self, provider: str, provider_error: str) -> list[str]:
        warnings = ["Selected provider failed. Mock response returned."]

        if provider.lower().strip() == "gemini" and self._looks_like_quota_error(
            provider_error,
        ):
            warnings.insert(
                0,
                "Gemini quota or token limit appears to be reached. Mock response returned instead.",
            )

        return warnings

    #---------- <Summary> ----------
    # Summary: Detects common Gemini quota, token, and rate-limit error messages.
    #---------- </Summary> ----------
    def _looks_like_quota_error(self, provider_error: str) -> bool:
        normalized_error = provider_error.lower()
        quota_markers = {
            "429",
            "quota",
            "rate limit",
            "ratelimit",
            "resource exhausted",
            "token limit",
            "too many requests",
            "exceeded",
            "limit exceeded",
        }

        return any(marker in normalized_error for marker in quota_markers)

    #---------- <Summary> ----------
    # Summary: Builds the API response from parsed LLM output and analysis metadata.
    #---------- </Summary> ----------
    def _build_response(
        self,
        text: str,
        provider_used: str,
        raw_response: str,
        prompt: str,
        pre_analysis,
        is_fallback: bool,
        warnings: list[str],
        errors: list[str],
        pre_analysis_duration_ms: int,
        llm_duration_ms: int,
        total_duration_ms: int,
    ) -> dict:
        parsed = self._parse_response(raw_response)

        return {
            "originalText": text,
            "userStory": parsed["userStory"],
            "requirementType": parsed["requirementType"],
            "ambiguities": parsed["ambiguities"],
            "suggestions": parsed["suggestions"],
            "improvedText": parsed["improvedText"],
            "improvedTextOptions": parsed.get("improvedTextOptions", []),
            "providerUsed": provider_used,
            "isFallback": is_fallback,
            "warnings": warnings,
            "errors": errors,
            "timings": {
                "preAnalysisMs": pre_analysis_duration_ms,
                "llmMs": llm_duration_ms,
                "totalMs": total_duration_ms,
            },
            "promptUsed": prompt,
            "preAnalysis": self._serialize_pre_analysis(pre_analysis),
        }

    #---------- <Summary> ----------
    # Summary: Converts a perf_counter start value to rounded milliseconds.
    #---------- </Summary> ----------
    def _elapsed_ms(self, start_time: float) -> int:
        return int(round((perf_counter() - start_time) * 1000))

    #---------- <Summary> ----------
    # Summary: Converts internal pre-analysis models into API response dictionaries.
    #---------- </Summary> ----------
    def _serialize_pre_analysis(self, pre_analysis) -> dict | None:
        if not pre_analysis:
            return None

        return {
            "cleanedText": pre_analysis.cleaned_text,
            "ambiguityCandidates": [
                {
                    "phrase": item.phrase,
                    "matchedText": item.matched_text,
                    "reason": item.reason,
                    "severity": item.severity,
                    "category": item.category,
                    "sentence": item.sentence,
                    "source": item.source,
                    "linguisticRole": item.linguistic_role,
                    "promptGuidance": item.prompt_guidance,
                }
                for item in pre_analysis.ambiguity_candidates
            ],
            "confirmedAmbiguities": [
                {
                    "phrase": item.phrase,
                    "matchedText": item.matched_text,
                    "reason": item.reason,
                    "severity": item.severity,
                    "category": item.category,
                    "evidence": item.evidence,
                    "sentence": item.sentence,
                    "source": item.source,
                    "linguisticRole": item.linguistic_role,
                    "promptGuidance": item.prompt_guidance,
                }
                for item in pre_analysis.confirmed_ambiguities
            ],
            "rejectedAmbiguityCandidates": [
                {
                    "phrase": item.phrase,
                    "matchedText": item.matched_text,
                    "reason": item.reason,
                    "category": item.category,
                    "rejectionReason": item.rejection_reason,
                    "supportingExpression": item.supporting_expression,
                    "sentence": item.sentence,
                    "source": item.source,
                    "linguisticRole": item.linguistic_role,
                    "promptGuidance": item.prompt_guidance,
                }
                for item in pre_analysis.rejected_ambiguity_candidates
            ],
            "referenceAmbiguities": [
                {
                    "phrase": item.phrase,
                    "reason": item.reason,
                    "severity": item.severity,
                    "category": item.category,
                    "evidence": item.evidence,
                    "sentence": item.sentence,
                }
                for item in pre_analysis.reference_ambiguities
            ],
            "measurementAmbiguities": [
                {
                    "phrase": item.phrase,
                    "reason": item.reason,
                    "severity": item.severity,
                    "category": item.category,
                    "missingDimension": item.missing_dimension,
                    "evidence": item.evidence,
                    "sentence": item.sentence,
                }
                for item in pre_analysis.measurement_ambiguities
            ],
            "measurementContexts": [
                {
                    "sentence": item.sentence,
                    "timeTarget": item.time_target,
                    "percentageTarget": item.percentage_target,
                    "percentageSubject": item.percentage_subject,
                    "countTarget": item.count_target,
                    "loadContext": item.load_context,
                    "statisticalTarget": item.statistical_target,
                    "measuredItem": item.measured_item,
                    "nearbyAction": item.nearby_action,
                    "condition": item.condition,
                }
                for item in pre_analysis.measurement_contexts
            ],
            "measurableExpressions": [
                {
                    "text": item.text,
                    "category": item.category,
                }
                for item in pre_analysis.measurable_expressions
            ],
            "semanticFindings": [
                {
                    "phrase": item.phrase,
                    "decision": item.decision,
                    "semanticLabel": item.semantic_label,
                    "interpretation": item.interpretation,
                    "promptGuidance": item.prompt_guidance,
                    "category": item.category,
                    "sentence": item.sentence,
                }
                for item in pre_analysis.semantic_findings
            ],
            "requirementTypeAnalysis": self._serialize_requirement_type_analysis(
                pre_analysis.requirement_type_analysis,
            ),
            "promptGuidance": pre_analysis.prompt_guidance,
        }

    #---------- <Summary> ----------
    # Summary: Converts V3 requirement type analysis into API response data.
    #---------- </Summary> ----------
    def _serialize_requirement_type_analysis(self, requirement_type_analysis):
        if not requirement_type_analysis:
            return None

        return {
            "requirementType": requirement_type_analysis.requirement_type,
            "confidence": requirement_type_analysis.confidence,
            "description": requirement_type_analysis.description,
            "secondaryTypes": [
                {
                    "requirementType": item.requirement_type,
                    "confidence": item.confidence,
                    "description": item.description,
                }
                for item in requirement_type_analysis.secondary_types
            ],
            "observations": [
                {
                    "checkpoint": item.checkpoint,
                    "phrase": item.phrase,
                    "similarityScore": item.similarity_score,
                    "sentence": item.sentence,
                }
                for item in requirement_type_analysis.observations
            ],
        }

    #---------- <Summary> ----------
    # Summary: Parses JSON returned by an LLM, including fenced markdown JSON blocks.
    #---------- </Summary> ----------
    def _parse_response(self, raw_response: str) -> dict:
        cleaned_response = raw_response.strip()

        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response.replace("```json", "", 1).strip()

        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3].strip()

        return json.loads(cleaned_response)
