#!/usr/bin/env python3
"""Shared pipeline utilities — retry logic, logging setup, and common helpers."""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] | None = None,
) -> Callable[[F], F]:
    """Decorator: retry a function on failure with exponential backoff.

    Args:
        max_attempts: Maximum retry attempts (including first try).
        delay: Initial delay in seconds before first retry.
        backoff: Multiplier for delay after each retry.
        exceptions: Tuple of exception types to catch. Defaults to all exceptions.

    Usage:
        @retry(max_attempts=3, delay=1.0)
        def fetch_data(url: str) -> dict: ...
    """
    if exceptions is None:
        exceptions = (Exception,)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            wait = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt < max_attempts:
                        logging.getLogger(func.__module__).warning(
                            "%s attempt %d/%d failed: %s. Retrying in %.1fs...",
                            func.__name__, attempt, max_attempts, e, wait,
                        )
                        time.sleep(wait)
                        wait *= backoff
                    else:
                        logging.getLogger(func.__module__).error(
                            "%s failed after %d attempts: %s",
                            func.__name__, max_attempts, e,
                        )
                        raise
            raise  # pragma: no cover
        return wrapper  # type: ignore
    return decorator