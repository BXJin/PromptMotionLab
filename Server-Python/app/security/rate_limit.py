import asyncio
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.security.client_identity import client_key_from_headers


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: str, *, limit: int, window_seconds: float, now: float | None = None) -> tuple[bool, int]:
        if limit <= 0:
            return False, 1
        now = time.monotonic() if now is None else now
        cutoff = now - window_seconds
        async with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(events[0] + window_seconds - now))
                return False, retry_after
            events.append(now)
            return True, 0

    async def clear(self) -> None:
        async with self._lock:
            self._events.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        limiter: SlidingWindowRateLimiter | None = None,
        enabled: bool = True,
        runtime_limit: int = 60,
        runtime_job_poll_limit: int = 600,
        runtime_stt_limit: int = 60,
        runtime_tts_limit: int = 120,
        audio_limit: int = 180,
        window_seconds: float = 60.0,
    ) -> None:
        super().__init__(app)
        self._limiter = limiter or SlidingWindowRateLimiter()
        self._enabled = enabled
        self._runtime_limit = runtime_limit
        self._runtime_job_poll_limit = runtime_job_poll_limit
        self._runtime_stt_limit = runtime_stt_limit
        self._runtime_tts_limit = runtime_tts_limit
        self._audio_limit = audio_limit
        self._window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if not self._enabled:
            return await call_next(request)

        limit = self._limit_for_path(request.url.path)
        if limit is None:
            return await call_next(request)

        client_key = client_key_from_headers(request.headers, request.client.host if request.client else None)
        bucket_key = f"{client_key}:{request.method}:{self._bucket_for_path(request.url.path)}"
        allowed, retry_after = await self._limiter.allow(
            bucket_key,
            limit=limit,
            window_seconds=self._window_seconds,
        )
        if allowed:
            return await call_next(request)

        return JSONResponse(
            {"detail": "rate limit exceeded"},
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )

    def _limit_for_path(self, path: str) -> int | None:
        if path.startswith("/api/runtime/audio/"):
            return self._audio_limit
        if self._is_runtime_job_poll_path(path):
            return self._runtime_job_poll_limit
        if path.startswith("/api/runtime/stt/"):
            return self._runtime_stt_limit
        if path.startswith("/api/runtime/tts/"):
            return self._runtime_tts_limit
        if path.startswith("/api/runtime/"):
            return self._runtime_limit
        return None

    def _bucket_for_path(self, path: str) -> str:
        if path.startswith("/api/runtime/audio/"):
            return "runtime_audio"
        if self._is_runtime_job_poll_path(path):
            return "runtime_job_poll"
        if path.startswith("/api/runtime/stt/"):
            return "runtime_stt"
        if path.startswith("/api/runtime/tts/"):
            return "runtime_tts"
        if path.startswith("/api/runtime/turn/"):
            return "runtime_turn"
        return "runtime"

    @staticmethod
    def _is_runtime_job_poll_path(path: str) -> bool:
        return (
            path.startswith("/api/runtime/turn/jobs/")
            or path.startswith("/api/runtime/respond/jobs/")
            or path.startswith("/api/runtime/tts/jobs/")
        )
