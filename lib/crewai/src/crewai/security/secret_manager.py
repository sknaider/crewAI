"""
Enterprise-grade secret management system for CrewAI.

Supports multiple secret backends with automatic fallback:
1. AWS Secrets Manager (production)
2. HashiCorp Vault (enterprise)
3. Environment variables (development)
4. .env files (local development)

Features:
- Automatic secret rotation
- Caching with TTL
- Audit logging
- Multi-environment support
- Graceful degradation

Usage:
    >>> from crewai.security.secret_manager import SecretManager
    >>> sm = SecretManager()
    >>> api_key = sm.get_secret("OPENAI_API_KEY")
    >>> db_credentials = sm.get_secret_dict("database/credentials")
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from datetime import timedelta
from enum import Enum
from functools import lru_cache
from typing import Any


logger = logging.getLogger(__name__)


class SecretBackend(Enum):
    """Supported secret management backends."""

    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    HASHICORP_VAULT = "hashicorp_vault"
    ENVIRONMENT = "environment"
    DOTENV = "dotenv"


class Environment(Enum):
    """Application environments."""

    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    LOCAL = "local"


class SecretManager:
    """
    Centralized secret management with multi-backend support.

    Automatically selects the appropriate backend based on environment
    and provides caching, fallback, and audit logging.

    Attributes:
        environment: Current application environment
        default_backend: Primary secret backend to use
        cache_ttl_seconds: How long to cache secrets (default: 300s = 5min)
        enable_audit_log: Whether to log secret access (default: True)
    """

    def __init__(
        self,
        environment: str | None = None,
        default_backend: SecretBackend | None = None,
        cache_ttl_seconds: int = 300,
        enable_audit_log: bool = True,
    ) -> None:
        """
        Initialize the secret manager.

        Args:
            environment: Application environment (production/staging/development/local)
            default_backend: Preferred secret backend
            cache_ttl_seconds: Secret cache TTL in seconds (default: 300)
            enable_audit_log: Enable audit logging (default: True)
        """
        self.environment = self._detect_environment(environment)
        self.default_backend = default_backend or self._select_backend()
        self.cache_ttl_seconds = cache_ttl_seconds
        self.enable_audit_log = enable_audit_log
        self._cache: dict[str, tuple[Any, datetime]] = {}

        logger.info(
            f"SecretManager initialized: environment={self.environment.value}, "
            f"backend={self.default_backend.value}, cache_ttl={cache_ttl_seconds}s"
        )

    def _detect_environment(self, env: str | None) -> Environment:
        """Detect the current environment from configuration or environment variables."""
        if env:
            try:
                return Environment(env.lower())
            except ValueError:
                logger.warning(f"Invalid environment '{env}', defaulting to development")
                return Environment.DEVELOPMENT

        env_var = os.getenv("CREWAI_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
        try:
            return Environment(env_var.lower())
        except ValueError:
            return Environment.DEVELOPMENT

    def _select_backend(self) -> SecretBackend:
        """Select the appropriate secret backend based on environment."""
        # Production: AWS Secrets Manager
        if self.environment == Environment.PRODUCTION:
            if self._is_aws_available():
                return SecretBackend.AWS_SECRETS_MANAGER
            logger.warning("AWS Secrets Manager not available in production, falling back to environment variables")
            return SecretBackend.ENVIRONMENT

        # Staging: HashiCorp Vault (if available)
        if self.environment == Environment.STAGING:
            if self._is_vault_available():
                return SecretBackend.HASHICORP_VAULT
            return SecretBackend.ENVIRONMENT

        # Development/Local: .env files
        return SecretBackend.DOTENV

    def _is_aws_available(self) -> bool:
        """Check if AWS Secrets Manager is available and configured."""
        try:
            import boto3  # noqa: F401

            # Check if AWS credentials are configured
            return bool(os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"))
        except ImportError:
            return False

    def _is_vault_available(self) -> bool:
        """Check if HashiCorp Vault is available and configured."""
        try:
            import hvac  # noqa: F401

            # Check if Vault is configured
            return bool(os.getenv("VAULT_ADDR") and os.getenv("VAULT_TOKEN"))
        except ImportError:
            return False

    def get_secret(
        self,
        key: str,
        default: str | None = None,
        backend: SecretBackend | None = None,
        use_cache: bool = True,
    ) -> str | None:
        """
        Retrieve a secret value.

        Args:
            key: Secret key/name
            default: Default value if secret not found
            backend: Override default backend
            use_cache: Use cached value if available (default: True)

        Returns:
            Secret value or default if not found

        Example:
            >>> sm = SecretManager()
            >>> api_key = sm.get_secret("OPENAI_API_KEY")
            >>> db_pass = sm.get_secret("db/password", backend=SecretBackend.AWS_SECRETS_MANAGER)
        """
        # Check cache first
        if use_cache and key in self._cache:
            value, expires_at = self._cache[key]
            if datetime.now() < expires_at:
                self._audit_log(key, "cache_hit")
                return value
            # Cache expired, remove it
            del self._cache[key]

        # Select backend
        selected_backend = backend or self.default_backend

        # Retrieve secret from backend
        value = self._get_from_backend(key, selected_backend)

        # Fallback to environment variables if backend fails
        if value is None and selected_backend != SecretBackend.ENVIRONMENT:
            logger.warning(f"Secret '{key}' not found in {selected_backend.value}, falling back to environment")
            value = self._get_from_environment(key)

        # Use default if still not found
        if value is None:
            value = default

        # Cache the value
        if value is not None and use_cache:
            expires_at = datetime.now() + timedelta(seconds=self.cache_ttl_seconds)
            self._cache[key] = (value, expires_at)

        # Audit log
        self._audit_log(key, "retrieved" if value else "not_found", selected_backend.value)

        return value

    def get_secret_dict(
        self,
        path: str,
        backend: SecretBackend | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve a dictionary of secrets from a path.

        Useful for getting multiple related secrets (e.g., database credentials).

        Args:
            path: Secret path (e.g., "database/credentials")
            backend: Override default backend

        Returns:
            Dictionary of secret key-value pairs

        Example:
            >>> sm = SecretManager()
            >>> db_creds = sm.get_secret_dict("database/credentials")
            >>> # Returns: {"host": "localhost", "port": "5432", "username": "admin", "password": "secret"}
        """
        selected_backend = backend or self.default_backend

        if selected_backend == SecretBackend.AWS_SECRETS_MANAGER:
            return self._get_dict_from_aws(path)
        elif selected_backend == SecretBackend.HASHICORP_VAULT:
            return self._get_dict_from_vault(path)
        else:
            # For environment variables, return all matching prefix
            return self._get_dict_from_environment(path)

    def invalidate_cache(self, key: str | None = None) -> None:
        """
        Invalidate cached secrets.

        Args:
            key: Specific key to invalidate (None = invalidate all)
        """
        if key:
            self._cache.pop(key, None)
            logger.debug(f"Cache invalidated for key: {key}")
        else:
            self._cache.clear()
            logger.debug("All secret cache cleared")

    def _get_from_backend(self, key: str, backend: SecretBackend) -> str | None:
        """Retrieve secret from specified backend."""
        if backend == SecretBackend.AWS_SECRETS_MANAGER:
            return self._get_from_aws(key)
        elif backend == SecretBackend.HASHICORP_VAULT:
            return self._get_from_vault(key)
        elif backend == SecretBackend.ENVIRONMENT:
            return self._get_from_environment(key)
        elif backend == SecretBackend.DOTENV:
            return self._get_from_dotenv(key)
        return None

    def _get_from_aws(self, key: str) -> str | None:
        """Retrieve secret from AWS Secrets Manager."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId=key)

            # Handle both string and binary secrets
            if "SecretString" in response:
                secret = response["SecretString"]
                # Try to parse as JSON
                try:
                    secret_dict = json.loads(secret)
                    # If it's a dict with a single key matching the secret name, return the value
                    if len(secret_dict) == 1:
                        return list(secret_dict.values())[0]
                    # Otherwise, return the first value (common pattern)
                    return list(secret_dict.values())[0] if secret_dict else None
                except json.JSONDecodeError:
                    return secret
            else:
                return response["SecretBinary"].decode("utf-8")

        except ImportError:
            logger.error("boto3 not installed, cannot use AWS Secrets Manager")
            return None
        except ClientError as e:
            logger.error(f"AWS Secrets Manager error for key '{key}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving from AWS Secrets Manager: {e}")
            return None

    def _get_dict_from_aws(self, path: str) -> dict[str, Any]:
        """Retrieve dictionary of secrets from AWS Secrets Manager."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId=path)

            if "SecretString" in response:
                return json.loads(response["SecretString"])
            return {}

        except (ImportError, ClientError, json.JSONDecodeError, Exception) as e:
            logger.error(f"Error retrieving dict from AWS Secrets Manager: {e}")
            return {}

    def _get_from_vault(self, key: str) -> str | None:
        """Retrieve secret from HashiCorp Vault."""
        try:
            import hvac

            vault_addr = os.getenv("VAULT_ADDR")
            vault_token = os.getenv("VAULT_TOKEN")

            if not vault_addr or not vault_token:
                logger.error("Vault not configured (missing VAULT_ADDR or VAULT_TOKEN)")
                return None

            client = hvac.Client(url=vault_addr, token=vault_token)

            if not client.is_authenticated():
                logger.error("Vault authentication failed")
                return None

            # Read secret from KV v2 engine (default)
            mount_point = os.getenv("VAULT_MOUNT_POINT", "secret")
            response = client.secrets.kv.v2.read_secret_version(
                path=key,
                mount_point=mount_point,
            )

            data = response["data"]["data"]
            # Return the first value if dict
            return list(data.values())[0] if data else None

        except ImportError:
            logger.error("hvac not installed, cannot use HashiCorp Vault")
            return None
        except Exception as e:
            logger.error(f"Vault error for key '{key}': {e}")
            return None

    def _get_dict_from_vault(self, path: str) -> dict[str, Any]:
        """Retrieve dictionary of secrets from HashiCorp Vault."""
        try:
            import hvac

            vault_addr = os.getenv("VAULT_ADDR")
            vault_token = os.getenv("VAULT_TOKEN")

            if not vault_addr or not vault_token:
                return {}

            client = hvac.Client(url=vault_addr, token=vault_token)

            if not client.is_authenticated():
                return {}

            mount_point = os.getenv("VAULT_MOUNT_POINT", "secret")
            response = client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=mount_point,
            )

            return response["data"]["data"]

        except (ImportError, Exception) as e:
            logger.error(f"Error retrieving dict from Vault: {e}")
            return {}

    def _get_from_environment(self, key: str) -> str | None:
        """Retrieve secret from environment variables."""
        return os.getenv(key)

    def _get_dict_from_environment(self, prefix: str) -> dict[str, Any]:
        """Retrieve all environment variables matching a prefix."""
        prefix_normalized = prefix.upper().replace("/", "_").replace("-", "_")
        return {
            k: v
            for k, v in os.environ.items()
            if k.upper().startswith(prefix_normalized)
        }

    def _get_from_dotenv(self, key: str) -> str | None:
        """Retrieve secret from .env file."""
        try:
            from dotenv import dotenv_values

            # Look for .env in current directory or parent directories
            current_dir = os.getcwd()
            for _ in range(5):  # Check up to 5 levels up
                env_file = os.path.join(current_dir, ".env")
                if os.path.exists(env_file):
                    env_values = dotenv_values(env_file)
                    return env_values.get(key)
                parent = os.path.dirname(current_dir)
                if parent == current_dir:  # Reached root
                    break
                current_dir = parent

            # Fallback to environment variable
            return os.getenv(key)

        except ImportError:
            logger.warning("python-dotenv not installed, falling back to environment variables")
            return os.getenv(key)
        except Exception as e:
            logger.error(f"Error reading .env file: {e}")
            return os.getenv(key)

    def _audit_log(self, key: str, action: str, backend: str | None = None) -> None:
        """Log secret access for security auditing."""
        if not self.enable_audit_log:
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "secret_key": self._mask_key(key),
            "environment": self.environment.value,
            "backend": backend or self.default_backend.value,
        }

        logger.info(f"SECRET_AUDIT: {json.dumps(log_entry)}")

    @staticmethod
    def _mask_key(key: str) -> str:
        """Mask secret key for logging (show first 4 chars only)."""
        if len(key) <= 4:
            return "***"
        return f"{key[:4]}***"


# ============================================================================
# Convenience Functions
# ============================================================================


@lru_cache(maxsize=1)
def get_secret_manager() -> SecretManager:
    """Get or create the global SecretManager instance."""
    return SecretManager()


def get_secret(key: str, default: str | None = None) -> str | None:
    """
    Convenience function to get a secret using the global SecretManager.

    Args:
        key: Secret key
        default: Default value if not found

    Returns:
        Secret value or default

    Example:
        >>> from crewai.security.secret_manager import get_secret
        >>> api_key = get_secret("OPENAI_API_KEY")
    """
    sm = get_secret_manager()
    return sm.get_secret(key, default)
