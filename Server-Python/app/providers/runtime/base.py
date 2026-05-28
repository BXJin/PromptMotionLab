from abc import ABC, abstractmethod

from app.contracts.character_profile import CharacterProfile
from app.contracts.runtime_behavior import BehaviorJson, RuntimeConversationTurn, SceneContext


class RuntimeBehaviorProvider(ABC):
    @abstractmethod
    async def respond(
        self,
        message: str,
        scene_context: SceneContext,
        character_id: str,
        conversation_history: list[RuntimeConversationTurn] | None = None,
        character_profile: CharacterProfile | None = None,
    ) -> tuple[str, BehaviorJson]:
        raise NotImplementedError
