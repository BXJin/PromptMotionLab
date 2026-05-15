from app.contracts.motion_spec import BodyScope, GestureName, HandSide, MotionSpec
from app.contracts.procedural_gesture import ProceduralGestureJson
from app.providers.llm.base import LlmProvider


class MockLlmProvider(LlmProvider):
    async def generate_motion_spec(self, prompt: str, skeleton_preset: str) -> MotionSpec:
        text = prompt.lower()
        gesture = self._detect_gesture(text)
        hand = self._detect_hand(text)
        emotion = self._detect_emotion(text)

        return MotionSpec(
            gesture=gesture,
            hand=hand,
            emotion=emotion,
            style="friendly" if emotion in {"happy", "cheerful"} else "natural",
            bodyScope=BodyScope.UPPER_BODY,
            durationSeconds=1.8 if gesture == GestureName.WAVE else 1.5,
            speed=1.2 if gesture == GestureName.WAVE else 1.0,
            amplitude=0.68 if gesture == GestureName.WAVE else 0.5,
            feetPlanted=True,
            rootMotion=False,
            skeletonPreset=skeleton_preset,
        )

    async def generate_procedural_gesture(self, motion_spec: MotionSpec) -> ProceduralGestureJson:
        if motion_spec.gesture == GestureName.WAVE:
            return ProceduralGestureJson(
                gesture=motion_spec.gesture,
                hand=motion_spec.hand,
                durationSeconds=motion_spec.duration_seconds,
                speed=motion_spec.speed,
                amplitude=motion_spec.amplitude,
                shoulderRaise=0.28,
                elbowBend=0.48,
                wristOscillation=0.72,
                bodyLean=0.05,
                headNod=0.1,
                feetPlanted=motion_spec.feet_planted,
                rootMotion=motion_spec.root_motion,
                skeletonPreset=motion_spec.skeleton_preset,
            )

        if motion_spec.gesture == GestureName.BOW:
            return ProceduralGestureJson(
                gesture=motion_spec.gesture,
                hand=HandSide.NONE,
                durationSeconds=motion_spec.duration_seconds,
                speed=motion_spec.speed,
                amplitude=motion_spec.amplitude,
                shoulderRaise=0.05,
                elbowBend=0.1,
                wristOscillation=0.0,
                bodyLean=0.45,
                headNod=0.35,
                feetPlanted=True,
                rootMotion=False,
                skeletonPreset=motion_spec.skeleton_preset,
            )

        return ProceduralGestureJson(
            gesture=motion_spec.gesture,
            hand=motion_spec.hand,
            durationSeconds=motion_spec.duration_seconds,
            speed=motion_spec.speed,
            amplitude=motion_spec.amplitude,
            feetPlanted=motion_spec.feet_planted,
            rootMotion=motion_spec.root_motion,
            skeletonPreset=motion_spec.skeleton_preset,
        )

    async def generate_enriched_prompt(self, prompt: str, motion_spec: MotionSpec) -> str:
        hand_phrase = {
            HandSide.LEFT: "left hand",
            HandSide.RIGHT: "right hand",
            HandSide.BOTH: "both hands",
            HandSide.NONE: "upper body",
        }.get(HandSide(motion_spec.hand), "right hand")

        constraints = []
        if motion_spec.feet_planted:
            constraints.append("feet planted")
        if not motion_spec.root_motion:
            constraints.append("no root motion")

        constraint_text = ", ".join(constraints) if constraints else "natural body motion"
        return (
            f"A {motion_spec.emotion} character performs a {motion_spec.gesture} gesture "
            f"with the {hand_phrase}. Upper-body motion, {motion_spec.style} style. "
            f"Duration {motion_spec.duration_seconds:.1f} seconds, speed {motion_spec.speed:.1f}, "
            f"medium amplitude {motion_spec.amplitude:.2f}. Keep {constraint_text}. "
            f"Original intent: {prompt}"
        )

    def _detect_gesture(self, text: str) -> GestureName:
        if "bow" in text or "인사" in text and "손" not in text:
            return GestureName.BOW
        if "point" in text or "가리" in text:
            return GestureName.POINT
        if "nod" in text or "끄덕" in text:
            return GestureName.NOD
        if "explain" in text or "설명" in text:
            return GestureName.EXPLAIN
        return GestureName.WAVE

    def _detect_hand(self, text: str) -> HandSide:
        if "both" in text or "양손" in text:
            return HandSide.BOTH
        if "left" in text or "왼손" in text:
            return HandSide.LEFT
        if "none" in text:
            return HandSide.NONE
        return HandSide.RIGHT

    def _detect_emotion(self, text: str) -> str:
        if "happy" in text or "smil" in text or "웃" in text:
            return "happy"
        if "calm" in text or "차분" in text:
            return "calm"
        return "neutral"

