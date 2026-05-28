from pydantic import BaseModel, Field

from app.contracts.enriched_prompt import EnrichedPromptExport
from app.contracts.motion_spec import MotionSpec
from app.contracts.procedural_gesture import ProceduralGestureJson
from app.contracts.runtime_behavior import BehaviorJson
from app.contracts.speech_timeline import SpeechTimeline
from app.contracts.tts import TtsSynthesizeResponse


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "prompt-motion-lab-server"


class AnalyzeIntentResponse(BaseModel):
    motion_spec: MotionSpec = Field(..., alias="motionSpec")

    model_config = {"populate_by_name": True}


class ProceduralGenerationResponse(BaseModel):
    motion_spec: MotionSpec = Field(..., alias="motionSpec")
    procedural_gesture: ProceduralGestureJson = Field(..., alias="proceduralGesture")

    model_config = {"populate_by_name": True}


class EnrichedPromptResponse(BaseModel):
    export: EnrichedPromptExport


class RuntimeResponseMetadata(BaseModel):
    request_id: str = Field(..., alias="requestId")
    provider: str
    model: str
    tech_profile: str = Field(..., alias="techProfile")
    input_mode: str = Field(..., alias="inputMode")
    fallback_used: bool = Field(..., alias="fallbackUsed")
    provider_latency_ms: int = Field(..., alias="providerLatencyMs")
    total_server_ms: int = Field(..., alias="totalServerMs")
    route: str | None = None

    model_config = {"populate_by_name": True}


class RuntimeRespondResponse(BaseModel):
    reply: str = Field(..., min_length=1)
    behavior: BehaviorJson
    metadata: RuntimeResponseMetadata | None = None


class RuntimeAsyncRespondAcceptedResponse(BaseModel):
    job_id: str = Field(..., alias="jobId")
    status: str
    reaction: BehaviorJson

    model_config = {"populate_by_name": True}


class RuntimeAsyncRespondJobResponse(BaseModel):
    job_id: str = Field(..., alias="jobId")
    status: str
    response: RuntimeRespondResponse | None = None
    error: str | None = None

    model_config = {"populate_by_name": True}


class RuntimeTurnAsyncAcceptedResponse(BaseModel):
    turn_job_id: str = Field(..., alias="turnJobId")
    status: str
    reaction: BehaviorJson

    model_config = {"populate_by_name": True}


class RuntimeTurnAsyncJobResponse(BaseModel):
    turn_job_id: str = Field(..., alias="turnJobId")
    status: str
    reaction: BehaviorJson
    response_ready: bool = Field(..., alias="responseReady")
    tts_ready: bool = Field(..., alias="ttsReady")
    response: RuntimeRespondResponse | None = None
    speech_timeline: SpeechTimeline | None = Field(None, alias="speechTimeline")
    error: str | None = None

    model_config = {"populate_by_name": True}
