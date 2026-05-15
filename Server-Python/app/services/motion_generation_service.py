from app.contracts.enriched_prompt import EnrichedPromptExport
from app.contracts.motion_spec import MotionSpec
from app.contracts.procedural_gesture import ProceduralGestureJson
from app.providers.llm.base import LlmProvider
from app.storage.prompt_export_store import PromptExportStore


class MotionGenerationService:
    def __init__(self, llm_provider: LlmProvider, prompt_store: PromptExportStore) -> None:
        self._llm_provider = llm_provider
        self._prompt_store = prompt_store

    async def analyze_intent(self, prompt: str, skeleton_preset: str) -> MotionSpec:
        return await self._llm_provider.generate_motion_spec(prompt, skeleton_preset)

    async def generate_procedural(
        self,
        prompt: str,
        skeleton_preset: str,
    ) -> tuple[MotionSpec, ProceduralGestureJson]:
        motion_spec = await self.analyze_intent(prompt, skeleton_preset)
        gesture = await self._llm_provider.generate_procedural_gesture(motion_spec)
        return motion_spec, gesture

    async def generate_enriched_prompt(
        self,
        prompt: str,
        skeleton_preset: str,
        motion_spec: MotionSpec | None = None,
    ) -> EnrichedPromptExport:
        spec = motion_spec or await self.analyze_intent(prompt, skeleton_preset)
        enriched = await self._llm_provider.generate_enriched_prompt(prompt, spec)
        export = self._prompt_store.create(
            original_prompt=prompt,
            enriched_prompt=enriched,
            motion_spec=spec,
        )
        return export

    def get_prompt_export(self, export_id: str) -> EnrichedPromptExport | None:
        return self._prompt_store.get(export_id)
