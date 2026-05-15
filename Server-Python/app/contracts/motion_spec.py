from enum import StrEnum

from pydantic import BaseModel, Field


class GestureName(StrEnum):
    WAVE = "wave"
    POINT = "point"
    BOW = "bow"
    NOD = "nod"
    EXPLAIN = "explain"


class HandSide(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"
    NONE = "none"


class BodyScope(StrEnum):
    UPPER_BODY = "upper_body"
    FULL_BODY = "full_body"


class MotionSpec(BaseModel):
    gesture: GestureName = Field(..., description="Primary gesture intent.")
    hand: HandSide = Field(HandSide.RIGHT, description="Dominant hand for the gesture.")
    emotion: str = Field("neutral", min_length=1, max_length=40)
    style: str = Field("natural", min_length=1, max_length=60)
    body_scope: BodyScope = Field(BodyScope.UPPER_BODY, alias="bodyScope")
    duration_seconds: float = Field(1.8, ge=0.3, le=10.0, alias="durationSeconds")
    speed: float = Field(1.0, ge=0.2, le=3.0)
    amplitude: float = Field(0.6, ge=0.0, le=1.0)
    feet_planted: bool = Field(True, alias="feetPlanted")
    root_motion: bool = Field(False, alias="rootMotion")
    skeleton_preset: str = Field("ue5_manny", alias="skeletonPreset")

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }

