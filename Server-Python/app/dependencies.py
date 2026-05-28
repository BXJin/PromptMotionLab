from functools import lru_cache
import os
from pathlib import Path

from app.providers.llm import MockLlmProvider
from app.providers.runtime import OpenAiRuntimeBehaviorProvider, RoutingOpenAiRuntimeBehaviorProvider
from app.providers.stt import OpenAiSttProvider
from app.providers.tts import AzureSpeechTtsProvider
from app.services import (
    MotionGenerationService,
    RuntimeAsyncJobService,
    RuntimeCharacterService,
    RuntimeTurnAsyncJobService,
    SttService,
    TtsAsyncJobService,
    TtsService,
)
from app.storage import PromptExportStore


@lru_cache(maxsize=1)
def get_motion_generation_service() -> MotionGenerationService:
    data_root = Path(__file__).resolve().parent.parent / "data" / "prompt_exports"
    return MotionGenerationService(
        llm_provider=MockLlmProvider(),
        prompt_store=PromptExportStore(data_root),
    )


@lru_cache(maxsize=1)
def get_runtime_character_service() -> RuntimeCharacterService:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
    if not api_key:
        return RuntimeCharacterService()

    endpoint = os.getenv("OPENAI_RESPONSES_ENDPOINT", "https://api.openai.com/v1/responses")
    timeout_seconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "3.5"))
    max_history_turns = int(os.getenv("RUNTIME_OPENAI_HISTORY_TURNS", "20"))
    openai_max_concurrency = int(os.getenv("OPENAI_MAX_CONCURRENCY", "8"))
    default_provider = OpenAiRuntimeBehaviorProvider(
        api_key=api_key,
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        endpoint=endpoint,
        timeout_seconds=timeout_seconds,
        max_output_tokens=int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "130")),
        max_history_turns=max_history_turns,
        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.55")),
        max_concurrency=openai_max_concurrency,
    )
    if os.getenv("OPENAI_ROUTING_ENABLED", "1").strip().lower() in {"0", "false", "no"}:
        primary_provider = default_provider
    else:
        primary_provider = RoutingOpenAiRuntimeBehaviorProvider(
            short_social_provider=OpenAiRuntimeBehaviorProvider(
                api_key=api_key,
                model=os.getenv("OPENAI_NANO_MODEL", "gpt-4.1-nano"),
                endpoint=endpoint,
                timeout_seconds=timeout_seconds,
                max_output_tokens=int(os.getenv("OPENAI_NANO_MAX_OUTPUT_TOKENS", "110")),
                max_history_turns=max_history_turns,
                temperature=float(os.getenv("OPENAI_NANO_TEMPERATURE", "0.75")),
                max_concurrency=int(os.getenv("OPENAI_NANO_MAX_CONCURRENCY", str(openai_max_concurrency))),
            ),
            default_provider=default_provider,
            short_token_limit=int(os.getenv("OPENAI_ROUTER_SHORT_TOKEN_LIMIT", "20")),
            short_char_limit=int(os.getenv("OPENAI_ROUTER_SHORT_CHAR_LIMIT", "90")),
        )

    return RuntimeCharacterService(
        primary_provider=primary_provider,
        provider_timeout_seconds=float(os.getenv("RUNTIME_PROVIDER_TIMEOUT_SECONDS", "3.75")),
        fallback_timeout_seconds=float(os.getenv("RUNTIME_FALLBACK_TIMEOUT_SECONDS", "0.75")),
        max_in_flight=int(os.getenv("RUNTIME_MAX_IN_FLIGHT", "64")),
    )


@lru_cache(maxsize=1)
def get_runtime_async_job_service() -> RuntimeAsyncJobService:
    return RuntimeAsyncJobService(
        get_runtime_character_service(),
        max_jobs=int(os.getenv("RUNTIME_ASYNC_MAX_JOBS", "256")),
        ttl_seconds=float(os.getenv("RUNTIME_ASYNC_JOB_TTL_SECONDS", "300")),
        prune_interval_seconds=float(os.getenv("RUNTIME_ASYNC_PRUNE_INTERVAL_SECONDS", "5")),
        job_timeout_seconds=float(os.getenv("RUNTIME_ASYNC_JOB_TIMEOUT_SECONDS", "15")),
        max_in_flight=int(os.getenv("RUNTIME_ASYNC_MAX_IN_FLIGHT", "64")),
    )


@lru_cache(maxsize=1)
def get_tts_service() -> TtsService:
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")
    if not speech_key or not speech_region:
        return TtsService(
            provider_max_concurrency=int(os.getenv("TTS_PROVIDER_MAX_CONCURRENCY", "8")),
            max_in_flight=int(os.getenv("TTS_MAX_IN_FLIGHT", "64")),
        )

    return TtsService(
        provider=AzureSpeechTtsProvider(
            speech_key=speech_key,
            speech_region=speech_region,
            default_voice=os.getenv("AZURE_TTS_VOICE", "en-US-JennyNeural"),
            korean_voice=os.getenv("AZURE_TTS_KO_VOICE", "ko-KR-SunHiNeural"),
            viseme_trim_tail_seconds=float(os.getenv("TTS_VISEME_TRIM_TAIL_SECONDS", "0.15")),
        ),
        provider_timeout_seconds=float(os.getenv("TTS_PROVIDER_TIMEOUT_SECONDS", "4.0")),
        fallback_timeout_seconds=float(os.getenv("TTS_FALLBACK_TIMEOUT_SECONDS", "1.0")),
        provider_max_concurrency=int(os.getenv("TTS_PROVIDER_MAX_CONCURRENCY", "8")),
        max_in_flight=int(os.getenv("TTS_MAX_IN_FLIGHT", "64")),
    )


@lru_cache(maxsize=1)
def get_stt_service() -> SttService:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
    if not api_key:
        return SttService(
            provider_max_concurrency=int(os.getenv("STT_PROVIDER_MAX_CONCURRENCY", "8")),
            max_in_flight=int(os.getenv("STT_MAX_IN_FLIGHT", "64")),
            max_audio_bytes=int(os.getenv("STT_MAX_AUDIO_BYTES", str(5 * 1024 * 1024))),
        )

    return SttService(
        provider=OpenAiSttProvider(
            api_key=api_key,
            model=os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe"),
            endpoint=os.getenv("OPENAI_STT_ENDPOINT", "https://api.openai.com/v1/audio/transcriptions"),
            timeout_seconds=float(os.getenv("OPENAI_STT_TIMEOUT_SECONDS", "4.0")),
        ),
        provider_timeout_seconds=float(os.getenv("STT_PROVIDER_TIMEOUT_SECONDS", "4.0")),
        fallback_timeout_seconds=float(os.getenv("STT_FALLBACK_TIMEOUT_SECONDS", "1.0")),
        provider_max_concurrency=int(os.getenv("STT_PROVIDER_MAX_CONCURRENCY", "8")),
        max_in_flight=int(os.getenv("STT_MAX_IN_FLIGHT", "64")),
        max_audio_bytes=int(os.getenv("STT_MAX_AUDIO_BYTES", str(5 * 1024 * 1024))),
    )


@lru_cache(maxsize=1)
def get_tts_async_job_service() -> TtsAsyncJobService:
    return TtsAsyncJobService(
        get_tts_service(),
        max_jobs=int(os.getenv("TTS_ASYNC_MAX_JOBS", "256")),
        ttl_seconds=float(os.getenv("TTS_ASYNC_JOB_TTL_SECONDS", "300")),
        prune_interval_seconds=float(os.getenv("TTS_ASYNC_PRUNE_INTERVAL_SECONDS", "5")),
        job_timeout_seconds=float(os.getenv("TTS_ASYNC_JOB_TIMEOUT_SECONDS", "15")),
        max_in_flight=int(os.getenv("TTS_ASYNC_MAX_IN_FLIGHT", "64")),
    )


@lru_cache(maxsize=1)
def get_runtime_turn_async_job_service() -> RuntimeTurnAsyncJobService:
    return RuntimeTurnAsyncJobService(
        get_runtime_character_service(),
        get_tts_service(),
        max_jobs=int(os.getenv("RUNTIME_TURN_ASYNC_MAX_JOBS", "256")),
        ttl_seconds=float(os.getenv("RUNTIME_TURN_ASYNC_JOB_TTL_SECONDS", "300")),
        prune_interval_seconds=float(os.getenv("RUNTIME_TURN_ASYNC_PRUNE_INTERVAL_SECONDS", "5")),
        job_timeout_seconds=float(os.getenv("RUNTIME_TURN_ASYNC_JOB_TIMEOUT_SECONDS", "20")),
        max_in_flight=int(os.getenv("RUNTIME_TURN_ASYNC_MAX_IN_FLIGHT", "64")),
        segment_tts_enabled=os.getenv("RUNTIME_TURN_SEGMENT_TTS_ENABLED", "1").strip().lower() not in {"0", "false", "no"},
        max_tts_segments=int(os.getenv("RUNTIME_TURN_MAX_TTS_SEGMENTS", "4")),
    )
