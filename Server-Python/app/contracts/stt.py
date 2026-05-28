from pydantic import BaseModel, Field


class SttTranscribeResponse(BaseModel):
    text: str
    language: str | None = None
    durationMs: int = Field(0, ge=0)
    provider: str
    model: str
    sttLatencyMs: int = Field(0, ge=0)

