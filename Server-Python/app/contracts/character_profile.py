from pydantic import BaseModel, Field


class CharacterProfile(BaseModel):
    character_id: str = Field(..., alias="characterId")
    display_name: str = Field(..., alias="displayName")
    persona: str
    speech_style: str = Field(..., alias="speechStyle")
    default_emotion: str = Field("friendly", alias="defaultEmotion")
    emotion_intensity_scale: float = Field(1.0, ge=0.5, le=1.5, alias="emotionIntensityScale")
    energy: float = Field(0.5, ge=0.0, le=1.0)
    empathy: float = Field(0.5, ge=0.0, le=1.0)
    imagination: float = Field(0.5, ge=0.0, le=1.0)
    playfulness: float = Field(0.35, ge=0.0, le=1.0)
    follow_up_tendency: float = Field(0.45, ge=0.0, le=1.0, alias="followUpTendency")
    reply_length: float = Field(0.35, ge=0.0, le=1.0, alias="replyLength")
    speech_register: str = Field("casual_polite", alias="speechRegister")
    response_examples: list[str] = Field(default_factory=list, alias="responseExamples")

    model_config = {"populate_by_name": True}
