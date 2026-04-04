def build_requirement_analysis_prompt(text: str) -> str:
    return f"""
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
- The userStory MUST strictly follow this format:
  "As a <type of user>, I want <goal>, so that <reason>."
- Do not use any other user story format.
- requirementType must be one of: Functional, Performance, Security, Usability, Reliability, Other
- ambiguities must be an array of objects with: phrase, reason, severity
- suggestions must be an array of objects with: originalPart, suggestedPart, reason
- Return only valid JSON

Example user story:
"As a user, I want to log into the system, so that I can access my account."
"""