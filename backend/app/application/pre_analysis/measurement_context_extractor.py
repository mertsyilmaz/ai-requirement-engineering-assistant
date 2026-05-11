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
        measured_item = self._find_measured_item(sentence, expressions)
        nearby_action = self._find_nearby_action(sentence, expressions)

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
            measured_item=self._filter_redundant_measured_item(
                measured_item,
                nearby_action,
            ),
            nearby_action=nearby_action,
            condition=self._find_condition_phrase(sentence, expressions),
        )

    #---------- <Summary> ----------
    # Summary: Avoids repeating an action object as the measured item.
    #---------- </Summary> ----------
    def _filter_redundant_measured_item(
        self,
        measured_item: str | None,
        nearby_action: str | None,
    ) -> str | None:
        if not measured_item or not nearby_action:
            return measured_item

        if measured_item.lower() in nearby_action.lower():
            return None

        return measured_item

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
    # Summary: Leaves statistical wording unset unless it is represented by reliable measurements.
    #---------- </Summary> ----------
    def _find_statistical_target(self, _sentence: AnalyzedSentence) -> str | None:
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
            stop_char=first_time.start_char,
        )

    #---------- <Summary> ----------
    # Summary: Collects a compact noun phrase around one known noun token.
    #---------- </Summary> ----------
    def _collect_noun_phrase_around(
        self,
        tokens: list[AnalyzedToken],
        noun_token: AnalyzedToken,
        stop_char: int | None = None,
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
            if stop_char is not None and next_token.start_char >= stop_char:
                break

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
                and token.dependency not in {"aux", "auxpass", "amod"}
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
    # Summary: Finds the end of the primary measurement expression.
    #---------- </Summary> ----------
    def _target_expression_end(
        self,
        expressions: list[MeasurableExpression],
    ) -> int:
        time_expressions = [
            expression
            for expression in expressions
            if expression.category == "time"
        ]
        target_expressions = time_expressions or expressions
        first_expression = min(
            target_expressions,
            key=lambda expression: expression.start_char,
        )

        return first_expression.end_char

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
        target_start = self._target_expression_start(expressions)
        target_end = self._target_expression_end(expressions)
        after_target: list[tuple[int, str]] = []
        before_target: list[tuple[int, str]] = []

        for index, token in enumerate(sentence.tokens):
            if token.pos != "ADP":
                continue

            if self._starts_measurable_expression(token, expressions):
                continue

            if self._is_percentage_complement_preposition(token, expressions):
                continue

            stop_char = target_start if token.start_char < target_start else None
            phrase_tokens = self._collect_condition_tokens(
                sentence.tokens,
                index,
                stop_char,
            )
            if not phrase_tokens:
                continue

            if self._tokens_overlap_expression(phrase_tokens, expressions):
                continue

            if self._is_action_complement_before_frequency(
                token,
                phrase_tokens,
                sentence,
                expressions,
            ):
                continue

            if self._phrase_governs_target_expression(
                phrase_tokens,
                sentence,
                expressions,
            ):
                continue

            phrase = self._join_phrase_tokens(phrase_tokens)
            if self._same_as_measured_item(phrase, sentence, expressions):
                continue

            phrase_start = phrase_tokens[0].start_char
            phrase_end = phrase_tokens[-1].end_char
            if phrase_start >= target_end:
                after_target.append((phrase_start, phrase))
                continue

            if phrase_end <= target_start:
                before_target.append((phrase_end, phrase))

        if after_target:
            return min(after_target, key=lambda item: item[0])[1]

        if before_target:
            return max(before_target, key=lambda item: item[0])[1]

        return None

    #---------- <Summary> ----------
    # Summary: Avoids treating action complements as conditions for recurring intervals.
    #---------- </Summary> ----------
    def _is_action_complement_before_frequency(
        self,
        preposition: AnalyzedToken,
        phrase_tokens: list[AnalyzedToken],
        sentence: AnalyzedSentence,
        expressions: list[MeasurableExpression],
    ) -> bool:
        target_expression = self._target_expression(expressions)
        if target_expression.category != "frequency":
            return False

        if phrase_tokens[-1].end_char > target_expression.start_char:
            return False

        measured_verb = self._find_measured_verb(sentence, expressions)
        if not measured_verb or not preposition.head_text:
            return False

        return (
            preposition.dependency == "prep"
            and preposition.head_text == measured_verb.text
        )

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
    # Summary: Skips metric phrases that syntactically govern the time expression.
    #---------- </Summary> ----------
    def _phrase_governs_target_expression(
        self,
        phrase_tokens: list[AnalyzedToken],
        sentence: AnalyzedSentence,
        expressions: list[MeasurableExpression],
    ) -> bool:
        target_expression = self._target_expression(expressions)
        first_target_token = self._first_token_in_expression(
            sentence,
            target_expression,
        )
        if not first_target_token or not first_target_token.head_text:
            return False

        phrase_texts = {token.text for token in phrase_tokens}
        return first_target_token.head_text in phrase_texts

    #---------- <Summary> ----------
    # Summary: Returns the primary measurement expression used for context.
    #---------- </Summary> ----------
    def _target_expression(
        self,
        expressions: list[MeasurableExpression],
    ) -> MeasurableExpression:
        time_expressions = [
            expression
            for expression in expressions
            if expression.category == "time"
        ]
        target_expressions = time_expressions or expressions

        return min(target_expressions, key=lambda expression: expression.start_char)

    #---------- <Summary> ----------
    # Summary: Finds the first token inside one measurable expression.
    #---------- </Summary> ----------
    def _first_token_in_expression(
        self,
        sentence: AnalyzedSentence,
        expression: MeasurableExpression,
    ) -> AnalyzedToken | None:
        for token in sentence.tokens:
            if expression.start_char <= token.start_char < expression.end_char:
                return token

        return None

    #---------- <Summary> ----------
    # Summary: Collects tokens for a compact prepositional phrase.
    #---------- </Summary> ----------
    def _collect_condition_tokens(
        self,
        tokens: list[AnalyzedToken],
        start_index: int,
        stop_char: int | None = None,
    ) -> list[AnalyzedToken]:
        phrase_tokens = [tokens[start_index]]

        for token in tokens[start_index + 1:]:
            if stop_char is not None and token.start_char >= stop_char:
                break

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
            return []

        return phrase_tokens

    #---------- <Summary> ----------
    # Summary: Avoids treating the measurable expression itself as a condition phrase.
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
