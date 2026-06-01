from __future__ import annotations

import asyncio
import time

from app.providers.stt.base import StreamingSttEvent, StreamingSttProvider, StreamingSttSession


class AzureSpeechStreamingSttSession(StreamingSttSession):
    provider_name = "AzureSpeechStreamingSttProvider"
    model_name = "azure-speech-streaming"

    def __init__(
        self,
        *,
        speech_key: str,
        speech_region: str,
        language: str = "ko-KR",
        sample_rate: int = 16000,
    ) -> None:
        if not speech_key.strip():
            raise ValueError("speech_key is required")
        if not speech_region.strip():
            raise ValueError("speech_region is required")
        self._speech_key = speech_key
        self._speech_region = speech_region
        self._language = _normalize_language(language)
        self._sample_rate = sample_rate
        self._started_at = 0.0
        self._queue: asyncio.Queue[StreamingSttEvent] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._push_stream = None
        self._recognizer = None

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._started_at = time.perf_counter()
        await asyncio.to_thread(self._start_sync)

    async def write(self, pcm_bytes: bytes) -> None:
        if not pcm_bytes or self._push_stream is None:
            return
        await asyncio.to_thread(self._push_stream.write, pcm_bytes)

    async def stop(self) -> None:
        try:
            if self._push_stream is not None:
                await asyncio.to_thread(self._push_stream.close)
        finally:
            self._push_stream = None
            if self._recognizer is not None:
                await asyncio.to_thread(lambda: self._recognizer.stop_continuous_recognition_async().get())
                self._recognizer = None

    async def next_event(self, timeout_seconds: float = 0.0) -> StreamingSttEvent | None:
        try:
            if timeout_seconds <= 0.0:
                return self._queue.get_nowait()
            return await asyncio.wait_for(self._queue.get(), timeout_seconds)
        except (asyncio.QueueEmpty, asyncio.TimeoutError):
            return None

    def _start_sync(self) -> None:
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError as exc:
            raise RuntimeError("azure-cognitiveservices-speech is not installed") from exc

        speech_config = speechsdk.SpeechConfig(subscription=self._speech_key, region=self._speech_region)
        speech_config.speech_recognition_language = self._language
        stream_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=self._sample_rate,
            bits_per_sample=16,
            channels=1,
        )
        self._push_stream = speechsdk.audio.PushAudioInputStream(stream_format=stream_format)
        audio_config = speechsdk.audio.AudioConfig(stream=self._push_stream)
        self._recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        self._recognizer.recognizing.connect(lambda event: self._emit("partial", event.result.text))
        self._recognizer.recognized.connect(lambda event: self._emit("final", event.result.text))
        self._recognizer.canceled.connect(lambda event: self._emit("error", error=str(event)))
        self._recognizer.session_stopped.connect(lambda event: self._emit("stopped"))
        self._recognizer.start_continuous_recognition_async().get()

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
            model=self.model_name,
            error=error,
        )
        self._loop.call_soon_threadsafe(self._queue.put_nowait, event)


def _normalize_language(language: str | None) -> str:
    normalized = (language or "ko-KR").strip()
    lower = normalized.lower()
    if lower == "ko":
        return "ko-KR"
    if lower == "en":
        return "en-US"
    return normalized


class AzureSpeechStreamingSttProvider(StreamingSttProvider):
    provider_name = "AzureSpeechStreamingSttProvider"

    def __init__(self, *, speech_key: str, speech_region: str) -> None:
        self._speech_key = speech_key
        self._speech_region = speech_region

    def create_session(
        self,
        *,
        language: str,
        sample_rate: int,
    ) -> AzureSpeechStreamingSttSession:
        return AzureSpeechStreamingSttSession(
            speech_key=self._speech_key,
            speech_region=self._speech_region,
            language=language,
            sample_rate=sample_rate,
        )
