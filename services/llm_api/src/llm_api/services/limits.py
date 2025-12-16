from __future__ import annotations

import asyncio
import time
from collections import deque
from contextlib import asynccontextmanager

from llm_api.services.config import Settings
from llm_api.services.errors import ApiError


class _InMemoryRateLimiter:
    def __init__(self, *, requests_per_minute: int):
        self._requests_per_minute = max(1, requests_per_minute)
        self._window_seconds = 60.0
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.time()
            cutoff = now - self._window_seconds
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            if len(self._timestamps) >= self._requests_per_minute:
                raise ApiError(
                    code="rate_limited",
                    message="Rate limit exceeded",
                    status_code=429,
                    details={"requests_per_minute": self._requests_per_minute},
                )

            self._timestamps.append(now)


class Limits:
    def __init__(self, settings: Settings):
        self._global_sem = asyncio.Semaphore(max(1, settings.max_concurrency))
        self._provider_sem = asyncio.Semaphore(max(1, settings.max_concurrency_per_provider))
        self._rate = _InMemoryRateLimiter(requests_per_minute=settings.requests_per_minute)

    @asynccontextmanager
    async def guard(self):
        await self._rate.acquire()
        async with self._global_sem:
            async with self._provider_sem:
                yield


_limits: Limits | None = None


def get_limits() -> Limits:
    global _limits
    if _limits is None:
        _limits = Limits(Settings())
    return _limits
