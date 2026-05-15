from pydantic import BaseModel, Field

from app.contracts.enriched_prompt import EnrichedPromptExport
from app.contracts.motion_spec import MotionSpec
from app.contracts.procedural_gesture import ProceduralGestureJson
from app.contracts.runtime_behavior import BehaviorJson


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


class RuntimeRespondResponse(BaseModel):
    reply: str = Field(..., min_length=1)
    behavior: BehaviorJson
