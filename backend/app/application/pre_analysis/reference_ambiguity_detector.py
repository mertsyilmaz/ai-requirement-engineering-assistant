import json
from pathlib import Path

from app.domain.pre_analysis import (
    AnalyzedSentence,
    AnalyzedText,
    ReferenceAmbiguity,
    ReferenceAmbiguityRuleConfig,
)


#---------- <Summary> ----------
# Summary: Detects unclear references such as it, this, that, they, and them.
# 
# This detector uses NLP token and noun information to avoid reporting a
# reference term when there is a clear antecedent in the current or previous
# sentence.
#---------- </Summary> ----------
class ReferenceAmbiguityDetector:

    def __init__(self, rule_config_path: Path | None = None):
        self.rule_config_path = rule_config_path or self._default_rule_config_path()
        self.unclear_reference_config = self._load_rule_config("unclearReference")

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
                if token.text.lower() not in self.unclear_reference_config.terms:
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
                        reason=self.unclear_reference_config.reason,
                        severity=self.unclear_reference_config.severity,
                        category=self.unclear_reference_config.category,
                        start_char=token.start_char,
                        end_char=token.end_char,
                        sentence=sentence.text,
                        evidence="A reference term was found without a single clear noun antecedent in the current or previous sentence.",
                    )
                )

        return ambiguities

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

    #---------- <Summary> ----------
    # Summary: Loads reference ambiguity terms and metadata from JSON configuration.
    #---------- </Summary> ----------
    def _load_rule_config(self, rule_name: str) -> ReferenceAmbiguityRuleConfig:
        with self.rule_config_path.open("r", encoding="utf-8") as file:
            rules = json.load(file)

        if rule_name not in rules:
            raise ValueError(f"Unsupported reference ambiguity rule: {rule_name}")

        raw_rule = rules[rule_name]

        return ReferenceAmbiguityRuleConfig(
            rule_name=rule_name,
            terms=raw_rule["terms"],
            reason=raw_rule["reason"],
            severity=raw_rule["severity"],
            category=raw_rule["category"],
        )

    #---------- <Summary> ----------
    # Summary: Returns the default JSON config path for reference ambiguity rules.
    #---------- </Summary> ----------
    def _default_rule_config_path(self) -> Path:
        return (
            Path(__file__).resolve().parents[2]
            / "infrastructure"
            / "data"
            / "reference_ambiguity_rules.json"
        )
