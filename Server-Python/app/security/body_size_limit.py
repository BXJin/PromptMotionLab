from collections.abc import Awaitable, Callable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodyTooLargeError(RuntimeError):
    pass


class BodySizeLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        limits: dict[str, int] | None = None,
    ) -> None:
        self._app = app
        self._limits = limits or {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = str(scope.get("path") or "")
        limit = self._limit_for_path(path)
        if limit is None:
            await self._app(scope, receive, send)
            return

        limited_receive = _LimitedReceive(receive, limit)
        try:
            await self._app(scope, limited_receive, send)
        except BodyTooLargeError:
            response = JSONResponse({"detail": "Request body too large"}, status_code=413)
            await response(scope, receive, send)

    def _limit_for_path(self, path: str) -> int | None:
        for prefix, limit in self._limits.items():
            if path.startswith(prefix):
                return limit
        return None


class _LimitedReceive:
    def __init__(self, receive: Callable[[], Awaitable[Message]], limit: int) -> None:
        self._receive = receive
        self._limit = max(0, limit)
        self._received = 0

    async def __call__(self) -> Message:
        message = await self._receive()
        if message["type"] != "http.request":
            return message

        body = message.get("body", b"")
        self._received += len(body)
        if self._received > self._limit:
            raise BodyTooLargeError
        return message
