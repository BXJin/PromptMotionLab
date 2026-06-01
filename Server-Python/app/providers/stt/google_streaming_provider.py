from __future__ import annotations

import asyncio
import queue
import threading
import time
from collections.abc import Iterator

from app.providers.stt.base import StreamingSttEvent, StreamingSttProvider, StreamingSttSession


class GoogleSpeechStreamingSttSession(StreamingSttSession):
    provider_name = "GoogleSpeechStreamingSttProvider"

    def __init__(
        self,
        *,
        project_id: str,
        location: str,
        recognizer: str,
        model: str,
        language: str,
        sample_rate: int,
        chunk_limit_bytes: int = 24_000,
        stop_wait_seconds: float = 2.0,
    ) -> None:
        if not project_id.strip():
            raise ValueError("project_id is required")
        self._project_id = project_id
        self._location = location or "global"
        self._recognizer = recognizer or "_"
        self._model = model
        self._language = _normalize_language(language)
        self._sample_rate = sample_rate
        self._chunk_limit_bytes = chunk_limit_bytes
        self._stop_wait_seconds = stop_wait_seconds
        self._started_at = 0.0
        self._audio_queue: queue.Queue[bytes | None] = queue.Queue()
        self._event_queue: asyncio.Queue[StreamingSttEvent] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    @property
    def model_name(self) -> str:
        return self._model

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._started_at = time.perf_counter()
        self._thread = threading.Thread(target=self._run_stream, daemon=True)
        self._thread.start()

    async def write(self, pcm_bytes: bytes) -> None:
        if not pcm_bytes:
            return
        for offset in range(0, len(pcm_bytes), self._chunk_limit_bytes):
            self._audio_queue.put(pcm_bytes[offset : offset + self._chunk_limit_bytes])

    async def stop(self) -> None:
        self._audio_queue.put(None)
        if self._thread is not None:
            await asyncio.to_thread(self._thread.join, self._stop_wait_seconds)

    async def next_event(self, timeout_seconds: float = 0.0) -> StreamingSttEvent | None:
        try:
            if timeout_seconds <= 0.0:
                return self._event_queue.get_nowait()
            return await asyncio.wait_for(self._event_queue.get(), timeout_seconds)
        except (asyncio.QueueEmpty, asyncio.TimeoutError):
            return None

    def _run_stream(self) -> None:
        try:
            from google.cloud.speech_v2 import SpeechClient
            from google.cloud.speech_v2.types import cloud_speech
        except ImportError as exc:
            self._emit("error", error="google-cloud-speech is not installed")
            return

        try:
            client = SpeechClient()
            recognizer_name = f"projects/{self._project_id}/locations/{self._location}/recognizers/{self._recognizer}"
            config = cloud_speech.RecognitionConfig(
                explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                    encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=self._sample_rate,
                    audio_channel_count=1,
                ),
                language_codes=[self._language],
                model=self._model,
            )
            streaming_config = cloud_speech.StreamingRecognitionConfig(config=config)

            responses = client.streaming_recognize(
                requests=self._request_iter(cloud_speech, recognizer_name, streaming_config)
            )
            for response in responses:
                for result in response.results:
                    text = result.alternatives[0].transcript if result.alternatives else ""
                    self._emit("final" if result.is_final else "partial", text=text)
        except Exception as exc:
            self._emit("error", error=str(exc))

    def _request_iter(self, cloud_speech, recognizer_name: str, streaming_config) -> Iterator:
        yield cloud_speech.StreamingRecognizeRequest(
            recognizer=recognizer_name,
            streaming_config=streaming_config,
        )
        while True:
            audio = self._audio_queue.get()
            if audio is None:
                return
            yield cloud_speech.StreamingRecognizeRequest(audio=audio)

    def _emit(self, event_type: str, text: str = "", error: str = "") -> None:
        if self._loop is None:
            return
        elapsed_ms = int((time.perf_counter() - self._started_at) * 1000) if self._started_at else 0
        event = StreamingSttEvent(
            type=event_type,
            text=(text or "").strip(),
            language=self._language,
            duration_ms=elapsed_ms,
            provider=self.provider_name,
            model=self._model,
            error=error,
        )
        self._loop.call_soon_threadsafe(self._event_queue.put_nowait, event)


class GoogleSpeechStreamingSttProvider(StreamingSttProvider):
    provider_name = "GoogleSpeechStreamingSttProvider"

    def __init__(
        self,
        *,
        project_id: str,
        location: str,
        recognizer: str,
        model: str,
        chunk_limit_bytes: int = 24_000,
        stop_wait_seconds: float = 2.0,
    ) -> None:
        self._project_id = project_id
        self._location = location
        self._recognizer = recognizer
        self._model = model
        self._chunk_limit_bytes = chunk_limit_bytes
        self._stop_wait_seconds = stop_wait_seconds

    def create_session(
        self,
        *,
        language: str,
        sample_rate: int,
    ) -> GoogleSpeechStreamingSttSession:
        return GoogleSpeechStreamingSttSession(
            project_id=self._project_id,
            location=self._location,
            recognizer=self._recognizer,
            model=self._model,
            language=language,
            sample_rate=sample_rate,
            chunk_limit_bytes=self._chunk_limit_bytes,
            stop_wait_seconds=self._stop_wait_seconds,
        )


def _normalize_language(language: str | None) -> str:
    normalized = (language or "ko-KR").strip()
    lower = normalized.lower()
    if lower == "ko":
        return "ko-KR"
    if lower == "en":
        return "en-US"
    return normalized
