from app.domain.pre_analysis import (
    AnalyzedSentence,
    AnalyzedText,
    ExtractedEntity,
    MeasurableExpression,
    MeasurementAmbiguity,
)


#---------- <Summary> ----------
# Summary: Detects measurable expressions and missing measurement details with NLP context.
#
# This detector uses spaCy entities, token context, and sentence structure
# instead of maintaining separate regex pattern JSON files. It treats measurable
# values as useful but checks whether they still miss statistical, load, or
# measurement-boundary context.
#---------- </Summary> ----------
class MeasurementAmbiguityDetector:

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
            category = self._category_for_entity(entity)
            if not category:
                continue

            sentence = self._find_sentence_for_range(
                analyzed_text,
                entity.start_char,
                entity.end_char,
            )
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

        return self._deduplicate(expressions)

    #---------- <Summary> ----------
    # Summary: Maps spaCy entity labels to requirement measurement categories.
    #---------- </Summary> ----------
    def _category_for_entity(self, entity: ExtractedEntity) -> str | None:
        if entity.label in {"TIME", "DATE"}:
            if self._is_frequency_expression(entity.text):
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
    # Summary: Detects recurring interval wording from a measurable time entity.
    #---------- </Summary> ----------
    def _is_frequency_expression(self, text: str) -> bool:
        normalized_text = text.lower().strip()

        return normalized_text.startswith("every ") or normalized_text.startswith("per ") or normalized_text in {
            "daily",
            "weekly",
            "monthly",
            "yearly",
            "annually",
            "hourly",
        }

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

        if not self._has_statistical_target(sentence, expressions):
            gaps.append(
                self._build_measurement_ambiguity(
                    expression,
                    sentence,
                    missing_dimension="statisticalTarget",
                    reason="The time target does not specify whether it is a maximum, average, median, or percentile-based target.",
                    evidence="No percentage, ordinal percentile, or statistical qualifier was found in the same measurement sentence.",
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
    # Summary: Uses percentage expressions or percentile wording as statistical context.
    #---------- </Summary> ----------
    def _has_statistical_target(
        self,
        sentence: AnalyzedSentence,
        expressions: list[MeasurableExpression],
    ) -> bool:
        if any(
            expression.category == "percentage"
            and expression.text in sentence.text
            for expression in expressions
        ):
            return True

        return any(
            (
                token.pos in {"NOUN", "PROPN"}
                and "percentile" in token.lemma.lower()
            )
            or token.lemma.lower() in {"average", "median", "maximum", "minimum"}
            for token in sentence.tokens
        )

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

        for token in sentence.tokens:
            if token.start_char < expression.end_char:
                continue

            if token.text.lower() in {"for", "of", "to"}:
                continue

            if token.pos == "ADP" and self._prepositional_phrase_has_load_context(
                    sentence,
                    token.start_char,
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
    # Summary: Checks whether a post-measurement phrase describes operating load.
    #---------- </Summary> ----------
    def _prepositional_phrase_has_load_context(
        self,
        sentence: AnalyzedSentence,
        preposition_start_char: int,
        expressions: list[MeasurableExpression],
    ) -> bool:
        later_tokens = [
            token
            for token in sentence.tokens
            if token.start_char > preposition_start_char
        ]

        if any(
            token.lemma.lower() in {
                "load",
                "traffic",
                "condition",
                "environment",
                "capacity",
            }
            for token in later_tokens
        ):
            return True

        if any(
            token.pos in {"NOUN", "PROPN", "NUM"}
            for token in later_tokens
        ):
            return True

        return any(
            expression.category == "count"
            and expression.start_char > preposition_start_char
            and expression.text in sentence.text
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
        if self._has_statistical_target(sentence, expressions) and self._has_load_condition(
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
