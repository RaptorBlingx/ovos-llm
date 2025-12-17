# OVOS EnMS Skill - Full OVOS Integration
# Production deployment with OVOS messagebus and skill framework
# Headless mode (no wake word/audio hardware required)

FROM python:3.10-slim-bookworm

LABEL maintainer="A Plus Engineering"
LABEL description="OVOS Energy Management Skill - ISO 50001 Voice Assistant"
LABEL version="1.0.0"
LABEL license="GPL-3.0"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies (including swig and libfann for Padatious neural networks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    curl \
    supervisor \
    swig \
    libfann-dev \
    && rm -rf /var/lib/apt/lists/*

# Create directories with proper structure
RUN mkdir -p /opt/ovos/skills \
             /var/log/ovos \
             /var/log/supervisor \
             /config \
             /models \
             /tmp/mycroft

# Create non-root user for security
RUN useradd -m -u 1000 ovos && \
    chown -R ovos:ovos /opt/ovos /var/log/ovos /var/log/supervisor /app /config /models /tmp/mycroft

# Copy requirements first for better layer caching
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy OVOS configuration
COPY ovos.conf /config/ovos.conf
ENV XDG_CONFIG_HOME=/config

# Copy skill source (for installation)
COPY enms-ovos-skill/ /tmp/enms-ovos-skill/

# Install the skill as a Python package
RUN cd /tmp/enms-ovos-skill && \
    pip install --no-cache-dir -e . && \
    mkdir -p /opt/ovos/skills && \
    ln -s /tmp/enms-ovos-skill /opt/ovos/skills/enms-ovos-skill

# Copy bridge code (REST API gateway to messagebus)
COPY enms-ovos-skill/bridge/ /app/bridge/

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set ownership
RUN chown -R ovos:ovos /opt/ovos /app /config /var/log/ovos /var/log/supervisor /tmp/mycroft /tmp/enms-ovos-skill

# Switch to non-root user
USER ovos

# Environment variables with defaults
ENV ENMS_API_URL=http://host.docker.internal:8001/api/v1
ENV OVOS_BRIDGE_PORT=5000
ENV OVOS_TTS_ENABLED=true
ENV LOG_LEVEL=INFO
ENV OVOS_CONFIG_PATH=/config/ovos.conf

# Expose ports
EXPOSE 5000 8181

# Health check - check both bridge and messagebus
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/health && curl -f http://localhost:8181/core || exit 1

# Default command - run supervisor to manage all services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
