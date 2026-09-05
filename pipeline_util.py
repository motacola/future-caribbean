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

# ── Output redirection ─────────────────────────────────────
# Packagers write artefacts the live site serves. A test run must never change
# what the site publishes, but several writers run in subprocesses where
# monkeypatching cannot reach them. So every writer resolves its destination
# through `output_path()`, and the test harness points that at a temp dir via
# ABENG_OUTPUT_ROOT. Inputs are unaffected — only writes are redirected.

OUTPUT_ROOT_ENV = "ABENG_OUTPUT_ROOT"


def output_path(default: "Path") -> "Path":
    """Where an artefact should actually be written.

    Returns `default` unless ABENG_OUTPUT_ROOT is set, in which case
    the path is remapped under that root, preserving its position relative to
    the repository so callers keep their directory layout.
    """
    import os
    from pathlib import Path as _Path

    root = os.environ.get(OUTPUT_ROOT_ENV)
    if not root:
        return default

    repo = _Path(__file__).resolve().parent
    default = _Path(default)
    try:
        relative = default.resolve().relative_to(repo)
    except ValueError:
        # Outside the repo — leave it alone rather than guess.
        return default

    destination = _Path(root) / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination
