import asyncio
import wave
from pathlib import Path

from app.contracts.runtime_behavior import RuntimeTtsStyle
from app.providers.tts.base import TtsProvider, TtsResult


class MockTtsProvider(TtsProvider):
    provider_name = "MockTtsProvider"
    model_name = "silent-wav"

    async def synthesize(
        self,
        *,
        text: str,
        output_path: Path,
        tts_style: RuntimeTtsStyle,
        voice: str | None = None,
    ) -> TtsResult:
        del tts_style, voice
        duration_seconds = max(0.4, min(4.0, len(text) / 18.0))
        await asyncio.to_thread(self._write_silence, output_path, duration_seconds)
        return TtsResult(
            audio_path=output_path,
            duration_seconds=duration_seconds,
            visemes=[],
            provider=self.provider_name,
            model=self.model_name,
        )

    def _write_silence(self, output_path: Path, duration_seconds: float) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sample_rate = 16_000
        frame_count = int(sample_rate * duration_seconds)
        with wave.open(str(output_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b"\x00\x00" * frame_count)
