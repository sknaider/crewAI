# ============================================================================
# CrewAI Framework - Production-Ready Multi-Service Dockerfile
# ============================================================================
# This Dockerfile supports both the main CrewAI framework and CrewAI Tools
# Optimized for enterprise deployment with security and performance best practices
#
# Build: docker build -t crewai:1.5.0 .
# Run:   docker run -p 8000:8000 -e OPENAI_API_KEY=xxx crewai:1.5.0
# ============================================================================

# ============================================================================
# Build Arguments
# ============================================================================
ARG PYTHON_VERSION=3.12
ARG ALPINE_VERSION=3.19

# ============================================================================
# Stage 1: Dependencies Builder
# ============================================================================
FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS builder

# Build metadata
LABEL stage=builder
LABEL org.opencontainers.image.title="CrewAI Builder"

# Install build dependencies
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    g++ \
    musl-dev \
    libffi-dev \
    openssl-dev \
    postgresql-dev \
    cargo \
    rust \
    git

# Install UV for fast Python package management
RUN pip install --no-cache-dir uv==0.8.4

# Create build directory
WORKDIR /build

# Copy workspace configuration
COPY pyproject.toml uv.lock ./
COPY lib ./lib

# Build all packages
RUN uv build --all-packages

# Install packages to a virtual environment
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install dist/*.whl

# ============================================================================
# Stage 2: Runtime Image
# ============================================================================
FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION}

# Production metadata
LABEL org.opencontainers.image.title="CrewAI Framework" \
      org.opencontainers.image.description="Cutting-edge framework for orchestrating role-playing, autonomous AI agents" \
      org.opencontainers.image.version="1.5.0" \
      org.opencontainers.image.vendor="CrewAI" \
      org.opencontainers.image.authors="Joao Moura <joao@crewai.com>" \
      org.opencontainers.image.url="https://www.crewai.com" \
      org.opencontainers.image.documentation="https://docs.crewai.com" \
      org.opencontainers.image.source="https://github.com/crewAIInc/crewAI" \
      org.opencontainers.image.licenses="MIT" \
      security.scan="required" \
      security.non-root="true" \
      security.read-only-root-filesystem="recommended"

# Install runtime dependencies only
RUN apk add --no-cache \
    libffi \
    openssl \
    ca-certificates \
    libpq \
    sqlite \
    tzdata && \
    rm -rf /var/cache/apk/*

# Create non-root user and group
RUN addgroup -g 1001 -S crewai && \
    adduser -u 1001 -S crewai -G crewai -h /home/crewai

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create application directory structure
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R crewai:crewai /app

# Set working directory
WORKDIR /app

# Switch to non-root user
USER crewai

# Environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CREWAI_HOME=/app/data \
    CREWAI_LOG_DIR=/app/logs

# Expose ports
# 8000: Main API server
# 9090: Prometheus metrics
EXPOSE 8000 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import crewai; import sys; sys.exit(0)" || exit 1

# Volume mounts for persistence
VOLUME ["/app/data", "/app/logs", "/app/config"]

# Default command (can be overridden)
CMD ["python", "-m", "crewai.cli.cli", "--help"]
