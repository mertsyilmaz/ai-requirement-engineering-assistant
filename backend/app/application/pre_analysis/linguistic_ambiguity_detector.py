from app.domain.pre_analysis import (
    AmbiguityCandidate,
    AnalyzedSentence,
    AnalyzedText,
    AnalyzedToken,
    ConfirmedAmbiguity,
    MeasurableExpression,
    RejectedAmbiguityCandidate,
)


#---------- <Summary> ----------
# Summary: Finds NLP-derived ambiguity candidates that are not dependent on JSON terms.
#
# This detector looks for simple requirement-language structures such as
# "system should be <adjective>" so V2 can still produce pre-analysis findings
# even when a risky word is not present in the knowledge JSON.
#---------- </Summary> ----------
class LinguisticAmbiguityDetector:

    #---------- <Summary> ----------
    # Summary: Returns linguistic ambiguity candidates plus confirmed/rejected decisions.
    #---------- </Summary> ----------
    def detect(
        self,
        analyzed_text: AnalyzedText,
        measurable_expressions: list[MeasurableExpression],
        existing_candidates: list[AmbiguityCandidate],
    ) -> tuple[
        list[AmbiguityCandidate],
        list[ConfirmedAmbiguity],
        list[RejectedAmbiguityCandidate],
    ]:
        candidates = self._find_candidates(analyzed_text, existing_candidates)
        confirmed: list[ConfirmedAmbiguity] = []
        rejected: list[RejectedAmbiguityCandidate] = []

        for candidate in candidates:
            supporting_expression = self._find_supporting_expression(
                candidate,
                measurable_expressions,
            )

            if supporting_expression and self._can_measurement_clarify_candidate(
                candidate,
                supporting_expression,
            ):
                rejected.append(
                    self._build_rejected_candidate(candidate, supporting_expression)
                )
            else:
                confirmed.append(self._build_confirmed_ambiguity(candidate))

        return candidates, confirmed, rejected

    #---------- <Summary> ----------
    # Summary: Finds adjectives used as quality expectations for system-like subjects.
    #---------- </Summary> ----------
    def _find_candidates(
        self,
        analyzed_text: AnalyzedText,
        existing_candidates: list[AmbiguityCandidate],
    ) -> list[AmbiguityCandidate]:
        candidates: list[AmbiguityCandidate] = []
        for sentence in analyzed_text.sentences:
            if not self._has_system_subject(sentence):
                continue

            for token in sentence.tokens:
                if not self._is_quality_adjective(token):
                    continue

                if self._is_inside_existing_candidate(token, existing_candidates):
                    continue

                candidates.append(self._build_candidate(token, sentence))

        return candidates

    #---------- <Summary> ----------
    # Summary: Avoids duplicating a known candidate that already covers a token.
    #---------- </Summary> ----------
    def _is_inside_existing_candidate(
        self,
        token: AnalyzedToken,
        existing_candidates: list[AmbiguityCandidate],
    ) -> bool:
        return any(
            candidate.start_char <= token.start_char
            and token.end_char <= candidate.end_char
            for candidate in existing_candidates
        )

    #---------- <Summary> ----------
    # Summary: Checks whether the sentence appears to describe the system itself.
    #---------- </Summary> ----------
    def _has_system_subject(self, sentence: AnalyzedSentence) -> bool:
        return any(
            token.pos in {"NOUN", "PROPN"}
            and token.dependency in {"nsubj", "nsubjpass", "ROOT"}
            and self._has_requirement_modal_or_copula(sentence)
            for token in sentence.tokens
        )

    #---------- <Summary> ----------
    # Summary: Checks whether the sentence uses requirement-style modal wording.
    #---------- </Summary> ----------
    def _has_requirement_modal_or_copula(self, sentence: AnalyzedSentence) -> bool:
        return any(
            token.pos in {"AUX", "VERB"}
            and token.lemma.lower() in {"should", "shall", "must", "be"}
            for token in sentence.tokens
        )

    #---------- <Summary> ----------
    # Summary: Checks whether a token is likely a vague quality adjective.
    #---------- </Summary> ----------
    def _is_quality_adjective(self, token: AnalyzedToken) -> bool:
        if token.pos != "ADJ":
            return False

        return token.dependency in {
            "acomp",
            "attr",
            "conj",
            "ROOT",
        }

    #---------- <Summary> ----------
    # Summary: Creates a linguistic ambiguity candidate from one adjective token.
    #---------- </Summary> ----------
    def _build_candidate(
        self,
        token: AnalyzedToken,
        sentence: AnalyzedSentence,
    ) -> AmbiguityCandidate:
        return AmbiguityCandidate(
            phrase=token.text,
            matched_text=token.text,
            reason="The adjective describes a system quality without objective criteria.",
            severity="medium",
            category="quality",
            start_char=token.start_char,
            end_char=token.end_char,
            sentence=sentence.text,
            source="linguisticAnalysis",
            linguistic_role=(
                "The adjective is used as a quality expectation for a system-like subject."
            ),
            prompt_guidance=(
                "Treat this as a possible ambiguity only if the text does not provide objective criteria."
            ),
        )

    #---------- <Summary> ----------
    # Summary: Finds a measurable expression in the same sentence as the candidate.
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

    #---------- <Summary> ----------
    # Summary: Keeps broad quality adjectives confirmed unless the measurement directly clarifies them.
    #---------- </Summary> ----------
    def _can_measurement_clarify_candidate(
        self,
        candidate: AmbiguityCandidate,
        supporting_expression: MeasurableExpression,
    ) -> bool:
        if candidate.category == "quality":
            return False

        return supporting_expression.category in {"time", "frequency", "percentage"}

    #---------- <Summary> ----------
    # Summary: Converts a linguistic candidate into a confirmed ambiguity finding.
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
            evidence=candidate.linguistic_role
            or "Linguistic analysis found a vague quality expectation.",
            source=candidate.source,
            linguistic_role=candidate.linguistic_role,
            prompt_guidance=candidate.prompt_guidance,
        )

    #---------- <Summary> ----------
    # Summary: Rejects a linguistic candidate when measurable context clarifies it.
    #---------- </Summary> ----------
    def _build_rejected_candidate(
        self,
        candidate: AmbiguityCandidate,
        supporting_expression: MeasurableExpression,
    ) -> RejectedAmbiguityCandidate:
        return RejectedAmbiguityCandidate(
            phrase=candidate.phrase,
            matched_text=candidate.matched_text,
            reason=candidate.reason,
            category=candidate.category,
            start_char=candidate.start_char,
            end_char=candidate.end_char,
            sentence=candidate.sentence,
            rejection_reason=(
                "A measurable expression in the same sentence provides objective context."
            ),
            supporting_expression=supporting_expression.text,
            source=candidate.source,
            linguistic_role=candidate.linguistic_role,
            prompt_guidance=(
                "Do not report this linguistic candidate as a standalone ambiguity."
            ),
        )
