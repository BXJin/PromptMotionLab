import asyncio
import logging
import os
import time
from uuid import uuid4
import uuid
from dataclasses import dataclass

from app.contracts.character_profile import CharacterProfile
from app.contracts.responses import RuntimeResponseMetadata
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
from app.providers.runtime import FastPathRuntimeProvider, MockRuntimeBehaviorProvider, RuntimeBehaviorProvider
from app.services.character_profile_store import CharacterProfileStore
from app.services.latency_metrics_logger import LatencyMetricsLogger
from app.services.provider_failure_logger import ProviderFailureLogger
from app.services.runtime_session_store import RuntimeSessionStore
from app.services.runtime_scenario_service import RuntimeScenarioService, looks_like_emotional_disclosure
from app.services.service_limits import AsyncInFlightLimiter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeCharacterResult:
    reply: str
    behavior: BehaviorJson
    metadata: RuntimeResponseMetadata


class RuntimeCharacterService:
    def __init__(
        self,
        primary_provider: RuntimeBehaviorProvider | None = None,
        fallback_provider: RuntimeBehaviorProvider | None = None,
        provider_timeout_seconds: float = 4.5,
        fallback_timeout_seconds: float = 0.75,
        session_store: RuntimeSessionStore | None = None,
        profile_store: CharacterProfileStore | None = None,
        metrics_logger: LatencyMetricsLogger | None = None,
        failure_logger: ProviderFailureLogger | None = None,
        fast_path_provider: FastPathRuntimeProvider | None = None,
        scenario_service: RuntimeScenarioService | None = None,
        max_in_flight: int = 64,
    ) -> None:
        self._primary_provider = primary_provider
        self._fallback_provider = fallback_provider or MockRuntimeBehaviorProvider()
        self._provider_timeout_seconds = provider_timeout_seconds
        self._fallback_timeout_seconds = fallback_timeout_seconds
        max_session_turns = int(os.getenv("RUNTIME_MAX_SESSION_TURNS", "40"))
        self._session_store = session_store or RuntimeSessionStore(max_session_turns)
        self._profile_store = profile_store or CharacterProfileStore()
        self._metrics_logger = metrics_logger or LatencyMetricsLogger.default()
        self._failure_logger = failure_logger or ProviderFailureLogger.default()
        self._fast_path_provider = fast_path_provider or FastPathRuntimeProvider()
        self._scenario_service = scenario_service or RuntimeScenarioService()
        self._in_flight_limiter = AsyncInFlightLimiter(max_in_flight)
        self._tech_profile = os.getenv("RUNTIME_TECH_PROFILE", "text_llm_behavior_json_v1")
        self._input_mode = os.getenv("RUNTIME_INPUT_MODE", "text")

    async def respond(
        self,
        message: str,
        scene_context: SceneContext,
        character_id: str,
        session_id: str | None = None,
    ) -> RuntimeCharacterResult:
        session_id = session_id or f"anon_{uuid4().hex}"
        async with self._in_flight_limiter.slot():
            return await self._respond_unlimited(message, scene_context, character_id, session_id)

    async def _respond_unlimited(
        self,
        message: str,
        scene_context: SceneContext,
        character_id: str,
        session_id: str,
    ) -> RuntimeCharacterResult:
        request_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        debug_response = self._try_create_debug_emotion_response(message)
        if debug_response is not None:
            reply, behavior = debug_response
            latency_ms = int((time.perf_counter() - started) * 1000)
            metadata = RuntimeResponseMetadata(
                requestId=request_id,
                provider="DebugEmotionProvider",
                model="debug",
                techProfile=self._tech_profile,
                inputMode=self._input_mode,
                fallbackUsed=False,
                providerLatencyMs=latency_ms,
                totalServerMs=latency_ms,
                route="debug",
            )
            self._metrics_logger.append_runtime_response(
                metadata=metadata,
                session_id=session_id,
                message=message,
                behavior=behavior,
                notes="debug_emotion",
            )
            return RuntimeCharacterResult(reply=reply, behavior=behavior, metadata=metadata)

        fast_response = None if self._primary_provider is not None else self._fast_path_provider.try_respond(message)
        if fast_response is not None:
            reply, behavior = fast_response
            profile = self._profile_store.get(character_id)
            behavior.intensity = min(1.0, behavior.intensity * profile.emotion_intensity_scale)
            self._session_store.append_exchange(session_id, message, reply)
            latency_ms = int((time.perf_counter() - started) * 1000)
            metadata = RuntimeResponseMetadata(
                requestId=request_id,
                provider=self._fast_path_provider.provider_name,
                model=self._fast_path_provider.model_name,
                techProfile="text_fastpath_behavior_json_v1",
                inputMode=self._input_mode,
                fallbackUsed=False,
                providerLatencyMs=latency_ms,
                totalServerMs=latency_ms,
                route="fast_path",
            )
            self._metrics_logger.append_runtime_response(
                metadata=metadata,
                session_id=session_id,
                message=message,
                behavior=behavior,
                notes="fast_path",
            )
            return RuntimeCharacterResult(reply=reply, behavior=behavior, metadata=metadata)

        history = self._session_store.get_recent_turns(session_id)
        scenario_match = self._scenario_service.match(
            message=message,
            scene_context=scene_context,
            history=history,
        )
        provider_message = self._scenario_service.build_provider_message(message, scenario_match)
        profile = self._profile_store.get(character_id)
        provider = self._primary_provider or self._fallback_provider
        provider_name = self._provider_name(provider)
        provider_model = self._provider_model(provider)
        provider_route = self._provider_route_for_request(provider, message, scene_context)
        if provider_route[1]:
            provider_model = provider_route[1]
        fallback_used = self._primary_provider is None
        fallback_note = ""
        provider_started = started
        primary_latency_ms = -1
        fallback_latency_ms = -1

        try:
            provider_started = time.perf_counter()
            reply, behavior = await asyncio.wait_for(
                provider.respond(provider_message, scene_context, character_id, history, profile),
                timeout=self._provider_timeout_seconds,
            )
            provider_latency_ms = int((time.perf_counter() - provider_started) * 1000)
            primary_latency_ms = provider_latency_ms
        except Exception as exc:
            logger.warning("Runtime primary provider failed; using fallback. error=%s", exc)
            self._log_timeout_failure(
                exc,
                provider_name=provider_name,
                provider_model=provider_model,
                provider_route=provider_route[0],
                session_id=session_id,
                request_id=request_id,
                character_id=character_id,
                message=message,
            )
            fallback_used = True
            fallback_note = f"primary_failed:{exc.__class__.__name__}"
            provider = self._fallback_provider
            provider_name = self._provider_name(provider)
            provider_model = self._provider_model(provider)
            provider_route = ("fallback", provider_model)
            provider_started = time.perf_counter()
            try:
                reply, behavior = await asyncio.wait_for(
                    provider.respond(provider_message, scene_context, character_id, history, profile),
                    timeout=self._fallback_timeout_seconds,
                )
            except Exception as fallback_exc:
                logger.error("Runtime fallback provider failed; using emergency response. error=%s", fallback_exc)
                provider_name = "EmergencyRuntimeProvider"
                provider_model = "rule"
                provider_route = ("fallback", provider_model)
                fallback_note = f"{fallback_note};fallback_failed:{fallback_exc.__class__.__name__}"
                reply, behavior = self._emergency_response()
            provider_latency_ms = int((time.perf_counter() - provider_started) * 1000)
            fallback_latency_ms = provider_latency_ms

        behavior = self._guard_behavior(message, scene_context, behavior, profile)
        behavior = self._scenario_service.apply_behavior_override(behavior, scenario_match)
        self._session_store.append_exchange(session_id, message, reply)

        latency_ms = int((time.perf_counter() - started) * 1000)
        metadata = RuntimeResponseMetadata(
            requestId=request_id,
            provider=provider_name,
            model=provider_model,
            techProfile=self._tech_profile,
            inputMode=self._input_mode,
            fallbackUsed=fallback_used,
            providerLatencyMs=provider_latency_ms,
            totalServerMs=latency_ms,
            route=provider_route[0] or None,
        )
        self._metrics_logger.append_runtime_response(
            metadata=metadata,
            session_id=session_id,
            message=message,
            behavior=behavior,
            notes=self._format_metric_notes(
                fallback_note,
                scenario_id=scenario_match.scenario_id if scenario_match is not None else "",
                primary_latency_ms=primary_latency_ms,
                fallback_latency_ms=fallback_latency_ms,
            ),
        )
        return RuntimeCharacterResult(
            reply=reply,
            behavior=behavior,
            metadata=metadata,
        )

    def _guard_behavior(
        self,
        message: str,
        scene_context: SceneContext,
        behavior: BehaviorJson,
        profile: CharacterProfile,
    ) -> BehaviorJson:
        text = message.strip().lower()

        is_apology = self._looks_like_apology(text)
        is_emotional_disclosure = self._looks_like_emotional_disclosure(text)

        if behavior.intent == RuntimeIntent.GREET and not self._looks_like_greeting(text):
            behavior.intent = RuntimeIntent.CLARIFY if is_emotional_disclosure or is_apology else RuntimeIntent.ANSWER
        if is_apology and behavior.intent in {RuntimeIntent.GREET, RuntimeIntent.EXPLAIN}:
            behavior.intent = RuntimeIntent.ANSWER

        if is_emotional_disclosure or is_apology:
            if behavior.emotion == RuntimeEmotion.NEUTRAL or (
                is_emotional_disclosure and behavior.emotion in {RuntimeEmotion.FRIENDLY, RuntimeEmotion.HAPPY}
            ):
                behavior.emotion = RuntimeEmotion.CONCERNED
            behavior.intensity = max(behavior.intensity, 0.55)
            behavior.confidence = min(behavior.confidence, 0.78)
            behavior.gaze = RuntimeGaze.USER
            behavior.gesture_key = RuntimeGestureKey.SMALL_ACK
            behavior.tts_style = RuntimeTtsStyle.CAREFUL

        behavior.intensity = min(1.0, behavior.intensity * profile.emotion_intensity_scale)

        if scene_context.focused_object_id and behavior.intent == RuntimeIntent.EXPLAIN:
            behavior.gaze = RuntimeGaze.FOCUSED_OBJECT
            if behavior.gesture_key in {RuntimeGestureKey.NONE, RuntimeGestureKey.SMALL_ACK}:
                behavior.gesture_key = RuntimeGestureKey.EXPLAIN_SMALL

        return behavior

    def _looks_like_greeting(self, text: str) -> bool:
        words = set(text.replace(".", " ").replace(",", " ").replace("!", " ").split())
        return bool(words & {"hello", "hi", "hey"}) or "안녕" in text or "반가" in text

    def _looks_like_emotional_disclosure(self, text: str) -> bool:
        return looks_like_emotional_disclosure(text)

    def _looks_like_apology(self, text: str) -> bool:
        return any(
            keyword in text
            for keyword in (
                "sorry",
                "apologize",
                "apology",
                "my fault",
                "didn't mean",
                "did not mean",
                "미안",
                "죄송",
                "사과",
                "내 잘못",
                "그럴 뜻은 아니",
            )
        )

    def _log_timeout_failure(
        self,
        exc: Exception,
        *,
        provider_name: str,
        provider_model: str,
        provider_route: str,
        session_id: str,
        request_id: str,
        character_id: str,
        message: str,
    ) -> None:
        error_type = exc.__class__.__name__
        if "timeout" not in error_type.lower():
            return
        self._failure_logger.append(
            provider=provider_name,
            model=provider_model,
            error_type=error_type,
            error_message=str(exc),
            sample=message,
            metadata={
                "sessionId": session_id,
                "requestId": request_id,
                "characterId": character_id,
                "route": provider_route,
            },
        )

    def _provider_name(self, provider: RuntimeBehaviorProvider) -> str:
        return provider.__class__.__name__

    def _provider_model(self, provider: RuntimeBehaviorProvider) -> str:
        return str(getattr(provider, "model_name", "mock"))

    def _provider_route_for_request(
        self,
        provider: RuntimeBehaviorProvider,
        message: str,
        scene_context: SceneContext,
    ) -> tuple[str, str]:
        route_for = getattr(provider, "route_for", None)
        if not callable(route_for):
            return "", ""
        route, model = route_for(message, scene_context)
        return str(route), str(model)

    def _format_metric_notes(
        self,
        base: str,
        *,
        scenario_id: str = "",
        primary_latency_ms: int,
        fallback_latency_ms: int,
    ) -> str:
        parts = [base] if base else []
        if scenario_id:
            parts.append(f"scenario={scenario_id}")
        if primary_latency_ms >= 0:
            parts.append(f"primary_ms={primary_latency_ms}")
        if fallback_latency_ms >= 0:
            parts.append(f"fallback_ms={fallback_latency_ms}")
        return ";".join(parts)

    def _emergency_response(self) -> tuple[str, BehaviorJson]:
        return (
            "잠깐만요. 지금 답변을 정리하는 데 문제가 있어서 다시 시도해 주세요.",
            BehaviorJson(
                emotion=RuntimeEmotion.UNCERTAIN,
                intensity=0.45,
                confidence=0.2,
                intent=RuntimeIntent.FALLBACK,
                gaze=RuntimeGaze.DOWN_LEFT,
                gestureKey=RuntimeGestureKey.HESITATE,
                headMotion=RuntimeHeadMotion.THINKING_TILT,
                ttsStyle=RuntimeTtsStyle.CAREFUL,
            ),
        )

    def _try_create_debug_emotion_response(self, message: str) -> tuple[str, BehaviorJson] | None:
        normalized = message.strip().lower()
        if not normalized.startswith("/emotion "):
            return None

        emotion_text = normalized.removeprefix("/emotion ").strip()
        if emotion_text == "list":
            supported = ", ".join(emotion.value for emotion in RuntimeEmotion)
            return (
                f"Supported emotions: {supported}",
                BehaviorJson(
                    emotion=RuntimeEmotion.NEUTRAL,
                    intensity=0.0,
                    confidence=1.0,
                    intent=RuntimeIntent.ANSWER,
                    gaze=RuntimeGaze.USER,
                    gestureKey=RuntimeGestureKey.NONE,
                    headMotion="none",
                    ttsStyle=RuntimeTtsStyle.NEUTRAL,
                ),
            )

        try:
            emotion = RuntimeEmotion(emotion_text)
        except ValueError:
            supported = ", ".join(emotion.value for emotion in RuntimeEmotion)
            return (
                f"Unknown emotion '{emotion_text}'. Use one of: {supported}",
                BehaviorJson(
                    emotion=RuntimeEmotion.UNCERTAIN,
                    intensity=0.5,
                    confidence=0.2,
                    intent=RuntimeIntent.FALLBACK,
                    gaze=RuntimeGaze.DOWN_LEFT,
                    gestureKey=RuntimeGestureKey.HESITATE,
                    headMotion=RuntimeHeadMotion.THINKING_TILT,
                    ttsStyle=RuntimeTtsStyle.CAREFUL,
                ),
            )

        return (f"Debug emotion: {emotion.value}", self._debug_behavior_for_emotion(emotion))

    def _debug_behavior_for_emotion(self, emotion: RuntimeEmotion) -> BehaviorJson:
        if emotion == RuntimeEmotion.NEUTRAL:
            return BehaviorJson(
                emotion=emotion,
                intensity=0.0,
                confidence=1.0,
                intent=RuntimeIntent.ANSWER,
                gaze=RuntimeGaze.USER,
                gestureKey=RuntimeGestureKey.NONE,
                headMotion="none",
                ttsStyle=RuntimeTtsStyle.NEUTRAL,
            )

        if emotion in {RuntimeEmotion.THINKING, RuntimeEmotion.CURIOUS}:
            return BehaviorJson(
                emotion=emotion,
                intensity=0.75,
                confidence=0.8,
                intent=RuntimeIntent.CLARIFY if emotion == RuntimeEmotion.CURIOUS else RuntimeIntent.ANSWER,
                gaze=RuntimeGaze.USER,
                gestureKey=RuntimeGestureKey.SMALL_ACK,
                headMotion=RuntimeHeadMotion.THINKING_TILT,
                ttsStyle=RuntimeTtsStyle.NEUTRAL,
            )

        if emotion in {RuntimeEmotion.CONCERNED, RuntimeEmotion.UNCERTAIN, RuntimeEmotion.APOLOGETIC}:
            return BehaviorJson(
                emotion=emotion,
                intensity=0.75,
                confidence=0.55 if emotion == RuntimeEmotion.UNCERTAIN else 0.72,
                intent=RuntimeIntent.CLARIFY,
                gaze=RuntimeGaze.DOWN_LEFT if emotion == RuntimeEmotion.UNCERTAIN else RuntimeGaze.USER,
                gestureKey=RuntimeGestureKey.HESITATE if emotion == RuntimeEmotion.UNCERTAIN else RuntimeGestureKey.SMALL_ACK,
                headMotion=RuntimeHeadMotion.THINKING_TILT if emotion == RuntimeEmotion.UNCERTAIN else RuntimeHeadMotion.SMALL_TILT,
                ttsStyle=RuntimeTtsStyle.CAREFUL,
            )

        return BehaviorJson(
            emotion=emotion,
            intensity=0.75,
            confidence=0.9,
            intent=RuntimeIntent.GREET if emotion == RuntimeEmotion.FRIENDLY else RuntimeIntent.ANSWER,
            gaze=RuntimeGaze.USER,
            gestureKey=RuntimeGestureKey.GREET_SMALL if emotion == RuntimeEmotion.FRIENDLY else RuntimeGestureKey.SMALL_ACK,
            headMotion=RuntimeHeadMotion.SMALL_NOD,
            ttsStyle=RuntimeTtsStyle.ENERGETIC if emotion == RuntimeEmotion.HAPPY else RuntimeTtsStyle.WARM,
        )

