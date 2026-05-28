from pydantic import BaseModel, Field

from app.contracts.runtime_behavior import RuntimeTtsStyle
from app.contracts.speech_timeline import SpeechTimeline


class TtsSynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    tts_style: RuntimeTtsStyle = Field(RuntimeTtsStyle.WARM, alias="ttsStyle")
    voice: str | None = None

    model_config = {"populate_by_name": True}


class TtsSynthesizeResponse(BaseModel):
    speech_timeline: SpeechTimeline = Field(..., alias="speechTimeline")

    model_config = {"populate_by_name": True}


class TtsAsyncSynthesizeAcceptedResponse(BaseModel):
    job_id: str = Field(..., alias="jobId")
    status: str

    model_config = {"populate_by_name": True}


class TtsAsyncSynthesizeJobResponse(BaseModel):
    job_id: str = Field(..., alias="jobId")
    status: str
    speech_timeline: SpeechTimeline | None = Field(None, alias="speechTimeline")
    error: str | None = None

    model_config = {"populate_by_name": True}
