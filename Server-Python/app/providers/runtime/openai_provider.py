import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.contracts.runtime_behavior import BehaviorJson, SceneContext
from app.providers.runtime.base import RuntimeBehaviorProvider


class OpenAiRuntimeBehaviorProvider(RuntimeBehaviorProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        endpoint: str = "https://api.openai.com/v1/responses",
        timeout_seconds: float = 4.0,
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key is required")

        self._api_key = api_key
        self._model = model
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds

    async def respond(
        self,
        message: str,
        scene_context: SceneContext,
        character_id: str,
    ) -> tuple[str, BehaviorJson]:
        payload = {
            "model": self._model,
            "instructions": self._build_instructions(),
            "input": self._build_input(message, scene_context, character_id),
        }

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                self._endpoint,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()

        output_text = self._extract_output_text(response.json())
        return self._parse_model_output(output_text)

    def _build_instructions(self) -> str:
        return """
You are the runtime brain for a real-time 3D AI character.
Reply in the same language as the user. If the user writes Korean, reply in Korean.

Return only a compact JSON object. Do not wrap it in markdown.
Schema:
{
  "reply": "short user-facing answer",
  "behavior": {
    "emotion": "neutral | friendly | happy | thinking | curious | concerned | uncertain | apologetic",
    "intensity": 0.0,
    "confidence": 0.0,
    "intent": "greet | explain | answer | clarify | refuse | fallback",
    "gaze": "user | focused_object | down_left | side | none",
    "gestureKey": "none | small_ack | explain_small | point_soft | hesitate | greet_small",
    "headMotion": "none | small_nod | small_tilt | thinking_tilt",
    "ttsStyle": "neutral | warm | careful | energetic"
  }
}

Behavior rules:
- Keep reply concise. The 3D character must start speaking quickly.
- Use confidence to express certainty, not fake emotion.
- If the answer is uncertain, choose emotion=uncertain, confidence below 0.55, gaze=down_left, gestureKey=hesitate.
- If explaining a focused object, use gaze=focused_object and gestureKey=explain_small or point_soft.
- Do not output morph target values, visemes, bone rotations, frame data, or arbitrary commands.
- Do not add fields outside the schema.
""".strip()

    def _build_input(
        self,
        message: str,
        scene_context: SceneContext,
        character_id: str,
    ) -> str:
        context_json = scene_context.model_dump(by_alias=True)
        return "\n".join(
            [
                f"characterId: {character_id}",
                f"sceneContext: {json.dumps(context_json, ensure_ascii=False)}",
                f"userMessage: {message}",
            ]
        )

    def _extract_output_text(self, body: dict[str, Any]) -> str:
        output_text = body.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        chunks: list[str] = []
        for output_item in body.get("output", []):
            if not isinstance(output_item, dict):
                continue
            for content_item in output_item.get("content", []):
                if not isinstance(content_item, dict):
                    continue
                text = content_item.get("text")
                if isinstance(text, str):
                    chunks.append(text)

        output = "".join(chunks).strip()
        if not output:
            raise ValueError("OpenAI response did not include output text")
        return output

    def _parse_model_output(self, output_text: str) -> tuple[str, BehaviorJson]:
        raw = self._strip_markdown_fence(output_text)
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Model output must be a JSON object")

        reply = data.get("reply")
        behavior_data = data.get("behavior")
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError("Model output missing reply")
        if not isinstance(behavior_data, dict):
            raise ValueError("Model output missing behavior object")

        try:
            behavior = BehaviorJson.model_validate(behavior_data)
        except ValidationError as exc:
            raise ValueError(f"Invalid behavior JSON: {exc}") from exc

        return reply.strip(), behavior

    def _strip_markdown_fence(self, value: str) -> str:
        trimmed = value.strip()
        if not trimmed.startswith("```"):
            return trimmed

        first_line_end = trimmed.find("\n")
        if first_line_end < 0:
            return trimmed

        without_opening = trimmed[first_line_end + 1 :].strip()
        if without_opening.endswith("```"):
            return without_opening[:-3].strip()
        return without_opening
