import spacy

from app.application.ports.nlp_processor import NlpProcessorPort
from app.domain.pre_analysis import (
    AnalyzedSentence,
    AnalyzedText,
    AnalyzedToken,
    ExtractedNounPhrase,
)


#---------- <Summary> ----------
# Summary: Runs spaCy NLP and maps spaCy objects into domain pre-analysis models.
#---------- </Summary> ----------
class SpacyNlpProcessor(NlpProcessorPort):
    def __init__(self, model_name: str = "en_core_web_trf"):
        self.nlp = spacy.load(model_name)

    #---------- <Summary> ----------
    # Summary: Analyzes text with spaCy and returns sentences, tokens, and noun phrases.
    #---------- </Summary> ----------
    def analyze(self, text: str) -> AnalyzedText:
        doc = self.nlp(text)

        sentences = [
            AnalyzedSentence(
                text=sentence.text,
                start_char=sentence.start_char,
                end_char=sentence.end_char,
                tokens=[
                    AnalyzedToken(
                        text=token.text,
                        lemma=token.lemma_,
                        pos=token.pos_,
                        dependency=token.dep_,
                        start_char=token.idx,
                        end_char=token.idx + len(token.text),
                    )
                    for token in sentence
                ],
            )
            for sentence in doc.sents
        ]

        noun_phrases = [
            ExtractedNounPhrase(
                text=chunk.text,
                root_text=chunk.root.text,
                root_dependency=chunk.root.dep_,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
            )
            for chunk in doc.noun_chunks
        ]

        return AnalyzedText(
            original_text=text,
            sentences=sentences,
            noun_phrases=noun_phrases,
        )
