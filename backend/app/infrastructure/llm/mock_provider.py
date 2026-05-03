import json

from app.application.ports.llm_provider import LlmProviderPort


class MockProvider(LlmProviderPort):
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
            "improvedText": "The system should respond within 2 seconds and provide an intuitive interface.",
            "improvedTextOptions": [
                {
                    "label": "Minimal",
                    "text": "The system should respond within 2 seconds and provide a user-friendly interface.",
                    "reason": "Keeps the original intent while replacing the vague performance term."
                },
                {
                    "label": "Balanced",
                    "text": "The system should respond to common user actions within 2 seconds and provide an intuitive interface.",
                    "reason": "Clarifies the operation scope without adding strict operating conditions."
                },
                {
                    "label": "Strict",
                    "text": "The system should complete 95% of common user actions within 2 seconds under normal load and provide an interface that users can complete key tasks with successfully.",
                    "reason": "Adds measurable performance and usability criteria."
                }
            ]
        }

        return json.dumps(mock_response)
