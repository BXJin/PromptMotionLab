import asyncio
from collections import defaultdict


class WebSocketConnectionLimiter:
    def __init__(self, *, max_total: int = 32, max_per_client: int = 2) -> None:
        self._max_total = max(1, max_total)
        self._max_per_client = max(1, max_per_client)
        self._total = 0
        self._by_client: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def try_acquire(self, client_key: str) -> bool:
        async with self._lock:
            if self._total >= self._max_total:
                return False
            if self._by_client[client_key] >= self._max_per_client:
                return False
            self._total += 1
            self._by_client[client_key] += 1
            return True

    async def release(self, client_key: str) -> None:
        async with self._lock:
            current = self._by_client.get(client_key, 0)
            if current <= 1:
                self._by_client.pop(client_key, None)
            else:
                self._by_client[client_key] = current - 1
            self._total = max(0, self._total - 1)

    async def clear(self) -> None:
        async with self._lock:
            self._total = 0
            self._by_client.clear()
