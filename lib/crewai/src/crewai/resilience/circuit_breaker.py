"""
Circuit Breaker pattern implementation for CrewAI.

Prevents cascading failures by monitoring service health and
automatically opening the circuit when failure threshold is reached.

Usage:
    >>> from crewai.resilience import CircuitBreaker
    >>> breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
    >>> result = breaker.call(external_api_function, arg1, arg2)
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any
from typing import Callable

from crewai.exceptions import CrewAIException


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, circuit is open
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerOpen(CrewAIException):
    """Raised when circuit breaker is open and calls are rejected."""

    def __init__(self, message: str = "Circuit breaker is OPEN", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code="CIRCUIT_BREAKER_OPEN",
            **kwargs,
        )


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation.

    Monitors failures and automatically opens circuit to prevent
    cascading failures. After recovery timeout, allows test requests.

    States:
        - CLOSED: Normal operation, all requests allowed
        - OPEN: Too many failures, requests rejected immediately
        - HALF_OPEN: Testing if service recovered, limited requests allowed

    Attributes:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type that counts as failure
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
        success_threshold: int = 2,
        name: str = "default",
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers circuit
            success_threshold: Successes needed in HALF_OPEN to close
            name: Circuit breaker name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        self.name = name

        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._state = CircuitState.CLOSED

        logger.info(
            f"CircuitBreaker '{name}' initialized: "
            f"failure_threshold={failure_threshold}, "
            f"recovery_timeout={recovery_timeout}s"
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: When circuit is open
            Exception: Original exception if circuit is closed

        Example:
            >>> breaker = CircuitBreaker()
            >>> result = breaker.call(api.get_data, user_id=123)
        """
        # Check if circuit should transition to HALF_OPEN
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(f"CircuitBreaker '{self.name}' transitioned to HALF_OPEN")
            else:
                raise CircuitBreakerOpen(
                    context={
                        "circuit_name": self.name,
                        "failure_count": self._failure_count,
                        "time_until_retry": self._time_until_retry(),
                    }
                )

        # Try to execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return True
        return time.time() - self._last_failure_time >= self.recovery_timeout

    def _time_until_retry(self) -> float:
        """Calculate seconds until circuit can be retried."""
        if self._last_failure_time is None:
            return 0.0
        elapsed = time.time() - self._last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)

    def _on_success(self) -> None:
        """Handle successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            logger.debug(
                f"CircuitBreaker '{self.name}' success in HALF_OPEN "
                f"({self._success_count}/{self.success_threshold})"
            )

            if self._success_count >= self.success_threshold:
                self._reset()
                logger.info(f"CircuitBreaker '{self.name}' closed after successful recovery")
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success in CLOSED state
            self._failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        logger.warning(
            f"CircuitBreaker '{self.name}' failure "
            f"({self._failure_count}/{self.failure_threshold})"
        )

        if self._state == CircuitState.HALF_OPEN:
            # Single failure in HALF_OPEN opens circuit again
            self._state = CircuitState.OPEN
            logger.warning(f"CircuitBreaker '{self.name}' opened (failure in HALF_OPEN)")
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.error(
                f"CircuitBreaker '{self.name}' opened "
                f"(threshold {self.failure_threshold} reached)"
            )

    def _reset(self) -> None:
        """Reset circuit breaker to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None

    def reset(self) -> None:
        """Manually reset circuit breaker (use with caution)."""
        logger.info(f"CircuitBreaker '{self.name}' manually reset")
        self._reset()

    def get_status(self) -> dict[str, Any]:
        """
        Get circuit breaker status.

        Returns:
            Dict with current state, failure count, etc.
        """
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "success_count": self._success_count,
            "time_until_retry": self._time_until_retry() if self._state == CircuitState.OPEN else 0,
        }
