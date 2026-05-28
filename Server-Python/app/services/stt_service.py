import asyncio
import logging
import time

from app.contracts.stt import SttTranscribeResponse
from app.providers.stt import MockSttProvider, SttProvider
from app.services.service_limits import AsyncInFlightLimiter

logger = logging.getLogger(__name__)


class SttService:
    def __init__(
        self,
        *,
        provider: SttProvider | None = None,
        fallback_provider: SttProvider | None = None,
        provider_timeout_seconds: float = 4.0,
        fallback_timeout_seconds: float = 1.0,
        provider_max_concurrency: int = 8,
        max_in_flight: int = 64,
        max_audio_bytes: int = 5 * 1024 * 1024,
    ) -> None:
        self._provider = provider or MockSttProvider()
        self._fallback_provider = fallback_provider or MockSttProvider()
        self._provider_timeout_seconds = provider_timeout_seconds
        self._fallback_timeout_seconds = fallback_timeout_seconds
        self._provider_semaphore = asyncio.Semaphore(max(1, provider_max_concurrency))
        self._in_flight_limiter = AsyncInFlightLimiter(max_in_flight)
        self._max_audio_bytes = max(1024, max_audio_bytes)

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        language: str | None = None,
    ) -> SttTranscribeResponse:
        if not audio_bytes:
            raise ValueError("audio body is empty")
        if len(audio_bytes) > self._max_audio_bytes:
            raise ValueError(f"audio body exceeds {self._max_audio_bytes} bytes")

        async with self._in_flight_limiter.slot():
            return await self._transcribe_unlimited(
                audio_bytes=audio_bytes,
                content_type=content_type,
                language=language,
            )

    async def _transcribe_unlimited(
        self,
        *,
        audio_bytes: bytes,
        content_type: str,
        language: str | None,
    ) -> SttTranscribeResponse:
        started = time.perf_counter()
        provider = self._provider
        try:
            async with self._provider_semaphore:
                result = await asyncio.wait_for(
                    provider.transcribe(
                        audio_bytes=audio_bytes,
                        content_type=content_type,
                        language=language,
                    ),
                    timeout=self._provider_timeout_seconds,
                )
        except Exception as exc:
            logger.warning("[STT] primary provider failed (%s: %s), falling back to mock", type(exc).__name__, exc)
            provider = self._fallback_provider
            result = await asyncio.wait_for(
                provider.transcribe(
                    audio_bytes=audio_bytes,
                    content_type=content_type,
                    language=language,
                ),
                timeout=self._fallback_timeout_seconds,
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        return SttTranscribeResponse(
            text=result.text,
            language=result.language,
            durationMs=result.duration_ms,
            provider=result.provider,
            model=result.model,
            sttLatencyMs=latency_ms,
        )

