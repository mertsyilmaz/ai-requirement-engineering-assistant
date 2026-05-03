from abc import ABC, abstractmethod


#---------- <Summary> ----------
# Summary: Contract for LLM providers such as Gemini or Mock.
#---------- </Summary> ----------
class LlmProviderPort(ABC):

    @abstractmethod
    #---------- <Summary> ----------
    # Summary: Sends a prompt to the provider and returns the raw text response.
    #---------- </Summary> ----------
    def generate(self, prompt: str) -> str:
        pass
