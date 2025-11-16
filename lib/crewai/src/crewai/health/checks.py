"""
Health check implementation for CrewAI.

Provides standardized health checks for:
- Liveness: Is the application running?
- Readiness: Can it accept traffic?
- Startup: Has it finished initializing?

Usage (Flask):
    >>> from crewai.health import get_health_router
    >>> from flask import Flask
    >>> app = Flask(__name__)
    >>> health_router = get_health_router()
    >>> app.register_blueprint(health_router, url_prefix="/health")

Usage (FastAPI):
    >>> from crewai.health import get_health_router
    >>> from fastapi import FastAPI
    >>> app = FastAPI()
    >>> app.include_router(get_health_router())
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any
from typing import Callable


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthCheck:
    """
    Health check coordinator.

    Manages application health state and provides endpoints
    for liveness, readiness, and startup probes.
    """

    def __init__(self) -> None:
        """Initialize health check system."""
        self._startup_complete = False
        self._startup_time = time.time()
        self._ready = False
        self._checks: dict[str, Callable[[], bool]] = {}

        logger.info("HealthCheck initialized")

    def mark_startup_complete(self) -> None:
        """Mark startup as complete."""
        self._startup_complete = True
        logger.info("Application startup complete")

    def mark_ready(self) -> None:
        """Mark application as ready to accept traffic."""
        self._ready = True
        logger.info("Application ready to accept traffic")

    def mark_not_ready(self) -> None:
        """Mark application as not ready (e.g., during shutdown)."""
        self._ready = False
        logger.warning("Application marked as not ready")

    def register_check(self, name: str, check_func: Callable[[], bool]) -> None:
        """
        Register a custom health check.

        Args:
            name: Check name
            check_func: Function that returns True if healthy

        Example:
            >>> health = HealthCheck()
            >>> def check_db():
            ...     return db.is_connected()
            >>> health.register_check("database", check_db)
        """
        self._checks[name] = check_func
        logger.info(f"Registered health check: {name}")

    def liveness(self) -> dict[str, Any]:
        """
        Liveness probe - is the application running?

        Returns:
            Dict with status and details

        Kubernetes uses this to determine if the pod should be restarted.
        """
        return {
            "status": "healthy",
            "uptime_seconds": round(time.time() - self._startup_time, 2),
            "timestamp": time.time(),
        }

    def readiness(self) -> dict[str, Any]:
        """
        Readiness probe - can the application accept traffic?

        Returns:
            Dict with status and check results

        Kubernetes uses this to determine if the pod should receive traffic.
        """
        if not self._ready:
            return {
                "status": "not_ready",
                "reason": "Application not marked as ready",
                "timestamp": time.time(),
            }

        # Run all registered checks
        check_results = {}
        all_healthy = True

        for name, check_func in self._checks.items():
            try:
                result = check_func()
                check_results[name] = "healthy" if result else "unhealthy"
                if not result:
                    all_healthy = False
            except Exception as e:
                check_results[name] = f"error: {e!s}"
                all_healthy = False
                logger.error(f"Health check '{name}' failed: {e}")

        status = "healthy" if all_healthy else "unhealthy"

        return {
            "status": status,
            "checks": check_results,
            "timestamp": time.time(),
        }

    def startup(self) -> dict[str, Any]:
        """
        Startup probe - has the application finished initializing?

        Returns:
            Dict with status and startup info

        Kubernetes uses this to know when to start liveness/readiness probes.
        """
        if not self._startup_complete:
            return {
                "status": "starting",
                "elapsed_seconds": round(time.time() - self._startup_time, 2),
                "timestamp": time.time(),
            }

        return {
            "status": "started",
            "startup_duration_seconds": round(time.time() - self._startup_time, 2),
            "timestamp": time.time(),
        }

    def get_all_status(self) -> dict[str, Any]:
        """
        Get comprehensive health status.

        Returns:
            Dict with all health check results
        """
        return {
            "liveness": self.liveness(),
            "readiness": self.readiness(),
            "startup": self.startup(),
        }


# Global health check instance
_health_check = HealthCheck()


def get_health_check() -> HealthCheck:
    """Get the global health check instance."""
    return _health_check


def get_health_router() -> Any:
    """
    Get health check router for web framework.

    Returns a router/blueprint with health endpoints:
    - /health/live - Liveness probe
    - /health/ready - Readiness probe
    - /health/startup - Startup probe
    - /health - Full status

    Returns:
        Router/blueprint compatible with Flask or FastAPI

    Example (Flask):
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> app.register_blueprint(get_health_router(), url_prefix="/health")

    Example (FastAPI):
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> app.include_router(get_health_router())
    """
    # Try FastAPI first
    try:
        from fastapi import APIRouter
        from fastapi import Response
        from fastapi import status

        router = APIRouter(prefix="/health", tags=["health"])

        @router.get("/live")
        def liveness() -> dict[str, Any]:
            """Liveness probe endpoint."""
            return _health_check.liveness()

        @router.get("/ready")
        def readiness(response: Response) -> dict[str, Any]:
            """Readiness probe endpoint."""
            result = _health_check.readiness()
            if result["status"] != "healthy":
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return result

        @router.get("/startup")
        def startup_probe(response: Response) -> dict[str, Any]:
            """Startup probe endpoint."""
            result = _health_check.startup()
            if result["status"] != "started":
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return result

        @router.get("")
        def health() -> dict[str, Any]:
            """Full health status endpoint."""
            return _health_check.get_all_status()

        return router

    except ImportError:
        pass

    # Try Flask
    try:
        from flask import Blueprint
        from flask import jsonify

        bp = Blueprint("health", __name__)

        @bp.route("/live")
        def liveness() -> Any:
            """Liveness probe endpoint."""
            return jsonify(_health_check.liveness())

        @bp.route("/ready")
        def readiness() -> Any:
            """Readiness probe endpoint."""
            result = _health_check.readiness()
            status_code = 200 if result["status"] == "healthy" else 503
            return jsonify(result), status_code

        @bp.route("/startup")
        def startup_probe() -> Any:
            """Startup probe endpoint."""
            result = _health_check.startup()
            status_code = 200 if result["status"] == "started" else 503
            return jsonify(result), status_code

        @bp.route("/")
        def health() -> Any:
            """Full health status endpoint."""
            return jsonify(_health_check.get_all_status())

        return bp

    except ImportError:
        pass

    # Fallback: simple dict-based router
    logger.warning("No web framework detected, returning basic health functions")
    return {
        "/health/live": _health_check.liveness,
        "/health/ready": _health_check.readiness,
        "/health/startup": _health_check.startup,
        "/health": _health_check.get_all_status,
    }
