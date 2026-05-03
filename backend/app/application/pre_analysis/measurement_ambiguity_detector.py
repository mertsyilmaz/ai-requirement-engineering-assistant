import re

from app.domain.pre_analysis import (
    AnalyzedSentence,
    AnalyzedText,
    MeasurableExpression,
    MeasurementAmbiguity,
)


#---------- <Summary> ----------
# Summary: Detects measurable expressions and missing measurement details.
#
# A measurable expression can still be ambiguous when it lacks context such as
# load condition, statistical target, measurement boundary, or application scope.
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
        expressions = self._detect_measurable_expressions(text)
        ambiguities = self._detect_measurement_ambiguities(
            expressions,
            analyzed_text,
        )

        return expressions, ambiguities

    #---------- <Summary> ----------
    # Summary: Finds concrete time, count, percentage, frequency, and size expressions.
    #---------- </Summary> ----------
    def _detect_measurable_expressions(self, text: str) -> list[MeasurableExpression]:
        expressions: list[MeasurableExpression] = []

        for pattern, category, reason in self._patterns():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                expressions.append(
                    MeasurableExpression(
                        text=match.group(0),
                        category=category,
                        start_char=match.start(),
                        end_char=match.end(),
                        reason=reason,
                    )
                )

        return self._remove_overlapping(self._deduplicate(expressions))

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
                    self._detect_time_measurement_gaps(expression, sentence)
                )

            if expression.category in {"count", "percentage"}:
                ambiguities.extend(
                    self._detect_volume_or_percentage_gaps(expression, sentence)
                )

        return ambiguities

    #---------- <Summary> ----------
    # Summary: Finds missing dimensions around time-based measurable expressions.
    #---------- </Summary> ----------
    def _detect_time_measurement_gaps(
        self,
        expression: MeasurableExpression,
        sentence: AnalyzedSentence,
    ) -> list[MeasurementAmbiguity]:
        gaps: list[MeasurementAmbiguity] = []
        sentence_text = sentence.text.lower()

        if not self._has_statistical_target(sentence_text):
            gaps.append(
                self._build_measurement_ambiguity(
                    expression,
                    sentence,
                    missing_dimension="statisticalTarget",
                    reason="The time target does not specify whether it is a maximum, average, median, or percentile-based target.",
                    evidence="No statistical qualifier such as maximum, average, median, 95th percentile, or 99th percentile was found near the time expression.",
                    severity="medium",
                )
            )

        if not self._has_load_condition(sentence_text):
            gaps.append(
                self._build_measurement_ambiguity(
                    expression,
                    sentence,
                    missing_dimension="loadCondition",
                    reason="The time target does not specify the load or operating condition under which it must be met.",
                    evidence="No load context such as concurrent users, requests per second, peak load, or normal load was found near the time expression.",
                    severity="medium",
                )
            )

        if self._has_generic_measurement_action(sentence) and not self._has_boundary_context(
            sentence_text
        ):
            gaps.append(
                self._build_measurement_ambiguity(
                    expression,
                    sentence,
                    missing_dimension="measurementBoundary",
                    reason="The requirement does not clearly define when the measured operation starts and ends.",
                    evidence="A generic measured action was found, but no boundary context such as after, when, until, displayed, rendered, completed, or available was found.",
                    severity="high",
                )
            )

        return gaps

    #---------- <Summary> ----------
    # Summary: Finds missing condition or scope around count and percentage expressions.
    #---------- </Summary> ----------
    def _detect_volume_or_percentage_gaps(
        self,
        expression: MeasurableExpression,
        sentence: AnalyzedSentence,
    ) -> list[MeasurementAmbiguity]:
        sentence_text = sentence.text.lower()

        if self._has_condition_context(sentence_text):
            return []

        return [
            self._build_measurement_ambiguity(
                expression,
                sentence,
                missing_dimension="conditionContext",
                reason="The measurable target does not specify the condition or scope where it applies.",
                evidence="The measurable expression was found without condition context such as under, during, when, for, or per.",
                severity="medium",
            )
        ]

    #---------- <Summary> ----------
    # Summary: Defines regex patterns for measurable expressions used by V2 pre-analysis.
    #---------- </Summary> ----------
    def _patterns(self) -> list[tuple[str, str, str]]:
        return [
            (
                r"\bwithin\s+\d+(\.\d+)?\s*(ms|milliseconds?|seconds?|secs?|minutes?|mins?|hours?)\b",
                "time",
                "Defines a measurable upper time limit.",
            ),
            (
                r"\b(less than|under|below|no more than|maximum of|max)\s+\d+(\.\d+)?\s*(ms|milliseconds?|seconds?|secs?|minutes?|mins?|hours?)\b",
                "time",
                "Defines a measurable maximum time threshold.",
            ),
            (
                r"\b(at least|minimum of|min)\s+\d+(\.\d+)?\s*(%|percent|percentage)\b",
                "percentage",
                "Defines a measurable minimum percentage.",
            ),
            (
                r"\b(less than|under|below|no more than|maximum of|max)\s+\d+(\.\d+)?\s*(%|percent|percentage)\b",
                "percentage",
                "Defines a measurable maximum percentage.",
            ),
            (
                r"\b\d+(\.\d+)?\s*(%|percent|percentage)\b",
                "percentage",
                "Defines a measurable percentage.",
            ),
            (
                r"\b(at least|minimum of|min|more than|over)\s+\d+\s+(users?|requests?|transactions?|records?|items?|files?|attempts?)\b",
                "count",
                "Defines a measurable minimum count.",
            ),
            (
                r"\b(less than|under|below|no more than|maximum of|max)\s+\d+\s+(users?|requests?|transactions?|records?|items?|files?|attempts?)\b",
                "count",
                "Defines a measurable maximum count.",
            ),
            (
                r"\b\d+\s+(users?|requests?|transactions?|records?|items?|files?|attempts?)\b",
                "count",
                "Defines a measurable count.",
            ),
            (
                r"\b(per|every)\s+\d+(\.\d+)?\s*(ms|milliseconds?|seconds?|secs?|minutes?|mins?|hours?|days?)\b",
                "frequency",
                "Defines a measurable frequency.",
            ),
            (
                r"\b\d+(\.\d+)?\s*(kb|mb|gb|tb|kilobytes?|megabytes?|gigabytes?|terabytes?)\b",
                "size",
                "Defines a measurable size.",
            ),
        ]

    #---------- <Summary> ----------
    # Summary: Removes duplicate measurable expressions found by overlapping patterns.
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

    #---------- <Summary> ----------
    # Summary: Keeps the longest useful expression when regex matches overlap.
    #---------- </Summary> ----------
    def _remove_overlapping(
        self,
        expressions: list[MeasurableExpression],
    ) -> list[MeasurableExpression]:
        sorted_expressions = sorted(
            expressions,
            key=lambda expression: (
                expression.start_char,
                -(expression.end_char - expression.start_char),
            ),
        )

        selected: list[MeasurableExpression] = []

        for expression in sorted_expressions:
            overlaps_existing = any(
                expression.start_char < selected_expression.end_char
                and expression.end_char > selected_expression.start_char
                for selected_expression in selected
            )

            if not overlaps_existing:
                selected.append(expression)

        return selected

    #---------- <Summary> ----------
    # Summary: Finds the analyzed sentence that contains a measurable expression.
    #---------- </Summary> ----------
    def _find_sentence_for_expression(
        self,
        analyzed_text: AnalyzedText,
        expression: MeasurableExpression,
    ) -> AnalyzedSentence:
        for sentence in analyzed_text.sentences:
            if (
                sentence.start_char <= expression.start_char
                and expression.end_char <= sentence.end_char
            ):
                return sentence

        return AnalyzedSentence(
            text=analyzed_text.original_text,
            start_char=0,
            end_char=len(analyzed_text.original_text),
            tokens=[],
        )

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
    # Summary: Checks whether the sentence defines max/average/median/percentile context.
    #---------- </Summary> ----------
    def _has_statistical_target(self, sentence_text: str) -> bool:
        return any(
            marker in sentence_text
            for marker in {
                "maximum",
                "max",
                "average",
                "avg",
                "median",
                "percentile",
                "95th",
                "99th",
                "p95",
                "p99",
                "for 95%",
                "for 99%",
            }
        )

    #---------- <Summary> ----------
    # Summary: Checks whether the sentence defines load or operating conditions.
    #---------- </Summary> ----------
    def _has_load_condition(self, sentence_text: str) -> bool:
        return any(
            marker in sentence_text
            for marker in {
                "concurrent user",
                "concurrent users",
                "requests per second",
                "transactions per second",
                "peak load",
                "normal load",
                "under load",
                "under typical load",
                "under peak load",
                "users",
                "requests",
            }
        )

    #---------- <Summary> ----------
    # Summary: Checks whether the sentence gives start/end clues for the measurement.
    #---------- </Summary> ----------
    def _has_boundary_context(self, sentence_text: str) -> bool:
        return any(
            marker in sentence_text
            for marker in {
                "after",
                "when",
                "until",
                "complete",
                "completed",
                "display",
                "displayed",
                "render",
                "rendered",
                "available",
                "visible",
            }
        )

    #---------- <Summary> ----------
    # Summary: Checks whether count/percentage measurements include condition context.
    #---------- </Summary> ----------
    def _has_condition_context(self, sentence_text: str) -> bool:
        return any(
            marker in sentence_text
            for marker in {
                "under",
                "during",
                "when",
                "while",
                "for",
                "per",
                "at",
            }
        )

    #---------- <Summary> ----------
    # Summary: Checks whether the measured action is generic enough to need boundaries.
    #---------- </Summary> ----------
    def _has_generic_measurement_action(self, sentence: AnalyzedSentence) -> bool:
        generic_actions = {
            "respond",
            "process",
            "complete",
            "load",
            "display",
            "render",
            "show",
            "retrieve",
            "return",
        }

        return any(
            token.lemma.lower() in generic_actions and token.pos in {"VERB", "AUX"}
            for token in sentence.tokens
        )
