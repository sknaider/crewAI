"""
Retry policies with exponential backoff for CrewAI.

Provides intelligent retry mechanisms with backoff strategies
for handling transient failures.

Usage:
    >>> from crewai.resilience import retry_with_backoff
    >>> @retry_with_backoff(max_attempts=3, base_delay=1.0)
    >>> def unstable_api_call():
    ...     return api.get_data()
"""

from __future__ import annotations

import logging
import random
import time
from functools import wraps
from typing import Any
from typing import Callable
from typing import TypeVar


logger = logging.getLogger(__name__)

T = TypeVar("T")


def exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> float:
    """
    Calculate exponential backoff delay.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap
        exponential_base: Exponential base (default: 2.0)
        jitter: Add random jitter to prevent thundering herd

    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (exponential_base**attempt), max_delay)

    if jitter:
        # Add up to 25% jitter
        delay = delay * (0.75 + random.random() * 0.5)

    return delay


class RetryPolicy:
    """
    Configurable retry policy.

    Attributes:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter
        retryable_exceptions: Tuple of exceptions to retry on
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        """
        Initialize retry policy.

        Args:
            max_attempts: Maximum retry attempts (default: 3)
            base_delay: Initial delay in seconds (default: 1.0)
            max_delay: Maximum delay cap (default: 60.0)
            exponential_base: Exponential base (default: 2.0)
            jitter: Add random jitter (default: True)
            retryable_exceptions: Exceptions to retry (default: all)
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute function with retry policy.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: Last exception if all retries exhausted
        """
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)

            except self.retryable_exceptions as e:
                last_exception = e

                if attempt < self.max_attempts - 1:
                    delay = exponential_backoff(
                        attempt=attempt,
                        base_delay=self.base_delay,
                        max_delay=self.max_delay,
                        exponential_base=self.exponential_base,
                        jitter=self.jitter,
                    )

                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_attempts} attempts failed. Last error: {e}"
                    )

        # All retries exhausted
        if last_exception:
            raise last_exception

        # Should never reach here
        msg = "Unexpected state in retry policy"
        raise RuntimeError(msg)


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap
        exponential_base: Exponential base
        jitter: Add random jitter
        retryable_exceptions: Exceptions to retry on

    Returns:
        Decorated function

    Example:
        >>> @retry_with_backoff(max_attempts=3, base_delay=1.0)
        >>> def fetch_data():
        >>>     return api.get("/data")

        >>> # With custom exceptions
        >>> @retry_with_backoff(
        ...     max_attempts=5,
        ...     retryable_exceptions=(ConnectionError, TimeoutError)
        ... )
        >>> def connect_database():
        >>>     return db.connect()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            policy = RetryPolicy(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions,
            )
            return policy.execute(func, *args, **kwargs)

        return wrapper

    return decorator
