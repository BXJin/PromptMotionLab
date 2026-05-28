from pydantic import BaseModel, Field


class SpeechAudio(BaseModel):
    url: str
    duration_seconds: float = Field(..., ge=0.0, alias="durationSeconds")
    format: str = "wav"

    model_config = {"populate_by_name": True}


class SpeechViseme(BaseModel):
    time: float = Field(..., ge=0.0)
    id: int = Field(..., ge=0)
    weight: float = Field(1.0, ge=0.0, le=1.0)


class SpeechSegment(BaseModel):
    segment_id: str = Field(..., alias="segmentId")
    index: int = Field(..., ge=0)
    text: str = Field(..., min_length=1)
    start_time: float = Field(..., ge=0.0, alias="startTime")
    duration_seconds: float = Field(..., ge=0.0, alias="durationSeconds")
    audio: SpeechAudio
    visemes: list[SpeechViseme] = Field(default_factory=list)
    tts_latency_ms: int = Field(..., ge=0, alias="ttsLatencyMs")

    model_config = {"populate_by_name": True}


class SpeechTimeline(BaseModel):
    utterance_id: str = Field(..., alias="utteranceId")
    audio: SpeechAudio
    visemes: list[SpeechViseme] = Field(default_factory=list)
    segments: list[SpeechSegment] = Field(default_factory=list)
    provider: str
    model: str
    tts_latency_ms: int = Field(..., ge=0, alias="ttsLatencyMs")

    model_config = {"populate_by_name": True}
