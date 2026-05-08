import json
from pathlib import Path

from app.application.ports.ambiguity_knowledge_repository import (
    AmbiguityKnowledgeRepositoryPort,
)
from app.domain.pre_analysis import AmbiguityTerm


#---------- <Summary> ----------
# Summary: Loads known ambiguity terms from the local JSON data file.
#---------- </Summary> ----------
class JsonAmbiguityRepository(AmbiguityKnowledgeRepositoryPort):

    def __init__(self, file_path: Path | None = None):
        self.file_path = file_path or self._default_file_path()

    #---------- <Summary> ----------
    # Summary: Returns known ambiguity terms used by KnownAmbiguityDetector.
    #---------- </Summary> ----------
    def get_all_terms(self) -> list[AmbiguityTerm]:
        with self.file_path.open("r", encoding="utf-8-sig") as file:
            raw_terms = json.load(file)

        return [
            AmbiguityTerm(
                phrase=item["phrase"],
                severity=item["severity"],
                category=item["category"],
            )
            for item in raw_terms
        ]

    #---------- <Summary> ----------
    # Summary: Returns the default known ambiguity JSON file path.
    #---------- </Summary> ----------
    def _default_file_path(self) -> Path:
        return Path(__file__).resolve().parents[1] / "data" / "ambiguity_terms.json"
