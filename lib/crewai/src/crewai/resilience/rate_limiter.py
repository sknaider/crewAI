"""
Rate Limiting implementation for CrewAI.

Provides distributed rate limiting using token bucket algorithm
with optional Redis backend for multi-process/multi-server scenarios.

Usage:
    >>> from crewai.resilience import RateLimiter
    >>> limiter = RateLimiter(max_requests=100, window_seconds=60)
    >>> if limiter.allow("user_123"):
    ...     # Process request
    ...     pass
    >>> else:
    ...     # Reject request
    ...     raise RateLimitExceeded()
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any

from crewai.exceptions import CrewAIException


logger = logging.getLogger(__name__)


class RateLimitExceeded(CrewAIException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if retry_after:
            context["retry_after_seconds"] = retry_after
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            context=context,
            **kwargs,
        )


class RateLimiter:
    """
    Token bucket rate limiter with sliding window.

    Supports both in-memory and Redis-based distributed rate limiting.

    Attributes:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        redis_client: Optional Redis client for distributed limiting
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        redis_client: Any = None,
        key_prefix: str = "crewai:ratelimit:",
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            redis_client: Optional Redis client (redis.Redis instance)
            key_prefix: Redis key prefix (default: "crewai:ratelimit:")
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis_client = redis_client
        self.key_prefix = key_prefix

        # In-memory storage (used when Redis not available)
        self._requests: dict[str, deque[float]] = {}

        logger.info(
            f"RateLimiter initialized: {max_requests} requests per {window_seconds}s "
            f"(backend: {'redis' if redis_client else 'memory'})"
        )

    def allow(self, key: str) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Identifier for rate limiting (e.g., user_id, api_key)

        Returns:
            True if request is allowed, False if rate limit exceeded

        Example:
            >>> limiter = RateLimiter(max_requests=100, window_seconds=60)
            >>> if limiter.allow("user_123"):
            ...     process_request()
            >>> else:
            ...     raise RateLimitExceeded()
        """
        if self.redis_client:
            return self._allow_redis(key)
        return self._allow_memory(key)

    def _allow_memory(self, key: str) -> bool:
        """Check rate limit using in-memory storage."""
        now = time.time()
        window_start = now - self.window_seconds

        # Initialize deque for this key if needed
        if key not in self._requests:
            self._requests[key] = deque()

        requests = self._requests[key]

        # Remove old requests outside window
        while requests and requests[0] < window_start:
            requests.popleft()

        # Check if we're within limit
        if len(requests) < self.max_requests:
            requests.append(now)
            return True

        return False

    def _allow_redis(self, key: str) -> bool:
        """Check rate limit using Redis."""
        try:
            redis_key = f"{self.key_prefix}{key}"
            now = time.time()
            window_start = now - self.window_seconds

            # Use Redis sorted set for sliding window
            # Score is timestamp, member is unique request ID
            pipe = self.redis_client.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(redis_key, 0, window_start)

            # Count current requests in window
            pipe.zcard(redis_key)

            # Execute pipeline
            results = pipe.execute()
            current_count = results[1]

            # Check if within limit
            if current_count < self.max_requests:
                # Add new request
                request_id = f"{now}:{id(self)}"
                self.redis_client.zadd(redis_key, {request_id: now})

                # Set expiry on key
                self.redis_client.expire(redis_key, self.window_seconds)

                return True

            return False

        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}, falling back to allow")
            # Fail open - allow request if Redis fails
            return True

    def get_remaining(self, key: str) -> int:
        """
        Get remaining requests allowed in current window.

        Args:
            key: Identifier to check

        Returns:
            Number of remaining requests allowed
        """
        if self.redis_client:
            return self._get_remaining_redis(key)
        return self._get_remaining_memory(key)

    def _get_remaining_memory(self, key: str) -> int:
        """Get remaining requests using in-memory storage."""
        now = time.time()
        window_start = now - self.window_seconds

        if key not in self._requests:
            return self.max_requests

        requests = self._requests[key]

        # Remove old requests
        while requests and requests[0] < window_start:
            requests.popleft()

        return max(0, self.max_requests - len(requests))

    def _get_remaining_redis(self, key: str) -> int:
        """Get remaining requests using Redis."""
        try:
            redis_key = f"{self.key_prefix}{key}"
            now = time.time()
            window_start = now - self.window_seconds

            # Remove old entries and count current
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zcard(redis_key)
            results = pipe.execute()

            current_count = results[1]
            return max(0, self.max_requests - current_count)

        except Exception as e:
            logger.error(f"Redis error getting remaining: {e}")
            return self.max_requests  # Fail open

    def reset(self, key: str) -> None:
        """
        Reset rate limit for a specific key.

        Args:
            key: Identifier to reset
        """
        if self.redis_client:
            redis_key = f"{self.key_prefix}{key}"
            self.redis_client.delete(redis_key)
        else:
            self._requests.pop(key, None)

        logger.info(f"Rate limit reset for key: {key}")

    def get_retry_after(self, key: str) -> int:
        """
        Get seconds until rate limit resets.

        Args:
            key: Identifier to check

        Returns:
            Seconds until oldest request exits window
        """
        if self.redis_client:
            return self._get_retry_after_redis(key)
        return self._get_retry_after_memory(key)

    def _get_retry_after_memory(self, key: str) -> int:
        """Get retry-after using in-memory storage."""
        if key not in self._requests or not self._requests[key]:
            return 0

        oldest_request = self._requests[key][0]
        time_until_reset = (oldest_request + self.window_seconds) - time.time()
        return max(0, int(time_until_reset))

    def _get_retry_after_redis(self, key: str) -> int:
        """Get retry-after using Redis."""
        try:
            redis_key = f"{self.key_prefix}{key}"

            # Get oldest entry
            oldest = self.redis_client.zrange(redis_key, 0, 0, withscores=True)

            if not oldest:
                return 0

            oldest_timestamp = oldest[0][1]
            time_until_reset = (oldest_timestamp + self.window_seconds) - time.time()
            return max(0, int(time_until_reset))

        except Exception as e:
            logger.error(f"Redis error getting retry-after: {e}")
            return self.window_seconds  # Conservative estimate
