from app.application.ports.llm_provider import LlmProviderPort
from app.infrastructure.llm.gemini_provider import GeminiProvider
from app.infrastructure.llm.mock_provider import MockProvider


#---------- <Summary> ----------
# Summary: Creates the selected LLM provider implementation.
#---------- </Summary> ----------
class LlmProviderFactory:

    @staticmethod
    #---------- <Summary> ----------
    # Summary: Returns a provider instance for names such as gemini or mock.
    #---------- </Summary> ----------
    def create(provider_name: str) -> LlmProviderPort:
        provider_name = provider_name.lower()

        if provider_name == "gemini":
            return GeminiProvider()

        if provider_name == "mock":
            return MockProvider()

        raise ValueError(f"Unsupported provider: {provider_name}")
