# ============================================================================
# Multi-stage Dockerfile for Cloud Optimizer
# Uses Poetry for deterministic, reproducible builds
# ============================================================================

# ============================================================================
# Stage 1 - Builder: Install Poetry and build dependencies
# ============================================================================
FROM python:3.11-slim AS builder

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Poetry configuration - use 2.x to match local development
    POETRY_VERSION=2.1.3 \
    POETRY_HOME=/opt/poetry \
    POETRY_VENV=/opt/poetry-venv \
    POETRY_CACHE_DIR=/opt/.cache \
    POETRY_NO_INTERACTION=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry in isolated environment
RUN python -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==$POETRY_VERSION

ENV PATH="$POETRY_VENV/bin:$PATH"

# Copy dependency files first (for better layer caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies only (no dev dependencies, no root package)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction

# Copy source code and install the package
COPY src/ src/
COPY README.md ./
RUN poetry install --only main --no-interaction

# ============================================================================
# Stage 2 - Runtime: Minimal runtime image
# ============================================================================
FROM python:3.11-slim AS runtime

# Prevent Python from writing .pyc files and buffer stdout/stderr
# Set API_PORT to match EXPOSE and HEALTHCHECK port
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    API_PORT=8000

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
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files
COPY --chown=appuser:appuser src/ src/
COPY --chown=appuser:appuser alembic/ alembic/
COPY --chown=appuser:appuser alembic.ini .

# Create data directory for compliance files
RUN mkdir -p data/compliance && chown -R appuser:appuser data/

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8000

# Health check using the health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Launch the FastAPI app via the Python entrypoint module
ENTRYPOINT ["python", "-m", "cloud_optimizer.entrypoint"]
