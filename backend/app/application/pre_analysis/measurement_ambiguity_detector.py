import logging

import torch
import torch.nn.functional as functional
from transformers import AutoModel, AutoTokenizer

from app.domain.pre_analysis import (
    AnalyzedSentence,
    AnalyzedText,
    AnalyzedToken,
    ExtractedEntity,
    MeasurableExpression,
    MeasurementAmbiguity,
)

logger = logging.getLogger(__name__)


#---------- <Summary> ----------
# Summary: Detects measurable expressions and missing measurement details with NLP context.
#
# This detector uses spaCy entities, token context, and sentence structure
# instead of maintaining separate regex pattern JSON files. It treats measurable
# values as useful but checks whether they still miss statistical,
# operating-condition, or measurement-boundary context.
#---------- </Summary> ----------
class MeasurementAmbiguityDetector:

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        statistical_qualifier_threshold: float = 0.18,
    ):
        self.model_name = model_name
        self.statistical_qualifier_threshold = statistical_qualifier_threshold
        self.tokenizer = None
        self.model = None
        self._model_available: bool | None = None

    #---------- <Summary> ----------
    # Summary: Returns measurable expressions and measurement-related ambiguity findings.
    #---------- </Summary> ----------
    def detect(
        self,
        text: str,
        analyzed_text: AnalyzedText,
    ) -> tuple[list[MeasurableExpression], list[MeasurementAmbiguity]]:
        expressions = self._detect_measurable_expressions(analyzed_text)
        ambiguities = self._detect_measurement_ambiguities(
            expressions,
            analyzed_text,
        )

        return expressions, ambiguities

    #---------- <Summary> ----------
    # Summary: Converts spaCy measurable entities into pre-analysis expressions.
    #---------- </Summary> ----------
    def _detect_measurable_expressions(
        self,
        analyzed_text: AnalyzedText,
    ) -> list[MeasurableExpression]:
        expressions: list[MeasurableExpression] = []

        for entity in analyzed_text.entities:
            sentence = self._find_sentence_for_range(
                analyzed_text,
                entity.start_char,
                entity.end_char,
            )
            category = self._category_for_entity(entity, sentence)
            if not category:
                continue

            start_char = self._expanded_start_char(entity, sentence, category)
            expression_text = analyzed_text.original_text[start_char:entity.end_char]

            expressions.append(
                MeasurableExpression(
                    text=expression_text,
                    category=category,
                    start_char=start_char,
                    end_char=entity.end_char,
                )
            )

        expressions.extend(
            self._detect_structural_frequency_expressions(analyzed_text)
        )

        return self._deduplicate(expressions)

    #---------- <Summary> ----------
    # Summary: Maps spaCy entity labels and sentence role to measurement categories.
    #---------- </Summary> ----------
    def _category_for_entity(
        self,
        entity: ExtractedEntity,
        sentence: AnalyzedSentence,
    ) -> str | None:
        if entity.label in {"TIME", "DATE"}:
            matching_tokens = self._tokens_for_entity(entity, sentence)
            if self._is_descriptive_time_modifier(matching_tokens):
                return None

            if self._is_frequency_expression(entity.text) or self._is_frequency_entity(
                matching_tokens,
            ):
                return "frequency"

            return "time"

        if entity.label == "PERCENT":
            return "percentage"

        if entity.label in {"QUANTITY", "MONEY"}:
            return "size"

        if entity.label == "CARDINAL":
            return "count"

        return None

    #---------- <Summary> ----------
    # Summary: Returns NLP tokens covered by one entity span.
    #---------- </Summary> ----------
    def _tokens_for_entity(
        self,
        entity: ExtractedEntity,
        sentence: AnalyzedSentence,
    ) -> list[AnalyzedToken]:
        return [
            token
            for token in sentence.tokens
            if entity.start_char <= token.start_char
            and token.end_char <= entity.end_char
        ]

    #---------- <Summary> ----------
    # Summary: Skips DATE/TIME entities used as noun modifiers instead of targets.
    #---------- </Summary> ----------
    def _is_descriptive_time_modifier(
        self,
        matching_tokens: list[AnalyzedToken],
    ) -> bool:
        if len(matching_tokens) != 1:
            return False

        token = matching_tokens[0]
        return (
            token.dependency in {"amod", "compound"}
            and token.head_pos in {"NOUN", "PROPN"}
        )

    #---------- <Summary> ----------
    # Summary: Detects DATE/TIME entities that modify an action as recurrence.
    #---------- </Summary> ----------
    def _is_frequency_entity(
        self,
        matching_tokens: list[AnalyzedToken],
    ) -> bool:
        return any(
            token.pos == "ADV"
            and token.dependency == "advmod"
            and token.head_pos == "VERB"
            for token in matching_tokens
        )

    #---------- <Summary> ----------
    # Summary: Detects recurring interval wording from a measurable time entity.
    #---------- </Summary> ----------
    def _is_frequency_expression(self, text: str) -> bool:
        normalized_text = text.lower().strip()

        return normalized_text.startswith("every ") or normalized_text.startswith("per ")

    #---------- <Summary> ----------
    # Summary: Finds frequency phrases that spaCy does not expose as entities.
    #---------- </Summary> ----------
    def _detect_structural_frequency_expressions(
        self,
        analyzed_text: AnalyzedText,
    ) -> list[MeasurableExpression]:
        expressions: list[MeasurableExpression] = []

        for sentence in analyzed_text.sentences:
            for index, token in enumerate(sentence.tokens):
                phrase_tokens = None
                if self._is_adverbial_frequency_phrase(sentence.tokens, token):
                    phrase_tokens = self._collect_adverbial_frequency_phrase_tokens(
                        sentence.tokens,
                        token,
                    )
                elif self._is_rate_frequency_phrase(sentence.tokens, index):
                    phrase_tokens = self._collect_prepositional_phrase_tokens(
                        sentence.tokens,
                        index,
                    )

                if not phrase_tokens:
                    continue

                expressions.append(
                    MeasurableExpression(
                        text=analyzed_text.original_text[
                            phrase_tokens[0].start_char:phrase_tokens[-1].end_char
                        ],
                        category="frequency",
                        start_char=phrase_tokens[0].start_char,
                        end_char=phrase_tokens[-1].end_char,
                    )
                )

        return expressions

    #---------- <Summary> ----------
    # Summary: Detects determiner-led adverbial noun phrases such as every day.
    #---------- </Summary> ----------
    def _is_adverbial_frequency_phrase(
        self,
        tokens: list[AnalyzedToken],
        token: AnalyzedToken,
    ) -> bool:
        if token.pos not in {"NOUN", "PROPN"}:
            return False

        if token.dependency != "npadvmod" or token.head_pos != "VERB":
            return False

        phrase_tokens = self._collect_adverbial_frequency_phrase_tokens(tokens, token)

        return any(
            phrase_token.pos == "DET"
            and phrase_token.dependency == "det"
            and phrase_token.head_text == token.text
            for phrase_token in phrase_tokens
        )

    #---------- <Summary> ----------
    # Summary: Collects modifiers syntactically attached to an adverbial frequency noun.
    #---------- </Summary> ----------
    def _collect_adverbial_frequency_phrase_tokens(
        self,
        tokens: list[AnalyzedToken],
        noun_token: AnalyzedToken,
    ) -> list[AnalyzedToken]:
        noun_index = tokens.index(noun_token)
        start_index = noun_index

        while start_index > 0:
            previous_token = tokens[start_index - 1]
            if previous_token.head_text != noun_token.text:
                break

            if previous_token.dependency not in {"det", "amod", "compound", "nummod"}:
                break

            start_index -= 1

        return tokens[start_index:noun_index + 1]

    #---------- <Summary> ----------
    # Summary: Detects rate-style frequency phrases such as per second.
    #---------- </Summary> ----------
    def _is_rate_frequency_phrase(
        self,
        tokens: list[AnalyzedToken],
        index: int,
    ) -> bool:
        token = tokens[index]
        if token.pos != "ADP" or token.text.lower() != "per":
            return False

        return any(
            following_token.pos in {"NOUN", "PROPN"}
            and following_token.dependency == "pobj"
            and following_token.head_text == token.text
            for following_token in tokens[index + 1:index + 4]
        )

    #---------- <Summary> ----------
    # Summary: Collects a compact prepositional phrase starting at one token.
    #---------- </Summary> ----------
    def _collect_prepositional_phrase_tokens(
        self,
        tokens: list[AnalyzedToken],
        start_index: int,
    ) -> list[AnalyzedToken]:
        phrase_tokens = [tokens[start_index]]

        for token in tokens[start_index + 1:]:
            if token.pos in {"DET", "ADJ", "NOUN", "PROPN", "NUM"}:
                phrase_tokens.append(token)
                continue

            break

        if len(phrase_tokens) < 2:
            return []

        return phrase_tokens

    #---------- <Summary> ----------
    # Summary: Includes a nearby preposition such as "within" when spaCy marks only the value.
    #---------- </Summary> ----------
    def _expanded_start_char(
        self,
        entity: ExtractedEntity,
        sentence: AnalyzedSentence,
        category: str,
    ) -> int:
        if category != "time":
            return entity.start_char

        previous_token = None

        for token in sentence.tokens:
            if token.end_char <= entity.start_char:
                previous_token = token
                continue

            break

        if previous_token and previous_token.pos == "ADP":
            return previous_token.start_char

        return entity.start_char

    #---------- <Summary> ----------
    # Summary: Checks each measurable expression for missing requirement dimensions.
    #---------- </Summary> ----------
    def _detect_measurement_ambiguities(
        self,
        expressions: list[MeasurableExpression],
        analyzed_text: AnalyzedText,
    ) -> list[MeasurementAmbiguity]:
        ambiguities: list[MeasurementAmbiguity] = []

        for expression in expressions:
            sentence = self._find_sentence_for_expression(analyzed_text, expression)

            if expression.category == "time":
                ambiguities.extend(
                    self._detect_time_measurement_gaps(
                        expression,
                        sentence,
                        expressions,
                    )
                )

        return ambiguities

    #---------- <Summary> ----------
    # Summary: Finds missing dimensions around time-based measurable expressions.
    #---------- </Summary> ----------
    def _detect_time_measurement_gaps(
        self,
        expression: MeasurableExpression,
        sentence: AnalyzedSentence,
        expressions: list[MeasurableExpression],
    ) -> list[MeasurementAmbiguity]:
        gaps: list[MeasurementAmbiguity] = []

        if not self._is_performance_time_target(expression, sentence):
            return gaps

        if not self._has_statistical_target(sentence, expression, expressions):
            gaps.append(
                self._build_measurement_ambiguity(
                    expression,
                    sentence,
                    missing_dimension="statisticalTarget",
                    reason="The time target does not specify the required statistical interpretation, such as whether the target applies to all cases or a subset of cases.",
                    evidence="No percentage-based target was found in the same measurement sentence.",
                    severity="medium",
                )
            )

        if not self._has_load_condition(sentence, expression, expressions):
            gaps.append(
                self._build_measurement_ambiguity(
                    expression,
                    sentence,
                    missing_dimension="loadCondition",
                    reason="The time target does not specify the load or operating condition under which it must be met.",
                    evidence="No condition phrase was found after the measurable time expression.",
                    severity="medium",
                )
            )

        if not self._has_measurement_boundary(sentence, expression, expressions):
            gaps.append(
                self._build_measurement_ambiguity(
                    expression,
                    sentence,
                    missing_dimension="measurementBoundary",
                    reason="The requirement does not clearly define when the measured operation starts and ends.",
                    evidence="The sentence contains a time target but does not provide enough surrounding measurement context to infer the measured boundary.",
                    severity="high",
                )
            )

        return gaps

    #---------- <Summary> ----------
    # Summary: Uses only reliable extracted percentage expressions as statistical context.
    #---------- </Summary> ----------
    def _has_statistical_target(
        self,
        sentence: AnalyzedSentence,
        expression: MeasurableExpression,
        expressions: list[MeasurableExpression],
    ) -> bool:
        if any(
            expression.category == "percentage"
            and expression.text in sentence.text
            for expression in expressions
        ):
            return True

        return self._has_semantic_statistical_qualifier(sentence, expression)

    #---------- <Summary> ----------
    # Summary: Uses semantic similarity for metric qualifier phrases, not word matching.
    #---------- </Summary> ----------
    def _has_semantic_statistical_qualifier(
        self,
        sentence: AnalyzedSentence,
        expression: MeasurableExpression,
    ) -> bool:
        candidates = self._statistical_qualifier_candidates(sentence, expression)
        if not candidates:
            return False

        if not self._ensure_model_loaded():
            return False

        concept_embedding = self._encode_text(
            "Statistical metric qualifier for a requirement measurement, such as "
            "aggregation, distribution, central tendency, percentile, average, "
            "median, minimum, maximum, or upper/lower bound across many measurements."
        )
        candidate_embeddings = self._encode_texts(candidates)
        similarities = functional.cosine_similarity(
            concept_embedding.expand_as(candidate_embeddings),
            candidate_embeddings,
            dim=1,
        )
        best_score = float(torch.max(similarities).item())

        return best_score >= self.statistical_qualifier_threshold

    #---------- <Summary> ----------
    # Summary: Extracts nearby metric noun phrases before a time target.
    #---------- </Summary> ----------
    def _statistical_qualifier_candidates(
        self,
        sentence: AnalyzedSentence,
        expression: MeasurableExpression,
    ) -> list[str]:
        candidates: list[str] = []

        for token in sentence.tokens:
            if token.end_char > expression.start_char:
                continue

            if token.pos not in {"NOUN", "PROPN"}:
                continue

            if token.dependency not in {"dobj", "pobj", "attr", "nsubj"}:
                continue

            phrase_tokens = self._collect_noun_phrase_tokens(sentence.tokens, token)
            if not self._has_metric_qualifier_structure(phrase_tokens):
                continue

            candidates.append(" ".join(token.text for token in phrase_tokens))

        return list(dict.fromkeys(candidates[-3:]))

    #---------- <Summary> ----------
    # Summary: Collects a compact noun phrase around one noun token.
    #---------- </Summary> ----------
    def _collect_noun_phrase_tokens(
        self,
        tokens: list[AnalyzedToken],
        noun_token: AnalyzedToken,
    ) -> list[AnalyzedToken]:
        noun_index = tokens.index(noun_token)
        start_index = noun_index
        while start_index > 0:
            previous_token = tokens[start_index - 1]
            if previous_token.pos not in {"DET", "ADJ", "NOUN", "PROPN", "NUM"}:
                break

            start_index -= 1

        end_index = noun_index
        while end_index + 1 < len(tokens):
            next_token = tokens[end_index + 1]
            if next_token.pos not in {"ADJ", "NOUN", "PROPN", "NUM"}:
                break

            end_index += 1

        return tokens[start_index:end_index + 1]

    #---------- <Summary> ----------
    # Summary: Checks for a noun phrase structure that can carry metric qualification.
    #---------- </Summary> ----------
    def _has_metric_qualifier_structure(
        self,
        tokens: list[AnalyzedToken],
    ) -> bool:
        return any(token.pos in {"ADJ", "NUM"} for token in tokens[:-1])

    #---------- <Summary> ----------
    # Summary: Loads the local embedding model only when qualifier semantics are needed.
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
                "Measurement semantic qualifier model is not available locally. "
                "Continuing without semantic statistical qualifier support. Error: %s",
                str(error),
            )
            self._model_available = False

        return self._model_available

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
    # Summary: Detects operating context from prepositional phrases after the time target.
    #---------- </Summary> ----------
    def _has_load_condition(
        self,
        sentence: AnalyzedSentence,
        expression: MeasurableExpression,
        expressions: list[MeasurableExpression],
    ) -> bool:
        if any(
            measurable_expression.category == "count"
            and measurable_expression.start_char < expression.start_char
            and measurable_expression.text in sentence.text
            for measurable_expression in expressions
        ):
            return True

        for index, token in enumerate(sentence.tokens):
            if token.start_char < expression.end_char:
                continue

            if self._is_percentage_complement_preposition(token, expressions):
                continue

            if token.pos == "ADP" and self._prepositional_phrase_has_condition_context(
                    sentence,
                    index,
                    expressions,
            ):
                return True

        return False

    #---------- <Summary> ----------
    # Summary: Keeps measurement-gap checks focused on performance-style time targets.
    #---------- </Summary> ----------
    def _is_performance_time_target(
        self,
        expression: MeasurableExpression,
        sentence: AnalyzedSentence,
    ) -> bool:
        leading_token = self._find_first_token_in_expression(sentence, expression)
        if leading_token and leading_token.text.lower() == "after":
            return False

        return True

    #---------- <Summary> ----------
    # Summary: Finds the first sentence token that belongs to a measurable expression.
    #---------- </Summary> ----------
    def _find_first_token_in_expression(
        self,
        sentence: AnalyzedSentence,
        expression: MeasurableExpression,
    ):
        for token in sentence.tokens:
            if token.start_char == expression.start_char:
                return token

        return None

    #---------- <Summary> ----------
    # Summary: Checks whether a post-measurement prepositional phrase gives condition context.
    #---------- </Summary> ----------
    def _prepositional_phrase_has_condition_context(
        self,
        sentence: AnalyzedSentence,
        preposition_index: int,
        expressions: list[MeasurableExpression],
    ) -> bool:
        if any(
            expression.start_char
            <= sentence.tokens[preposition_index].start_char
            < expression.end_char
            for expression in expressions
        ):
            return False

        phrase_tokens = []
        for token in sentence.tokens[preposition_index + 1:]:
            if token.pos in {"DET", "ADJ", "NOUN", "PROPN", "NUM"}:
                phrase_tokens.append(token)
                continue

            if token.pos == "ADP" and phrase_tokens:
                break

            if token.pos == "PUNCT":
                break

            if phrase_tokens:
                break

        if self._tokens_overlap_expression(phrase_tokens, expressions):
            return False

        return any(token.pos in {"NOUN", "PROPN", "NUM"} for token in phrase_tokens)

    #---------- <Summary> ----------
    # Summary: Skips prepositional complements that belong to a percentage expression.
    #---------- </Summary> ----------
    def _is_percentage_complement_preposition(
        self,
        token: AnalyzedToken,
        expressions: list[MeasurableExpression],
    ) -> bool:
        if token.pos != "ADP" or not token.head_text:
            return False

        return any(
            expression.category == "percentage"
            and token.start_char >= expression.end_char
            and token.head_text in expression.text
            for expression in expressions
        )

    #---------- <Summary> ----------
    # Summary: Avoids treating another measurable expression as operating context.
    #---------- </Summary> ----------
    def _tokens_overlap_expression(
        self,
        tokens: list[AnalyzedToken],
        expressions: list[MeasurableExpression],
    ) -> bool:
        return any(
            token.start_char < expression.end_char
            and token.end_char > expression.start_char
            for token in tokens
            for expression in expressions
        )

    #---------- <Summary> ----------
    # Summary: Infers whether the sentence gives enough context for measurement boundaries.
    #---------- </Summary> ----------
    def _has_measurement_boundary(
        self,
        sentence: AnalyzedSentence,
        expression: MeasurableExpression,
        expressions: list[MeasurableExpression],
    ) -> bool:
        if self._has_statistical_target(sentence, expression, expressions) and self._has_load_condition(
            sentence,
            expression,
            expressions,
        ):
            return True

        content_verbs = [
            token
            for token in sentence.tokens
            if token.pos == "VERB"
        ]
        concrete_nouns = [
            token
            for token in sentence.tokens
            if token.pos in {"NOUN", "PROPN"}
            and token.dependency in {"nsubj", "dobj", "pobj", "attr"}
        ]

        measured_objects = [
            token
            for token in sentence.tokens
            if (
                token.start_char < expression.start_char
                and token.pos in {"NOUN", "PROPN"}
                and token.dependency in {"dobj", "pobj", "attr"}
            )
        ]
        if content_verbs and measured_objects:
            return True

        return len(content_verbs) >= 2 and len(concrete_nouns) >= 2

    #---------- <Summary> ----------
    # Summary: Creates a measurement ambiguity for one missing measurement dimension.
    #---------- </Summary> ----------
    def _build_measurement_ambiguity(
        self,
        expression: MeasurableExpression,
        sentence: AnalyzedSentence,
        missing_dimension: str,
        reason: str,
        evidence: str,
        severity: str,
    ) -> MeasurementAmbiguity:
        return MeasurementAmbiguity(
            phrase=expression.text,
            reason=reason,
            severity=severity,
            category="measurement",
            missing_dimension=missing_dimension,
            start_char=expression.start_char,
            end_char=expression.end_char,
            sentence=sentence.text,
            evidence=evidence,
        )

    #---------- <Summary> ----------
    # Summary: Finds the analyzed sentence that contains a measurable expression.
    #---------- </Summary> ----------
    def _find_sentence_for_expression(
        self,
        analyzed_text: AnalyzedText,
        expression: MeasurableExpression,
    ) -> AnalyzedSentence:
        return self._find_sentence_for_range(
            analyzed_text,
            expression.start_char,
            expression.end_char,
        )

    #---------- <Summary> ----------
    # Summary: Finds the analyzed sentence that contains a character range.
    #---------- </Summary> ----------
    def _find_sentence_for_range(
        self,
        analyzed_text: AnalyzedText,
        start_char: int,
        end_char: int,
    ) -> AnalyzedSentence:
        for sentence in analyzed_text.sentences:
            if sentence.start_char <= start_char and end_char <= sentence.end_char:
                return sentence

        return AnalyzedSentence(
            text=analyzed_text.original_text,
            start_char=0,
            end_char=len(analyzed_text.original_text),
            tokens=[],
        )

    #---------- <Summary> ----------
    # Summary: Removes duplicate measurable expressions created from overlapping entities.
    #---------- </Summary> ----------
    def _deduplicate(
        self,
        expressions: list[MeasurableExpression],
    ) -> list[MeasurableExpression]:
        unique: dict[tuple[int, int, str], MeasurableExpression] = {}

        for expression in expressions:
            key = (
                expression.start_char,
                expression.end_char,
                expression.category,
            )
            unique[key] = expression

        return list(unique.values())
