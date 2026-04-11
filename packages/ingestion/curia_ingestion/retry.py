"""Retry policy and helper for transient HTTP errors."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_DEFAULT_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class RetryPolicy:
    """Configuration for retry behaviour."""

    max_retries: int = 3
    backoff_factor: float = 0.5
    retryable_status_codes: frozenset[int] = field(default_factory=lambda: _DEFAULT_RETRYABLE_STATUS_CODES)

    def __post_init__(self) -> None:
        """Validate retry policy values."""
        if self.max_retries < 1:
            raise ValueError("max_retries must be at least 1")
        if self.backoff_factor < 0:
            raise ValueError("backoff_factor must be non-negative")


class RetryableError(Exception):
    """Raised when a retryable failure occurs (e.g. transient HTTP status)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize with an error message and optional HTTP status code."""
        super().__init__(message)
        self.status_code = status_code


async def retry_with_policy(
    func: Callable[..., Awaitable[T]],
    policy: RetryPolicy,
    *args: Any,
    **kwargs: Any,
) -> T:
    """Call *func* with retries governed by *policy*.

    Raises the last exception if all attempts fail.
    """
    last_exc: Exception | None = None
    for attempt in range(1, policy.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except RetryableError as exc:
            last_exc = exc
            delay = policy.backoff_factor * (2 ** (attempt - 1))
            logger.warning(
                "Attempt %d/%d failed (status=%s). Retrying in %.1fs …",
                attempt,
                policy.max_retries,
                exc.status_code,
                delay,
            )
            await asyncio.sleep(delay)
        except Exception:
            raise  # non-retryable → propagate immediately
    if last_exc is None:
        raise RuntimeError("retry_with_policy exhausted without capturing an exception")
    raise last_exc
