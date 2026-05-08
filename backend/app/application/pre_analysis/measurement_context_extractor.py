from app.domain.pre_analysis import (
    AnalyzedSentence,
    AnalyzedText,
    AnalyzedToken,
    MeasurableExpression,
    MeasurementContext,
)


#---------- <Summary> ----------
# Summary: Extracts structural measurement context for the LLM without judging ambiguity.
#
# This extractor does not decide that a phrase is wrong or ambiguous. It packages
# NLP-derived context such as percentage subject, related action, time target,
# and condition phrase so the LLM can make a better requirements-engineering
# interpretation.
#---------- </Summary> ----------
class MeasurementContextExtractor:

    #---------- <Summary> ----------
    # Summary: Returns one measurement context per sentence that contains measurable data.
    #---------- </Summary> ----------
    def extract(
        self,
        analyzed_text: AnalyzedText,
        measurable_expressions: list[MeasurableExpression],
    ) -> list[MeasurementContext]:
        contexts: list[MeasurementContext] = []

        for sentence in analyzed_text.sentences:
            sentence_expressions = [
                expression
                for expression in measurable_expressions
                if expression.text in sentence.text
            ]
            if not sentence_expressions:
                continue

            context = self._build_context(sentence, sentence_expressions)
            if self._has_context_observation(context):
                contexts.append(context)

        return contexts

    #---------- <Summary> ----------
    # Summary: Builds structural context from measurable expressions in one sentence.
    #---------- </Summary> ----------
    def _build_context(
        self,
        sentence: AnalyzedSentence,
        expressions: list[MeasurableExpression],
    ) -> MeasurementContext:
        time_target = self._first_expression_text(expressions, "time")
        percentage_target = self._last_expression_text(expressions, "percentage")

        return MeasurementContext(
            sentence=sentence.text,
            time_target=time_target,
            percentage_target=percentage_target,
            percentage_subject=self._find_percentage_subject(
                sentence,
                percentage_target,
            ),
            count_target=self._first_expression_text(expressions, "count"),
            load_context=self._find_load_context(sentence, expressions),
            statistical_target=self._find_statistical_target(sentence),
            measured_item=self._find_measured_item(sentence, expressions),
            nearby_action=self._find_nearby_action(sentence, expressions),
            condition=self._find_condition_phrase(sentence, expressions),
        )

    #---------- <Summary> ----------
    # Summary: Returns the first measurable expression text for a category.
    #---------- </Summary> ----------
    def _first_expression_text(
        self,
        expressions: list[MeasurableExpression],
        category: str,
    ) -> str | None:
        for expression in expressions:
            if expression.category == category:
                return expression.text

        return None

    #---------- <Summary> ----------
    # Summary: Returns the last measurable expression text for a category.
    #---------- </Summary> ----------
    def _last_expression_text(
        self,
        expressions: list[MeasurableExpression],
        category: str,
    ) -> str | None:
        for expression in reversed(expressions):
            if expression.category == category:
                return expression.text

        return None

    #---------- <Summary> ----------
    # Summary: Finds count-based load context such as "5000 concurrent users".
    #---------- </Summary> ----------
    def _find_load_context(
        self,
        sentence: AnalyzedSentence,
        expressions: list[MeasurableExpression],
    ) -> str | None:
        count_expressions = [
            expression
            for expression in expressions
            if expression.category == "count"
        ]
        if not count_expressions:
            return None

        first_count = min(count_expressions, key=lambda expression: expression.start_char)

        for token in sentence.tokens:
            if token.start_char <= first_count.start_char < token.end_char:
                return self._collect_noun_phrase_around(sentence.tokens, token)

        return first_count.text

    #---------- <Summary> ----------
    # Summary: Extracts statistical wording such as average, median, maximum, or percentile.
    #---------- </Summary> ----------
    def _find_statistical_target(self, sentence: AnalyzedSentence) -> str | None:
        for token in sentence.tokens:
            if token.lemma.lower() in {"average", "median", "maximum", "minimum"}:
                return token.text

            if "percentile" in token.lemma.lower():
                return token.text

        return None

    #---------- <Summary> ----------
    # Summary: Finds the noun phrase being measured near a time target.
    #---------- </Summary> ----------
    def _find_measured_item(
        self,
        sentence: AnalyzedSentence,
        expressions: list[MeasurableExpression],
    ) -> str | None:
        time_expressions = [
            expression
            for expression in expressions
            if expression.category == "time"
        ]
        if not time_expressions:
            return None

        first_time = min(time_expressions, key=lambda expression: expression.start_char)
        candidates = [
            token
            for token in sentence.tokens
            if (
                token.end_char <= first_time.start_char
                and token.pos in {"NOUN", "PROPN"}
                and token.dependency in {"pobj", "dobj", "attr", "nsubj"}
            )
        ]
        if not candidates:
            return None

        return self._collect_noun_phrase_around(
            sentence.tokens,
            max(candidates, key=lambda token: token.start_char),
        )

    #---------- <Summary> ----------
    # Summary: Collects a compact noun phrase around one known noun token.
    #---------- </Summary> ----------
    def _collect_noun_phrase_around(
        self,
        tokens: list[AnalyzedToken],
        noun_token: AnalyzedToken,
    ) -> str:
        phrase_tokens: list[AnalyzedToken] = []
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

        for token in tokens[start_index:end_index + 1]:
            phrase_tokens.append(token)

        return " ".join(token.text for token in phrase_tokens)

    #---------- <Summary> ----------
    # Summary: Extracts the noun phrase attached to a percentage target.
    #---------- </Summary> ----------
    def _find_percentage_subject(
        self,
        sentence: AnalyzedSentence,
        percentage_target: str | None,
    ) -> str | None:
        if not percentage_target:
            return None

        percentage_start = sentence.text.find(percentage_target)
        if percentage_start < 0:
            return None

        absolute_percentage_end = sentence.start_char + percentage_start + len(
            percentage_target
        )

        for index, token in enumerate(sentence.tokens):
            if token.start_char < absolute_percentage_end:
                continue

            if token.text.lower() != "of":
                continue

            return self._collect_noun_phrase_after(sentence.tokens, index + 1)

        return None

    #---------- <Summary> ----------
    # Summary: Collects a compact noun phrase after a known token index.
    #---------- </Summary> ----------
    def _collect_noun_phrase_after(
        self,
        tokens: list[AnalyzedToken],
        start_index: int,
    ) -> str | None:
        phrase_tokens: list[AnalyzedToken] = []

        for token in tokens[start_index:]:
            if token.pos in {"DET", "ADJ", "NOUN", "PROPN", "NUM"}:
                phrase_tokens.append(token)
                continue

            if phrase_tokens:
                break

        if not phrase_tokens:
            return None

        return " ".join(token.text for token in phrase_tokens)

    #---------- <Summary> ----------
    # Summary: Extracts the main measured action around the sentence root verb.
    #---------- </Summary> ----------
    def _find_nearby_action(
        self,
        sentence: AnalyzedSentence,
        expressions: list[MeasurableExpression],
    ) -> str | None:
        root = self._find_measured_verb(sentence, expressions)
        if not root:
            return None

        action_tokens = [
            token
            for token in sentence.tokens
            if (
                token.start_char >= root.start_char
                and token.pos not in {"PUNCT", "CCONJ"}
                and token.dependency not in {"aux", "mark"}
            )
        ]
        if not action_tokens:
            return root.text

        bounded_tokens: list[AnalyzedToken] = []
        for token in action_tokens:
            if self._starts_measurable_expression(token, expressions):
                break

            if token.pos == "ADP" and self._precedes_measurable_expression(
                token,
                expressions,
            ):
                break

            if token.pos == "ADP" and token.text.lower() in {"within", "under", "for"}:
                break

            bounded_tokens.append(token)

        if not bounded_tokens:
            return root.text

        return " ".join(token.text for token in bounded_tokens).strip()

    #---------- <Summary> ----------
    # Summary: Detects prepositions that introduce a measurable phrase.
    #---------- </Summary> ----------
    def _precedes_measurable_expression(
        self,
        token: AnalyzedToken,
        expressions: list[MeasurableExpression],
    ) -> bool:
        return any(
            token.start_char < expression.start_char
            and expression.start_char - token.end_char <= 24
            for expression in expressions
        )

    #---------- <Summary> ----------
    # Summary: Selects the content verb nearest to the first measurement expression.
    #---------- </Summary> ----------
    def _find_measured_verb(
        self,
        sentence: AnalyzedSentence,
        expressions: list[MeasurableExpression],
    ) -> AnalyzedToken | None:
        first_expression_start = self._target_expression_start(expressions)
        previous_verbs = [
            token
            for token in sentence.tokens
            if (
                token.pos == "VERB"
                and token.end_char <= first_expression_start
                and token.dependency not in {"aux", "auxpass"}
            )
        ]

        if previous_verbs:
            return max(previous_verbs, key=lambda token: token.start_char)

        return self._find_root_verb(sentence)

    #---------- <Summary> ----------
    # Summary: Prefers duration targets over supporting counts or recurring intervals.
    #---------- </Summary> ----------
    def _target_expression_start(
        self,
        expressions: list[MeasurableExpression],
    ) -> int:
        time_expressions = [
            expression
            for expression in expressions
            if expression.category == "time"
        ]
        target_expressions = time_expressions or expressions

        return min(expression.start_char for expression in target_expressions)

    #---------- <Summary> ----------
    # Summary: Detects whether token collection reached a known measurement span.
    #---------- </Summary> ----------
    def _starts_measurable_expression(
        self,
        token: AnalyzedToken,
        expressions: list[MeasurableExpression],
    ) -> bool:
        return any(
            expression.start_char <= token.start_char < expression.end_char
            for expression in expressions
        )

    #---------- <Summary> ----------
    # Summary: Finds the root content verb of a sentence.
    #---------- </Summary> ----------
    def _find_root_verb(self, sentence: AnalyzedSentence) -> AnalyzedToken | None:
        for token in sentence.tokens:
            if token.dependency == "ROOT" and token.pos == "VERB":
                return token

        for token in sentence.tokens:
            if token.pos == "VERB":
                return token

        return None

    #---------- <Summary> ----------
    # Summary: Extracts a condition phrase such as "under peak load".
    #---------- </Summary> ----------
    def _find_condition_phrase(
        self,
        sentence: AnalyzedSentence,
        expressions: list[MeasurableExpression],
    ) -> str | None:
        preferred_phrase: str | None = None

        for index, token in enumerate(sentence.tokens):
            if token.pos != "ADP":
                continue

            if self._starts_measurable_expression(token, expressions):
                continue

            if token.text.lower() in {"within", "for", "to", "of"}:
                continue

            phrase = self._collect_condition_phrase(sentence.tokens, index)
            if phrase:
                if self._same_as_measured_item(phrase, sentence, expressions):
                    continue

                if self._looks_like_operating_condition(phrase):
                    return phrase

                preferred_phrase = preferred_phrase or phrase

        return preferred_phrase

    #---------- <Summary> ----------
    # Summary: Avoids repeating the measured item as a condition phrase.
    #---------- </Summary> ----------
    def _same_as_measured_item(
        self,
        phrase: str,
        sentence: AnalyzedSentence,
        expressions: list[MeasurableExpression],
    ) -> bool:
        measured_item = self._find_measured_item(sentence, expressions)

        return bool(measured_item and phrase.lower() == f"with {measured_item}".lower())

    #---------- <Summary> ----------
    # Summary: Prioritizes phrases that look like operating or environmental conditions.
    #---------- </Summary> ----------
    def _looks_like_operating_condition(self, phrase: str) -> bool:
        normalized_phrase = phrase.lower()

        return any(
            word in normalized_phrase
            for word in {"load", "condition", "environment", "traffic", "capacity"}
        )

    #---------- <Summary> ----------
    # Summary: Collects a prepositional condition phrase from token context.
    #---------- </Summary> ----------
    def _collect_condition_phrase(
        self,
        tokens: list[AnalyzedToken],
        start_index: int,
    ) -> str | None:
        phrase_tokens = [tokens[start_index]]

        for token in tokens[start_index + 1:]:
            if token.pos in {"DET", "ADJ", "NOUN", "PROPN", "NUM"}:
                phrase_tokens.append(token)
                continue

            if token.pos == "VERB" and token.dependency in {"amod", "acl"}:
                phrase_tokens.append(token)
                continue

            if token.pos == "ADP" and token.text.lower() == "of":
                phrase_tokens.append(token)
                continue

            if token.pos == "PUNCT" and token.text == "-":
                phrase_tokens.append(token)
                continue

            break

        if len(phrase_tokens) < 2:
            return None

        return self._join_phrase_tokens(phrase_tokens)

    #---------- <Summary> ----------
    # Summary: Joins condition tokens while preserving hyphenated phrases cleanly.
    #---------- </Summary> ----------
    def _join_phrase_tokens(self, tokens: list[AnalyzedToken]) -> str:
        text = " ".join(token.text for token in tokens)

        return text.replace(" - ", "-")

    #---------- <Summary> ----------
    # Summary: Keeps only contexts that contain useful structural observations.
    #---------- </Summary> ----------
    def _has_context_observation(self, context: MeasurementContext) -> bool:
        return any(
            [
                context.percentage_subject,
                context.load_context,
                context.statistical_target,
                context.measured_item,
                context.nearby_action,
                context.condition,
            ]
        )
