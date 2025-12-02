# ============================================================================
# Multi-stage Dockerfile for Cloud Optimizer
# Optimized for production deployment with security and size in mind
# ============================================================================

# ============================================================================
# Stage 1 - Builder: Build dependencies in an isolated image
# ============================================================================
FROM python:3.11-slim AS builder

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml README.md ./

# Copy source code
COPY src/ src/

# Install application and dependencies to /install prefix
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefix=/install .

# ============================================================================
# Stage 2 - Runtime: Minimal runtime image
# ============================================================================
FROM python:3.11-slim AS runtime

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user with specific UID for security
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application files
COPY --chown=appuser:appuser src/ src/
COPY --chown=appuser:appuser alembic/ alembic/
COPY --chown=appuser:appuser alembic.ini .

# Create data directory for compliance files (if needed in future)
RUN mkdir -p data/compliance && chown -R appuser:appuser data/

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8000

# Health check using the health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Use entrypoint script for startup
ENTRYPOINT ["python", "-m", "cloud_optimizer.entrypoint"]
