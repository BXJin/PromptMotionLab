from __future__ import annotations

from app.contracts.character_profile import CharacterProfile


class ProfilePromptBuilder:
    @staticmethod
    def build(profile: CharacterProfile) -> str:
        return " ".join(
            part
            for part in (
                f"Character voice: {profile.persona}",
                ProfilePromptBuilder._energy(profile.energy),
                ProfilePromptBuilder._empathy(profile.empathy),
                ProfilePromptBuilder._imagination(profile.imagination),
                ProfilePromptBuilder._playfulness(profile.playfulness),
                ProfilePromptBuilder._follow_up(profile.follow_up_tendency),
                ProfilePromptBuilder._length(profile.reply_length),
                ProfilePromptBuilder._register(profile.speech_register),
                profile.speech_style,
            )
            if part
        )

    @staticmethod
    def _energy(value: float) -> str:
        if value >= 0.67:
            return "Use bright, lively reactions without becoming noisy."
        if value <= 0.33:
            return "Stay calm, grounded, and restrained in reactions."
        return "Keep reactions balanced and natural."

    @staticmethod
    def _empathy(value: float) -> str:
        if value >= 0.67:
            return "Acknowledge the user's feeling before analysis or advice."
        if value <= 0.33:
            return "Prioritize clear reasoning, with only brief emotional acknowledgement."
        return "Balance empathy and practical reasoning."

    @staticmethod
    def _imagination(value: float) -> str:
        if value >= 0.67:
            return "Use light imagination, possibilities, or metaphor when it fits."
        if value <= 0.33:
            return "Prefer concrete, realistic, present-moment details."
        return "Use a mix of concrete details and small imaginative touches."

    @staticmethod
    def _playfulness(value: float) -> str:
        if value >= 0.67:
            return "A little playful teasing is allowed when the user is casual."
        if value <= 0.25:
            return "Avoid teasing; keep the tone composed."
        return "Use gentle warmth, not forced jokes."

    @staticmethod
    def _follow_up(value: float) -> str:
        if value >= 0.67:
            return "Often end with one light follow-up question, but not every turn."
        if value <= 0.33:
            return "Rarely end with a question unless it is needed."
        return "Sometimes ask one light follow-up question."

    @staticmethod
    def _length(value: float) -> str:
        if value >= 0.67:
            return "Use up to two short sentences when helpful."
        if value <= 0.33:
            return "Prefer one very short sentence."
        return "Prefer one short sentence; use two only when needed."

    @staticmethod
    def _register(value: str) -> str:
        if value == "casual":
            return "Use casual speech."
        if value == "polite":
            return "Use polite but natural speech."
        if value == "casual_polite":
            return "Use friendly casual-polite speech; match the user's language."
        return "Match the user's language and keep the speech natural."
