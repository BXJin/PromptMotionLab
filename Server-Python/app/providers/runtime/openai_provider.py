import json
import logging
import asyncio
import re
from typing import Any

import httpx
from pydantic import ValidationError

from app.contracts.character_profile import CharacterProfile
from app.contracts.runtime_behavior import BehaviorJson, RuntimeConversationTurn, SceneContext
from app.providers.runtime.base import RuntimeBehaviorProvider
from app.providers.runtime.profile_prompt_builder import ProfilePromptBuilder
from app.security import loggable_text
from app.services.provider_failure_logger import ProviderFailureLogger

logger = logging.getLogger(__name__)


class OpenAiRuntimeBehaviorProvider(RuntimeBehaviorProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        endpoint: str = "https://api.openai.com/v1/responses",
        timeout_seconds: float = 4.0,
        max_output_tokens: int = 100,
        max_history_turns: int = 20,
        temperature: float | None = None,
        max_concurrency: int = 8,
        failure_logger: ProviderFailureLogger | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key is required")

        self._api_key = api_key
        self._model = model
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max(64, min(max_output_tokens, 256))
        self._max_history_turns = max(0, min(max_history_turns, 32))
        self._temperature = None if temperature is None else max(0.0, min(temperature, 2.0))
        self._max_concurrency = max(1, max_concurrency)
        self._semaphore = asyncio.Semaphore(self._max_concurrency)
        self._failure_logger = failure_logger or ProviderFailureLogger.default()
        self._client: httpx.AsyncClient | None = None

    @property
    def model_name(self) -> str:
        return self._model

    async def respond(
        self,
        message: str,
        scene_context: SceneContext,
        character_id: str,
        conversation_history: list[RuntimeConversationTurn] | None = None,
        character_profile: CharacterProfile | None = None,
    ) -> tuple[str, BehaviorJson]:
        payload = {
            "model": self._model,
            "instructions": self._build_instructions(character_profile),
            "input": self._build_input(
                message,
                scene_context,
                character_id,
                conversation_history or [],
            ),
            "max_output_tokens": self._max_output_tokens,
        }
        if self._temperature is not None:
            payload["temperature"] = self._temperature

        async with self._semaphore:
            response = await self._get_client().post(
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

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout_seconds,
                limits=httpx.Limits(
                    max_keepalive_connections=self._max_concurrency,
                    max_connections=self._max_concurrency,
                ),
            )
        return self._client

    def _build_instructions(self, character_profile: CharacterProfile | None = None) -> str:
        instructions = (
            "You drive a real-time 3D character. Return only compact JSON, no markdown.\n"
            "Reply in the user's language.\n"
            "Default reply: 1 short sentence, under 25 words. Use 2 sentences only if needed. "
            "Do not over-explain.\n"
            'Schema: {"reply":"...","behavior":{"emotion":"neutral|friendly|happy|thinking|'
            'curious|concerned|uncertain|apologetic","intensity":0.0,"confidence":0.0,'
            '"intent":"greet|explain|answer|clarify|refuse|fallback","gaze":"user|'
            'focused_object|down_left|side|none","gestureKey":"none|small_ack|explain_small|'
            'point_soft|hesitate|greet_small","headMotion":"none|small_nod|small_tilt|'
            'thinking_tilt","ttsStyle":"neutral|warm|careful|energetic"}}\n'
            "Rules:\n"
            "- For greetings, use emotion=friendly and intent=greet.\n"
            "- If a greeting is followed by a stronger topic or feeling, respond to the strongest point naturally.\n"
            "- If a greeting is followed by a concrete question, behavior.intent must be answer or clarify, not greet.\n"
            "- Weather, news, price, schedule, or other realtime-info questions must use intent=answer or clarify.\n"
            "- For analysis, explanation, comparison, or why/how questions, use emotion=thinking unless the user emotion is stronger.\n"
            "- Do not answer every clause separately; compress the response like natural conversation.\n"
            "- Do not always end with a question.\n"
            "- Use at most two short questions in a reply. Two questions are allowed for gentle emotional support; avoid interview-style question chains.\n"
            "- When asking a follow-up, choose it from the user's latest concrete topic, feeling, or implied next step. "
            "Do not ask a generic follow-up when a more specific one is available.\n"
            "- Prefer follow-up questions that advance the same conversation thread: ask about the scene, reason, choice, feeling, or next action the user just mentioned.\n"
            "- If the user shares an experience, ask about the most vivid detail or emotional aftertaste, not a broad survey question.\n"
            "- If the user asks for advice, ask only for the missing constraint that changes the answer; otherwise give the next practical step.\n"
            "- If the user sounds sad, tired, lonely, angry, or anxious, first react to that feeling, then ask one gentle specific question only if it helps.\n"
            "- Avoid generic assistant endings such as 'if you need anything else', 'feel free to ask', or 'I am here to help'.\n"
            "- In Korean casual character modes, avoid formal service-desk endings and customer-support phrasing.\n"
            "- Never close with generic availability phrases. End on the useful answer instead.\n"
            "- Do not invent realtime facts such as weather, news, or prices. Say you cannot check live information yet.\n"
            "- For realtime, latest, trending, ranking, current game, news, weather, price, or schedule questions, never guess names or rankings. "
            "Say you cannot check live information yet, then offer a stable way to choose or compare.\n"
            "- For realtime data, do not add guesses, probabilities, seasonal averages, examples, or general claims. Only say you cannot check it yet.\n"
            "- For sadness, worry, loneliness, or apology, use concerned/apologetic and careful/warm style.\n"
            "- For uncertainty, use emotion=uncertain and confidence < 0.55.\n"
            "- For focused object explanation, use gaze=focused_object and explain_small or point_soft.\n"
            "- behavior.emotion must be exactly one of: neutral, friendly, happy, thinking, curious, concerned, uncertain, apologetic. No other values.\n"
            "- behavior.intent must be exactly one of: greet, explain, answer, clarify, refuse, fallback. No other values.\n"
            "- behavior.gaze must be exactly one of: user, focused_object, down_left, side, none.\n"
            "- behavior.gestureKey must be exactly one of: none, small_ack, explain_small, point_soft, hesitate, greet_small.\n"
            "- behavior.headMotion must be exactly one of: none, small_nod, small_tilt, thinking_tilt.\n"
            "- behavior.ttsStyle must be exactly one of: neutral, warm, careful, energetic.\n"
            "- No morphs, visemes, bones, frame data, or extra fields."
        )
        if character_profile:
            instructions += f"\n\nCharacter voice:\n{ProfilePromptBuilder.build(character_profile)}"
        return instructions

    def _build_input(
        self,
        message: str,
        scene_context: SceneContext,
        character_id: str,
        conversation_history: list[RuntimeConversationTurn],
        character_profile: CharacterProfile | None = None,
    ) -> str:
        del character_profile
        context_json = scene_context.model_dump(by_alias=True, exclude_none=True)
        lines = [
            f"characterId:{character_id}",
            f"sceneContext:{json.dumps(context_json, ensure_ascii=False, separators=(',', ':'))}",
        ]

        history = conversation_history[-self._max_history_turns :]
        if history:
            lines.append("recentConversation:")
            for turn in history:
                lines.append(f"- {turn.role}: {turn.content}")

        lines.append(f"userMessage:{message}")
        return "\n".join(lines)

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
            self._log_provider_failure("ValueError", "OpenAI response did not include output text", json.dumps(body, ensure_ascii=False))
            raise ValueError("OpenAI response did not include output text")
        return output

    def _parse_model_output(self, output_text: str) -> tuple[str, BehaviorJson]:
        raw = self._extract_json_object(self._strip_markdown_fence(output_text))
        try:
            data = self._load_json_object(raw)
        except json.JSONDecodeError as exc:
            logger.warning("OpenAI runtime JSON parse failed. sample=%r", loggable_text(output_text)[:500])
            self._log_provider_failure("JSONDecodeError", str(exc), output_text)
            raise
        if not isinstance(data, dict):
            self._log_provider_failure("ValueError", "Model output must be a JSON object", output_text)
            raise ValueError("Model output must be a JSON object")

        reply = data.get("reply")
        behavior_data = data.get("behavior")
        if not isinstance(reply, str) or not reply.strip():
            self._log_provider_failure("ValueError", "Model output missing reply", output_text)
            raise ValueError("Model output missing reply")
        if not isinstance(behavior_data, dict):
            self._log_provider_failure("ValueError", "Model output missing behavior object", output_text)
            raise ValueError("Model output missing behavior object")

        normalization_notes = self._normalize_behavior_data(behavior_data)
        try:
            behavior = BehaviorJson.model_validate(behavior_data)
        except ValidationError as exc:
            logger.warning("OpenAI runtime behavior validation failed. sample=%r", loggable_text(output_text)[:500])
            self._log_provider_failure(
                "ValidationError",
                str(exc),
                output_text,
                {"normalizationNotes": normalization_notes, "behavior": behavior_data},
            )
            raise ValueError(f"Invalid behavior JSON: {exc}") from exc

        return self._polish_reply(reply.strip()), behavior

    def _polish_reply(self, reply: str) -> str:
        original = reply.strip()
        if not original:
            return original

        text = self._keep_at_most_two_questions(original)
        text = self._remove_generic_assistant_closers(text)
        return text.strip() or original

    def _keep_at_most_two_questions(self, reply: str) -> str:
        question_positions = [index for index, character in enumerate(reply) if character in {"?", "\uff1f"}]
        if len(question_positions) <= 2:
            return reply
        return reply[: question_positions[1] + 1].strip()

    def _remove_generic_assistant_closers(self, reply: str) -> str:
        generic_phrases = (
            "\uc5b8\uc81c\ub4e0 \ub9d0\ud574",
            "\uc5b8\uc81c\ub4e0 \uc774\uc57c\uae30",
            "\ub3c4\uc6c0\uc774 \ud544\uc694\ud558\uba74",
            "\ub354 \ud544\uc694\ud558\uba74",
            "\ud544\uc694\ud558\uba74 \uc5b8\uc81c\ub4e0",
            "\ud3b8\ud558\uac8c \ub9d0",
            "\ub09c \uc5ec\uae30 \uc788\uc744\uac8c",
            "\uacc1\uc5d0 \uc788\uc744\uac8c",
            "feel free",
            "anything else",
            "i am here to help",
        )

        parts = re.split(r"(?<=[.!?])\s+", reply)
        cleaned: list[str] = []
        for part in parts:
            trimmed = part.strip()
            if not trimmed:
                continue

            lowered = trimmed.lower()
            matches = [
                index
                for phrase in generic_phrases
                for index in [lowered.find(phrase.lower())]
                if index >= 0
            ]
            if not matches:
                cleaned.append(trimmed)
                continue

            prefix = trimmed[: min(matches)].rstrip(" ,.!?\uff0c")
            if prefix:
                cleaned.append(prefix)

        return " ".join(cleaned)

    def _normalize_behavior_data(self, behavior_data: dict[str, Any]) -> list[str]:
        notes: list[str] = []
        enum_aliases = {
            "emotion": {
                "calm": "neutral",
                "relaxed": "neutral",
                "serious": "thinking",
                "analytical": "thinking",
                "focused": "thinking",
                "confused": "uncertain",
                "unsure": "uncertain",
                "worried": "concerned",
                "sad": "concerned",
                "sorry": "apologetic",
                "excited": "happy",
                "cheerful": "happy",
                "warm": "friendly",
                "caring": "friendly",
            },
            "intent": {
                "question": "answer",
                "smalltalk": "answer",
                "comfort": "answer",
                "support": "answer",
                "apology": "answer",
                "inform": "answer",
                "unknown": "clarify",
            },
            "gaze": {
                "focusedObject": "focused_object",
                "object": "focused_object",
                "down": "down_left",
                "user_face": "user",
            },
            "gestureKey": {
                "small_nod": "small_ack",
                "nod": "small_ack",
                "explain": "explain_small",
                "point": "point_soft",
                "greet": "greet_small",
            },
            "headMotion": {
                "nod": "small_nod",
                "tilt": "small_tilt",
                "thinking": "thinking_tilt",
            },
            "ttsStyle": {
                "soft": "warm",
                "gentle": "warm",
                "friendly": "warm",
                "calm": "neutral",
                "excited": "energetic",
            },
        }

        for field_name, aliases in enum_aliases.items():
            value = behavior_data.get(field_name)
            if not isinstance(value, str):
                continue
            normalized = aliases.get(value.strip())
            if normalized:
                behavior_data[field_name] = normalized
                notes.append(f"{field_name}:{value}->{normalized}")
        return notes

    def _log_provider_failure(
        self,
        error_type: str,
        error_message: str,
        sample: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._failure_logger.append(
            provider=self.__class__.__name__,
            model=self._model,
            error_type=error_type,
            error_message=error_message,
            sample=sample,
            metadata=metadata,
        )

    def _extract_json_object(self, value: str) -> str:
        trimmed = value.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            return trimmed

        start = trimmed.find("{")
        end = trimmed.rfind("}")
        if start < 0 or end <= start:
            return trimmed
        return trimmed[start : end + 1]

    def _load_json_object(self, raw: str) -> Any:
        decoder = json.JSONDecoder()
        data, end_index = decoder.raw_decode(raw)
        trailing = raw[end_index:].strip()
        if trailing and any(character != "}" for character in trailing):
            raise json.JSONDecodeError("Extra data", raw, end_index)
        return data

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
