from dataclasses import dataclass


@dataclass(frozen=True)
class SttResult:
    text: str
    language: str | None
    duration_ms: int
    provider: str
    model: str


class SttProvider:
    provider_name = "SttProvider"
    model_name = "unknown"

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        content_type: str,
        language: str | None = None,
    ) -> SttResult:
        raise NotImplementedError

