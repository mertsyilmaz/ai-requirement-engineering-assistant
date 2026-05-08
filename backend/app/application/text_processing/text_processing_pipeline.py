import re


#---------- <Summary> ----------
# Summary: Normalizes raw requirement text before analysis or prompt generation.
#---------- </Summary> ----------
#---------- <Summary> ----------
# Summary: Returns cleaned text while preserving the original meaning.
#---------- </Summary> ----------
class TextProcessingPipeline:

    def process(self, text: str) -> str:
        processed_text = self._normalize_whitespace(text)
        processed_text = self._normalize_quotes(processed_text)
        processed_text = self._normalize_spacing_around_punctuation(processed_text)

        return processed_text.strip()

    #---------- <Summary> ----------
    # Summary: Collapses repeated whitespace into a single space.
    #---------- </Summary> ----------
    def _normalize_whitespace(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    #---------- <Summary> ----------
    # Summary: Converts smart quotes to standard ASCII quotes.
    #---------- </Summary> ----------
    def _normalize_quotes(self, text: str) -> str:
        return (
            text.replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2018", "'")
            .replace("\u2019", "'")
        )

    #---------- <Summary> ----------
    # Summary: Fixes spacing before and after common punctuation marks.
    #---------- </Summary> ----------
    def _normalize_spacing_around_punctuation(self, text: str) -> str:
        text = re.sub(r"\s+([.,;:!?])", r"\1", text)
        text = re.sub(r"([.,;:!?])(?=\S)", self._space_after_punctuation, text)

        return text.strip()

    #---------- <Summary> ----------
    # Summary: Adds punctuation spacing without breaking decimal or thousands numbers.
    #---------- </Summary> ----------
    def _space_after_punctuation(self, match: re.Match) -> str:
        punctuation = match.group(1)
        text = match.string
        index = match.start(1)
        previous_char = text[index - 1] if index > 0 else ""
        next_char = text[index + 1] if index + 1 < len(text) else ""

        if (
            punctuation in {".", ","}
            and previous_char.isdigit()
            and next_char.isdigit()
        ):
            return punctuation

        return f"{punctuation} "
