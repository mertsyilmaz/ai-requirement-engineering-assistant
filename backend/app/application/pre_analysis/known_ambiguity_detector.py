import re

from app.application.ports.ambiguity_knowledge_repository import (
    AmbiguityKnowledgeRepositoryPort,
)
from app.domain.pre_analysis import (
    AmbiguityCandidate,
    AmbiguityTerm,
    AnalyzedSentence,
    AnalyzedText,
    AnalyzedToken,
    ConfirmedAmbiguity,
    MeasurableExpression,
    RejectedAmbiguityCandidate,
)


#---------- <Summary> ----------
# Summary: Detects known ambiguity terms from seed knowledge without regex rules.
#
# The JSON file only provides seed phrases and broad categories. Matching and
# validation use spaCy token, lemma, sentence, and dependency context so the
# detector is not driven by hidden pattern lists.
#---------- </Summary> ----------
class KnownAmbiguityDetector:

    def __init__(self, ambiguity_repository: AmbiguityKnowledgeRepositoryPort):
        self.ambiguity_repository = ambiguity_repository

    #---------- <Summary> ----------
    # Summary: Returns known ambiguity candidates plus confirmed/rejected decisions.
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
        candidates = self._remove_overlapping_candidates(
            self._find_candidates(analyzed_text)
        )
        confirmed: list[ConfirmedAmbiguity] = []
        rejected: list[RejectedAmbiguityCandidate] = []

        for candidate in candidates:
            domain_object_reason = self._get_domain_object_rejection(candidate)
            if domain_object_reason:
                rejected.append(
                    self._build_rejected_candidate(
                        candidate,
                        measurable_expressions,
                        domain_object_reason,
                    )
                )
                continue

            if self._is_clarified_by_measurement(candidate, measurable_expressions):
                rejected.append(
                    self._build_rejected_candidate(candidate, measurable_expressions)
                )
                continue

            confirmed.append(self._build_confirmed_ambiguity(candidate))

        return candidates, confirmed, rejected

    #---------- <Summary> ----------
    # Summary: Finds seed phrases by comparing JSON terms with spaCy token text and lemmas.
    #---------- </Summary> ----------
    def _find_candidates(self, analyzed_text: AnalyzedText) -> list[AmbiguityCandidate]:
        candidates: list[AmbiguityCandidate] = []

        for term in self.ambiguity_repository.get_all_terms():
            term_parts = self._normalize_phrase_parts(term.phrase)

            for sentence in analyzed_text.sentences:
                tokens = [token for token in sentence.tokens if token.text.strip()]

                for index in range(0, len(tokens) - len(term_parts) + 1):
                    window = tokens[index:index + len(term_parts)]

                    if not self._tokens_match_phrase(window, term_parts):
                        continue

                    candidates.append(
                        self._build_candidate_from_tokens(window, sentence, term)
                    )

        return candidates

    #---------- <Summary> ----------
    # Summary: Keeps the longest seed phrase when known ambiguity matches overlap.
    #---------- </Summary> ----------
    def _remove_overlapping_candidates(
        self,
        candidates: list[AmbiguityCandidate],
    ) -> list[AmbiguityCandidate]:
        selected: list[AmbiguityCandidate] = []
        sorted_candidates = sorted(
            candidates,
            key=lambda candidate: (
                candidate.start_char,
                -(candidate.end_char - candidate.start_char),
            ),
        )

        for candidate in sorted_candidates:
            if any(
                candidate.start_char < selected_candidate.end_char
                and candidate.end_char > selected_candidate.start_char
                for selected_candidate in selected
            ):
                continue

            selected.append(candidate)

        return self._remove_modifier_duplicates(selected)

    #---------- <Summary> ----------
    # Summary: Removes adverb candidates when they only modify another selected candidate.
    #---------- </Summary> ----------
    def _remove_modifier_duplicates(
        self,
        candidates: list[AmbiguityCandidate],
    ) -> list[AmbiguityCandidate]:
        filtered: list[AmbiguityCandidate] = []

        for candidate in candidates:
            if not self._is_adverb_modifier_of_candidate(candidate, candidates):
                filtered.append(candidate)

        return filtered

    #---------- <Summary> ----------
    # Summary: Checks whether an adverb candidate points to another candidate as its head.
    #---------- </Summary> ----------
    def _is_adverb_modifier_of_candidate(
        self,
        candidate: AmbiguityCandidate,
        candidates: list[AmbiguityCandidate],
    ) -> bool:
        role = candidate.linguistic_role or ""
        if "used as ADV" not in role:
            return False

        head_match = re.search(r"depends on '([^']+)'", role)
        if not head_match:
            return False

        head_text = head_match.group(1).lower()

        return any(
            other is not candidate
            and other.sentence == candidate.sentence
            and other.category == candidate.category
            and other.matched_text.lower() == head_text
            for other in candidates
        )

    #---------- <Summary> ----------
    # Summary: Normalizes one configured phrase into comparable token parts.
    #---------- </Summary> ----------
    def _normalize_phrase_parts(self, phrase: str) -> list[str]:
        return re.findall(r"\w+|[^\w\s]", phrase.lower())

    #---------- <Summary> ----------
    # Summary: Compares seed phrase parts with spaCy token text and lemma values.
    #---------- </Summary> ----------
    def _tokens_match_phrase(
        self,
        tokens: list[AnalyzedToken],
        term_parts: list[str],
    ) -> bool:
        return all(
            term_part in self._token_variants(token)
            for token, term_part in zip(tokens, term_parts)
        )

    #---------- <Summary> ----------
    # Summary: Produces comparable text variants for one token without duplicating JSON seeds.
    #---------- </Summary> ----------
    def _token_variants(self, token: AnalyzedToken) -> set[str]:
        variants = {
            token.text.lower(),
            token.lemma.lower(),
        }
        normalized_adverb = self._normalize_adverb(token.text.lower())
        if normalized_adverb:
            variants.add(normalized_adverb)

        normalized_lemma_adverb = self._normalize_adverb(token.lemma.lower())
        if normalized_lemma_adverb:
            variants.add(normalized_lemma_adverb)

        return variants

    #---------- <Summary> ----------
    # Summary: Converts common adverb forms into their adjective seed form.
    #---------- </Summary> ----------
    def _normalize_adverb(self, value: str) -> str | None:
        if value.endswith("ably") and len(value) > 5:
            return value[:-4] + "able"

        if value.endswith("ibly") and len(value) > 5:
            return value[:-4] + "ible"

        if value.endswith("ily") and len(value) > 4:
            return value[:-3] + "y"

        if value.endswith("ly") and len(value) > 3:
            return value[:-2]

        return None

    #---------- <Summary> ----------
    # Summary: Converts one matched token window into a pre-analysis candidate.
    #---------- </Summary> ----------
    def _build_candidate_from_tokens(
        self,
        tokens: list[AnalyzedToken],
        sentence: AnalyzedSentence,
        term: AmbiguityTerm,
    ) -> AmbiguityCandidate:
        matched_text = sentence.text[
            tokens[0].start_char - sentence.start_char:
            tokens[-1].end_char - sentence.start_char
        ]

        return AmbiguityCandidate(
            phrase=term.phrase,
            matched_text=matched_text,
            reason=self._reason_for_category(term.category),
            severity=term.severity,
            category=term.category,
            start_char=tokens[0].start_char,
            end_char=tokens[-1].end_char,
            sentence=sentence.text,
            source="knownKnowledge",
            linguistic_role=self._describe_linguistic_role(tokens),
        )

    #---------- <Summary> ----------
    # Summary: Creates a short explanation based on the ambiguity category.
    #---------- </Summary> ----------
    def _reason_for_category(self, category: str) -> str:
        reasons = {
            "performance": "The performance expectation is not measurable without objective context.",
            "usability": "The usability expectation is subjective without observable criteria.",
            "security": "The security expectation is unclear without specified controls, standards, or threat scope.",
            "reliability": "The reliability expectation is not measurable without failure-rate, availability, or recovery criteria.",
            "availability": "The availability expectation is incomplete without a concrete availability target.",
            "scalability": "The scalability expectation is unclear without workload, user count, or throughput targets.",
            "maintainability": "The maintainability expectation is subjective without measurable maintenance criteria.",
            "time": "The expected time frame is not measurable without a concrete time target.",
            "frequency": "The recurrence expectation is incomplete without a concrete interval.",
            "quantity": "The quantity or magnitude is not measurable without a concrete amount.",
            "scope": "The requirement scope is open-ended and incomplete.",
            "condition": "The condition or trigger is not specified.",
        }

        return reasons.get(
            category,
            "The expression is unclear without objective acceptance criteria.",
        )

    #---------- <Summary> ----------
    # Summary: Describes the grammatical role of a matched ambiguity term.
    #---------- </Summary> ----------
    def _describe_linguistic_role(self, tokens: list[AnalyzedToken]) -> str:
        token = tokens[0]

        if len(tokens) == 1:
            role = (
                f"Matched token is used as {token.pos} "
                f"with dependency {token.dependency}."
            )
            if token.head_text:
                role += (
                    f" It modifies or depends on '{token.head_text}' "
                    f"({token.head_pos}, dependency {token.head_dependency})."
                )
            return role

        return "Matched phrase is represented by consecutive NLP tokens."

    #---------- <Summary> ----------
    # Summary: Rejects a performance adjective when grammar shows it modifies a domain object.
    #---------- </Summary> ----------
    def _get_domain_object_rejection(
        self,
        candidate: AmbiguityCandidate,
    ) -> str | None:
        if candidate.category != "performance":
            return None

        if "dependency amod" not in (candidate.linguistic_role or ""):
            return None

        if self._candidate_mentions_system_behavior(candidate):
            return None

        return (
            "The candidate modifies a domain object rather than defining "
            "a measurable system performance expectation."
        )

    #---------- <Summary> ----------
    # Summary: Checks whether the candidate is grammatically tied to a system behavior.
    #---------- </Summary> ----------
    def _candidate_mentions_system_behavior(self, candidate: AmbiguityCandidate) -> bool:
        sentence = candidate.sentence.lower()
        matched = candidate.matched_text.lower()
        role = candidate.linguistic_role or ""

        if "dependency compound" in role:
            return False

        if "It modifies or depends on" in role and "(VERB, dependency amod)" in role:
            return False

        return matched in sentence and any(
            word.endswith("ing") or word.endswith("ed")
            for word in sentence.split()
        )

    #---------- <Summary> ----------
    # Summary: Decides whether measurable context clarifies a known ambiguity.
    #---------- </Summary> ----------
    def _is_clarified_by_measurement(
        self,
        candidate: AmbiguityCandidate,
        measurable_expressions: list[MeasurableExpression],
    ) -> bool:
        allowed_categories = self._clarifying_measurement_categories(
            candidate.category,
        )
        if not allowed_categories:
            return False

        return self._has_related_measurable_expression(
            candidate,
            measurable_expressions,
            allowed_categories,
        )

    #---------- <Summary> ----------
    # Summary: Defines which measurement types can clarify each ambiguity category.
    #---------- </Summary> ----------
    def _clarifying_measurement_categories(self, category: str) -> set[str]:
        category_map = {
            "performance": {"time"},
            "time": {"time"},
            "availability": {"percentage"},
            "frequency": {"frequency", "time"},
            "quantity": {"count", "percentage", "size"},
            "scalability": {"count", "percentage", "frequency"},
        }

        return category_map.get(category, set())

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
            source=candidate.source,
            linguistic_role=candidate.linguistic_role,
            prompt_guidance=candidate.prompt_guidance,
        )

    #---------- <Summary> ----------
    # Summary: Marks a candidate as rejected when measurable or grammatical context clarifies it.
    #---------- </Summary> ----------
    def _build_rejected_candidate(
        self,
        candidate: AmbiguityCandidate,
        measurable_expressions: list[MeasurableExpression],
        rejection_reason: str | None = None,
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
            rejection_reason=rejection_reason
            or "A measurable expression in the same sentence provides sufficient objective context.",
            supporting_expression=supporting_expression.text
            if supporting_expression
            else None,
            source=candidate.source,
            linguistic_role=candidate.linguistic_role,
            prompt_guidance=(
                "Do not report this term as a standalone ambiguity because context clarifies it."
            ),
        )

    #---------- <Summary> ----------
    # Summary: Finds the measurable expression that supports a rejection decision.
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
