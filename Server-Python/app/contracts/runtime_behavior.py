from enum import StrEnum

from pydantic import BaseModel, Field


class RuntimeEmotion(StrEnum):
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    HAPPY = "happy"
    THINKING = "thinking"
    CURIOUS = "curious"
    CONCERNED = "concerned"
    UNCERTAIN = "uncertain"
    APOLOGETIC = "apologetic"


class RuntimeIntent(StrEnum):
    GREET = "greet"
    EXPLAIN = "explain"
    ANSWER = "answer"
    CLARIFY = "clarify"
    REFUSE = "refuse"
    FALLBACK = "fallback"


class RuntimeGaze(StrEnum):
    USER = "user"
    FOCUSED_OBJECT = "focused_object"
    DOWN_LEFT = "down_left"
    SIDE = "side"
    NONE = "none"


class RuntimeGestureKey(StrEnum):
    NONE = "none"
    SMALL_ACK = "small_ack"
    EXPLAIN_SMALL = "explain_small"
    POINT_SOFT = "point_soft"
    HESITATE = "hesitate"
    GREET_SMALL = "greet_small"


class RuntimeHeadMotion(StrEnum):
    NONE = "none"
    SMALL_NOD = "small_nod"
    SMALL_TILT = "small_tilt"
    THINKING_TILT = "thinking_tilt"


class RuntimeTtsStyle(StrEnum):
    NEUTRAL = "neutral"
    WARM = "warm"
    CAREFUL = "careful"
    ENERGETIC = "energetic"


class SceneContext(BaseModel):
    location_id: str | None = Field(None, alias="locationId")
    focused_object_id: str | None = Field(None, alias="focusedObjectId")
    nearby_object_ids: list[str] = Field(default_factory=list, alias="nearbyObjectIds")
    interaction_mode: str | None = Field(None, alias="interactionMode")

    model_config = {"populate_by_name": True}


class BehaviorJson(BaseModel):
    emotion: RuntimeEmotion = RuntimeEmotion.FRIENDLY
    intensity: float = Field(0.6, ge=0.0, le=1.0)
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    intent: RuntimeIntent = RuntimeIntent.ANSWER
    gaze: RuntimeGaze = RuntimeGaze.USER
    gesture_key: RuntimeGestureKey = Field(RuntimeGestureKey.SMALL_ACK, alias="gestureKey")
    head_motion: RuntimeHeadMotion = Field(RuntimeHeadMotion.SMALL_NOD, alias="headMotion")
    tts_style: RuntimeTtsStyle = Field(RuntimeTtsStyle.WARM, alias="ttsStyle")

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }
