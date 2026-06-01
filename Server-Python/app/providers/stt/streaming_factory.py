from __future__ import annotations

import os

from app.providers.stt.azure_streaming_provider import AzureSpeechStreamingSttProvider
from app.providers.stt.base import StreamingSttProvider, StreamingSttSession
from app.providers.stt.google_streaming_provider import GoogleSpeechStreamingSttProvider
from app.providers.stt.openai_realtime_streaming_provider import OpenAiRealtimeStreamingSttProvider


def create_streaming_stt_provider() -> StreamingSttProvider:
    provider = os.getenv("STREAMING_STT_PROVIDER", "azure").strip().lower()
    if provider == "azure":
        speech_key = os.getenv("AZURE_SPEECH_KEY")
        speech_region = os.getenv("AZURE_SPEECH_REGION")
        if not speech_key or not speech_region:
            raise RuntimeError("Azure Speech credentials are required for streaming STT")
        return AzureSpeechStreamingSttProvider(speech_key=speech_key, speech_region=speech_region)

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI realtime streaming STT")
        return OpenAiRealtimeStreamingSttProvider(
            api_key=api_key,
            endpoint=os.getenv(
                "OPENAI_REALTIME_STT_ENDPOINT",
                "wss://api.openai.com/v1/realtime?intent=transcription",
            ),
            model=os.getenv("OPENAI_REALTIME_STT_MODEL", "gpt-4o-mini-transcribe"),
            delay=os.getenv("OPENAI_REALTIME_STT_DELAY", "low"),
            final_wait_seconds=float(os.getenv("OPENAI_REALTIME_STT_FINAL_WAIT_SECONDS", "2.0")),
        )

    if provider == "google":
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_STT_PROJECT_ID")
        if not project_id:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Google streaming STT")
        return GoogleSpeechStreamingSttProvider(
            project_id=project_id,
            location=os.getenv("GOOGLE_STT_LOCATION", "global"),
            recognizer=os.getenv("GOOGLE_STT_RECOGNIZER", "_"),
            model=os.getenv("GOOGLE_STT_MODEL", "latest_short"),
            chunk_limit_bytes=int(os.getenv("GOOGLE_STT_CHUNK_LIMIT_BYTES", "24000")),
            stop_wait_seconds=float(os.getenv("GOOGLE_STT_STOP_WAIT_SECONDS", "2.0")),
        )

    raise RuntimeError(f"Unsupported STREAMING_STT_PROVIDER: {provider}")


def create_streaming_stt_session(*, language: str, sample_rate: int) -> StreamingSttSession:
    return create_streaming_stt_provider().create_session(language=language, sample_rate=sample_rate)
