from abc import ABC, abstractmethod

from app.domain.pre_analysis import AnalyzedText


#---------- <Summary> ----------
# Summary: Contract for NLP processors used before prompt generation.
#---------- </Summary> ----------
class NlpProcessorPort(ABC):

    @abstractmethod
    #---------- <Summary> ----------
    # Summary: Analyzes cleaned text and returns structured NLP information.
    #---------- </Summary> ----------
    def analyze(self, text: str) -> AnalyzedText:
        pass
