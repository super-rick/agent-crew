"""
Exponential backoff retry utilities.

Used by BaseAgent and PlatformAdapter layers to automatically
retry transient failures with increasing delays.
"""

from __future__ import annotations

import random
import time
from functools import wraps
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 1.0  # seconds
DEFAULT_BACKOFF_FACTOR = 2.0  # exponential multiplier
DEFAULT_JITTER = True  # add random jitter to avoid thundering herd
MAX_BACKOFF = 60.0  # cap at 60 seconds


def retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    jitter: bool = DEFAULT_JITTER,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """Decorator: retry a function with exponential backoff.

    Delay formula: backoff_base * (backoff_factor ** attempt) + jitter
    Attempt 0: no delay (first try)
    Attempt 1: ~1-2s
    Attempt 2: ~2-4s
    Attempt 3: ~4-8s (capped at MAX_BACKOFF)

    Args:
        max_retries: Maximum number of retry attempts after initial failure.
        backoff_base: Base delay in seconds.
        backoff_factor: Exponential multiplier.
        jitter: Add random jitter (±25%) to avoid thundering herd.
        retryable_exceptions: Exception types that trigger a retry.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    # If result has retry_count, set it
                    _set_retry_count(result, attempt)
                    return result
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt >= max_retries:
                        break
                    delay = _compute_delay(attempt, backoff_base, backoff_factor, jitter)
                    time.sleep(delay)

            # All retries exhausted
            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


def retry_callable(
    fn: Callable[[], Any],
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    jitter: bool = DEFAULT_JITTER,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
) -> tuple[Any, int]:
    """Call a function with exponential backoff retry.

    Returns (result, attempt_number).
    Raises the last exception if all retries are exhausted.
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            result = fn()
            _set_retry_count(result, attempt)
            return result, attempt
        except retryable_exceptions as e:
            last_exception = e
            if attempt >= max_retries:
                break
            if on_retry:
                on_retry(attempt + 1, e)
            delay = _compute_delay(attempt, backoff_base, backoff_factor, jitter)
            time.sleep(delay)

    raise last_exception  # type: ignore[misc]


def _compute_delay(attempt: int, base: float, factor: float, jitter: bool) -> float:
    """Compute backoff delay: base * (factor ** attempt) + optional jitter."""
    delay = base * (factor**attempt)
    delay = min(delay, MAX_BACKOFF)
    if jitter:
        delay *= 1.0 + random.uniform(-0.25, 0.25)
    return max(0, delay)


def _set_retry_count(result: Any, attempt: int) -> None:
    """Set retry_count on a result object if it supports it."""
    if hasattr(result, "retry_count"):
        result.retry_count = attempt
