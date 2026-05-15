from abc import ABC, abstractmethod

from app.contracts.runtime_behavior import BehaviorJson, SceneContext


class RuntimeBehaviorProvider(ABC):
    @abstractmethod
    async def respond(
        self,
        message: str,
        scene_context: SceneContext,
        character_id: str,
    ) -> tuple[str, BehaviorJson]:
        raise NotImplementedError
