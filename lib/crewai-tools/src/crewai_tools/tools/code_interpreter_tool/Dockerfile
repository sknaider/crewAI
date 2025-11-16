# ============================================================================
# CrewAI Code Interpreter Tool - Enterprise-Grade Dockerfile
# ============================================================================
# Multi-stage build for optimal security and minimal image size
# Features:
# - Non-root user execution
# - Pinned dependency versions
# - Health checks
# - Security scanning metadata
# - Minimal attack surface
# ============================================================================

# ============================================================================
# Stage 1: Builder - Build and install dependencies
# ============================================================================
FROM python:3.12-alpine AS builder

# Metadata for security scanning and compliance
LABEL org.opencontainers.image.title="CrewAI Code Interpreter Tool" \
      org.opencontainers.image.description="Secure code interpreter tool for CrewAI" \
      org.opencontainers.image.version="1.5.0" \
      org.opencontainers.image.vendor="CrewAI" \
      org.opencontainers.image.authors="CrewAI Team <support@crewai.com>" \
      security.scan="required" \
      security.non-root="true"

# Install build dependencies
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

# Create non-root user and group
RUN addgroup -g 1001 -S appuser && \
    adduser -u 1001 -S appuser -G appuser

# Set working directory
WORKDIR /tmp/build

# Copy requirements with pinned versions
COPY requirements.txt .

# Install Python dependencies with pinned versions
# Note: In production, replace with actual requirements.txt or use Poetry/uv
RUN pip install --no-cache-dir --upgrade pip==24.3.1 && \
    pip install --no-cache-dir \
        requests==2.32.3 \
        beautifulsoup4==4.12.3 \
        lxml==5.3.0 \
        charset-normalizer==3.3.2

# Remove build dependencies
RUN apk del .build-deps

# ============================================================================
# Stage 2: Runtime - Minimal runtime image
# ============================================================================
FROM python:3.12-alpine

# Metadata
LABEL org.opencontainers.image.title="CrewAI Code Interpreter Tool" \
      org.opencontainers.image.version="1.5.0" \
      security.scan="required"

# Install runtime dependencies only
RUN apk add --no-cache \
    libffi \
    openssl \
    ca-certificates && \
    rm -rf /var/cache/apk/*

# Create non-root user (matching builder stage)
RUN addgroup -g 1001 -S appuser && \
    adduser -u 1001 -S appuser -G appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set working directory
WORKDIR /workspace

# Change ownership to non-root user
RUN chown -R appuser:appuser /workspace

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Health check - verify Python runtime is working
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; import requests; import bs4; sys.exit(0)" || exit 1

# Security: Run with read-only filesystem (mount /workspace as volume)
# docker run --read-only -v /path/to/data:/workspace crewai-code-interpreter

# Default command
CMD ["python", "--version"]
