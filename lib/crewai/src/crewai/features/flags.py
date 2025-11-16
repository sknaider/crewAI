"""
Feature flags implementation for CrewAI.

Provides environment-based feature toggling with percentage rollouts
and A/B testing capabilities.

Usage:
    >>> from crewai.features import is_enabled
    >>> if is_enabled("experimental_reasoning"):
    ...     # Use new reasoning system
    ...     pass
    >>> else:
    ...     # Use legacy system
    ...     pass
"""

from __future__ import annotations

import hashlib
import logging
import os
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class Environment(Enum):
    """Application environments."""

    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    LOCAL = "local"


class FeatureFlags:
    """
    Feature flags configuration and evaluation.

    Supports:
    - Environment-based toggles
    - Percentage-based rollouts
    - User-based targeting
    - Kill switches

    Attributes:
        FLAGS: Feature flag definitions
    """

    FLAGS: dict[str, dict[str, Any]] = {
        # Experimental features
        "experimental_reasoning": {
            "description": "Enhanced reasoning system with chain-of-thought",
            "enabled": {
                Environment.PRODUCTION: False,
                Environment.STAGING: True,
                Environment.DEVELOPMENT: True,
                Environment.LOCAL: True,
            },
            "rollout_percentage": 10,  # 10% of users in enabled environments
        },
        "new_memory_system": {
            "description": "Improved memory system with better retrieval",
            "enabled": {
                Environment.PRODUCTION: False,
                Environment.STAGING: True,
                Environment.DEVELOPMENT: True,
                Environment.LOCAL: True,
            },
            "rollout_percentage": 0,  # Disabled for now
        },
        "enhanced_telemetry": {
            "description": "Detailed telemetry and tracing",
            "enabled": {
                Environment.PRODUCTION: True,
                Environment.STAGING: True,
                Environment.DEVELOPMENT: True,
                Environment.LOCAL: False,
            },
            "rollout_percentage": 100,  # Full rollout
        },
        "advanced_error_recovery": {
            "description": "Advanced error recovery with circuit breakers",
            "enabled": {
                Environment.PRODUCTION: True,
                Environment.STAGING: True,
                Environment.DEVELOPMENT: True,
                Environment.LOCAL: True,
            },
            "rollout_percentage": 100,
        },
        "multi_agent_collaboration_v2": {
            "description": "Enhanced multi-agent collaboration protocol",
            "enabled": {
                Environment.PRODUCTION: False,
                Environment.STAGING: True,
                Environment.DEVELOPMENT: True,
                Environment.LOCAL: True,
            },
            "rollout_percentage": 25,
        },
        "smart_caching": {
            "description": "Intelligent caching with TTL and invalidation",
            "enabled": {
                Environment.PRODUCTION: True,
                Environment.STAGING: True,
                Environment.DEVELOPMENT: True,
                Environment.LOCAL: True,
            },
            "rollout_percentage": 100,
        },
        "cost_optimization": {
            "description": "Automatic cost optimization for LLM calls",
            "enabled": {
                Environment.PRODUCTION: True,
                Environment.STAGING: True,
                Environment.DEVELOPMENT: False,
                Environment.LOCAL: False,
            },
            "rollout_percentage": 50,  # 50% rollout
        },
        "parallel_task_execution": {
            "description": "Execute independent tasks in parallel",
            "enabled": {
                Environment.PRODUCTION: False,
                Environment.STAGING: True,
                Environment.DEVELOPMENT: True,
                Environment.LOCAL: True,
            },
            "rollout_percentage": 5,  # Limited rollout
        },
        # Kill switches
        "disable_external_tools": {
            "description": "Emergency kill switch for external tool execution",
            "enabled": {
                Environment.PRODUCTION: False,
                Environment.STAGING: False,
                Environment.DEVELOPMENT: False,
                Environment.LOCAL: False,
            },
            "rollout_percentage": 0,
        },
        "maintenance_mode": {
            "description": "Put system in maintenance mode",
            "enabled": {
                Environment.PRODUCTION: False,
                Environment.STAGING: False,
                Environment.DEVELOPMENT: False,
                Environment.LOCAL: False,
            },
            "rollout_percentage": 0,
        },
    }

    @classmethod
    def is_enabled(
        cls,
        flag_name: str,
        user_id: str | None = None,
        environment: str | Environment | None = None,
    ) -> bool:
        """
        Check if feature flag is enabled.

        Args:
            flag_name: Name of the feature flag
            user_id: Optional user ID for percentage rollout
            environment: Override environment detection

        Returns:
            True if flag is enabled, False otherwise

        Example:
            >>> if FeatureFlags.is_enabled("experimental_reasoning"):
            ...     use_new_system()

            >>> # With user targeting
            >>> if FeatureFlags.is_enabled("new_feature", user_id="user123"):
            ...     show_new_feature()
        """
        # Get flag configuration
        flag = cls.FLAGS.get(flag_name)
        if not flag:
            logger.warning(f"Unknown feature flag: {flag_name}")
            return False

        # Determine environment
        if environment is None:
            environment = cls._detect_environment()
        elif isinstance(environment, str):
            try:
                environment = Environment(environment.lower())
            except ValueError:
                logger.warning(f"Invalid environment: {environment}, defaulting to development")
                environment = Environment.DEVELOPMENT

        # Check if flag is enabled for this environment
        enabled_map = flag.get("enabled", {})
        if not enabled_map.get(environment, False):
            return False

        # Check percentage rollout
        rollout_percentage = flag.get("rollout_percentage", 100)
        if rollout_percentage >= 100:
            return True
        if rollout_percentage <= 0:
            return False

        # Use user_id for consistent bucketing
        if user_id:
            return cls._is_in_rollout(flag_name, user_id, rollout_percentage)

        # No user_id provided, use random bucketing based on flag name hash
        return cls._is_in_rollout(flag_name, flag_name, rollout_percentage)

    @classmethod
    def _detect_environment(cls) -> Environment:
        """Detect current environment from environment variables."""
        env_var = os.getenv("CREWAI_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
        try:
            return Environment(env_var.lower())
        except ValueError:
            return Environment.DEVELOPMENT

    @classmethod
    def _is_in_rollout(cls, flag_name: str, user_id: str, percentage: int) -> bool:
        """
        Determine if user is in rollout percentage using consistent hashing.

        Args:
            flag_name: Feature flag name
            user_id: User identifier
            percentage: Rollout percentage (0-100)

        Returns:
            True if user is in rollout group
        """
        # Create consistent hash from flag + user_id
        hash_input = f"{flag_name}:{user_id}".encode("utf-8")
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)

        # Map hash to 0-100 range
        bucket = hash_value % 100

        return bucket < percentage

    @classmethod
    def get_all_flags(cls, environment: Environment | None = None) -> dict[str, bool]:
        """
        Get all feature flags and their status.

        Args:
            environment: Environment to check (None = auto-detect)

        Returns:
            Dict mapping flag names to enabled status
        """
        if environment is None:
            environment = cls._detect_environment()

        return {
            flag_name: cls.is_enabled(flag_name, environment=environment)
            for flag_name in cls.FLAGS
        }

    @classmethod
    def override(cls, flag_name: str, enabled: bool) -> None:
        """
        Override feature flag (for testing only).

        Args:
            flag_name: Flag to override
            enabled: New enabled status

        Warning:
            This modifies the class-level FLAGS dict and should only
            be used in tests. Not thread-safe.
        """
        logger.warning(f"Feature flag override: {flag_name} = {enabled}")

        if flag_name not in cls.FLAGS:
            cls.FLAGS[flag_name] = {"enabled": {}, "rollout_percentage": 100}

        # Set all environments to the override value
        for env in Environment:
            cls.FLAGS[flag_name]["enabled"][env] = enabled


# ============================================================================
# Convenience Functions
# ============================================================================


def is_enabled(
    flag_name: str,
    user_id: str | None = None,
    environment: str | Environment | None = None,
) -> bool:
    """
    Convenience function to check if feature is enabled.

    Args:
        flag_name: Feature flag name
        user_id: Optional user ID for rollout targeting
        environment: Optional environment override

    Returns:
        True if enabled, False otherwise

    Example:
        >>> from crewai.features import is_enabled
        >>> if is_enabled("experimental_reasoning"):
        ...     # New feature code
        ...     pass
    """
    return FeatureFlags.is_enabled(flag_name, user_id, environment)


def get_all_flags(environment: Environment | None = None) -> dict[str, bool]:
    """
    Get all feature flags.

    Args:
        environment: Optional environment override

    Returns:
        Dict of flag name -> enabled status
    """
    return FeatureFlags.get_all_flags(environment)
