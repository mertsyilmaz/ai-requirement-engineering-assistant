from abc import ABC, abstractmethod

from app.domain.pre_analysis import AmbiguityTerm


#---------- <Summary> ----------
# Summary: Contract for loading known ambiguity terms from any data source.
#---------- </Summary> ----------
class AmbiguityKnowledgeRepositoryPort(ABC):

    @abstractmethod
    #---------- <Summary> ----------
    # Summary: Returns known ambiguity terms for KnownAmbiguityDetector.
    #---------- </Summary> ----------
    def get_all_terms(self) -> list[AmbiguityTerm]:
        pass
