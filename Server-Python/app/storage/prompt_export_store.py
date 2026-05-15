import json
from pathlib import Path
from uuid import uuid4

from app.contracts.enriched_prompt import EnrichedPromptExport
from app.contracts.motion_spec import MotionSpec


class PromptExportStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        original_prompt: str,
        enriched_prompt: str,
        motion_spec: MotionSpec,
    ) -> EnrichedPromptExport:
        export = EnrichedPromptExport(
            exportId=f"prompt_{uuid4().hex[:12]}",
            originalPrompt=original_prompt,
            enrichedPrompt=enriched_prompt,
            motionSpec=motion_spec,
        )
        self.save(export)
        return export

    def save(self, export: EnrichedPromptExport) -> None:
        path = self._path_for(export.export_id)
        payload = export.model_dump(mode="json", by_alias=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def get(self, export_id: str) -> EnrichedPromptExport | None:
        path = self._path_for(export_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return EnrichedPromptExport.model_validate(payload)

    def _path_for(self, export_id: str) -> Path:
        safe_id = export_id.replace("/", "_").replace("\\", "_")
        return self._root / f"{safe_id}.json"

