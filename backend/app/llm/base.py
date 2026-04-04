from abc import ABC, abstractmethod


class LlmProvider(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass