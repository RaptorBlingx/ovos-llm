# OVOS EnMS Skill - Headless Docker Image
# Production deployment for Energy Management Voice Assistant
# No audio hardware dependencies - REST API only

FROM python:3.10-slim-bookworm

LABEL maintainer="EnMS Team"
LABEL description="OVOS Voice Assistant for Energy Management System - Headless Mode"
LABEL version="1.0.0"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies (minimal - no audio packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 ovos && \
    mkdir -p /app /models /config && \
    chown -R ovos:ovos /app /models /config

# Copy requirements first for better layer caching
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY enms-ovos-skill/ /app/

# Switch to non-root user
USER ovos

# Environment variables with defaults
ENV ENMS_API_URL=http://localhost:8001/api/v1
ENV OVOS_BRIDGE_PORT=5000
ENV OVOS_TTS_ENABLED=true
ENV OVOS_TTS_ENGINE=edge-tts
ENV OVOS_TTS_VOICE=en-US-GuyNeural
ENV LOG_LEVEL=INFO
ENV LLM_MODEL_PATH=/models/Qwen_Qwen3-1.7B-Q4_K_M.gguf

# Expose REST API port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Default command - run the headless REST bridge
CMD ["python", "bridge/ovos_headless_bridge.py"]
