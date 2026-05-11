import logging

import torch
import torch.nn.functional as functional
from transformers import AutoModel, AutoTokenizer

from app.domain.pre_analysis import (
    AnalyzedText,
    ConfirmedAmbiguity,
    MeasurableExpression,
    MeasurementContext,
    RequirementTypeAnalysis,
    RequirementTypeDefinition,
    RequirementTypeObservation,
    SecondaryRequirementType,
)
from app.infrastructure.repositories.json_requirement_type_repository import (
    JsonRequirementTypeRepository,
)

logger = logging.getLogger(__name__)


#---------- <Summary> ----------
# Summary: Detects V3 requirement type using semantic similarity, not keyword matching.
#
# The analyzer compares the cleaned requirement with type descriptions and uses
# checkpoint strings only as optional semantic anchors for extra observations.
# Missing checkpoint observations are not reported.
#---------- </Summary> ----------
class RequirementTypeAnalyzer:

    def __init__(
        self,
        requirement_type_repository: JsonRequirementTypeRepository,
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        observation_threshold: float = 0.55,
        secondary_type_threshold: float = 0.25,
    ):
        self.requirement_type_repository = requirement_type_repository
        self.model_name = model_name
        self.observation_threshold = observation_threshold
        self.secondary_type_threshold = secondary_type_threshold
        self.tokenizer = None
        self.model = None
        self._type_definitions: list[RequirementTypeDefinition] | None = None
        self._model_available: bool | None = None

    #---------- <Summary> ----------
    # Summary: Returns detected requirement type and optional type-aware observations.
    #---------- </Summary> ----------
    def analyze(
        self,
        cleaned_text: str,
        analyzed_text: AnalyzedText,
        measurable_expressions: list[MeasurableExpression],
        confirmed_ambiguities: list[ConfirmedAmbiguity] | None = None,
        measurement_contexts: list[MeasurementContext] | None = None,
    ) -> RequirementTypeAnalysis | None:
        if not self._ensure_model_loaded():
            return None

        type_definitions = self._get_type_definitions()
        if not type_definitions:
            return None

        detected_type = self._detect_type(
            cleaned_text,
            analyzed_text,
            measurable_expressions,
            confirmed_ambiguities or [],
            measurement_contexts or [],
            type_definitions,
        )
        observations = self._detect_observations(
            detected_type,
            analyzed_text,
            measurable_expressions,
        )

        return RequirementTypeAnalysis(
            requirement_type=detected_type.requirement_type,
            confidence=detected_type.confidence,
            description=detected_type.description,
            secondary_types=detected_type.secondary_types,
            observations=observations,
        )

    #---------- <Summary> ----------
    # Summary: Loads the local embedding model once for type analysis.
    #---------- </Summary> ----------
    def _ensure_model_loaded(self) -> bool:
        if self._model_available is not None:
            return self._model_available

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                local_files_only=True,
            )
            self.model = AutoModel.from_pretrained(
                self.model_name,
                local_files_only=True,
            )
            self.model.eval()
            self._model_available = True
        except Exception as error:
            logger.warning(
                "Requirement type model is not available locally. "
                "V3 will continue without type analysis. Error: %s",
                str(error),
            )
            self._model_available = False

        return self._model_available

    #---------- <Summary> ----------
    # Summary: Loads type definitions from the repository once.
    #---------- </Summary> ----------
    def _get_type_definitions(self) -> list[RequirementTypeDefinition]:
        if self._type_definitions is None:
            self._type_definitions = self.requirement_type_repository.get_all_types()

        return self._type_definitions

    #---------- <Summary> ----------
    # Summary: Chooses the closest requirement type description.
    #---------- </Summary> ----------
    def _detect_type(
        self,
        cleaned_text: str,
        analyzed_text: AnalyzedText,
        measurable_expressions: list[MeasurableExpression],
        confirmed_ambiguities: list[ConfirmedAmbiguity],
        measurement_contexts: list[MeasurementContext],
        type_definitions: list[RequirementTypeDefinition],
    ):
        requirement_embedding = self._encode_text(
            f"Requirement: {cleaned_text}"
        )
        type_embeddings = self._encode_texts(
            [
                self._build_type_text(type_definition)
                for type_definition in type_definitions
            ]
        )
        similarities = functional.cosine_similarity(
            requirement_embedding.expand_as(type_embeddings),
            type_embeddings,
            dim=1,
        )
        similarities = self._apply_v2_context_support(
            similarities,
            type_definitions,
            confirmed_ambiguities,
            measurement_contexts,
            analyzed_text,
        )
        best_index = int(torch.argmax(similarities).item())
        best_score = float(similarities[best_index].item())
        second_score = self._get_second_score(similarities)
        selected_type = type_definitions[best_index]

        if self._should_prefer_functional_structure(
            selected_type.requirement_type,
            best_score,
            analyzed_text,
            confirmed_ambiguities,
            measurement_contexts,
        ):
            fallback_type = self._get_type_by_name(type_definitions, "Functional")
            if fallback_type is not None:
                selected_type = fallback_type
                best_score = max(best_score, 0.25)

        if best_score < 0.25 and best_score - second_score < 0.03:
            fallback_type = self._infer_structural_fallback(
                analyzed_text,
                measurable_expressions,
                type_definitions,
            )
            if fallback_type is not None:
                selected_type = fallback_type
                best_score = max(best_score, 0.25)

        return _ScoredRequirementType(
            requirement_type=selected_type.requirement_type,
            description=selected_type.description,
            checkpoints=selected_type.checkpoints,
            confidence=best_score,
            secondary_types=self._detect_secondary_types(
                similarities,
                type_definitions,
                selected_type.requirement_type,
                confirmed_ambiguities,
                measurement_contexts,
            ),
        )

    #---------- <Summary> ----------
    # Summary: Returns the second highest semantic type score.
    #---------- </Summary> ----------
    def _get_second_score(self, similarities) -> float:
        top_scores = torch.topk(similarities, k=min(2, similarities.shape[0])).values
        return float(top_scores[1].item()) if len(top_scores) > 1 else 0.0

    #---------- <Summary> ----------
    # Summary: Keeps V2-supported alternative requirement types as secondary candidates.
    #---------- </Summary> ----------
    def _detect_secondary_types(
        self,
        similarities,
        type_definitions: list[RequirementTypeDefinition],
        primary_type: str,
        confirmed_ambiguities: list[ConfirmedAmbiguity],
        measurement_contexts: list[MeasurementContext],
    ) -> list[SecondaryRequirementType]:
        type_index = {
            type_definition.requirement_type: index
            for index, type_definition in enumerate(type_definitions)
        }
        secondary_types: list[SecondaryRequirementType] = []

        def add_secondary_type(requirement_type: str) -> None:
            if requirement_type == primary_type:
                return

            if requirement_type not in type_index:
                return

            if any(
                item.requirement_type == requirement_type
                for item in secondary_types
            ):
                return

            index = type_index[requirement_type]
            score = float(similarities[index].item())
            if score < self.secondary_type_threshold:
                return

            type_definition = type_definitions[index]
            secondary_types.append(
                SecondaryRequirementType(
                    requirement_type=type_definition.requirement_type,
                    confidence=score,
                    description=type_definition.description,
                )
            )

        for ambiguity in confirmed_ambiguities:
            supported_type = self._map_ambiguity_category_to_type(
                ambiguity.category
            )
            if supported_type:
                add_secondary_type(supported_type)

            if len(secondary_types) >= 2:
                return secondary_types

        if self._has_performance_measurement_context(measurement_contexts):
            add_secondary_type("Performance Efficiency")

        return secondary_types

    #---------- <Summary> ----------
    # Summary: Checks whether V2 context has concrete performance-specific evidence.
    #---------- </Summary> ----------
    def _has_performance_measurement_context(
        self,
        measurement_contexts: list[MeasurementContext],
    ) -> bool:
        return any(
            self._is_concrete_performance_time(context.time_target)
            or context.load_context
            for context in measurement_contexts
        )

    #---------- <Summary> ----------
    # Summary: Returns a type definition by name.
    #---------- </Summary> ----------
    def _get_type_by_name(
        self,
        type_definitions: list[RequirementTypeDefinition],
        requirement_type: str,
    ) -> RequirementTypeDefinition | None:
        for type_definition in type_definitions:
            if type_definition.requirement_type == requirement_type:
                return type_definition

        return None

    #---------- <Summary> ----------
    # Summary: Keeps domain-object actions from being over-classified as performance.
    #---------- </Summary> ----------
    def _should_prefer_functional_structure(
        self,
        selected_requirement_type: str,
        confidence: float,
        analyzed_text: AnalyzedText,
        confirmed_ambiguities: list[ConfirmedAmbiguity],
        measurement_contexts: list[MeasurementContext],
    ) -> bool:
        if selected_requirement_type != "Performance Efficiency":
            return False

        if confidence >= 0.30 or measurement_contexts:
            return False

        has_performance_confirmation = any(
            self._map_ambiguity_category_to_type(ambiguity.category)
            == "Performance Efficiency"
            for ambiguity in confirmed_ambiguities
        )
        if has_performance_confirmation:
            return False

        return self._has_concrete_behavior(analyzed_text)

    #---------- <Summary> ----------
    # Summary: Uses already extracted V2 findings as support for type scoring.
    #---------- </Summary> ----------
    def _apply_v2_context_support(
        self,
        similarities,
        type_definitions: list[RequirementTypeDefinition],
        confirmed_ambiguities: list[ConfirmedAmbiguity],
        measurement_contexts: list[MeasurementContext],
        analyzed_text: AnalyzedText,
    ):
        supported_scores = similarities.clone()
        type_index = {
            type_definition.requirement_type: index
            for index, type_definition in enumerate(type_definitions)
        }

        best_index = int(torch.argmax(similarities).item())
        best_score = float(similarities[best_index].item())

        for ambiguity in confirmed_ambiguities:
            supported_type = self._map_ambiguity_category_to_type(
                ambiguity.category
            )
            if supported_type not in type_index:
                continue

            supported_index = type_index[supported_type]
            supported_score = float(similarities[supported_index].item())
            if best_score - supported_score <= 0.08:
                supported_scores[supported_index] += 0.08

        performance_contexts = [
            context
            for context in measurement_contexts
            if (
                self._is_concrete_performance_time(context.time_target)
                or context.load_context
            )
        ]

        if performance_contexts and "Performance Efficiency" in type_index:
            performance_index = type_index["Performance Efficiency"]
            best_type = type_definitions[best_index].requirement_type
            performance_score = float(similarities[performance_index].item())

            if (
                best_type not in {"Reliability", "Security", "Safety"}
                and best_score - performance_score <= 0.08
            ):
                supported_scores[performance_index] += 0.08

        return supported_scores

    #---------- <Summary> ----------
    # Summary: Keeps vague relative time phrases from forcing performance type support.
    #---------- </Summary> ----------
    def _is_concrete_performance_time(self, time_target: str | None) -> bool:
        if not time_target:
            return False

        return any(character.isdigit() for character in time_target)

    #---------- <Summary> ----------
    # Summary: Maps ambiguity categories to requirement types when the concepts match.
    #---------- </Summary> ----------
    def _map_ambiguity_category_to_type(self, category: str) -> str | None:
        category_to_type = {
            "performance": "Performance Efficiency",
            "scalability": "Performance Efficiency",
            "time": "Performance Efficiency",
            "frequency": "Performance Efficiency",
            "usability": "Interaction Capability",
            "reliability": "Reliability",
            "availability": "Reliability",
            "security": "Security",
            "safety": "Safety",
            "maintainability": "Maintainability",
        }

        return category_to_type.get(category)

    #---------- <Summary> ----------
    # Summary: Falls back to broad NLP structure when semantic confidence is weak.
    #---------- </Summary> ----------
    def _infer_structural_fallback(
        self,
        analyzed_text: AnalyzedText,
        measurable_expressions: list[MeasurableExpression],
        type_definitions: list[RequirementTypeDefinition],
    ) -> RequirementTypeDefinition | None:
        type_by_name = {
            type_definition.requirement_type: type_definition
            for type_definition in type_definitions
        }

        if (
            self._has_concrete_performance_measurement(measurable_expressions)
            and "Performance Efficiency" in type_by_name
        ):
            return type_by_name["Performance Efficiency"]

        if self._has_concrete_behavior(analyzed_text):
            return type_by_name.get("Functional")

        return None

    #---------- <Summary> ----------
    # Summary: Checks whether extracted measurements are concrete enough for performance fallback.
    #---------- </Summary> ----------
    def _has_concrete_performance_measurement(
        self,
        measurable_expressions: list[MeasurableExpression],
    ) -> bool:
        return any(
            expression.category in {"percentage", "size"}
            or (
                expression.category == "time"
                and self._is_concrete_performance_time(expression.text)
            )
            for expression in measurable_expressions
        )

    #---------- <Summary> ----------
    # Summary: Detects broad actor/action/object structure without keyword lists.
    #---------- </Summary> ----------
    def _has_concrete_behavior(self, analyzed_text: AnalyzedText) -> bool:
        for sentence in analyzed_text.sentences:
            has_domain_object = any(
                token.pos in {"NOUN", "PROPN", "PRON"}
                for token in sentence.tokens
            )
            has_action = any(
                token.pos == "VERB" and token.lemma.lower() not in {"be", "have"}
                for token in sentence.tokens
            )

            if has_domain_object and has_action:
                return True

        return False

    #---------- <Summary> ----------
    # Summary: Finds optional text spans that semantically support type checkpoints.
    #---------- </Summary> ----------
    def _detect_observations(
        self,
        detected_type,
        analyzed_text: AnalyzedText,
        measurable_expressions: list[MeasurableExpression],
    ) -> list[RequirementTypeObservation]:
        candidates = self._extract_candidate_phrases(
            analyzed_text,
            measurable_expressions,
        )
        if not detected_type.checkpoints or not candidates:
            return []

        candidate_embeddings = self._encode_texts(
            [self._build_candidate_text(candidate) for candidate in candidates]
        )
        checkpoint_embeddings = self._encode_texts(
            [
                self._build_checkpoint_text(detected_type, checkpoint)
                for checkpoint in detected_type.checkpoints
            ]
        )
        observations: list[RequirementTypeObservation] = []
        used_phrases: set[str] = set()

        for checkpoint_index, checkpoint in enumerate(detected_type.checkpoints):
            similarities = functional.cosine_similarity(
                checkpoint_embeddings[checkpoint_index].expand_as(candidate_embeddings),
                candidate_embeddings,
                dim=1,
            )
            best_index = int(torch.argmax(similarities).item())
            best_score = float(similarities[best_index].item())

            if best_score < self.observation_threshold:
                continue

            candidate = candidates[best_index]
            if candidate["phrase"].lower() in used_phrases:
                continue

            used_phrases.add(candidate["phrase"].lower())
            observations.append(
                RequirementTypeObservation(
                    checkpoint=checkpoint,
                    phrase=candidate["phrase"],
                    similarity_score=best_score,
                    sentence=candidate["sentence"],
                )
            )

        return observations

    #---------- <Summary> ----------
    # Summary: Extracts reusable text spans from NLP output and measurable expressions.
    #---------- </Summary> ----------
    def _extract_candidate_phrases(
        self,
        analyzed_text: AnalyzedText,
        measurable_expressions: list[MeasurableExpression],
    ) -> list[dict[str, str]]:
        candidates: list[dict[str, str]] = []

        for noun_phrase in analyzed_text.noun_phrases:
            candidates.append(
                {
                    "phrase": noun_phrase.text,
                    "sentence": self._find_sentence_for_range(
                        analyzed_text,
                        noun_phrase.start_char,
                        noun_phrase.end_char,
                    ),
                    "role": "noun phrase",
                }
            )

        for entity in analyzed_text.entities:
            candidates.append(
                {
                    "phrase": entity.text,
                    "sentence": self._find_sentence_for_range(
                        analyzed_text,
                        entity.start_char,
                        entity.end_char,
                    ),
                    "role": f"named entity {entity.label}",
                }
            )

        for expression in measurable_expressions:
            candidates.append(
                {
                    "phrase": expression.text,
                    "sentence": self._find_sentence_for_range(
                        analyzed_text,
                        expression.start_char,
                        expression.end_char,
                    ),
                    "role": f"measurable {expression.category}",
                }
            )

        for sentence in analyzed_text.sentences:
            for token in sentence.tokens:
                if token.pos not in {"VERB", "NOUN", "PROPN"}:
                    continue

                if len(token.text.strip()) < 3:
                    continue

                candidates.append(
                    {
                        "phrase": token.text,
                        "sentence": sentence.text,
                        "role": f"{token.pos} {token.dependency}",
                    }
                )

        return self._deduplicate_candidates(candidates)

    #---------- <Summary> ----------
    # Summary: Removes duplicate candidate phrases while keeping their first context.
    #---------- </Summary> ----------
    def _deduplicate_candidates(
        self,
        candidates: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        unique: dict[str, dict[str, str]] = {}

        for candidate in candidates:
            key = candidate["phrase"].lower()
            if key not in unique:
                unique[key] = candidate

        return list(unique.values())

    #---------- <Summary> ----------
    # Summary: Finds the sentence text that contains a character range.
    #---------- </Summary> ----------
    def _find_sentence_for_range(
        self,
        analyzed_text: AnalyzedText,
        start_char: int,
        end_char: int,
    ) -> str:
        for sentence in analyzed_text.sentences:
            if sentence.start_char <= start_char and end_char <= sentence.end_char:
                return sentence.text

        return analyzed_text.original_text

    #---------- <Summary> ----------
    # Summary: Builds semantic text for one requirement type.
    #---------- </Summary> ----------
    def _build_type_text(self, type_definition: RequirementTypeDefinition) -> str:
        return (
            f"Requirement type: {type_definition.requirement_type}\n"
            f"Description: {type_definition.description}\n"
            f"Typical checkpoints: {', '.join(type_definition.checkpoints)}"
        )

    #---------- <Summary> ----------
    # Summary: Builds semantic text for one type checkpoint.
    #---------- </Summary> ----------
    def _build_checkpoint_text(self, detected_type, checkpoint: str) -> str:
        return (
            f"Requirement type: {detected_type.requirement_type}\n"
            f"Checkpoint: {checkpoint}"
        )

    #---------- <Summary> ----------
    # Summary: Builds semantic text for one extracted candidate phrase.
    #---------- </Summary> ----------
    def _build_candidate_text(self, candidate: dict[str, str]) -> str:
        return (
            f"Requirement text span: {candidate['phrase']}\n"
            f"Role: {candidate['role']}\n"
            f"Sentence: {candidate['sentence']}"
        )

    #---------- <Summary> ----------
    # Summary: Encodes one text into a normalized embedding vector.
    #---------- </Summary> ----------
    def _encode_text(self, text: str):
        return self._encode_texts([text])

    #---------- <Summary> ----------
    # Summary: Encodes multiple texts using mean pooling over transformer tokens.
    #---------- </Summary> ----------
    def _encode_texts(self, texts: list[str]):
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )

        with torch.no_grad():
            model_output = self.model(**encoded)

        token_embeddings = model_output.last_hidden_state
        attention_mask = encoded["attention_mask"].unsqueeze(-1)
        masked_embeddings = token_embeddings * attention_mask
        summed_embeddings = masked_embeddings.sum(dim=1)
        token_counts = attention_mask.sum(dim=1).clamp(min=1)
        embeddings = summed_embeddings / token_counts

        return functional.normalize(embeddings, p=2, dim=1)


#---------- <Summary> ----------
# Summary: Internal scored type object used while building the final analysis model.
#---------- </Summary> ----------
class _ScoredRequirementType:

    def __init__(
        self,
        requirement_type: str,
        description: str,
        checkpoints: list[str],
        confidence: float,
        secondary_types: list[SecondaryRequirementType],
    ):
        self.requirement_type = requirement_type
        self.description = description
        self.checkpoints = checkpoints
        self.confidence = confidence
        self.secondary_types = secondary_types
