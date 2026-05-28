from app.providers.stt.base import SttProvider, SttResult


class MockSttProvider(SttProvider):
    provider_name = "MockSttProvider"
    model_name = "mock"

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        content_type: str,
        language: str | None = None,
    ) -> SttResult:
        del content_type
        text = "안녕, 오늘 날씨 좋네."
        if len(audio_bytes) == 0:
            text = ""
        return SttResult(
            text=text,
            language=language,
            duration_ms=0,
            provider=self.provider_name,
            model=self.model_name,
        )

