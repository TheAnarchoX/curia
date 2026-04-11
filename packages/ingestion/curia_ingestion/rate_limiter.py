"""Token-bucket rate limiter for async crawling."""

from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Async token-bucket rate limiter.

    Parameters
    ----------
    rate:
        Tokens added per second (sustained request rate).
    burst:
        Maximum tokens stored (allows short bursts above *rate*).
    """

    def __init__(self, rate: float = 2.0, burst: int = 5) -> None:
        """Initialize the rate limiter with a sustained rate and burst size."""
        if rate <= 0:
            raise ValueError("rate must be greater than 0")
        if burst <= 0:
            raise ValueError("burst must be greater than 0")
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
        self._last_refill = now

    async def acquire(self) -> None:
        """Wait until a token is available, then consume it."""
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
            # Sleep for the estimated time until the next token arrives.
            await asyncio.sleep(1.0 / self._rate)
