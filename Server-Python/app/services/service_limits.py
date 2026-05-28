import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator


class ServiceBusyError(RuntimeError):
    pass


class AsyncInFlightLimiter:
    def __init__(self, limit: int) -> None:
        self._limit = max(0, limit)
        self._active = 0
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        if self._limit <= 0:
            yield
            return

        async with self._lock:
            if self._active >= self._limit:
                raise ServiceBusyError(f"max in-flight exceeded: {self._limit}")
            self._active += 1

        try:
            yield
        finally:
            async with self._lock:
                self._active = max(0, self._active - 1)
