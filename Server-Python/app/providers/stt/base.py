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


@dataclass(frozen=True)
class StreamingSttEvent:
    type: str
    text: str = ""
    language: str | None = None
    duration_ms: int = 0
    provider: str = "StreamingSttProvider"
    model: str = "unknown"
    error: str = ""


class StreamingSttSession:
    provider_name = "StreamingSttProvider"
    model_name = "unknown"

    async def start(self) -> None:
        raise NotImplementedError

    async def write(self, pcm_bytes: bytes) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

    async def next_event(self, timeout_seconds: float = 0.0) -> StreamingSttEvent | None:
        raise NotImplementedError


class StreamingSttProvider:
    provider_name = "StreamingSttProvider"

    def create_session(
        self,
        *,
        language: str,
        sample_rate: int,
    ) -> StreamingSttSession:
        raise NotImplementedError
