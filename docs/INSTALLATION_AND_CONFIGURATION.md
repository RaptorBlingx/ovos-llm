# OVOS-EnMS Installation and Configuration

This guide covers deployment of the HumanEnerDIA OVOS runtime and skill.

## Requirements

- Docker Engine 20.10+
- Docker Compose v2
- HumanEnerDIA-compatible analytics API reachable from the OVOS container
- Docker network access to the HumanEnerDIA stack, usually `enms-network`, or
  network access to a third-party EnMS adapter/proxy
- Linux server recommended for deployment

## Docker Deployment

1. Clone the repository:

   ```bash
   git clone https://github.com/RaptorBlingx/ovos-prod.git
   cd ovos-prod
   ```

2. Create environment file:

   ```bash
   cp .env.example .env
   ```

3. Set the compatible backend API URL in `.env`.

   For the same Docker network as HumanEnerDIA:

   ```env
   ENMS_API_URL=http://enms-analytics:8001/api/v1
   ```

   For a backend on the host:

   ```env
   ENMS_API_URL=http://host.docker.internal:8001/api/v1
   ```

   For a third-party EnMS adapter/proxy:

   ```env
   ENMS_API_URL=http://adapter-host:8001/api/v1
   ```

4. Ensure the network exists:

   ```bash
   docker network create enms-network || true
   ```

5. Build and start:

   ```bash
   docker compose build
   docker compose up -d
   ```

6. Verify:

   ```bash
   docker compose ps
   curl -fsS http://localhost:5000/health
   ```

## Runtime Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | Bridge metadata |
| `GET /health` | REST bridge and messagebus health |
| `POST /query` | Text query endpoint |
| `POST /query/voice` | Alias for `/query` used by voice integrations |
| `GET /docs` | FastAPI OpenAPI UI |

Default exposed ports:

- `5000`: REST bridge
- `8181`: OVOS messagebus

## Important Environment Values

| Variable | Default | Meaning |
|---|---|---|
| `ENMS_API_URL` | `http://host.docker.internal:8001/api/v1` | HumanEnerDIA-compatible analytics API |
| `LLM_MODEL_DIR` | `./enms-ovos-skill/models` | Local model directory |
| `OVOS_TTS_ENABLED` | `true` | Enable spoken responses |
| `OVOS_TTS_ENGINE` | `edge-tts` | TTS engine hint |
| `OVOS_TTS_VOICE` | `en-US-GuyNeural` | TTS voice hint |
| `LOG_LEVEL` | `INFO` | Runtime log level |

The Dockerfile also uses:

- `OVOS_BRIDGE_PORT=5000`
- `STRUCTURED_RESPONSE_GRACE_SECONDS=2.5`
- `OVOS_CONFIG_PATH=/config/mycroft/mycroft.conf`

## Skill Settings

The source skill settings live in:

- `enms-ovos-skill/settings.json`
- `enms-ovos-skill/settings.docker.json`
- `enms-ovos-skill/config.yaml.template`

Main settings:

```json
{
  "enms_api_base_url": "http://localhost:8001/api/v1",
  "llm_model_path": "./models/Qwen3.5-2B-Q4_K_M.gguf",
  "confidence_threshold": 0.85,
  "enable_progress_feedback": true,
  "progress_threshold_ms": 500
}
```

In Docker, prefer `ENMS_API_URL` for the compatible backend URL. For a
third-party EnMS, see [EnMS API Compatibility](./ENMS_API_COMPATIBILITY.md).

## Optional LLM Fallback

The base build does not install the local LLM dependencies unless the build arg
is enabled:

```bash
docker compose build --build-arg INSTALL_LLM_FALLBACK=true
```

The GGUF model file is not bundled. See
[LLM Fallback Model Guide](./LLM_FALLBACK_MODEL_GUIDE.md).

## Manual Skill Installation

For development or non-Docker OVOS environments:

```bash
cd enms-ovos-skill
pip install -e .
```

Then configure the OVOS skill settings for your deployment.

## Screenshot Placeholders

- `docs/images/operations/docker-compose-ps.png`
- `docs/images/operations/bridge-health.png`
