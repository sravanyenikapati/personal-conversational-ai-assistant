# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into /install so we can copy to final stage
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Minimal runtime system deps (no audio — server-only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY src/ ./src/
COPY pyproject.toml .

# Install the package itself (no deps, already installed)
RUN pip install --no-deps -e .

# Create data directory for custom agents persistence
RUN mkdir -p /data && chmod 755 /data

# Non-root user for security
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app /data
USER appuser

# Expose port
EXPOSE 8000

# Health check — matches GET /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start the FastAPI server
CMD ["sh", "-c", "uvicorn assistant.api.server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
