import json
import logging

from app.llm.provider_factory import LlmProviderFactory
from app.prompts.requirement_analysis_prompt import build_requirement_analysis_prompt

logger = logging.getLogger(__name__)


class AnalysisService:
    def analyze(self, text: str, provider: str) -> dict:
        logger.info("Analyze request started. Provider: %s", provider)

        prompt = build_requirement_analysis_prompt(text)

        try:
            llm_provider = LlmProviderFactory.create(provider)
            raw_response = llm_provider.generate(prompt)

            parsed = self._parse_response(raw_response)

            logger.info("Analyze request completed successfully. Provider: %s", provider)

            return {
                "originalText": text,
                "userStory": parsed["userStory"],
                "requirementType": parsed["requirementType"],
                "ambiguities": parsed["ambiguities"],
                "suggestions": parsed["suggestions"],
                "improvedText": parsed["improvedText"],
                "providerUsed": provider,
                "isFallback": False,
                "warnings": [],
                "errors": []
            }

        except Exception as e:
            logger.error("Provider failed. Falling back to mock. Error: %s", str(e))

            # fallback → mock
            mock_provider = LlmProviderFactory.create("mock")
            raw_response = mock_provider.generate(prompt)
            parsed = self._parse_response(raw_response)

            return {
                "originalText": text,
                "userStory": parsed["userStory"],
                "requirementType": parsed["requirementType"],
                "ambiguities": parsed["ambiguities"],
                "suggestions": parsed["suggestions"],
                "improvedText": parsed["improvedText"],
                "providerUsed": provider,
                "isFallback": True,
                "warnings": ["Selected provider failed. Mock response returned."],
                "errors": [str(e)]
            }

    def _parse_response(self, raw_response: str) -> dict:
        cleaned_response = raw_response.strip()

        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response.replace("```json", "", 1).strip()

        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3].strip()

        return json.loads(cleaned_response)