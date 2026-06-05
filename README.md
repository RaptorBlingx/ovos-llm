# OVOS-EnMS

OVOS integration for HumanEnerDIA and compatible industrial energy management
backends.

This package provides the OVOS skill, REST bridge, Docker deployment, and
runtime configuration used to query energy data through natural language.

[![OVOS](https://img.shields.io/badge/OVOS-compatible-green.svg)](https://openvoiceos.org/)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](docker-compose.yml)

## Overview

OVOS-EnMS provides a voice and API layer for energy management systems. The
default adapter targets HumanEnerDIA, and the adapter layer makes it possible
to support additional backends without rewriting the skill.

The stack includes:

- an OVOS skill for machine, factory, KPI, forecast, and anomaly queries
- a REST bridge for web clients and external integrations
- Docker-based deployment for headless Linux environments
- an optional local Qwen GGUF fallback model for harder queries

## Features

- natural-language energy and machine-status queries
- multi-tier intent routing with heuristic, Adapt, and optional LLM fallback
- fuzzy machine matching for spoken or loosely typed equipment names
- structured validation before backend API execution
- response formatting tuned for voice output and chat-style integrations
- support for factory-wide summaries, KPIs, forecasts, reports, and comparisons

## Architecture

```text
Portal / Client / CLI
        |
        v
REST Bridge (port 5000)
        |
        v
OVOS Messagebus + OVOS Core
        |
        v
HumanEnerDIA OVOS Skill
        |
        v
EnMS API
```

## Quick Start

### Requirements

- Docker Engine 20.10+
- Docker Compose v2
- a reachable EnMS API endpoint
- Linux host recommended for deployment

### Run with Docker

```bash
git clone https://github.com/RaptorBlingx/ovos-llm.git
cd ovos-llm
cp .env.example .env
docker network create enms-network || true
docker compose build
docker compose up -d
```

### Default local endpoints

- REST bridge: `http://localhost:5000`
- Health check: `http://localhost:5000/health`
- OVOS messagebus: `ws://localhost:8181/core`

### Smoke test

```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"text":"What is the status of Compressor-1?"}'
```

## Skill Installation Without Docker

```bash
git clone https://github.com/RaptorBlingx/ovos-llm.git
cd ovos-llm/enms-ovos-skill
pip install -e .
```

Create or edit `~/.config/ovos/skills/enms-ovos-skill/settings.json`:

```json
{
  "enms_api_base_url": "http://your-enms-server:8001/api/v1",
  "llm_model_path": "./models/Qwen3.5-2B-Q4_K_M.gguf",
  "confidence_threshold": 0.85,
  "api_timeout_seconds": 30
}
```

## Configuration

Root environment settings live in `.env.example`.

Common values:

- `ENMS_API_URL`: backend API base URL
- `LLM_MODEL_DIR`: directory for optional GGUF fallback models
- `OVOS_TTS_ENABLED`: enable or disable spoken responses
- `LOG_LEVEL`: runtime log verbosity

The Docker deployment expects an `enms-network` Docker network so the OVOS
container can reach the HumanEnerDIA stack by service name.

## Example Queries

- "What is the status of Compressor-1?"
- "How much energy did Boiler-1 use yesterday?"
- "Show me the top three energy consumers."
- "What is tomorrow's forecast?"
- "Give me a factory overview."

## Package Layout

```text
ovos-llm/
├── enms-ovos-skill/      # OVOS skill package
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── ovos.conf
├── setup.sh
└── supervisord.conf
```

## License

See [enms-ovos-skill/LICENSE](enms-ovos-skill/LICENSE) and
[enms-ovos-skill/RELEASE_LICENSE.md](enms-ovos-skill/RELEASE_LICENSE.md).
