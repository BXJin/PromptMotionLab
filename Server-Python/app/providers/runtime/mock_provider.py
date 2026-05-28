from app.contracts.runtime_behavior import (
    BehaviorJson,
    RuntimeEmotion,
    RuntimeGestureKey,
    RuntimeGaze,
    RuntimeHeadMotion,
    RuntimeIntent,
    RuntimeTtsStyle,
    SceneContext,
)
from app.providers.runtime.base import RuntimeBehaviorProvider


class MockRuntimeBehaviorProvider(RuntimeBehaviorProvider):
    async def respond(
        self,
        message: str,
        scene_context: SceneContext,
        character_id: str,
        conversation_history: list | None = None,
        character_profile: object | None = None,
    ) -> tuple[str, BehaviorJson]:
        del character_id, conversation_history, character_profile

        normalized = message.strip().lower()

        if self._is_uncertain_question(normalized):
            return self._uncertain_response(scene_context)

        if self._is_greeting(normalized):
            return self._greeting_response()

        if self._is_explanation_request(normalized, scene_context):
            return self._explanation_response(scene_context)

        return self._default_response(scene_context)

    def _uncertain_response(self, scene_context: SceneContext) -> tuple[str, BehaviorJson]:
        target = scene_context.focused_object_id or "that topic"
        reply = (
            f"I am not fully certain about {target} yet. "
            "I can explain the confirmed parts first and mark uncertain details separately."
        )
        return reply, BehaviorJson(
            emotion=RuntimeEmotion.UNCERTAIN,
            intensity=0.55,
            confidence=0.42,
            intent=RuntimeIntent.CLARIFY,
            gaze=RuntimeGaze.DOWN_LEFT,
            gestureKey=RuntimeGestureKey.HESITATE,
            headMotion=RuntimeHeadMotion.THINKING_TILT,
            ttsStyle=RuntimeTtsStyle.CAREFUL,
        )

    def _greeting_response(self) -> tuple[str, BehaviorJson]:
        return (
            "Hello. I can guide you through this space and explain the selected exhibit.",
            BehaviorJson(
                emotion=RuntimeEmotion.FRIENDLY,
                intensity=0.68,
                confidence=0.9,
                intent=RuntimeIntent.GREET,
                gaze=RuntimeGaze.USER,
                gestureKey=RuntimeGestureKey.GREET_SMALL,
                headMotion=RuntimeHeadMotion.SMALL_NOD,
                ttsStyle=RuntimeTtsStyle.WARM,
            ),
        )

    def _explanation_response(self, scene_context: SceneContext) -> tuple[str, BehaviorJson]:
        target = scene_context.focused_object_id or "the selected exhibit"
        reply = (
            f"{target} is the current focus. "
            "I will look toward it and explain the key point in a concise way."
        )
        return reply, BehaviorJson(
            emotion=RuntimeEmotion.FRIENDLY,
            intensity=0.62,
            confidence=0.86,
            intent=RuntimeIntent.EXPLAIN,
            gaze=RuntimeGaze.FOCUSED_OBJECT if scene_context.focused_object_id else RuntimeGaze.USER,
            gestureKey=RuntimeGestureKey.EXPLAIN_SMALL,
            headMotion=RuntimeHeadMotion.SMALL_NOD,
            ttsStyle=RuntimeTtsStyle.WARM,
        )

    def _default_response(self, scene_context: SceneContext) -> tuple[str, BehaviorJson]:
        gaze = RuntimeGaze.FOCUSED_OBJECT if scene_context.focused_object_id else RuntimeGaze.USER
        reply = "지금 답변 생성이 지연되고 있어요. 잠시 후 다시 시도해 주세요."
        return reply, BehaviorJson(
            emotion=RuntimeEmotion.UNCERTAIN,
            intensity=0.55,
            confidence=0.35,
            intent=RuntimeIntent.FALLBACK,
            gaze=gaze,
            gestureKey=RuntimeGestureKey.HESITATE,
            headMotion=RuntimeHeadMotion.THINKING_TILT,
            ttsStyle=RuntimeTtsStyle.CAREFUL,
        )

    def _is_uncertain_question(self, text: str) -> bool:
        return any(keyword in text for keyword in ("not sure", "uncertain", "maybe", "모르", "확실"))

    def _is_greeting(self, text: str) -> bool:
        words = set(text.replace(".", " ").replace(",", " ").split())
        return "hello" in words or "hi" in words or "안녕" in text

    def _is_explanation_request(self, text: str, scene_context: SceneContext) -> bool:
        if scene_context.interaction_mode == "object_selected" or scene_context.focused_object_id:
            return True
        return any(keyword in text for keyword in ("explain", "describe", "설명"))
