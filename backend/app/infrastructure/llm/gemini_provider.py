import google.generativeai as genai

from app.core.config import Settings
from app.application.ports.llm_provider import LlmProviderPort


class GeminiProvider(LlmProviderPort):
    def __init__(self):
        genai.configure(api_key=Settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def generate(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text