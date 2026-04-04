from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=5)
    provider: str = "mock"

    @field_validator("text")
    def text_must_not_be_blank(cls, value: str):
        if not value or not value.strip():
            raise ValueError("Text cannot be empty or only whitespace")
        return value.strip()