from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.contracts.motion_spec import MotionSpec


class EnrichedPromptExport(BaseModel):
    export_id: str = Field(..., alias="exportId")
    original_prompt: str = Field(..., alias="originalPrompt")
    enriched_prompt: str = Field(..., alias="enrichedPrompt")
    motion_spec: MotionSpec = Field(..., alias="motionSpec")
    created_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="createdAtUtc",
    )
    target_provider_hint: str = Field("deepmotion_web_manual", alias="targetProviderHint")

    model_config = {
        "populate_by_name": True,
    }

