from app.domain.pre_analysis import (
    AnalyzedSentence,
    AnalyzedText,
    AnalyzedToken,
    ReferenceAmbiguity,
)


#---------- <Summary> ----------
# Summary: Detects unclear references using spaCy pronoun morphology.
#
# Instead of checking a JSON list of words such as "it" or "that", this detector
# asks spaCy whether a token is a personal or demonstrative pronoun and then
# checks whether the current or previous sentence provides a clear antecedent.
#---------- </Summary> ----------
class ReferenceAmbiguityDetector:

    #---------- <Summary> ----------
    # Summary: Returns reference ambiguity findings from the analyzed requirement text.
    #---------- </Summary> ----------
    def detect(self, analyzed_text: AnalyzedText) -> list[ReferenceAmbiguity]:
        ambiguities: list[ReferenceAmbiguity] = []

        for index, sentence in enumerate(analyzed_text.sentences):
            previous_sentence = (
                analyzed_text.sentences[index - 1] if index > 0 else None
            )

            for token in sentence.tokens:
                if not self._is_reference_candidate(token):
                    continue

                if self._has_clear_reference(
                    sentence,
                    previous_sentence,
                    token.start_char,
                ):
                    continue

                ambiguities.append(
                    ReferenceAmbiguity(
                        phrase=token.text,
                        reason="The reference may be unclear without an explicit antecedent.",
                        severity="medium",
                        category="reference",
                        start_char=token.start_char,
                        end_char=token.end_char,
                        sentence=sentence.text,
                        evidence="A third-person or demonstrative pronoun was found without a single clear noun antecedent in the current or previous sentence.",
                    )
                )

        return ambiguities

    #---------- <Summary> ----------
    # Summary: Uses spaCy POS and morphology to identify reference candidates.
    #---------- </Summary> ----------
    def _is_reference_candidate(self, token: AnalyzedToken) -> bool:
        if token.pos != "PRON":
            return False

        pron_type = token.morph.get("PronType")
        person = token.morph.get("Person")

        return pron_type in {"Prs", "Dem"} and person in {"3", None}

    #---------- <Summary> ----------
    # Summary: Checks whether a reference term has a likely clear noun antecedent.
    #---------- </Summary> ----------
    def _has_clear_reference(
        self,
        sentence: AnalyzedSentence,
        previous_sentence: AnalyzedSentence | None,
        reference_start_char: int,
    ) -> bool:
        current_object_count = self._count_object_like_nouns_before(
            sentence,
            reference_start_char,
        )

        if current_object_count > 0:
            return current_object_count == 1

        if self._count_object_like_nouns(previous_sentence) > 0:
            return True

        total_noun_count = self._count_noun_like_tokens(
            sentence,
        ) + self._count_noun_like_tokens(previous_sentence)

        return total_noun_count == 1

    #---------- <Summary> ----------
    # Summary: Counts object-like nouns before the reference term in the same sentence.
    #---------- </Summary> ----------
    def _count_object_like_nouns_before(
        self,
        sentence: AnalyzedSentence | None,
        reference_start_char: int,
    ) -> int:
        if not sentence:
            return 0

        return sum(
            1
            for token in sentence.tokens
            if token.start_char < reference_start_char
            and token.pos in {"NOUN", "PROPN"}
            and token.dependency in {"dobj", "pobj", "attr", "nsubjpass"}
        )

    #---------- <Summary> ----------
    # Summary: Counts nouns that are likely objects or passive subjects.
    #---------- </Summary> ----------
    def _count_object_like_nouns(self, sentence: AnalyzedSentence | None) -> int:
        if not sentence:
            return 0

        return sum(
            1
            for token in sentence.tokens
            if token.pos in {"NOUN", "PROPN"}
            and token.dependency in {"dobj", "pobj", "attr", "nsubjpass"}
        )

    #---------- <Summary> ----------
    # Summary: Counts noun-like tokens when dependency information is not enough.
    #---------- </Summary> ----------
    def _count_noun_like_tokens(self, sentence: AnalyzedSentence | None) -> int:
        if not sentence:
            return 0

        return sum(
            1
            for token in sentence.tokens
            if token.pos in {"NOUN", "PROPN"}
        )
