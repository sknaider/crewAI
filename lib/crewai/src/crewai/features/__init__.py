"""
Feature flags system for CrewAI.

Enables gradual rollouts, A/B testing, and kill switches for production features.
"""

from crewai.features.flags import Environment
from crewai.features.flags import FeatureFlags
from crewai.features.flags import is_enabled


__all__ = ["FeatureFlags", "Environment", "is_enabled"]
