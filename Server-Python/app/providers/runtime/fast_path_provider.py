from app.contracts.runtime_behavior import (
    BehaviorJson,
    RuntimeEmotion,
    RuntimeGestureKey,
    RuntimeGaze,
    RuntimeHeadMotion,
    RuntimeIntent,
    RuntimeTtsStyle,
)


class FastPathRuntimeProvider:
    provider_name = "FastPathRuntimeProvider"
    model_name = "rule"

    def try_respond(self, message: str) -> tuple[str, BehaviorJson] | None:
        text = self._normalize(message)
        if not text:
            return None

        if self._is_greeting_or_small_talk(text):
            return (
                self._small_talk_reply(text),
                BehaviorJson(
                    emotion=RuntimeEmotion.FRIENDLY,
                    intensity=0.68,
                    confidence=1.0,
                    intent=RuntimeIntent.GREET,
                    gaze=RuntimeGaze.USER,
                    gestureKey=RuntimeGestureKey.GREET_SMALL,
                    headMotion=RuntimeHeadMotion.SMALL_NOD,
                    ttsStyle=RuntimeTtsStyle.WARM,
                ),
            )

        if self._is_thanks(text):
            return (
                "천만에요. 필요하면 바로 도와줄게요.",
                BehaviorJson(
                    emotion=RuntimeEmotion.FRIENDLY,
                    intensity=0.55,
                    confidence=1.0,
                    intent=RuntimeIntent.ANSWER,
                    gaze=RuntimeGaze.USER,
                    gestureKey=RuntimeGestureKey.SMALL_ACK,
                    headMotion=RuntimeHeadMotion.SMALL_NOD,
                    ttsStyle=RuntimeTtsStyle.WARM,
                ),
            )

        if self._is_goodbye(text):
            return (
                "좋아요. 다음에 또 이야기해요.",
                BehaviorJson(
                    emotion=RuntimeEmotion.FRIENDLY,
                    intensity=0.5,
                    confidence=1.0,
                    intent=RuntimeIntent.ANSWER,
                    gaze=RuntimeGaze.USER,
                    gestureKey=RuntimeGestureKey.SMALL_ACK,
                    headMotion=RuntimeHeadMotion.SMALL_NOD,
                    ttsStyle=RuntimeTtsStyle.WARM,
                ),
            )

        if self._is_short_ack(text):
            return (
                "응.",
                BehaviorJson(
                    emotion=RuntimeEmotion.NEUTRAL,
                    intensity=0.25,
                    confidence=1.0,
                    intent=RuntimeIntent.ANSWER,
                    gaze=RuntimeGaze.USER,
                    gestureKey=RuntimeGestureKey.SMALL_ACK,
                    headMotion=RuntimeHeadMotion.SMALL_NOD,
                    ttsStyle=RuntimeTtsStyle.NEUTRAL,
                ),
            )

        return None

    def _normalize(self, message: str) -> str:
        return (
            message.strip()
            .lower()
            .replace("!", "")
            .replace(".", "")
            .replace(",", "")
            .replace("?", "")
        )

    def _is_greeting_or_small_talk(self, text: str) -> bool:
        greeting_words = {"안녕", "안녕하세요", "하이", "hello", "hi", "hey"}
        small_talk_phrases = {
            "오늘 날씨 좋네",
            "날씨 좋네",
            "오늘 뭐했어",
            "뭐했어",
            "how are you",
            "what did you do today",
            "nice weather",
        }
        return text in greeting_words or any(phrase in text for phrase in small_talk_phrases)

    def _small_talk_reply(self, text: str) -> str:
        if "뭐했어" in text or "what did you do" in text:
            return "안녕! 오늘은 사람들과 이야기하면서 지냈어. 너는 뭐 했어?"
        if "날씨" in text or "weather" in text:
            return "안녕! 그러게, 오늘 날씨가 좋아 보여. 기분도 조금 밝아지는 느낌이야."
        return "안녕! 만나서 반가워. 오늘은 뭐 하고 있었어?"

    def _is_thanks(self, text: str) -> bool:
        return text in {"고마워", "감사", "감사해", "감사합니다", "thanks", "thank you"}

    def _is_goodbye(self, text: str) -> bool:
        return text in {"잘가", "안녕히", "다음에 봐", "bye", "goodbye", "see you"}

    def _is_short_ack(self, text: str) -> bool:
        return text in {"응", "네", "어", "ㅇㅇ", "오케이", "ok", "okay", "yes", "yeah"}
