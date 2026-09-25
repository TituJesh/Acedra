# ==============================================================================
# Production Dockerfile for Acedra
# Multi-stage optimized, unprivileged non-root container for AWS ECS / EC2
# ==============================================================================

FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install curl for container healthcheck probe and clean apt cache
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged system user and group for container security hardening
RUN groupadd -r appuser && useradd -r -g appuser -u 10001 -d /app appuser

WORKDIR /app

# Install Python dependencies and gunicorn for production worker management
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application source code with non-root ownership
COPY --chown=appuser:appuser . .

# Switch to unprivileged user
USER appuser

# Expose API port
EXPOSE 8000

# Container liveness health check targeting the /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command using Gunicorn with Uvicorn workers
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]
