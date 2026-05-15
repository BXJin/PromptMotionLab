from pydantic import BaseModel, Field


class ProceduralGestureJson(BaseModel):
    gesture: str = Field(..., min_length=1)
    hand: str = Field("right")
    duration_seconds: float = Field(1.8, ge=0.3, le=10.0, alias="durationSeconds")
    speed: float = Field(1.0, ge=0.2, le=3.0)
    amplitude: float = Field(0.6, ge=0.0, le=1.0)
    shoulder_raise: float = Field(0.2, ge=0.0, le=1.0, alias="shoulderRaise")
    elbow_bend: float = Field(0.45, ge=0.0, le=1.0, alias="elbowBend")
    wrist_oscillation: float = Field(0.6, ge=0.0, le=1.0, alias="wristOscillation")
    body_lean: float = Field(0.0, ge=-1.0, le=1.0, alias="bodyLean")
    head_nod: float = Field(0.0, ge=0.0, le=1.0, alias="headNod")
    feet_planted: bool = Field(True, alias="feetPlanted")
    root_motion: bool = Field(False, alias="rootMotion")
    skeleton_preset: str = Field("ue5_manny", alias="skeletonPreset")

    model_config = {
        "populate_by_name": True,
    }

