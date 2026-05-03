from pydantic import BaseModel, Field, field_validator


#---------- <Summary> ----------
# Summary: Request body for requirement analysis.
#---------- </Summary> ----------
class AnalyzeRequest(BaseModel):

    text: str = Field(..., min_length=5)
    provider: str = "mock"
    analysisVersion: str = "v1"

    @field_validator("text")
    #---------- <Summary> ----------
    # Summary: Rejects empty or whitespace-only requirement text.
    #---------- </Summary> ----------
    def text_must_not_be_blank(cls, value: str):
        if not value or not value.strip():
            raise ValueError("Text cannot be empty or only whitespace")
        return value.strip()
