from app.llm.base import LlmProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.mock_provider import MockProvider


class LlmProviderFactory:
    @staticmethod
    def create(provider_name: str) -> LlmProvider:
        provider_name = provider_name.lower()

        if provider_name == "gemini":
            return GeminiProvider()

        if provider_name == "mock":
            return MockProvider()

        raise ValueError(f"Unsupported provider: {provider_name}")