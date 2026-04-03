import json
import google.generativeai as genai

from app.core.config import Settings


class AnalysisService:
    def __init__(self):
        genai.configure(api_key=Settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def analyze(self, text: str, provider: str) -> dict:
        prompt = f"""
You are a software requirements engineering assistant.

Analyze the following requirement:
{text}

Return a JSON object with these fields:
- userStory
- requirementType
- ambiguities
- suggestions
- improvedText

Rules:
- requirementType must be one of: Functional, Performance, Security, Usability, Reliability, Other
- ambiguities must be an array of objects with: phrase, reason, severity
- suggestions must be an array of objects with: originalPart, suggestedPart, reason
- Return only valid JSON
"""

        response = self.model.generate_content(prompt)
        raw_text = response.text.strip()

        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "", 1).strip()
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3].strip()

        parsed = json.loads(raw_text)

        return {
            "originalText": text,
            "userStory": parsed["userStory"],
            "requirementType": parsed["requirementType"],
            "ambiguities": parsed["ambiguities"],
            "suggestions": parsed["suggestions"],
            "improvedText": parsed["improvedText"]
        }