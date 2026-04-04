import json

from app.llm.base import LlmProvider


class MockProvider(LlmProvider):
    def generate(self, prompt: str) -> str:
        mock_response = {
            "userStory": "As a user, I want a fast and user-friendly system, so that I can complete tasks efficiently.(mock)",
            "requirementType": "Usability",
            "ambiguities": [
                {
                    "phrase": "fast",
                    "reason": "Not measurable",
                    "severity": "High"
                },
                {
                    "phrase": "user-friendly",
                    "reason": "Subjective term",
                    "severity": "High"
                }
            ],
            "suggestions": [
                {
                    "originalPart": "fast",
                    "suggestedPart": "respond within 2 seconds",
                    "reason": "Makes requirement measurable"
                }
            ],
            "improvedText": "The system should respond within 2 seconds and provide an intuitive interface."
        }

        return json.dumps(mock_response)