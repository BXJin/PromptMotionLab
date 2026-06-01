from __future__ import annotations

import asyncio
import base64
import json
import struct
import time

from app.providers.stt.base import StreamingSttEvent, StreamingSttProvider, StreamingSttSession


class OpenAiRealtimeStreamingSttSession(StreamingSttSession):
    provider_name = "OpenAiRealtimeStreamingSttProvider"

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str,
        model: str,
        language: str,
        sample_rate: int,
        delay: str,
        final_wait_seconds: float = 2.0,
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key is required")
        self._api_key = api_key
        self._endpoint = endpoint
        self._model = model
        self._language = _normalize_language(language)
        self._input_sample_rate = sample_rate
        self._api_sample_rate = 24000
        self._delay = delay
        self._final_wait_seconds = final_wait_seconds
        self._started_at = 0.0
        self._queue: asyncio.Queue[StreamingSttEvent] = asyncio.Queue()
        self._final_seen: asyncio.Event | None = None
        self._ws = None
        self._reader_task: asyncio.Task | None = None
        self._has_audio = False

    @property
    def model_name(self) -> str:
        return self._model

    async def start(self) -> None:
        try:
            import websockets
        except ImportError as exc:
            raise RuntimeError("websockets is not installed") from exc

        self._started_at = time.perf_counter()
        headers = {
            "Authorization": f"Bearer {self._api_key}",
        }
        self._final_seen = asyncio.Event()
        self._ws = await websockets.connect(self._endpoint, additional_headers=headers)
        await self._send_session_update()
        self._reader_task = asyncio.create_task(self._read_events())

    async def write(self, pcm_bytes: bytes) -> None:
        if not pcm_bytes or self._ws is None:
            return
        pcm_bytes = _resample_pcm16_mono(pcm_bytes, self._input_sample_rate, self._api_sample_rate)
        payload = {
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(pcm_bytes).decode("ascii"),
        }
        await self._ws.send(json.dumps(payload))
        self._has_audio = True

    async def stop(self) -> None:
        if self._ws is not None:
            if self._has_audio:
                await self._ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                await self._wait_for_final()
            await self._ws.close()
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

    async def next_event(self, timeout_seconds: float = 0.0) -> StreamingSttEvent | None:
        try:
            if timeout_seconds <= 0.0:
                return self._queue.get_nowait()
            return await asyncio.wait_for(self._queue.get(), timeout_seconds)
        except (asyncio.QueueEmpty, asyncio.TimeoutError):
            return None

    async def _send_session_update(self) -> None:
        if self._ws is None:
            return
        payload = {
            "type": "session.update",
            "session": {
                "type": "transcription",
                "audio": {
                    "input": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": self._api_sample_rate,
                        },
                        "transcription": {
                            "model": self._model,
                            "language": self._language,
                            "prompt": "",
                        },
                        "turn_detection": None,
                        "noise_reduction": {
                            "type": "near_field",
                        },
                    }
                }
            },
        }
        await self._ws.send(json.dumps(payload))

    async def _read_events(self) -> None:
        if self._ws is None:
            return
        try:
            async for message in self._ws:
                payload = json.loads(message)
                event_type = str(payload.get("type") or "")
                if event_type in {"conversation.item.input_audio_transcription.delta", "transcript.text.delta"}:
                    self._emit("partial", text=str(payload.get("delta") or ""))
                elif event_type in {"conversation.item.input_audio_transcription.completed", "transcript.text.done"}:
                    self._emit("final", text=str(payload.get("transcript") or payload.get("text") or ""))
                elif event_type == "error":
                    self._emit("error", error=json.dumps(payload.get("error") or payload, ensure_ascii=False))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._emit("error", error=str(exc))

    async def _wait_for_final(self) -> None:
        if self._final_seen is None:
            return
        try:
            await asyncio.wait_for(self._final_seen.wait(), timeout=self._final_wait_seconds)
        except asyncio.TimeoutError:
            return

    def _emit(self, event_type: str, text: str = "", error: str = "") -> None:
        elapsed_ms = int((time.perf_counter() - self._started_at) * 1000) if self._started_at else 0
        if event_type in {"final", "error"} and self._final_seen is not None:
            self._final_seen.set()
        self._queue.put_nowait(
            StreamingSttEvent(
                type=event_type,
                text=(text or "").strip(),
                language=self._language,
                duration_ms=elapsed_ms,
                provider=self.provider_name,
                model=self._model,
                error=error,
            )
        )


class OpenAiRealtimeStreamingSttProvider(StreamingSttProvider):
    provider_name = "OpenAiRealtimeStreamingSttProvider"

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str,
        model: str,
        delay: str,
        final_wait_seconds: float = 2.0,
    ) -> None:
        self._api_key = api_key
        self._endpoint = endpoint
        self._model = model
        self._delay = delay
        self._final_wait_seconds = final_wait_seconds

    def create_session(
        self,
        *,
        language: str,
        sample_rate: int,
    ) -> OpenAiRealtimeStreamingSttSession:
        return OpenAiRealtimeStreamingSttSession(
            api_key=self._api_key,
            endpoint=self._endpoint,
            model=self._model,
            language=language,
            sample_rate=sample_rate,
            delay=self._delay,
            final_wait_seconds=self._final_wait_seconds,
        )


def _normalize_language(language: str | None) -> str:
    normalized = (language or "ko-KR").strip()
    lower = normalized.lower()
    if lower == "ko-kr":
        return "ko"
    if lower == "en-us":
        return "en"
    return lower if "-" not in lower else normalized


def _resample_pcm16_mono(pcm_bytes: bytes, source_rate: int, target_rate: int) -> bytes:
    if source_rate == target_rate:
        return pcm_bytes
    frame_count = len(pcm_bytes) // 2
    if frame_count <= 1:
        return pcm_bytes
    samples = struct.unpack(f"<{frame_count}h", pcm_bytes[: frame_count * 2])
    target_count = max(1, int(round(frame_count * target_rate / source_rate)))
    if target_count == frame_count:
        return pcm_bytes[: frame_count * 2]

    result = []
    scale = (frame_count - 1) / max(1, target_count - 1)
    for index in range(target_count):
        position = index * scale
        left = int(position)
        right = min(left + 1, frame_count - 1)
        fraction = position - left
        value = int(samples[left] + (samples[right] - samples[left]) * fraction)
        result.append(max(-32768, min(32767, value)))
    return struct.pack(f"<{len(result)}h", *result)
