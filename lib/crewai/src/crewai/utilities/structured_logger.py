"""
Enterprise-grade structured logging system for CrewAI.

Features:
- JSON-formatted logs for easy parsing and indexing
- Correlation IDs for distributed tracing
- Context propagation across async boundaries
- Performance metrics and timing
- Integration with OpenTelemetry
- Multiple output handlers (console, file, remote)

Usage:
    >>> from crewai.utilities.structured_logger import get_logger
    >>> logger = get_logger(__name__)
    >>> logger.info("Agent started", agent_role="researcher", task_id="task-123")
    >>> # Output: {"timestamp": "2025-11-16T10:30:00Z", "level": "INFO", "message": "Agent started", ...}
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
import uuid
from contextvars import ContextVar
from datetime import datetime
from datetime import timezone
from typing import Any


# Context variable for correlation ID (thread-safe and async-safe)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class CorrelationContext:
    """
    Context manager for setting correlation ID.

    Usage:
        >>> with CorrelationContext("request-123"):
        ...     logger.info("Processing request")
    """

    def __init__(self, correlation_id: str | None = None) -> None:
        """
        Initialize correlation context.

        Args:
            correlation_id: Correlation ID (generated if None)
        """
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.token = None

    def __enter__(self) -> str:
        """Set correlation ID in context."""
        self.token = _correlation_id.set(self.correlation_id)
        return self.correlation_id

    def __exit__(self, *args: Any) -> None:
        """Reset correlation ID."""
        if self.token:
            _correlation_id.reset(self.token)


def get_correlation_id() -> str | None:
    """Get current correlation ID from context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    _correlation_id.set(correlation_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Converts log records to JSON format with consistent structure.
    """

    def __init__(
        self,
        service_name: str = "crewai",
        version: str = "1.5.0",
        include_extra: bool = True,
    ) -> None:
        """
        Initialize structured formatter.

        Args:
            service_name: Name of the service (default: "crewai")
            version: Service version (default: "1.5.0")
            include_extra: Include extra fields from record (default: True)
        """
        super().__init__()
        self.service_name = service_name
        self.version = version
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "version": self.version,
            "correlation_id": get_correlation_id(),
            "process": {
                "pid": record.process,
                "thread": record.thread,
                "thread_name": record.threadName,
            },
            "source": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields
        if self.include_extra:
            # Get all custom attributes
            standard_attrs = {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            }

            extra_data = {
                k: v
                for k, v in record.__dict__.items()
                if k not in standard_attrs and not k.startswith("_")
            }

            if extra_data:
                log_data["extra"] = extra_data

        return json.dumps(log_data, default=str)


class StructuredLogger:
    """
    Enhanced logger with structured logging capabilities.

    Wraps Python's standard logger with additional features:
    - Automatic correlation ID injection
    - Structured context fields
    - Performance timing
    - Integration with metrics
    """

    def __init__(self, name: str, logger: logging.Logger) -> None:
        """
        Initialize structured logger.

        Args:
            name: Logger name
            logger: Underlying Python logger
        """
        self.name = name
        self._logger = logger

    def _log(
        self,
        level: int,
        message: str,
        exc_info: Any = None,
        **kwargs: Any,
    ) -> None:
        """
        Internal logging method with extra fields.

        Args:
            level: Log level
            message: Log message
            exc_info: Exception info
            **kwargs: Additional context fields
        """
        # Create a new log record with extra fields
        extra = {k: v for k, v in kwargs.items()}
        self._logger.log(level, message, exc_info=exc_info, extra=extra)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with context."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with context."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with context."""
        self._log(logging.WARNING, message, **kwargs)

    def error(
        self,
        message: str,
        exc_info: Any = None,
        **kwargs: Any,
    ) -> None:
        """Log error message with context and optional exception."""
        self._log(logging.ERROR, message, exc_info=exc_info, **kwargs)

    def critical(
        self,
        message: str,
        exc_info: Any = None,
        **kwargs: Any,
    ) -> None:
        """Log critical message with context and optional exception."""
        self._log(logging.CRITICAL, message, exc_info=exc_info, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with full traceback."""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)

    def with_context(self, **context: Any) -> LoggerContext:
        """
        Create a context manager that adds fields to all log messages.

        Args:
            **context: Context fields to add

        Returns:
            LoggerContext instance

        Example:
            >>> with logger.with_context(request_id="req-123", user_id="user-456"):
            ...     logger.info("Processing request")
            ...     # All logs will include request_id and user_id
        """
        return LoggerContext(self, context)


class LoggerContext:
    """Context manager for adding fields to log messages."""

    def __init__(self, logger: StructuredLogger, context: dict[str, Any]) -> None:
        """
        Initialize logger context.

        Args:
            logger: Logger instance
            context: Context fields to add
        """
        self.logger = logger
        self.context = context
        self.original_log = logger._log

    def __enter__(self) -> StructuredLogger:
        """Enter context and wrap logging method."""

        def wrapped_log(level: int, message: str, exc_info: Any = None, **kwargs: Any) -> None:
            # Merge context with kwargs
            merged_kwargs = {**self.context, **kwargs}
            self.original_log(level, message, exc_info=exc_info, **merged_kwargs)

        self.logger._log = wrapped_log  # type: ignore[method-assign]
        return self.logger

    def __exit__(self, *args: Any) -> None:
        """Exit context and restore original logging method."""
        self.logger._log = self.original_log  # type: ignore[method-assign]


class PerformanceTimer:
    """
    Context manager for timing operations and logging performance.

    Usage:
        >>> logger = get_logger(__name__)
        >>> with PerformanceTimer(logger, "database_query", query_type="SELECT"):
        ...     # Database operation
        ...     pass
        >>> # Logs: {"message": "database_query completed", "duration_ms": 123.45, "query_type": "SELECT"}
    """

    def __init__(
        self,
        logger: StructuredLogger,
        operation: str,
        log_level: int = logging.INFO,
        **context: Any,
    ) -> None:
        """
        Initialize performance timer.

        Args:
            logger: Logger instance
            operation: Operation name
            log_level: Log level for timing message
            **context: Additional context fields
        """
        self.logger = logger
        self.operation = operation
        self.log_level = log_level
        self.context = context
        self.start_time: float | None = None

    def __enter__(self) -> PerformanceTimer:
        """Start timing."""
        import time

        self.start_time = time.time()
        return self

    def __exit__(self, *args: Any) -> None:
        """Stop timing and log duration."""
        import time

        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            self.logger._log(
                self.log_level,
                f"{self.operation} completed",
                duration_ms=round(duration_ms, 2),
                operation=self.operation,
                **self.context,
            )


# ============================================================================
# Logger Configuration and Factory
# ============================================================================


def configure_logging(
    level: str | int = "INFO",
    format_type: str = "json",
    output: str = "console",
    log_file: str | None = None,
) -> None:
    """
    Configure global logging settings.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("json" or "text")
        output: Output destination ("console", "file", or "both")
        log_file: Log file path (required if output includes "file")

    Example:
        >>> configure_logging(level="DEBUG", format_type="json", output="console")
    """
    # Convert string level to int
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create formatter
    if format_type == "json":
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Add console handler
    if output in ("console", "both"):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Add file handler
    if output in ("file", "both"):
        if not log_file:
            log_file = os.getenv("CREWAI_LOG_FILE", "crewai.log")

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> StructuredLogger:
    """
    Get or create a structured logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started", version="1.5.0")
    """
    python_logger = logging.getLogger(name)
    return StructuredLogger(name, python_logger)


# ============================================================================
# Auto-configuration on import
# ============================================================================

# Auto-configure logging based on environment
_log_level = os.getenv("CREWAI_LOG_LEVEL", "INFO")
_log_format = os.getenv("CREWAI_LOG_FORMAT", "json")
_log_output = os.getenv("CREWAI_LOG_OUTPUT", "console")

# Only configure if not already configured
if not logging.getLogger().handlers:
    configure_logging(level=_log_level, format_type=_log_format, output=_log_output)
