from dataclasses import dataclass
from pathlib import Path

from app.contracts.runtime_behavior import RuntimeTtsStyle
from app.contracts.speech_timeline import SpeechViseme


@dataclass(frozen=True)
class TtsResult:
    audio_path: Path
    duration_seconds: float
    visemes: list[SpeechViseme]
    provider: str
    model: str


class TtsProvider:
    provider_name = "TtsProvider"
    model_name = "unknown"

    async def synthesize(
        self,
        *,
        text: str,
        output_path: Path,
        tts_style: RuntimeTtsStyle,
        voice: str | None = None,
    ) -> TtsResult:
        raise NotImplementedError
