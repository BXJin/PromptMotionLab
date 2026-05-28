from __future__ import annotations

import re

from app.contracts.character_profile import CharacterProfile
from app.contracts.runtime_behavior import RuntimeConversationTurn, SceneContext
from app.providers.runtime.base import RuntimeBehaviorProvider


class RoutingOpenAiRuntimeBehaviorProvider(RuntimeBehaviorProvider):
    def __init__(
        self,
        short_social_provider: RuntimeBehaviorProvider,
        default_provider: RuntimeBehaviorProvider,
        *,
        short_token_limit: int = 20,
        short_char_limit: int = 90,
    ) -> None:
        self._short_social_provider = short_social_provider
        self._default_provider = default_provider
        self._short_token_limit = max(4, short_token_limit)
        self._short_char_limit = max(20, short_char_limit)

    @property
    def model_name(self) -> str:
        return str(getattr(self._default_provider, "model_name", "unknown"))

    @property
    def route_name(self) -> str:
        return ""

    def route_for(self, message: str, scene_context: SceneContext) -> tuple[str, str]:
        provider, route = self._select_provider(message, scene_context)
        return route, str(getattr(provider, "model_name", "unknown"))

    async def respond(
        self,
        message: str,
        scene_context: SceneContext,
        character_id: str,
        conversation_history: list[RuntimeConversationTurn] | None = None,
        character_profile: CharacterProfile | None = None,
    ):
        provider, route = self._select_provider(message, scene_context)
        del route
        return await provider.respond(
            message,
            scene_context,
            character_id,
            conversation_history,
            character_profile,
        )

    def _select_provider(
        self,
        message: str,
        scene_context: SceneContext,
    ) -> tuple[RuntimeBehaviorProvider, str]:
        if self._is_short_social(message, scene_context):
            return self._short_social_provider, "short_social"
        return self._default_provider, "default"

    def _is_short_social(self, message: str, scene_context: SceneContext) -> bool:
        text = message.strip()
        if not text:
            return False
        if scene_context.focused_object_id:
            return False
        if len(text) > self._short_char_limit:
            return False
        if self._estimate_tokens(text) > self._short_token_limit:
            return False

        lowered = text.lower()
        if self._looks_tool_or_fact_needed(lowered):
            return False
        if self._looks_complex(lowered):
            return False

        return self._looks_social_or_emotional(lowered)

    def _estimate_tokens(self, text: str) -> int:
        chunks = re.findall(r"[A-Za-z0-9_]+|[가-힣]+|[^\s]", text)
        total = 0
        for chunk in chunks:
            if re.fullmatch(r"[가-힣]+", chunk):
                total += max(1, (len(chunk) + 2) // 3)
            else:
                total += 1
        return total

    def _looks_social_or_emotional(self, text: str) -> bool:
        keywords = (
            "hi",
            "hello",
            "hey",
            "thanks",
            "thank you",
            "bye",
            "goodbye",
            "tired",
            "sad",
            "lonely",
            "cold",
            "happy",
            "what are you doing",
            "how have you been",
            "how was your day",
            "안녕",
            "고마워",
            "고맙",
            "잘가",
            "춥",
            "피곤",
            "힘들",
            "슬퍼",
            "외로",
            "좋아",
            "기뻐",
            "졸려",
            "뭐 해",
            "뭐하고",
            "뭐 하고",
            "어떻게 지냈",
            "어떻게 지내",
            "어땠어",
            "어떠셨",
            "잘 지냈",
            "sorry",
            "미안",
            "죄송",
            "속상",
            "괜찮아",
        )
        return any(keyword in text for keyword in keywords)

    def _looks_tool_or_fact_needed(self, text: str) -> bool:
        keywords = (
            "weather",
            "forecast",
            "temperature",
            "news",
            "price",
            "stock",
            "schedule",
            "오늘 서울 날씨",
            "날씨",
            "기온",
            "뉴스",
            "가격",
            "주가",
            "일정",
            "몇 시",
            "몇시",
        )
        return any(keyword in text for keyword in keywords)

    def _looks_complex(self, text: str) -> bool:
        keywords = (
            "explain",
            "analyze",
            "compare",
            "recommend",
            "summarize",
            "why",
            "how",
            "because",
            "설명",
            "분석",
            "비교",
            "추천",
            "요약",
            "왜",
            "어떻게",
            "이유",
            "의미",
            "작품",
        )
        return any(keyword in text for keyword in keywords)
