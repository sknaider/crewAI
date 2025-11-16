"""
Enterprise-grade exception hierarchy for CrewAI.

This module provides a comprehensive, structured exception system that enables:
- Granular error handling and recovery
- Rich error context and metadata
- Production-ready logging and monitoring
- Clear error codes for troubleshooting
- Support for distributed tracing

Exception Hierarchy:
    CrewAIException (base)
    ├── AgentException
    │   ├── AgentCreationException
    │   ├── AgentExecutionException
    │   ├── AgentTimeoutException
    │   └── AgentConfigurationException
    ├── TaskException
    │   ├── TaskExecutionException
    │   ├── TaskTimeoutException
    │   ├── TaskValidationException
    │   └── TaskOutputException
    ├── ToolException
    │   ├── ToolExecutionException
    │   ├── ToolNotFoundException
    │   ├── ToolTimeoutException
    │   └── ToolUsageLimitException
    ├── MemoryException
    │   ├── MemoryStorageException
    │   ├── MemoryRetrievalException
    │   └── MemoryCorruptionException
    ├── LLMException
    │   ├── LLMProviderException
    │   ├── LLMTimeoutException
    │   ├── LLMRateLimitException
    │   ├── LLMTokenLimitException
    │   └── LLMAuthenticationException
    ├── ConfigurationException
    │   ├── InvalidConfigurationException
    │   ├── MissingConfigurationException
    │   └── ConfigurationLoadException
    ├── SecurityException
    │   ├── AuthenticationException
    │   ├── AuthorizationException
    │   └── SecretManagementException
    ├── FlowException
    │   ├── FlowExecutionException
    │   ├── FlowValidationException
    │   └── FlowStateException
    └── CrewException
        ├── CrewCreationException
        ├── CrewExecutionException
        └── CrewValidationException

Usage:
    >>> from crewai.exceptions import ToolExecutionException
    >>> raise ToolExecutionException(
    ...     message="Failed to execute web scraping tool",
    ...     tool_name="WebScraperTool",
    ...     error_code="TOOL_001",
    ...     original_error=original_exception,
    ...     context={"url": "https://example.com", "timeout": 30}
    ... )
"""

from __future__ import annotations

from typing import Any


class CrewAIException(Exception):
    """
    Base exception for all CrewAI-related errors.

    This is the root of the exception hierarchy. All custom exceptions
    in CrewAI should inherit from this class.

    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code (e.g., "AGENT_001")
        context: Additional context data for debugging
        original_error: The underlying exception that caused this error
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize the CrewAI exception.

        Args:
            message: Human-readable error description
            error_code: Optional error code for categorization (e.g., "AGENT_001")
            context: Optional dictionary with additional debugging context
            original_error: Optional original exception that caused this error
        """
        self.message = message
        self.error_code = error_code or "UNKNOWN"
        self.context = context or {}
        self.original_error = original_error

        # Build the full error message
        full_message = f"[{self.error_code}] {message}"
        if context:
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            full_message += f" | Context: {context_str}"
        if original_error:
            full_message += f" | Caused by: {original_error!s}"

        super().__init__(full_message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "original_error": str(self.original_error) if self.original_error else None,
        }


# ============================================================================
# AGENT EXCEPTIONS
# ============================================================================


class AgentException(CrewAIException):
    """Base exception for all agent-related errors."""

    pass


class AgentCreationException(AgentException):
    """Raised when agent creation or initialization fails."""

    def __init__(
        self,
        message: str,
        agent_role: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if agent_role:
            context["agent_role"] = agent_role
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "AGENT_CREATE_001"),
            context=context,
            **kwargs,
        )


class AgentExecutionException(AgentException):
    """Raised when agent execution encounters an error."""

    def __init__(
        self,
        message: str,
        agent_role: str | None = None,
        task_description: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if agent_role:
            context["agent_role"] = agent_role
        if task_description:
            context["task_description"] = task_description
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "AGENT_EXEC_001"),
            context=context,
            **kwargs,
        )


class AgentTimeoutException(AgentException):
    """Raised when agent execution exceeds timeout limit."""

    def __init__(
        self,
        message: str,
        timeout_seconds: int | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "AGENT_TIMEOUT_001"),
            context=context,
            **kwargs,
        )


class AgentConfigurationException(AgentException):
    """Raised when agent configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if config_key:
            context["config_key"] = config_key
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "AGENT_CONFIG_001"),
            context=context,
            **kwargs,
        )


# ============================================================================
# TASK EXCEPTIONS
# ============================================================================


class TaskException(CrewAIException):
    """Base exception for all task-related errors."""

    pass


class TaskExecutionException(TaskException):
    """Raised when task execution fails."""

    def __init__(
        self,
        message: str,
        task_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if task_id:
            context["task_id"] = task_id
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "TASK_EXEC_001"),
            context=context,
            **kwargs,
        )


class TaskTimeoutException(TaskException):
    """Raised when task execution exceeds timeout."""

    def __init__(
        self,
        message: str,
        timeout_seconds: int | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "TASK_TIMEOUT_001"),
            context=context,
            **kwargs,
        )


class TaskValidationException(TaskException):
    """Raised when task validation fails."""

    def __init__(
        self,
        message: str,
        validation_errors: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if validation_errors:
            context["validation_errors"] = validation_errors
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "TASK_VALIDATION_001"),
            context=context,
            **kwargs,
        )


class TaskOutputException(TaskException):
    """Raised when task output processing fails."""

    def __init__(
        self,
        message: str,
        output_format: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if output_format:
            context["output_format"] = output_format
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "TASK_OUTPUT_001"),
            context=context,
            **kwargs,
        )


# ============================================================================
# TOOL EXCEPTIONS
# ============================================================================


class ToolException(CrewAIException):
    """Base exception for all tool-related errors."""

    pass


class ToolExecutionException(ToolException):
    """Raised when tool execution fails."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if tool_name:
            context["tool_name"] = tool_name
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "TOOL_EXEC_001"),
            context=context,
            **kwargs,
        )


class ToolNotFoundException(ToolException):
    """Raised when a requested tool cannot be found."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if tool_name:
            context["tool_name"] = tool_name
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "TOOL_NOT_FOUND_001"),
            context=context,
            **kwargs,
        )


class ToolTimeoutException(ToolException):
    """Raised when tool execution exceeds timeout."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        timeout_seconds: int | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if tool_name:
            context["tool_name"] = tool_name
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "TOOL_TIMEOUT_001"),
            context=context,
            **kwargs,
        )


class ToolUsageLimitException(ToolException):
    """Raised when tool usage limit is exceeded."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        limit: int | None = None,
        current_usage: int | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if tool_name:
            context["tool_name"] = tool_name
        if limit:
            context["limit"] = limit
        if current_usage:
            context["current_usage"] = current_usage
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "TOOL_LIMIT_001"),
            context=context,
            **kwargs,
        )


# ============================================================================
# MEMORY EXCEPTIONS
# ============================================================================


class MemoryException(CrewAIException):
    """Base exception for all memory-related errors."""

    pass


class MemoryStorageException(MemoryException):
    """Raised when memory storage operations fail."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if operation:
            context["operation"] = operation
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "MEMORY_STORAGE_001"),
            context=context,
            **kwargs,
        )


class MemoryRetrievalException(MemoryException):
    """Raised when memory retrieval operations fail."""

    def __init__(
        self,
        message: str,
        query: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if query:
            context["query"] = query
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "MEMORY_RETRIEVAL_001"),
            context=context,
            **kwargs,
        )


class MemoryCorruptionException(MemoryException):
    """Raised when memory data is corrupted or invalid."""

    def __init__(
        self,
        message: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "MEMORY_CORRUPTION_001"),
            **kwargs,
        )


# ============================================================================
# LLM EXCEPTIONS
# ============================================================================


class LLMException(CrewAIException):
    """Base exception for all LLM-related errors."""

    pass


class LLMProviderException(LLMException):
    """Raised when LLM provider encounters an error."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if provider:
            context["provider"] = provider
        if model:
            context["model"] = model
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "LLM_PROVIDER_001"),
            context=context,
            **kwargs,
        )


class LLMTimeoutException(LLMException):
    """Raised when LLM request exceeds timeout."""

    def __init__(
        self,
        message: str,
        timeout_seconds: int | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "LLM_TIMEOUT_001"),
            context=context,
            **kwargs,
        )


class LLMRateLimitException(LLMException):
    """Raised when LLM rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if retry_after:
            context["retry_after_seconds"] = retry_after
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "LLM_RATE_LIMIT_001"),
            context=context,
            **kwargs,
        )


class LLMTokenLimitException(LLMException):
    """Raised when LLM token limit is exceeded."""

    def __init__(
        self,
        message: str,
        token_count: int | None = None,
        token_limit: int | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if token_count:
            context["token_count"] = token_count
        if token_limit:
            context["token_limit"] = token_limit
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "LLM_TOKEN_LIMIT_001"),
            context=context,
            **kwargs,
        )


class LLMAuthenticationException(LLMException):
    """Raised when LLM authentication fails."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if provider:
            context["provider"] = provider
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "LLM_AUTH_001"),
            context=context,
            **kwargs,
        )


# ============================================================================
# CONFIGURATION EXCEPTIONS
# ============================================================================


class ConfigurationException(CrewAIException):
    """Base exception for configuration-related errors."""

    pass


class InvalidConfigurationException(ConfigurationException):
    """Raised when configuration is invalid."""

    def __init__(
        self,
        message: str,
        config_path: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if config_path:
            context["config_path"] = config_path
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "CONFIG_INVALID_001"),
            context=context,
            **kwargs,
        )


class MissingConfigurationException(ConfigurationException):
    """Raised when required configuration is missing."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if config_key:
            context["config_key"] = config_key
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "CONFIG_MISSING_001"),
            context=context,
            **kwargs,
        )


class ConfigurationLoadException(ConfigurationException):
    """Raised when configuration loading fails."""

    def __init__(
        self,
        message: str,
        config_file: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if config_file:
            context["config_file"] = config_file
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "CONFIG_LOAD_001"),
            context=context,
            **kwargs,
        )


# ============================================================================
# SECURITY EXCEPTIONS
# ============================================================================


class SecurityException(CrewAIException):
    """Base exception for security-related errors."""

    pass


class AuthenticationException(SecurityException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if user_id:
            context["user_id"] = user_id
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "SEC_AUTH_001"),
            context=context,
            **kwargs,
        )


class AuthorizationException(SecurityException):
    """Raised when authorization check fails."""

    def __init__(
        self,
        message: str,
        resource: str | None = None,
        action: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if resource:
            context["resource"] = resource
        if action:
            context["action"] = action
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "SEC_AUTHZ_001"),
            context=context,
            **kwargs,
        )


class SecretManagementException(SecurityException):
    """Raised when secret management operations fail."""

    def __init__(
        self,
        message: str,
        secret_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if secret_name:
            context["secret_name"] = secret_name
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "SEC_SECRET_001"),
            context=context,
            **kwargs,
        )


# ============================================================================
# FLOW EXCEPTIONS
# ============================================================================


class FlowException(CrewAIException):
    """Base exception for flow-related errors."""

    pass


class FlowExecutionException(FlowException):
    """Raised when flow execution fails."""

    def __init__(
        self,
        message: str,
        flow_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if flow_name:
            context["flow_name"] = flow_name
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "FLOW_EXEC_001"),
            context=context,
            **kwargs,
        )


class FlowValidationException(FlowException):
    """Raised when flow validation fails."""

    def __init__(
        self,
        message: str,
        validation_errors: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if validation_errors:
            context["validation_errors"] = validation_errors
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "FLOW_VALIDATION_001"),
            context=context,
            **kwargs,
        )


class FlowStateException(FlowException):
    """Raised when flow state management fails."""

    def __init__(
        self,
        message: str,
        state: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if state:
            context["state"] = state
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "FLOW_STATE_001"),
            context=context,
            **kwargs,
        )


# ============================================================================
# CREW EXCEPTIONS
# ============================================================================


class CrewException(CrewAIException):
    """Base exception for crew-related errors."""

    pass


class CrewCreationException(CrewException):
    """Raised when crew creation fails."""

    def __init__(
        self,
        message: str,
        crew_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if crew_name:
            context["crew_name"] = crew_name
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "CREW_CREATE_001"),
            context=context,
            **kwargs,
        )


class CrewExecutionException(CrewException):
    """Raised when crew execution fails."""

    def __init__(
        self,
        message: str,
        crew_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if crew_name:
            context["crew_name"] = crew_name
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "CREW_EXEC_001"),
            context=context,
            **kwargs,
        )


class CrewValidationException(CrewException):
    """Raised when crew validation fails."""

    def __init__(
        self,
        message: str,
        validation_errors: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if validation_errors:
            context["validation_errors"] = validation_errors
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "CREW_VALIDATION_001"),
            context=context,
            **kwargs,
        )


# ============================================================================
# BACKWARDS COMPATIBILITY
# ============================================================================

# Maintain backwards compatibility with existing code
ContextWindowExceedingException = LLMTokenLimitException
ToolUsageLimitExceededError = ToolUsageLimitException
ToolUsageError = ToolExecutionException
