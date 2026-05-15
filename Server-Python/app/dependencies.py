from functools import lru_cache
import os
from pathlib import Path

from app.providers.llm import MockLlmProvider
from app.providers.runtime import OpenAiRuntimeBehaviorProvider
from app.services import MotionGenerationService, RuntimeCharacterService
from app.storage import PromptExportStore


@lru_cache(maxsize=1)
def get_motion_generation_service() -> MotionGenerationService:
    data_root = Path(__file__).resolve().parent.parent / "data" / "prompt_exports"
    return MotionGenerationService(
        llm_provider=MockLlmProvider(),
        prompt_store=PromptExportStore(data_root),
    )


@lru_cache(maxsize=1)
def get_runtime_character_service() -> RuntimeCharacterService:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
    if not api_key:
        return RuntimeCharacterService()

    return RuntimeCharacterService(
        primary_provider=OpenAiRuntimeBehaviorProvider(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            endpoint=os.getenv("OPENAI_RESPONSES_ENDPOINT", "https://api.openai.com/v1/responses"),
            timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "4.0")),
        ),
        provider_timeout_seconds=float(os.getenv("RUNTIME_PROVIDER_TIMEOUT_SECONDS", "4.5")),
    )
