import re

from app.application.ports.ambiguity_knowledge_repository import (
    AmbiguityKnowledgeRepositoryPort,
)
from app.domain.pre_analysis import (
    AmbiguityCandidate,
    AmbiguityTerm,
    AnalyzedText,
    ConfirmedAmbiguity,
    MeasurableExpression,
    RejectedAmbiguityCandidate,
)


#---------- <Summary> ----------
# Summary: Detects known ambiguity terms defined in the ambiguity knowledge source.
# 
# This detector handles the full known-ambiguity flow:
# it reads configured terms, finds matches in the requirement text, and decides
# whether each match should be confirmed or rejected based on measurable context.
#---------- </Summary> ----------
class KnownAmbiguityDetector:

    def __init__(self, ambiguity_repository: AmbiguityKnowledgeRepositoryPort):
        self.ambiguity_repository = ambiguity_repository

    #---------- <Summary> ----------
    # Summary: Returns all known ambiguity candidates plus confirmed/rejected decisions.
    #---------- </Summary> ----------
    def detect(
        self,
        text: str,
        analyzed_text: AnalyzedText,
        measurable_expressions: list[MeasurableExpression],
    ) -> tuple[
        list[AmbiguityCandidate],
        list[ConfirmedAmbiguity],
        list[RejectedAmbiguityCandidate],
    ]:
        candidates = self._find_candidates(text, analyzed_text)
        confirmed: list[ConfirmedAmbiguity] = []
        rejected: list[RejectedAmbiguityCandidate] = []

        for candidate in candidates:
            if self._should_reject(candidate, measurable_expressions):
                rejected.append(
                    self._build_rejected_candidate(candidate, measurable_expressions)
                )
            else:
                confirmed.append(self._build_confirmed_ambiguity(candidate))

        return candidates, confirmed, rejected

    #---------- <Summary> ----------
    # Summary: Finds all configured ambiguity terms in the cleaned requirement text.
    #---------- </Summary> ----------
    def _find_candidates(
        self,
        text: str,
        analyzed_text: AnalyzedText,
    ) -> list[AmbiguityCandidate]:
        candidates: list[AmbiguityCandidate] = []

        for term in self.ambiguity_repository.get_all_terms():
            candidates.extend(self._find_matches(text, analyzed_text, term))

        return candidates

    #---------- <Summary> ----------
    # Summary: Chooses phrase or regex matching based on the term configuration.
    #---------- </Summary> ----------
    def _find_matches(
        self,
        text: str,
        analyzed_text: AnalyzedText,
        term: AmbiguityTerm,
    ) -> list[AmbiguityCandidate]:
        if term.match_type == "regex":
            return self._find_regex_matches(text, analyzed_text, term)

        return self._find_phrase_matches(text, analyzed_text, term)

    #---------- <Summary> ----------
    # Summary: Finds exact phrase matches without matching inside longer words.
    #---------- </Summary> ----------
    def _find_phrase_matches(
        self,
        text: str,
        analyzed_text: AnalyzedText,
        term: AmbiguityTerm,
    ) -> list[AmbiguityCandidate]:
        pattern = re.compile(rf"\b{re.escape(term.phrase)}\b", re.IGNORECASE)

        return [
            self._build_candidate(match, analyzed_text, term)
            for match in pattern.finditer(text)
        ]

    #---------- <Summary> ----------
    # Summary: Finds pattern-based matches for terms configured as regular expressions.
    #---------- </Summary> ----------
    def _find_regex_matches(
        self,
        text: str,
        analyzed_text: AnalyzedText,
        term: AmbiguityTerm,
    ) -> list[AmbiguityCandidate]:
        pattern = re.compile(term.phrase, re.IGNORECASE)

        return [
            self._build_candidate(match, analyzed_text, term)
            for match in pattern.finditer(text)
        ]

    #---------- <Summary> ----------
    # Summary: Converts a text match into a candidate object used by later analysis.
    #---------- </Summary> ----------
    def _build_candidate(
        self,
        match: re.Match,
        analyzed_text: AnalyzedText,
        term: AmbiguityTerm,
    ) -> AmbiguityCandidate:
        return AmbiguityCandidate(
            phrase=term.phrase,
            matched_text=match.group(0),
            reason=term.reason,
            severity=term.severity,
            category=term.category,
            match_type=term.match_type,
            start_char=match.start(),
            end_char=match.end(),
            sentence=self._find_sentence_for_match(
                analyzed_text,
                match.start(),
                match.end(),
            ),
            validation_rule=term.validation_rule,
        )

    #---------- <Summary> ----------
    # Summary: Finds the analyzed sentence that contains the matched ambiguity term.
    #---------- </Summary> ----------
    def _find_sentence_for_match(
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
    # Summary: Decides whether a known ambiguity is clarified by measurable context.
    #---------- </Summary> ----------
    def _should_reject(
        self,
        candidate: AmbiguityCandidate,
        measurable_expressions: list[MeasurableExpression],
    ) -> bool:
        if candidate.validation_rule in {
            "requires_measurable_performance_context",
            "requires_measurable_time_context",
        }:
            return self._has_related_measurable_expression(
                candidate,
                measurable_expressions,
                allowed_categories={"time"},
            )

        if candidate.validation_rule == "requires_quantifiable_amount":
            return self._has_related_measurable_expression(
                candidate,
                measurable_expressions,
                allowed_categories={"count", "percentage", "size"},
            )

        if candidate.validation_rule == "requires_availability_criteria":
            return self._has_related_measurable_expression(
                candidate,
                measurable_expressions,
                allowed_categories={"percentage"},
            )

        if candidate.validation_rule == "requires_frequency_criteria":
            return self._has_related_measurable_expression(
                candidate,
                measurable_expressions,
                allowed_categories={"frequency", "time"},
            )

        return False

    #---------- <Summary> ----------
    # Summary: Checks if a supporting measurable expression exists in the same sentence.
    #---------- </Summary> ----------
    def _has_related_measurable_expression(
        self,
        candidate: AmbiguityCandidate,
        measurable_expressions: list[MeasurableExpression],
        allowed_categories: set[str],
    ) -> bool:
        for expression in measurable_expressions:
            if expression.category not in allowed_categories:
                continue

            if expression.text in candidate.sentence:
                return True

        return False

    #---------- <Summary> ----------
    # Summary: Marks a candidate as a real ambiguity when no clarifying context exists.
    #---------- </Summary> ----------
    def _build_confirmed_ambiguity(
        self,
        candidate: AmbiguityCandidate,
    ) -> ConfirmedAmbiguity:
        return ConfirmedAmbiguity(
            phrase=candidate.phrase,
            matched_text=candidate.matched_text,
            reason=candidate.reason,
            severity=candidate.severity,
            category=candidate.category,
            start_char=candidate.start_char,
            end_char=candidate.end_char,
            sentence=candidate.sentence,
            evidence="No sufficient measurable or objective context was found for this candidate.",
        )

    #---------- <Summary> ----------
    # Summary: Marks a candidate as rejected when measurable context clarifies it.
    #---------- </Summary> ----------
    def _build_rejected_candidate(
        self,
        candidate: AmbiguityCandidate,
        measurable_expressions: list[MeasurableExpression],
    ) -> RejectedAmbiguityCandidate:
        supporting_expression = self._find_supporting_expression(
            candidate,
            measurable_expressions,
        )

        return RejectedAmbiguityCandidate(
            phrase=candidate.phrase,
            matched_text=candidate.matched_text,
            reason=candidate.reason,
            category=candidate.category,
            start_char=candidate.start_char,
            end_char=candidate.end_char,
            sentence=candidate.sentence,
            rejection_reason="A measurable expression in the same sentence provides sufficient objective context.",
            supporting_expression=supporting_expression.text
            if supporting_expression
            else None,
        )

    #---------- <Summary> ----------
    # Summary: Finds the measurable expression that explains why a candidate was rejected.
    #---------- </Summary> ----------
    def _find_supporting_expression(
        self,
        candidate: AmbiguityCandidate,
        measurable_expressions: list[MeasurableExpression],
    ) -> MeasurableExpression | None:
        for expression in measurable_expressions:
            if expression.text in candidate.sentence:
                return expression

        return None
