from dataclasses import dataclass

from app.contracts.runtime_behavior import (
    BehaviorJson,
    RuntimeConversationTurn,
    RuntimeEmotion,
    RuntimeGestureKey,
    RuntimeGaze,
    RuntimeHeadMotion,
    RuntimeIntent,
    RuntimeTtsStyle,
    SceneContext,
)


EMOTIONAL_DISCLOSURE_KEYWORDS: tuple[str, ...] = (
    "sad",
    "lonely",
    "depressed",
    "worried",
    "anxious",
    "tired",
    "hard time",
    "\ud798\ub4e4",
    "\uc6b0\uc6b8",
    "\uc2ac\ud37c",
    "\uc2ac\ud504",
    "\uc678\ub85c",
    "\ubd88\uc548",
    "\uc9c0\ucce4",
    "\uac71\uc815",
    "\ud53c\uace4",
)


def looks_like_emotional_disclosure(text: str) -> bool:
    normalized = text.strip().lower()
    return any(keyword in normalized for keyword in EMOTIONAL_DISCLOSURE_KEYWORDS)


@dataclass(frozen=True)
class RuntimeScenarioMatch:
    scenario_id: str
    prompt_hint: str
    min_intensity: float | None = None
    max_confidence: float | None = None
    emotion: RuntimeEmotion | None = None
    intent: RuntimeIntent | None = None
    gaze: RuntimeGaze | None = None
    gesture_key: RuntimeGestureKey | None = None
    head_motion: RuntimeHeadMotion | None = None
    tts_style: RuntimeTtsStyle | None = None


class RuntimeScenarioService:
    def match(
        self,
        *,
        message: str,
        scene_context: SceneContext,
        history: list[RuntimeConversationTurn],
    ) -> RuntimeScenarioMatch | None:
        emotional_hits = self._count_emotional_user_turns(message, history)
        if emotional_hits >= 2:
            return RuntimeScenarioMatch(
                scenario_id="repeated_emotional_disclosure",
                prompt_hint=(
                    "The user has repeated an emotionally difficult topic in this short session. "
                    "Acknowledge the pattern gently, avoid overreacting, and offer one concrete supportive next step."
                ),
                emotion=RuntimeEmotion.CONCERNED,
                intent=RuntimeIntent.ANSWER,
                gaze=RuntimeGaze.USER,
                gesture_key=RuntimeGestureKey.SMALL_ACK,
                head_motion=RuntimeHeadMotion.SMALL_TILT,
                tts_style=RuntimeTtsStyle.CAREFUL,
                min_intensity=0.62,
                max_confidence=0.72,
            )

        if scene_context.focused_object_id and self._looks_like_exhibit_question(message):
            return RuntimeScenarioMatch(
                scenario_id="focused_object_explanation",
                prompt_hint=(
                    "The user is asking while an exhibit/object is focused. "
                    "Tie the answer to the focused object if possible, and keep it short."
                ),
                emotion=RuntimeEmotion.THINKING,
                intent=RuntimeIntent.EXPLAIN,
                gaze=RuntimeGaze.FOCUSED_OBJECT,
                gesture_key=RuntimeGestureKey.EXPLAIN_SMALL,
                head_motion=RuntimeHeadMotion.SMALL_NOD,
                tts_style=RuntimeTtsStyle.WARM,
                min_intensity=0.45,
            )

        return None

    def build_provider_message(self, message: str, match: RuntimeScenarioMatch | None) -> str:
        if match is None:
            return message
        return f"scenarioHint:{match.prompt_hint}\nuserMessage:{message}"

    def apply_behavior_override(self, behavior: BehaviorJson, match: RuntimeScenarioMatch | None) -> BehaviorJson:
        if match is None:
            return behavior

        if match.emotion is not None:
            behavior.emotion = match.emotion
        if match.intent is not None:
            behavior.intent = match.intent
        if match.gaze is not None:
            behavior.gaze = match.gaze
        if match.gesture_key is not None:
            behavior.gesture_key = match.gesture_key
        if match.head_motion is not None:
            behavior.head_motion = match.head_motion
        if match.tts_style is not None:
            behavior.tts_style = match.tts_style
        if match.min_intensity is not None:
            behavior.intensity = max(behavior.intensity, match.min_intensity)
        if match.max_confidence is not None:
            behavior.confidence = min(behavior.confidence, match.max_confidence)

        return behavior

    def _count_emotional_user_turns(self, message: str, history: list[RuntimeConversationTurn]) -> int:
        count = 1 if looks_like_emotional_disclosure(message) else 0
        for turn in history:
            if turn.role == "user" and looks_like_emotional_disclosure(turn.content):
                count += 1
        return count

    def _looks_like_emotional_disclosure(self, text: str) -> bool:
        return looks_like_emotional_disclosure(text)

    def _looks_like_exhibit_question(self, text: str) -> bool:
        normalized = text.strip().lower()
        return any(
            keyword in normalized
            for keyword in (
                "what is",
                "tell me",
                "explain",
                "\uc774\uac70",
                "\uc774\uac74",
                "\uc124\uba85",
                "\ubb50\uc57c",
                "\ubb34\uc5c7",
                "\uc54c\ub824",
            )
        )
