import asyncio
import logging

from app.contracts.runtime_behavior import BehaviorJson, SceneContext
from app.providers.runtime import MockRuntimeBehaviorProvider, RuntimeBehaviorProvider

logger = logging.getLogger(__name__)


class RuntimeCharacterService:
    def __init__(
        self,
        primary_provider: RuntimeBehaviorProvider | None = None,
        fallback_provider: RuntimeBehaviorProvider | None = None,
        provider_timeout_seconds: float = 4.5,
    ) -> None:
        self._primary_provider = primary_provider
        self._fallback_provider = fallback_provider or MockRuntimeBehaviorProvider()
        self._provider_timeout_seconds = provider_timeout_seconds

    async def respond(
        self,
        message: str,
        scene_context: SceneContext,
        character_id: str,
    ) -> tuple[str, BehaviorJson]:
        if self._primary_provider is None:
            return await self._fallback_provider.respond(message, scene_context, character_id)

        try:
            return await asyncio.wait_for(
                self._primary_provider.respond(message, scene_context, character_id),
                timeout=self._provider_timeout_seconds,
            )
        except Exception as exc:
            logger.warning("Runtime primary provider failed; using fallback. error=%s", exc)
            return await self._fallback_provider.respond(message, scene_context, character_id)
