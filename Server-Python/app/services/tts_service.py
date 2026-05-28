import time
import uuid
import asyncio
import logging
from pathlib import Path

from app.contracts.runtime_behavior import RuntimeTtsStyle
from app.contracts.speech_timeline import SpeechAudio, SpeechTimeline
from app.providers.tts import MockTtsProvider, TtsProvider
from app.services.service_limits import AsyncInFlightLimiter

logger = logging.getLogger(__name__)


class TtsService:
    def __init__(
        self,
        *,
        provider: TtsProvider | None = None,
        fallback_provider: TtsProvider | None = None,
        audio_root: Path | None = None,
        provider_timeout_seconds: float = 4.0,
        fallback_timeout_seconds: float = 1.0,
        provider_max_concurrency: int = 8,
        max_in_flight: int = 64,
    ) -> None:
        self._provider = provider or MockTtsProvider()
        self._fallback_provider = fallback_provider or MockTtsProvider()
        self._audio_root = audio_root or Path(__file__).resolve().parent.parent / "data" / "runtime_audio"
        self._provider_timeout_seconds = provider_timeout_seconds
        self._fallback_timeout_seconds = fallback_timeout_seconds
        self._provider_semaphore = asyncio.Semaphore(max(1, provider_max_concurrency))
        self._in_flight_limiter = AsyncInFlightLimiter(max_in_flight)
        self._audio_root.mkdir(parents=True, exist_ok=True)

    async def synthesize(
        self,
        *,
        text: str,
        tts_style: RuntimeTtsStyle = RuntimeTtsStyle.WARM,
        voice: str | None = None,
    ) -> SpeechTimeline:
        async with self._in_flight_limiter.slot():
            return await self._synthesize_unlimited(text=text, tts_style=tts_style, voice=voice)

    async def _synthesize_unlimited(
        self,
        *,
        text: str,
        tts_style: RuntimeTtsStyle,
        voice: str | None,
    ) -> SpeechTimeline:
        utterance_id = f"utt_{uuid.uuid4().hex[:12]}"
        output_path = self._audio_root / f"{utterance_id}.wav"
        started = time.perf_counter()
        provider = self._provider

        try:
            async with self._provider_semaphore:
                result = await asyncio.wait_for(
                    provider.synthesize(
                        text=text,
                        output_path=output_path,
                        tts_style=tts_style,
                        voice=voice,
                    ),
                    timeout=self._provider_timeout_seconds,
                )
        except Exception:
            provider = self._fallback_provider
            result = await asyncio.wait_for(
                provider.synthesize(
                    text=text,
                    output_path=output_path,
                    tts_style=tts_style,
                    voice=voice,
                ),
                timeout=self._fallback_timeout_seconds,
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        return SpeechTimeline(
            utteranceId=utterance_id,
            audio=SpeechAudio(
                url=f"/api/runtime/audio/{utterance_id}.wav",
                durationSeconds=result.duration_seconds,
                format="wav",
            ),
            visemes=result.visemes,
            provider=result.provider,
            model=result.model,
            ttsLatencyMs=latency_ms,
        )

    def resolve_audio_path(self, filename: str) -> Path | None:
        if not filename.endswith(".wav"):
            return None

        candidate = (self._audio_root / filename).resolve()
        root = self._audio_root.resolve()
        if root not in candidate.parents:
            return None
        if not candidate.exists():
            return None
        return candidate

    async def cleanup_audio_files(self, *, ttl_seconds: float = 600.0, max_files: int = 512) -> int:
        return await asyncio.to_thread(self._cleanup_audio_files_sync, ttl_seconds, max_files)

    def _cleanup_audio_files_sync(self, ttl_seconds: float, max_files: int) -> int:
        now = time.time()
        deleted = 0
        wav_files = sorted(
            self._audio_root.glob("*.wav"),
            key=lambda path: path.stat().st_mtime if path.exists() else 0.0,
        )

        for path in wav_files:
            try:
                age_seconds = now - path.stat().st_mtime
                if age_seconds > ttl_seconds:
                    path.unlink()
                    deleted += 1
            except OSError as exc:
                logger.warning("Failed to delete expired TTS audio. path=%s error=%s", path, exc)

        remaining = sorted(
            self._audio_root.glob("*.wav"),
            key=lambda path: path.stat().st_mtime if path.exists() else 0.0,
        )
        overflow = max(0, len(remaining) - max_files)
        for path in remaining[:overflow]:
            try:
                path.unlink()
                deleted += 1
            except OSError as exc:
                logger.warning("Failed to delete overflow TTS audio. path=%s error=%s", path, exc)

        if deleted:
            logger.info("TTS audio cleanup deleted %d wav file(s).", deleted)
        return deleted
