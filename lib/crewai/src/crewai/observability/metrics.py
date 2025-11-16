"""
Prometheus metrics for CrewAI enterprise observability.

Provides comprehensive metrics for monitoring:
- Agent execution stats (success/failure rates)
- Task performance (duration, throughput)
- LLM API usage (calls, tokens, costs)
- System health (active crews, memory usage)
- Tool usage statistics

Usage:
    >>> from crewai.observability.metrics import agent_executions_total, task_duration_seconds
    >>> agent_executions_total.labels(agent_role="researcher", status="success").inc()
    >>> with task_duration_seconds.labels(task_type="research").time():
    ...     # Execute task
    ...     pass

Prometheus Integration:
    >>> from crewai.observability.metrics import get_metrics_handler
    >>> # Flask
    >>> app.route("/metrics")(get_metrics_handler())
    >>> # FastAPI
    >>> @app.get("/metrics")
    >>> def metrics():
    ...     return Response(content=get_metrics_handler()(), media_type="text/plain")
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from prometheus_client import Counter
    from prometheus_client import Gauge
    from prometheus_client import Histogram

logger = logging.getLogger(__name__)


# ============================================================================
# Prometheus Metrics Initialization
# ============================================================================

# Check if Prometheus client is available
try:
    from prometheus_client import Counter as PrometheusCounter
    from prometheus_client import Gauge as PrometheusGauge
    from prometheus_client import Histogram as PrometheusHistogram
    from prometheus_client import generate_latest
    from prometheus_client import REGISTRY

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning(
        "prometheus_client not installed. Metrics collection disabled. "
        "Install with: pip install prometheus-client"
    )

    # Create dummy classes for type hints
    class PrometheusCounter:  # type: ignore[no-redef]
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def labels(self, *args: object, **kwargs: object) -> PrometheusCounter:
            return self

        def inc(self, amount: float = 1) -> None:
            pass

    class PrometheusGauge:  # type: ignore[no-redef]
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def labels(self, *args: object, **kwargs: object) -> PrometheusGauge:
            return self

        def set(self, value: float) -> None:
            pass

        def inc(self, amount: float = 1) -> None:
            pass

        def dec(self, amount: float = 1) -> None:
            pass

    class PrometheusHistogram:  # type: ignore[no-redef]
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def labels(self, *args: object, **kwargs: object) -> PrometheusHistogram:
            return self

        def observe(self, amount: float) -> None:
            pass

        def time(self) -> object:
            return self

        def __enter__(self) -> PrometheusHistogram:
            return self

        def __exit__(self, *args: object) -> None:
            pass

    def generate_latest(*args: object, **kwargs: object) -> bytes:  # type: ignore[misc]
        return b""

    REGISTRY = None  # type: ignore[assignment]


# ============================================================================
# Agent Metrics
# ============================================================================

agent_executions_total: Counter = PrometheusCounter(
    name="crewai_agent_executions_total",
    documentation="Total number of agent executions",
    labelnames=["agent_role", "status"],  # status: success, failure, timeout
)

agent_execution_duration_seconds: Histogram = PrometheusHistogram(
    name="crewai_agent_execution_duration_seconds",
    documentation="Agent execution duration in seconds",
    labelnames=["agent_role"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

# ============================================================================
# Task Metrics
# ============================================================================

task_executions_total: Counter = PrometheusCounter(
    name="crewai_task_executions_total",
    documentation="Total number of task executions",
    labelnames=["task_type", "status"],  # status: success, failure, timeout
)

task_duration_seconds: Histogram = PrometheusHistogram(
    name="crewai_task_duration_seconds",
    documentation="Task execution duration in seconds",
    labelnames=["task_type"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
)

# ============================================================================
# Crew Metrics
# ============================================================================

crew_executions_total: Counter = PrometheusCounter(
    name="crewai_crew_executions_total",
    documentation="Total number of crew executions",
    labelnames=["crew_name", "status"],
)

active_crews: Gauge = PrometheusGauge(
    name="crewai_active_crews",
    documentation="Number of currently active crews",
)

crew_size: Histogram = PrometheusHistogram(
    name="crewai_crew_size",
    documentation="Number of agents in crew",
    labelnames=["crew_name"],
    buckets=[1, 2, 3, 5, 10, 20, 50],
)

# ============================================================================
# LLM Metrics
# ============================================================================

llm_api_calls_total: Counter = PrometheusCounter(
    name="crewai_llm_api_calls_total",
    documentation="Total number of LLM API calls",
    labelnames=["provider", "model", "status"],  # provider: openai, anthropic, etc.
)

llm_api_duration_seconds: Histogram = PrometheusHistogram(
    name="crewai_llm_api_duration_seconds",
    documentation="LLM API call duration in seconds",
    labelnames=["provider", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

token_usage_total: Counter = PrometheusCounter(
    name="crewai_token_usage_total",
    documentation="Total tokens consumed",
    labelnames=["provider", "model", "type"],  # type: prompt, completion
)

llm_errors_total: Counter = PrometheusCounter(
    name="crewai_llm_errors_total",
    documentation="Total number of LLM errors",
    labelnames=["provider", "error_type"],  # error_type: rate_limit, timeout, auth, etc.
)

# ============================================================================
# Tool Metrics
# ============================================================================

tool_executions_total: Counter = PrometheusCounter(
    name="crewai_tool_executions_total",
    documentation="Total number of tool executions",
    labelnames=["tool_name", "status"],
)

tool_duration_seconds: Histogram = PrometheusHistogram(
    name="crewai_tool_duration_seconds",
    documentation="Tool execution duration in seconds",
    labelnames=["tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
)

tool_errors_total: Counter = PrometheusCounter(
    name="crewai_tool_errors_total",
    documentation="Total number of tool errors",
    labelnames=["tool_name", "error_type"],
)

# ============================================================================
# Memory Metrics
# ============================================================================

memory_operations_total: Counter = PrometheusCounter(
    name="crewai_memory_operations_total",
    documentation="Total number of memory operations",
    labelnames=["operation", "memory_type", "status"],  # operation: save, load, search
)

memory_size_bytes: Gauge = PrometheusGauge(
    name="crewai_memory_size_bytes",
    documentation="Current memory size in bytes",
    labelnames=["memory_type"],  # memory_type: short_term, long_term, entity
)

# ============================================================================
# System Metrics
# ============================================================================

system_errors_total: Counter = PrometheusCounter(
    name="crewai_system_errors_total",
    documentation="Total number of system errors",
    labelnames=["component", "error_type"],
)

http_requests_total: Counter = PrometheusCounter(
    name="crewai_http_requests_total",
    documentation="Total number of HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
)

http_request_duration_seconds: Histogram = PrometheusHistogram(
    name="crewai_http_request_duration_seconds",
    documentation="HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ============================================================================
# Cost Metrics (Enterprise)
# ============================================================================

estimated_cost_usd: Counter = PrometheusCounter(
    name="crewai_estimated_cost_usd",
    documentation="Estimated cost in USD (based on token usage)",
    labelnames=["provider", "model"],
)


# ============================================================================
# Metrics Exporter
# ============================================================================


def get_metrics_handler() -> object:
    """
    Get metrics handler for HTTP endpoint.

    Returns a function that can be used as a route handler for /metrics endpoint.

    Returns:
        Callable that returns Prometheus metrics in text format

    Example:
        >>> # Flask
        >>> from flask import Flask, Response
        >>> app = Flask(__name__)
        >>> @app.route("/metrics")
        >>> def metrics():
        >>>     return Response(get_metrics_handler()(), mimetype="text/plain")

        >>> # FastAPI
        >>> from fastapi import FastAPI
        >>> from fastapi.responses import PlainTextResponse
        >>> app = FastAPI()
        >>> @app.get("/metrics")
        >>> def metrics():
        >>>     return PlainTextResponse(content=get_metrics_handler()())
    """
    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus client not available, /metrics endpoint will return empty")

        def empty_metrics() -> bytes:
            return b"# Prometheus client not installed\n"

        return empty_metrics

    def metrics_handler() -> bytes:
        """Generate Prometheus metrics."""
        return generate_latest(REGISTRY)

    return metrics_handler


# ============================================================================
# Helper Functions
# ============================================================================


def is_metrics_enabled() -> bool:
    """Check if metrics collection is enabled."""
    if not PROMETHEUS_AVAILABLE:
        return False

    # Allow disabling via environment variable
    return os.getenv("CREWAI_METRICS_ENABLED", "true").lower() != "false"


def calculate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate estimated cost for LLM usage.

    Args:
        provider: LLM provider (openai, anthropic, etc.)
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens

    Returns:
        Estimated cost in USD

    Note:
        Pricing data should be maintained in a separate configuration file.
        These are approximate rates as of 2024.
    """
    # Approximate pricing (per 1M tokens) - update regularly
    pricing = {
        "openai": {
            "gpt-4": {"prompt": 30.0, "completion": 60.0},
            "gpt-4-turbo": {"prompt": 10.0, "completion": 30.0},
            "gpt-3.5-turbo": {"prompt": 0.5, "completion": 1.5},
        },
        "anthropic": {
            "claude-3-opus": {"prompt": 15.0, "completion": 75.0},
            "claude-3-sonnet": {"prompt": 3.0, "completion": 15.0},
            "claude-3-haiku": {"prompt": 0.25, "completion": 1.25},
        },
    }

    provider_pricing = pricing.get(provider.lower(), {})
    model_pricing = None

    # Find matching model (handle versioned models)
    for model_key, prices in provider_pricing.items():
        if model_key in model.lower():
            model_pricing = prices
            break

    if not model_pricing:
        logger.warning(f"No pricing data for {provider}/{model}, using default rate")
        model_pricing = {"prompt": 1.0, "completion": 2.0}

    prompt_cost = (prompt_tokens / 1_000_000) * model_pricing["prompt"]
    completion_cost = (completion_tokens / 1_000_000) * model_pricing["completion"]

    return prompt_cost + completion_cost
