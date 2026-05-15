from abc import ABC, abstractmethod

from app.contracts.motion_spec import MotionSpec
from app.contracts.procedural_gesture import ProceduralGestureJson


class LlmProvider(ABC):
    @abstractmethod
    async def generate_motion_spec(self, prompt: str, skeleton_preset: str) -> MotionSpec:
        raise NotImplementedError

    @abstractmethod
    async def generate_procedural_gesture(self, motion_spec: MotionSpec) -> ProceduralGestureJson:
        raise NotImplementedError

    @abstractmethod
    async def generate_enriched_prompt(self, prompt: str, motion_spec: MotionSpec) -> str:
        raise NotImplementedError

