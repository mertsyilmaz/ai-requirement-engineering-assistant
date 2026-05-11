import json
from pathlib import Path

from app.domain.pre_analysis import RequirementTypeDefinition


#---------- <Summary> ----------
# Summary: Loads semantic requirement type definitions from local JSON data.
#---------- </Summary> ----------
class JsonRequirementTypeRepository:

    def __init__(self, file_path: Path | None = None):
        self.file_path = file_path or self._default_file_path()

    #---------- <Summary> ----------
    # Summary: Returns requirement type definitions used by V3 semantic analysis.
    #---------- </Summary> ----------
    def get_all_types(self) -> list[RequirementTypeDefinition]:
        with self.file_path.open("r", encoding="utf-8-sig") as file:
            raw_types = json.load(file)

        return [
            RequirementTypeDefinition(
                requirement_type=item["requirementType"],
                description=item["description"],
                checkpoints=item.get("checkpoints", []),
            )
            for item in raw_types
        ]

    #---------- <Summary> ----------
    # Summary: Returns the default requirement type JSON file path.
    #---------- </Summary> ----------
    def _default_file_path(self) -> Path:
        return Path(__file__).resolve().parents[1] / "data" / "requirement_types.json"
