import asyncio
import math
import time
import wave

import pytest
from fastapi.testclient import TestClient

from app.api.routes import _parse_stt_sample_rate
from app.contracts.requests import RuntimeRespondRequest
from app.contracts.responses import RuntimeResponseMetadata
from app.contracts.runtime_behavior import BehaviorJson, SceneContext
from app.dependencies import (
    get_runtime_async_job_service,
    get_runtime_character_service,
    get_runtime_turn_async_job_service,
    get_stt_service,
    get_tts_async_job_service,
    get_tts_service,
)
from app.main import app
from app.providers.runtime import RoutingOpenAiRuntimeBehaviorProvider, RuntimeBehaviorProvider
from app.providers.runtime.openai_provider import OpenAiRuntimeBehaviorProvider
from app.providers.runtime.profile_prompt_builder import ProfilePromptBuilder
from app.providers.tts.base import TtsProvider
from app.providers.tts.wav_trim import trim_wav_file_to_duration
from app.security import BodySizeLimitMiddleware, RateLimitMiddleware, SlidingWindowRateLimiter, WebSocketConnectionLimiter
from app.services.provider_failure_logger import ProviderFailureLogger
from app.services import (
    CharacterProfileStore,
    LatencyMetricsLogger,
    ProviderFailureLogger,
    RuntimeAsyncJobService,
    RuntimeCharacterService,
    RuntimeTurnAsyncJobService,
    TtsAsyncJobService,
    TtsService,
)
from app.services.service_limits import ServiceBusyError


@pytest.fixture(autouse=True)
def disable_real_openai_for_tests(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("openai_api_key", raising=False)
    get_runtime_character_service.cache_clear()
    get_runtime_async_job_service.cache_clear()
    get_runtime_turn_async_job_service.cache_clear()
    get_stt_service.cache_clear()
    get_tts_service.cache_clear()
    get_tts_async_job_service.cache_clear()
    yield
    get_runtime_character_service.cache_clear()
    get_runtime_async_job_service.cache_clear()
    get_runtime_turn_async_job_service.cache_clear()
    get_stt_service.cache_clear()
    get_tts_service.cache_clear()
    get_tts_async_job_service.cache_clear()


def test_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_sliding_window_rate_limiter_blocks_after_limit() -> None:
    limiter = SlidingWindowRateLimiter()

    assert asyncio.run(limiter.allow("client-a", limit=2, window_seconds=60, now=100.0)) == (True, 0)
    assert asyncio.run(limiter.allow("client-a", limit=2, window_seconds=60, now=101.0)) == (True, 0)
    allowed, retry_after = asyncio.run(limiter.allow("client-a", limit=2, window_seconds=60, now=102.0))

    assert allowed is False
    assert retry_after > 0


def test_websocket_connection_limiter_blocks_per_client() -> None:
    limiter = WebSocketConnectionLimiter(max_total=4, max_per_client=1)

    assert asyncio.run(limiter.try_acquire("client-a")) is True
    assert asyncio.run(limiter.try_acquire("client-a")) is False
    asyncio.run(limiter.release("client-a"))
    assert asyncio.run(limiter.try_acquire("client-a")) is True


def test_body_size_limit_middleware_blocks_body_without_content_length() -> None:
    limited_app = BodySizeLimitMiddleware(app, limits={"/api/runtime/stt/transcribe": 4})
    client = TestClient(limited_app)

    response = client.post(
        "/api/runtime/stt/transcribe",
        content=b"12345",
        headers={"content-type": "audio/wav"},
    )

    assert response.status_code == 413


def test_rate_limiter_uses_separate_limit_for_job_poll() -> None:
    limited_app = RateLimitMiddleware(
        app,
        runtime_limit=1,
        runtime_job_poll_limit=3,
        runtime_stt_limit=1,
        runtime_tts_limit=1,
        audio_limit=1,
    )
    client = TestClient(limited_app)

    for _ in range(3):
        response = client.get("/api/runtime/turn/jobs/turn_missing")
        assert response.status_code == 404

    response = client.get("/api/runtime/turn/jobs/turn_missing")
    assert response.status_code == 429


def test_trim_wav_file_to_duration_updates_audio_length(tmp_path) -> None:
    wav_path = tmp_path / "sample.wav"
    frame_rate = 16000
    with wave.open(str(wav_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(frame_rate)
        wav.writeframes(b"\x00\x00" * frame_rate)

    result = trim_wav_file_to_duration(wav_path, 0.25)

    assert result.trimmed is True
    assert math.isclose(result.original_duration_seconds, 1.0, abs_tol=0.001)
    assert math.isclose(result.trimmed_duration_seconds, 0.25, abs_tol=0.001)
    with wave.open(str(wav_path), "rb") as wav:
        assert wav.getnframes() == int(frame_rate * 0.25)


def test_generate_procedural_wave() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/generate/procedural",
        json={
            "prompt": "smile and wave with the right hand",
            "skeletonPreset": "ue5_manny",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["motionSpec"]["gesture"] == "wave"
    assert payload["proceduralGesture"]["gesture"] == "wave"
    assert payload["proceduralGesture"]["skeletonPreset"] == "ue5_manny"


def test_generate_enriched_prompt_export() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/generate/enriched-prompt",
        json={
            "prompt": "smile and wave with the right hand",
            "skeletonPreset": "ue5_manny",
        },
    )

    assert response.status_code == 200
    export = response.json()["export"]
    assert export["exportId"].startswith("prompt_")
    assert export["originalPrompt"] == "smile and wave with the right hand"
    assert "right hand" in export["enrichedPrompt"]


def test_runtime_respond_object_explanation() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/runtime/respond",
        json={
            "sessionId": "demo_session",
            "characterId": "default_guide",
            "message": "Explain this exhibit.",
            "sceneContext": {
                "locationId": "demo_hall",
                "focusedObjectId": "exhibit_01",
                "nearbyObjectIds": ["exhibit_01", "exhibit_02"],
                "interactionMode": "object_selected",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reply"]
    assert payload["behavior"]["intent"] == "explain"
    assert payload["behavior"]["gaze"] == "focused_object"
    assert payload["behavior"]["gestureKey"] == "explain_small"
    assert payload["metadata"]["fallbackUsed"] is True


def test_runtime_stt_transcribe_mock() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/runtime/stt/transcribe?language=ko",
        content=b"RIFF....WAVEfmt ",
        headers={"content-type": "audio/wav"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["text"]
    assert payload["language"] == "ko"
    assert payload["provider"] == "MockSttProvider"
    assert payload["model"] == "mock"


def test_runtime_stt_rejects_empty_audio() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/runtime/stt/transcribe",
        content=b"",
        headers={"content-type": "audio/wav"},
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_runtime_stt_rejects_unsupported_content_type() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/runtime/stt/transcribe",
        content=b"not audio",
        headers={"content-type": "text/plain"},
    )

    assert response.status_code == 415


def test_runtime_stt_rejects_large_content_length() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/runtime/stt/transcribe",
        content=b"x" * (6 * 1024 * 1024),
        headers={"content-type": "audio/wav"},
    )

    assert response.status_code == 413


def test_streaming_stt_rejects_unsupported_sample_rate() -> None:
    with pytest.raises(ValueError, match="unsupported_sample_rate"):
        _parse_stt_sample_rate({"sampleRate": 999999999})


def test_runtime_respond_uncertain_message() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/runtime/respond",
        json={
            "message": "I am not sure about this.",
            "sceneContext": {"focusedObjectId": "exhibit_02"},
        },
    )

    assert response.status_code == 200
    behavior = response.json()["behavior"]
    assert behavior["emotion"] == "uncertain"
    assert behavior["confidence"] < 0.5
    assert behavior["gestureKey"] == "hesitate"


def test_runtime_respond_rejects_long_message() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/runtime/respond",
        json={
            "sessionId": "long_message_test",
            "message": "x" * 2001,
            "sceneContext": {},
        },
    )

    assert response.status_code == 422


def test_runtime_respond_default_session_is_unique() -> None:
    first = RuntimeRespondRequest(message="hello")
    second = RuntimeRespondRequest(message="hello")

    assert first.session_id.startswith("anon_")
    assert second.session_id.startswith("anon_")
    assert first.session_id != second.session_id


def test_runtime_respond_greeting_uses_fast_path() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/runtime/respond",
        json={
            "sessionId": "fast_path_test",
            "characterId": "default_girl",
            "message": "안녕",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["behavior"]["intent"] == "greet"
    assert payload["metadata"]["provider"] == "FastPathRuntimeProvider"
    assert payload["metadata"]["model"] == "rule"
    assert payload["metadata"]["fallbackUsed"] is False
    assert payload["metadata"]["totalServerMs"] < 100


def test_runtime_respond_korean_small_talk_uses_fast_path() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/runtime/respond",
        json={
            "sessionId": "fast_path_ko_test",
            "characterId": "default_girl",
            "message": "안녕 오늘 날씨 좋네 오늘 뭐했어?",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["behavior"]["intent"] == "greet"
    assert payload["metadata"]["provider"] == "FastPathRuntimeProvider"
    assert payload["metadata"]["totalServerMs"] < 100


def test_runtime_respond_stream_sends_reaction_then_final() -> None:
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/runtime/respond/stream",
        json={
            "sessionId": "stream_test",
            "characterId": "default_girl",
            "message": "hello",
        },
    ) as response:
        assert response.status_code == 200
        body = "\n".join(response.iter_lines())

    assert "event: reaction" in body
    assert '"type": "reaction"' in body
    assert '"emotion": "thinking"' in body
    assert "event: final" in body
    assert '"type": "final"' in body
    assert '"provider": "FastPathRuntimeProvider"' in body


def test_runtime_respond_returns_429_when_service_is_busy() -> None:
    class BusyRuntimeService:
        async def respond(self, *, message, scene_context, character_id, session_id):
            del message, scene_context, character_id, session_id
            raise ServiceBusyError("runtime busy")

    app.dependency_overrides[get_runtime_character_service] = lambda: BusyRuntimeService()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/runtime/respond",
            json={
                "sessionId": "busy_test",
                "characterId": "default_girl",
                "message": "hello",
            },
        )
    finally:
        app.dependency_overrides.pop(get_runtime_character_service, None)

    assert response.status_code == 429
    assert "runtime busy" in response.json()["detail"]
    assert response.headers["Retry-After"] == "5"


def test_runtime_respond_async_returns_reaction_then_job_result() -> None:
    client = TestClient(app)

    accepted = client.post(
        "/api/runtime/respond/async",
        json={
            "sessionId": "async_test",
            "characterId": "default_girl",
            "message": "hello",
        },
    )

    assert accepted.status_code == 200
    accepted_payload = accepted.json()
    assert accepted_payload["jobId"].startswith("rt_")
    assert accepted_payload["status"] in {"pending", "running"}
    assert accepted_payload["reaction"]["emotion"] == "thinking"

    deadline = time.monotonic() + 2.0
    final_payload = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/runtime/respond/jobs/{accepted_payload['jobId']}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] == "succeeded":
            final_payload = payload
            break
        time.sleep(0.02)

    assert final_payload is not None
    assert final_payload["response"]["behavior"]["intent"] == "greet"
    assert final_payload["response"]["metadata"]["provider"] == "FastPathRuntimeProvider"


def test_runtime_respond_async_returns_429_when_in_flight_limit_reached() -> None:
    class BusyRuntimeAsyncJobService:
        async def submit(self, request):
            del request
            raise ServiceBusyError("runtime async busy")

    app.dependency_overrides[get_runtime_async_job_service] = lambda: BusyRuntimeAsyncJobService()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/runtime/respond/async",
            json={"sessionId": "busy_async", "characterId": "default_girl", "message": "hello"},
        )
    finally:
        app.dependency_overrides.pop(get_runtime_async_job_service, None)

    assert response.status_code == 429
    assert "runtime async busy" in response.json()["detail"]
    assert response.headers["Retry-After"] == "5"


def test_runtime_respond_async_unknown_job_returns_404() -> None:
    client = TestClient(app)

    response = client.get("/api/runtime/respond/jobs/rt_missing")

    assert response.status_code == 404


def test_runtime_turn_async_returns_reaction_response_and_tts() -> None:
    with TestClient(app) as client:
        accepted = client.post(
            "/api/runtime/turn/async",
            json={
                "sessionId": "turn_async_test",
                "characterId": "default_girl",
                "message": "hello",
            },
        )

        assert accepted.status_code == 200
        accepted_payload = accepted.json()
        assert accepted_payload["turnJobId"].startswith("turn_")
        assert accepted_payload["status"] in {"pending", "responding"}
        assert accepted_payload["reaction"]["emotion"] == "thinking"

        deadline = time.monotonic() + 2.0
        final_payload = None
        while time.monotonic() < deadline:
            response = client.get(f"/api/runtime/turn/jobs/{accepted_payload['turnJobId']}")
            assert response.status_code == 200
            payload = response.json()
            if payload["status"] == "succeeded":
                final_payload = payload
                break
            time.sleep(0.02)

    assert final_payload is not None
    assert final_payload["responseReady"] is True
    assert final_payload["ttsReady"] is True
    assert final_payload["response"]["behavior"]["intent"] == "greet"
    assert final_payload["response"]["metadata"]["provider"] == "FastPathRuntimeProvider"
    assert final_payload["speechTimeline"]["audio"]["url"].endswith(".wav")
    assert final_payload["speechTimeline"]["provider"] == "MockTtsProvider"


def test_runtime_turn_async_unknown_job_returns_404() -> None:
    client = TestClient(app)

    response = client.get("/api/runtime/turn/jobs/turn_missing")

    assert response.status_code == 404


def test_runtime_audio_rejects_suspicious_filename() -> None:
    client = TestClient(app)

    response = client.get("/api/runtime/audio/..%5Csecret.wav")

    assert response.status_code == 404


def test_runtime_websocket_sends_reaction_then_final() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws/runtime") as websocket:
        websocket.send_json(
            {
                "type": "runtime_request",
                "requestId": "test_001",
                "sessionId": "ws_test",
                "characterId": "default_girl",
                "message": "hello",
                "sceneContext": {},
            }
        )

        reaction = websocket.receive_json()
        final = websocket.receive_json()

    assert reaction["type"] == "reaction"
    assert reaction["requestId"] == "test_001"
    assert reaction["behavior"]["emotion"] == "thinking"
    assert final["type"] == "final"
    assert final["requestId"] == "test_001"
    assert final["response"]["behavior"]["intent"] == "greet"
    assert final["response"]["metadata"]["provider"] == "FastPathRuntimeProvider"


def test_runtime_websocket_invalid_request_hides_exception_type() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws/runtime") as websocket:
        websocket.send_json({"type": "runtime_request", "requestId": "bad"})
        response = websocket.receive_json()

    assert response["type"] == "error"
    assert response["error"] == "invalid_request"
    assert "KeyError" not in str(response)


def test_runtime_tts_synthesize_returns_audio_timeline() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/runtime/tts/synthesize",
        json={
            "text": "Hello. Nice to meet you.",
            "ttsStyle": "warm",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    timeline = payload["speechTimeline"]
    assert timeline["utteranceId"].startswith("utt_")
    assert timeline["audio"]["url"].endswith(".wav")
    assert timeline["audio"]["durationSeconds"] > 0
    assert timeline["provider"] == "MockTtsProvider"

    audio_response = client.get(timeline["audio"]["url"])
    assert audio_response.status_code == 200
    assert audio_response.headers["content-type"].startswith("audio/wav")
    assert audio_response.content.startswith(b"RIFF")


def test_runtime_tts_synthesize_async_returns_job_result() -> None:
    with TestClient(app) as client:
        accepted = client.post(
            "/api/runtime/tts/synthesize/async",
            json={
                "text": "Hello. Nice to meet you.",
                "ttsStyle": "warm",
            },
        )

        assert accepted.status_code == 200
        accepted_payload = accepted.json()
        assert accepted_payload["jobId"].startswith("tts_")
        assert accepted_payload["status"] in {"pending", "running"}

        deadline = time.monotonic() + 2.0
        final_payload = None
        while time.monotonic() < deadline:
            response = client.get(f"/api/runtime/tts/jobs/{accepted_payload['jobId']}")
            assert response.status_code == 200
            payload = response.json()
            if payload["status"] == "succeeded":
                final_payload = payload
                break
            time.sleep(0.02)

    assert final_payload is not None
    timeline = final_payload["speechTimeline"]
    assert timeline["utteranceId"].startswith("utt_")
    assert timeline["audio"]["url"].endswith(".wav")
    assert timeline["provider"] == "MockTtsProvider"


def test_runtime_tts_synthesize_async_unknown_job_returns_404() -> None:
    client = TestClient(app)

    response = client.get("/api/runtime/tts/jobs/tts_missing")

    assert response.status_code == 404


def test_tts_async_job_times_out() -> None:
    class HangingTtsProvider(TtsProvider):
        async def synthesize(self, *, text, output_path, tts_style, voice=None):
            del text, output_path, tts_style, voice
            await asyncio.sleep(10)
            raise AssertionError("unreachable")

    service = TtsAsyncJobService(
        TtsService(provider=HangingTtsProvider(), provider_timeout_seconds=10),
        job_timeout_seconds=0.01,
    )

    async def run_case():
        from app.contracts.tts import TtsSynthesizeRequest

        job = await service.submit(TtsSynthesizeRequest(text="timeout", ttsStyle="warm"))
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            current = await service.get(job.job_id)
            if current and current.status == "failed":
                return current
            await asyncio.sleep(0.01)
        return await service.get(job.job_id)

    result = asyncio.run(run_case())

    assert result is not None
    assert result.status == "failed"
    assert "TimeoutError" in (result.error or "")


def test_runtime_turn_async_job_times_out() -> None:
    class HangingProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            await asyncio.sleep(10)
            return "late", BehaviorJson()

    service = RuntimeTurnAsyncJobService(
        RuntimeCharacterService(primary_provider=HangingProvider(), provider_timeout_seconds=10),
        TtsService(),
        job_timeout_seconds=0.01,
    )

    async def run_case():
        job = await service.submit(RuntimeRespondRequestForTest("timeout", "default_girl", "turn_timeout"))
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            current = await service.get(job.turn_job_id)
            if current and current.status == "failed":
                return current
            await asyncio.sleep(0.01)
        return await service.get(job.turn_job_id)

    result = asyncio.run(run_case())

    assert result is not None
    assert result.status == "failed"
    assert "TimeoutError" in (result.error or "")


def test_runtime_turn_async_job_fails_when_tts_step_fails() -> None:
    class FailingTtsProvider(TtsProvider):
        async def synthesize(self, *, text, output_path, tts_style, voice=None):
            del text, output_path, tts_style, voice
            raise RuntimeError("forced tts failure")

    service = RuntimeTurnAsyncJobService(
        RuntimeCharacterService(),
        TtsService(
            provider=FailingTtsProvider(),
            fallback_provider=FailingTtsProvider(),
            provider_timeout_seconds=1,
            fallback_timeout_seconds=1,
        ),
    )

    async def run_case():
        job = await service.submit(RuntimeRespondRequestForTest("hello", "default_girl", "turn_tts_fail"))
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            current = await service.get(job.turn_job_id)
            if current and current.status == "failed":
                return current
            await asyncio.sleep(0.01)
        return await service.get(job.turn_job_id)

    result = asyncio.run(run_case())

    assert result is not None
    assert result.status == "failed"
    assert result.response_result is not None
    assert "RuntimeError" in (result.error or "")


def test_runtime_turn_async_job_returns_segmented_tts_for_multi_sentence_reply() -> None:
    class TwoSentenceProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            return "Hello there. Nice to meet you.", BehaviorJson(intent="greet", emotion="friendly")

    service = RuntimeTurnAsyncJobService(
        RuntimeCharacterService(primary_provider=TwoSentenceProvider()),
        TtsService(),
    )

    async def run_case():
        job = await service.submit(RuntimeRespondRequestForTest("hello", "default_girl", "turn_segments"))
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            current = await service.get(job.turn_job_id)
            if current and current.status == "succeeded":
                return current
            await asyncio.sleep(0.01)
        return await service.get(job.turn_job_id)

    result = asyncio.run(run_case())

    assert result is not None
    assert result.status == "succeeded"
    assert result.speech_timeline is not None
    assert len(result.speech_timeline.segments) == 2
    assert result.speech_timeline.audio.url == result.speech_timeline.segments[0].audio.url
    assert result.speech_timeline.segments[1].start_time >= result.speech_timeline.segments[0].duration_seconds


def test_runtime_turn_async_job_returns_single_segment_for_single_sentence_reply() -> None:
    class SingleSentenceProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            return "Hello there.", BehaviorJson(intent="greet", emotion="friendly")

    service = RuntimeTurnAsyncJobService(
        RuntimeCharacterService(primary_provider=SingleSentenceProvider()),
        TtsService(),
    )

    async def run_case():
        job = await service.submit(RuntimeRespondRequestForTest("hello", "default_girl", "turn_single_segment"))
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            current = await service.get(job.turn_job_id)
            if current and current.status == "succeeded":
                return current
            await asyncio.sleep(0.01)
        return await service.get(job.turn_job_id)

    result = asyncio.run(run_case())

    assert result is not None
    assert result.status == "succeeded"
    assert result.speech_timeline is not None
    assert len(result.speech_timeline.segments) == 1
    assert result.speech_timeline.segments[0].text == "Hello there."
    assert result.speech_timeline.audio.url == result.speech_timeline.segments[0].audio.url


def test_runtime_async_shutdown_marks_running_job_failed() -> None:
    class HangingProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            await asyncio.sleep(10)
            return "late", BehaviorJson()

    service = RuntimeAsyncJobService(
        RuntimeCharacterService(primary_provider=HangingProvider(), provider_timeout_seconds=10),
        job_timeout_seconds=10,
    )

    async def run_case():
        job = await service.submit(RuntimeRespondRequestForTest("shutdown", "default_girl", "shutdown"))
        await asyncio.sleep(0)
        await service.shutdown()
        return await service.get(job.job_id)

    result = asyncio.run(run_case())

    assert result is not None
    assert result.status == "failed"
    assert "server shutdown" in (result.error or "")


def test_runtime_service_falls_back_when_primary_provider_fails() -> None:
    class FailingProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            raise RuntimeError("forced failure")

    service = RuntimeCharacterService(primary_provider=FailingProvider(), provider_timeout_seconds=0.1)

    result = asyncio.run(service.respond("force provider failure", SceneContext(), "default_guide"))

    assert result.reply
    assert result.behavior.intent == "fallback"
    assert result.metadata.fallback_used is True
    assert result.metadata.route == "fallback"


def test_runtime_service_logs_primary_timeout_failures(tmp_path) -> None:
    class TimeoutProvider(RuntimeBehaviorProvider):
        model_name = "timeout-model"

        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            raise TimeoutError("provider too slow")

    failure_path = tmp_path / "provider_failures.jsonl"
    service = RuntimeCharacterService(
        primary_provider=TimeoutProvider(),
        provider_timeout_seconds=0.1,
        failure_logger=ProviderFailureLogger(failure_path),
    )

    result = asyncio.run(service.respond("hello", SceneContext(), "default_guide", session_id="timeout_session"))

    assert result.metadata.fallback_used is True
    text = failure_path.read_text(encoding="utf-8")
    assert '"errorType":"TimeoutError"' in text
    assert '"route":""' in text
    assert "timeout_session" in text


def test_runtime_async_job_times_out() -> None:
    class HangingProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            await asyncio.sleep(10)
            return "late", BehaviorJson()

    runtime_service = RuntimeCharacterService(
        primary_provider=HangingProvider(),
        provider_timeout_seconds=10,
    )
    job_service = RuntimeAsyncJobService(runtime_service, job_timeout_seconds=0.01)

    async def run_case():
        job = await job_service.submit(
            RuntimeRespondRequestForTest("timeout", "default_girl", "timeout_session")
        )
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            current = await job_service.get(job.job_id)
            if current and current.status == "failed":
                return current
            await asyncio.sleep(0.01)
        return await job_service.get(job.job_id)

    result = asyncio.run(run_case())

    assert result is not None
    assert result.status == "failed"
    assert "TimeoutError" in (result.error or "")


def test_runtime_async_prune_respects_max_jobs() -> None:
    service = RuntimeAsyncJobService(RuntimeCharacterService(), max_jobs=1, prune_interval_seconds=0)

    async def run_case():
        first = await service.submit(RuntimeRespondRequestForTest("hello", "default_girl", "p1"))
        second = await service.submit(RuntimeRespondRequestForTest("hello", "default_girl", "p2"))
        await service.prune_expired()
        return await service.get(first.job_id), await service.get(second.job_id)

    first_job, second_job = asyncio.run(run_case())

    assert first_job is None
    assert second_job is not None


def test_runtime_async_rejects_when_active_jobs_reach_limit() -> None:
    class HangingProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            await asyncio.sleep(10)
            return "late", BehaviorJson()

    service = RuntimeAsyncJobService(
        RuntimeCharacterService(primary_provider=HangingProvider(), provider_timeout_seconds=10),
        max_in_flight=1,
        job_timeout_seconds=10,
    )

    async def run_case():
        first = await service.submit(RuntimeRespondRequestForTest("hello", "default_girl", "limit_session"))
        try:
            await service.submit(RuntimeRespondRequestForTest("hello", "default_girl", "limit_session"))
        except ServiceBusyError as exc:
            await service.shutdown()
            return first, str(exc)
        await service.shutdown()
        return first, ""

    first_job, error = asyncio.run(run_case())

    assert first_job.job_id.startswith("rt_")
    assert "runtime queue is full" in error


def test_tts_service_cleanup_audio_files(tmp_path) -> None:
    service = TtsService(audio_root=tmp_path)
    old_file = tmp_path / "old.wav"
    new_file = tmp_path / "new.wav"
    old_file.write_bytes(b"RIFF-old")
    new_file.write_bytes(b"RIFF-new")
    old_time = time.time() - 120
    import os

    os.utime(old_file, (old_time, old_time))

    deleted = asyncio.run(service.cleanup_audio_files(ttl_seconds=60, max_files=10))

    assert deleted == 1
    assert not old_file.exists()
    assert new_file.exists()


def RuntimeRespondRequestForTest(message: str, character_id: str, session_id: str):
    from app.contracts.requests import RuntimeRespondRequest

    return RuntimeRespondRequest(
        message=message,
        characterId=character_id,
        sessionId=session_id,
    )


def test_runtime_service_uses_emergency_response_when_fallback_fails() -> None:
    class FailingProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            raise RuntimeError("forced failure")

    service = RuntimeCharacterService(
        primary_provider=FailingProvider(),
        fallback_provider=FailingProvider(),
        provider_timeout_seconds=0.1,
        fallback_timeout_seconds=0.1,
    )

    result = asyncio.run(service.respond("force total failure", SceneContext(), "default_guide"))

    assert result.reply
    assert result.behavior.intent == "fallback"
    assert result.metadata.provider == "EmergencyRuntimeProvider"
    assert result.metadata.fallback_used is True
    assert result.metadata.route == "fallback"


def test_runtime_service_guards_bad_greet_intent_for_emotional_message() -> None:
    class BadIntentProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            return "What happened?", BehaviorJson(intent="greet", emotion="friendly")

    service = RuntimeCharacterService(primary_provider=BadIntentProvider())

    result = asyncio.run(service.respond("I feel sad today.", SceneContext(), "default_guide"))

    assert result.behavior.intent == "clarify"
    assert result.behavior.emotion == "concerned"
    assert result.behavior.tts_style == "careful"


def test_runtime_service_guards_neutral_apology_as_concerned() -> None:
    class NeutralApologyProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            return "Thank you for saying that.", BehaviorJson(intent="answer", emotion="neutral")

    service = RuntimeCharacterService(primary_provider=NeutralApologyProvider())

    result = asyncio.run(
        service.respond("I'm sorry, I didn't mean to make you feel that way.", SceneContext(), "i_f_s")
    )

    assert result.behavior.intent == "answer"
    assert result.behavior.emotion == "concerned"
    assert result.behavior.tts_style == "careful"


def test_runtime_service_guards_apology_explain_intent_as_answer() -> None:
    class ExplainApologyProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            return "Let's move forward.", BehaviorJson(intent="explain", emotion="friendly")

    service = RuntimeCharacterService(primary_provider=ExplainApologyProvider())

    result = asyncio.run(service.respond("I'm sorry, I didn't mean to make you feel that way.", SceneContext(), "e_t_s"))

    assert result.behavior.intent == "answer"
    assert result.behavior.emotion == "friendly"


def test_runtime_service_passes_session_history_to_provider() -> None:
    seen_history_lengths: list[int] = []

    class HistoryProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, character_profile
            seen_history_lengths.append(len(conversation_history or []))
            return "ok", BehaviorJson()

    service = RuntimeCharacterService(primary_provider=HistoryProvider())

    asyncio.run(service.respond("first", SceneContext(), "default_guide", session_id="s1"))
    asyncio.run(service.respond("second", SceneContext(), "default_guide", session_id="s1"))

    assert seen_history_lengths == [0, 2]


def test_runtime_service_applies_repeated_emotional_scenario_hint() -> None:
    seen_messages: list[str] = []

    class ScenarioProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del scene_context, character_id, conversation_history, character_profile
            seen_messages.append(message)
            return "I am listening.", BehaviorJson(emotion="neutral", intent="answer", intensity=0.2, confidence=0.9)

    service = RuntimeCharacterService(primary_provider=ScenarioProvider())

    asyncio.run(service.respond("I feel sad today.", SceneContext(), "default_girl", session_id="scenario_sad"))
    result = asyncio.run(service.respond("I still feel lonely.", SceneContext(), "default_girl", session_id="scenario_sad"))

    assert seen_messages[0] == "I feel sad today."
    assert seen_messages[1].startswith("scenarioHint:")
    assert "repeated" in seen_messages[1]
    assert result.behavior.emotion == "concerned"
    assert result.behavior.tts_style == "careful"
    assert result.behavior.intensity >= 0.62
    assert result.behavior.confidence <= 0.72


def test_runtime_service_uses_shared_emotional_keywords_for_guard_and_scenario() -> None:
    seen_messages: list[str] = []

    class ScenarioProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del scene_context, character_id, conversation_history, character_profile
            seen_messages.append(message)
            return "I understand.", BehaviorJson(emotion="neutral", intent="answer", confidence=0.9)

    service = RuntimeCharacterService(primary_provider=ScenarioProvider())

    anxious_result = asyncio.run(
        service.respond("I feel anxious today.", SceneContext(), "default_girl", session_id="shared_keywords")
    )
    tired_result = asyncio.run(
        service.respond(
            "\ud53c\uace4\ud574.",
            SceneContext(),
            "default_girl",
            session_id="shared_keywords",
        )
    )

    assert anxious_result.behavior.emotion == "concerned"
    assert anxious_result.behavior.tts_style == "careful"
    assert seen_messages[0] == "I feel anxious today."
    assert seen_messages[1].startswith("scenarioHint:")
    assert tired_result.behavior.emotion == "concerned"
    assert tired_result.behavior.confidence <= 0.72


def test_runtime_service_applies_focused_object_scenario() -> None:
    seen_messages: list[str] = []

    class ScenarioProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del scene_context, character_id, conversation_history, character_profile
            seen_messages.append(message)
            return "This object is important.", BehaviorJson(emotion="friendly", intent="answer")

    service = RuntimeCharacterService(primary_provider=ScenarioProvider())

    result = asyncio.run(
        service.respond(
            "Can you explain this?",
            SceneContext(focusedObjectId="avatar_display"),
            "default_girl",
            session_id="scenario_object",
        )
    )

    assert seen_messages[0].startswith("scenarioHint:")
    assert "focused object" in seen_messages[0]
    assert result.behavior.intent == "explain"
    assert result.behavior.gaze == "focused_object"
    assert result.behavior.gesture_key == "explain_small"


def test_runtime_service_passes_minimal_character_profile_to_provider() -> None:
    seen_profile_ids: list[str] = []

    class ProfileProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history
            seen_profile_ids.append(character_profile.character_id)
            return "ok", BehaviorJson(intensity=1.0)

    service = RuntimeCharacterService(primary_provider=ProfileProvider())

    result = asyncio.run(service.respond("profile provider check", SceneContext(), "default_girl"))

    assert seen_profile_ids == ["default_girl"]
    assert result.behavior.intensity == 0.9


def test_character_profile_store_contains_eight_personality_presets() -> None:
    store = CharacterProfileStore()
    expected_ids = ["e_f_n", "e_f_s", "e_t_n", "e_t_s", "i_f_n", "i_f_s", "i_t_n", "i_t_s"]

    profiles = [store.get(character_id) for character_id in expected_ids]

    assert [profile.character_id for profile in profiles] == expected_ids
    assert store.get("e_f_n").energy > store.get("i_f_n").energy
    assert store.get("e_f_n").empathy > store.get("e_t_n").empathy
    assert store.get("e_f_n").imagination > store.get("e_f_s").imagination
    assert store.get("e_f_n").playfulness >= 0.67


def test_profile_prompt_builder_maps_profile_values_to_natural_language() -> None:
    profile = CharacterProfileStore().get("i_t_s")

    prompt = ProfilePromptBuilder.build(profile)

    assert "Stay calm" in prompt
    assert "Prioritize clear reasoning" in prompt
    assert "Prefer concrete" in prompt
    assert "Rarely end with a question" in prompt
    assert "energy" not in prompt
    assert "0.18" not in prompt


def test_openai_provider_uses_character_voice_prompt_not_raw_profile_json() -> None:
    provider = OpenAiRuntimeBehaviorProvider(api_key="test", model="test")
    profile = CharacterProfileStore().get("e_f_n")

    prompt = provider._build_input("안녕", SceneContext(), "e_f_n", [], profile)

    assert "characterVoice:" in prompt
    assert "Use bright, lively reactions" in prompt
    assert "playful teasing" in prompt
    assert "characterProfile:" not in prompt
    assert "emotionIntensityScale" not in prompt


def test_openai_provider_extracts_json_object_from_extra_text() -> None:
    provider = OpenAiRuntimeBehaviorProvider(api_key="test", model="test")

    reply, behavior = provider._parse_model_output(
        'Here is the result: {"reply":"ok","behavior":{"emotion":"thinking","intent":"answer"}} Thanks.'
    )

    assert reply == "ok"
    assert behavior.emotion == "thinking"
    assert behavior.intent == "answer"


def test_openai_provider_normalizes_common_behavior_enum_aliases() -> None:
    provider = OpenAiRuntimeBehaviorProvider(api_key="test", model="test")

    reply, behavior = provider._parse_model_output(
        '{"reply":"ok","behavior":{"emotion":"calm","intent":"comfort","gaze":"user",'
        '"gestureKey":"nod","headMotion":"nod","ttsStyle":"soft"}}'
    )

    assert reply == "ok"
    assert behavior.emotion == "neutral"
    assert behavior.intent == "answer"
    assert behavior.gesture_key == "small_ack"
    assert behavior.head_motion == "small_nod"
    assert behavior.tts_style == "warm"

    _, caring_behavior = provider._parse_model_output(
        '{"reply":"ok","behavior":{"emotion":"caring","intent":"answer","gaze":"user",'
        '"gestureKey":"none","headMotion":"none","ttsStyle":"warm"}}'
    )
    assert caring_behavior.emotion == "friendly"

    _, voice_alias_behavior = provider._parse_model_output(
        '{"reply":"ok","behavior":{"emotion":"friendly","intent":"answer","gaze":"user",'
        '"gestureKey":"none","headMotion":"none","ttsStyle":"friendly"}}'
    )
    assert voice_alias_behavior.tts_style == "warm"


def test_openai_provider_ignores_extra_closing_brace_after_json() -> None:
    provider = OpenAiRuntimeBehaviorProvider(api_key="test", model="test")

    reply, behavior = provider._parse_model_output(
        '{"reply":"ok","behavior":{"emotion":"friendly","intent":"answer","gaze":"user",'
        '"gestureKey":"none","headMotion":"none","ttsStyle":"warm"}}}'
    )

    assert reply == "ok"
    assert behavior.emotion == "friendly"


def test_openai_provider_records_unknown_behavior_enum_failures(tmp_path) -> None:
    failure_path = tmp_path / "provider_failures.jsonl"
    provider = OpenAiRuntimeBehaviorProvider(
        api_key="test",
        model="test",
        failure_logger=ProviderFailureLogger(failure_path),
    )

    with pytest.raises(ValueError):
        provider._parse_model_output(
            '{"reply":"ok","behavior":{"emotion":"sleepy","intent":"answer"}}'
        )

    text = failure_path.read_text(encoding="utf-8")
    assert '"errorType":"ValidationError"' in text
    assert '"sleepy"' in text


def test_routing_openai_provider_uses_short_social_provider_for_short_emotional_input() -> None:
    calls: list[str] = []

    class NamedProvider(RuntimeBehaviorProvider):
        def __init__(self, name: str) -> None:
            self.model_name = name

        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            calls.append(self.model_name)
            return self.model_name, BehaviorJson()

    provider = RoutingOpenAiRuntimeBehaviorProvider(
        short_social_provider=NamedProvider("nano"),
        default_provider=NamedProvider("mini"),
    )

    reply, _ = asyncio.run(provider.respond("안녕 오늘 너무 춥다 그지", SceneContext(), "default_girl"))

    assert reply == "nano"
    assert calls == ["nano"]
    assert provider.route_for("안녕 오늘 너무 춥다 그지", SceneContext()) == ("short_social", "nano")
    assert provider.route_for("오늘 뭐 하고 있었어?", SceneContext()) == ("short_social", "nano")
    assert provider.route_for("미안해, 아까 말이 너무 세게 나간 것 같아", SceneContext()) == ("short_social", "nano")
    assert provider.route_for("I'm sorry, I didn't mean to sound harsh.", SceneContext()) == ("short_social", "nano")
    assert provider.route_for("괜찮아 괜찮아, 근데 좀 속상하긴 해", SceneContext()) == ("short_social", "nano")


def test_routing_openai_provider_uses_default_for_weather_or_complex_input() -> None:
    calls: list[str] = []

    class NamedProvider(RuntimeBehaviorProvider):
        def __init__(self, name: str) -> None:
            self.model_name = name

        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
            conversation_history: list | None = None,
            character_profile: object | None = None,
        ) -> tuple[str, BehaviorJson]:
            del message, scene_context, character_id, conversation_history, character_profile
            calls.append(self.model_name)
            return self.model_name, BehaviorJson()

    provider = RoutingOpenAiRuntimeBehaviorProvider(
        short_social_provider=NamedProvider("nano"),
        default_provider=NamedProvider("mini"),
    )

    reply, _ = asyncio.run(provider.respond("안녕? 오늘 서울 날씨 어때?", SceneContext(), "default_girl"))

    assert reply == "mini"
    assert calls == ["mini"]
    assert provider.route_for("안녕? 오늘 서울 날씨 어때?", SceneContext()) == ("default", "mini")


def test_runtime_service_writes_latency_metrics_csv(tmp_path) -> None:
    metrics_path = tmp_path / "runtime_latency.csv"
    service = RuntimeCharacterService(metrics_logger=LatencyMetricsLogger(metrics_path))

    asyncio.run(service.respond("hello", SceneContext(), "default_girl", session_id="metrics_session"))

    text = metrics_path.read_text(encoding="utf-8-sig")
    assert "timestamp,session_id,request_id" in text
    assert "metrics_session" in text
    assert "text_fastpath_behavior_json_v1" in text


def test_provider_failure_logger_redacts_sample_in_production(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("RUNTIME_LOG_PRIVATE_DATA", raising=False)
    log_path = tmp_path / "provider_failures.jsonl"
    logger = ProviderFailureLogger(log_path)

    logger.append(
        provider="Provider",
        model="model",
        error_type="ValidationError",
        error_message="bad output",
        sample="user said a private thing and model replied with private content",
    )

    text = log_path.read_text(encoding="utf-8")
    assert "private thing" not in text
    assert "model replied" not in text
    assert "[redacted chars=" in text
    assert "sha256=" in text


def test_provider_failure_logger_can_keep_sample_for_local_debug(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("RUNTIME_LOG_PRIVATE_DATA", "true")
    log_path = tmp_path / "provider_failures.jsonl"
    logger = ProviderFailureLogger(log_path)

    logger.append(
        provider="Provider",
        model="model",
        error_type="ValidationError",
        error_message="bad output",
        sample="local debug sample",
    )

    assert "local debug sample" in log_path.read_text(encoding="utf-8")


def test_latency_metrics_logger_migrates_legacy_header(tmp_path) -> None:
    metrics_path = tmp_path / "runtime_latency.csv"
    legacy_header = ",".join(LatencyMetricsLogger.PreviousHeaderWithoutRoute)
    legacy_row = (
        "2026-01-01T00:00:00+00:00,s,r,text,5,Provider,model,"
        "text_llm_behavior_json_v1,False,-1,10,-1,10,-1,-1,-1,friendly,answer,old"
    )
    metrics_path.write_text(f"{legacy_header}\n{legacy_row}\n", encoding="utf-8-sig")

    logger = LatencyMetricsLogger(metrics_path)
    logger.append_runtime_response(
        metadata=RuntimeResponseMetadata(
            requestId="new",
            provider="Provider",
            model="model",
            techProfile="text_llm_behavior_json_v1",
            inputMode="text",
            fallbackUsed=False,
            providerLatencyMs=10,
            totalServerMs=10,
            route="default",
        ),
        session_id="new_session",
        message="hello",
        behavior=BehaviorJson(emotion="friendly", intent="answer"),
    )

    text = metrics_path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    assert lines[0].split(",")[7] == "route"
    assert ",model,,text_llm_behavior_json_v1," in lines[1]
    assert ",model,default,text_llm_behavior_json_v1," in lines[2]


def test_runtime_debug_emotion_command_outputs_each_emotion() -> None:
    client = TestClient(app)
    emotions = [
        "neutral",
        "friendly",
        "happy",
        "thinking",
        "curious",
        "concerned",
        "uncertain",
        "apologetic",
    ]

    for emotion in emotions:
        response = client.post(
            "/api/runtime/respond",
            json={
                "sessionId": "emotion_debug_test",
                "characterId": "default_girl",
                "message": f"/emotion {emotion}",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["behavior"]["emotion"] == emotion
        assert payload["metadata"]["provider"] == "DebugEmotionProvider"
        assert payload["metadata"]["fallbackUsed"] is False
