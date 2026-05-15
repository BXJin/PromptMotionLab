from pydantic import BaseModel, Field

from app.contracts.motion_spec import MotionSpec
from app.contracts.runtime_behavior import SceneContext


class AnalyzeIntentRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    skeleton_preset: str = Field("ue5_manny", alias="skeletonPreset")

    model_config = {"populate_by_name": True}


class ProceduralGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    skeleton_preset: str = Field("ue5_manny", alias="skeletonPreset")

    model_config = {"populate_by_name": True}


class EnrichedPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    motion_spec: MotionSpec | None = Field(None, alias="motionSpec")
    skeleton_preset: str = Field("ue5_manny", alias="skeletonPreset")

    model_config = {"populate_by_name": True}


class RuntimeRespondRequest(BaseModel):
    session_id: str = Field("demo_session", min_length=1, alias="sessionId")
    character_id: str = Field("default_guide", min_length=1, alias="characterId")
    message: str = Field(..., min_length=1)
    scene_context: SceneContext = Field(default_factory=SceneContext, alias="sceneContext")

    model_config = {"populate_by_name": True}
