# =====================================================================
# Captain Cool — Production Grade Dockerfile (FastAPI + Uvicorn)
# Optimized for Google Cloud Run (GCP)
# =====================================================================

# --- Stage 1: Build Dependencies ---
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Stage 2: Final Run Container ---
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Create a non-privileged system user for absolute security compliance
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

# Copy installed dependencies from Stage 1 builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application source code
COPY --chown=appuser:appgroup server.py .
COPY --chown=appuser:appgroup captain_cool/ ./captain_cool/
COPY --chown=appuser:appgroup frontend/ ./frontend/

USER appuser

EXPOSE 8080

# Execute server under Gunicorn/Uvicorn production configuration
CMD ["python", "server.py"]
