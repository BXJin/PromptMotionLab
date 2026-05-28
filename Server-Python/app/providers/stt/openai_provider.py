import httpx

from app.providers.stt.base import SttProvider, SttResult


class OpenAiSttProvider(SttProvider):
    provider_name = "OpenAiSttProvider"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini-transcribe",
        endpoint: str = "https://api.openai.com/v1/audio/transcriptions",
        timeout_seconds: float = 4.0,
    ) -> None:
        self._api_key = api_key
        self.model_name = model
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        content_type: str,
        language: str | None = None,
    ) -> SttResult:
        data: dict[str, str] = {
            "model": self.model_name,
            "response_format": "json",
        }
        if language:
            data["language"] = language

        files = {
            "file": ("speech.wav", audio_bytes, content_type or "audio/wav"),
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(self._endpoint, headers=headers, data=data, files=files)
            response.raise_for_status()
            payload = response.json()

        text = str(payload.get("text") or "").strip()
        detected_language = payload.get("language")
        return SttResult(
            text=text,
            language=str(detected_language) if detected_language else language,
            duration_ms=0,
            provider=self.provider_name,
            model=self.model_name,
        )

