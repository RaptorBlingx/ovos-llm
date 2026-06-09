# HumanEnerDIA OVOS Skill Installation

This product runs only the OVOS assistant layer. It does not include the
HumanEnerDIA portal, database, analytics service, simulator, or Grafana.

Use it when you already have a HumanEnerDIA backend, or a
HumanEnerDIA-compatible adapter/proxy for another EnMS, and you want a separate
OVOS runtime to answer natural-language questions against that API.

## What You Need

- Docker Engine 20.10+ and Docker Compose v2
- Network access to a HumanEnerDIA-compatible analytics API
- The analytics API URL, usually one of:
  - `http://<enms-host>:8001/api/v1`
  - `http://host.docker.internal:8001/api/v1`
  - `http://enms-analytics:8001/api/v1` when sharing the HumanEnerDIA Docker network

If you do not already have a HumanEnerDIA backend, install
`HumanEnerDIA-EnMS-v1.0.0` for the backend-only product, install the full-stack
product for EnMS plus embedded OVOS, or provide a compatibility adapter in
front of your own EnMS. See `docs/ENMS_API_COMPATIBILITY.md`.

## Clean OVOS-Only Run

Extract the Wasabi ZIP:

```bash
unzip HumanEnerDIA-OVOS-skill-v1.0.0.zip
cd HumanEnerDIA-OVOS-skill-v1.0.0
```

Start OVOS and point it at your HumanEnerDIA-compatible backend:

```bash
./setup.sh --enms-api-url http://<humanerdia-host>:8001/api/v1
```

For the standalone EnMS product running on another machine:

```bash
./setup.sh --enms-api-url http://<enms-host>:8001/api/v1
```

For a third-party EnMS, use the URL of your adapter/proxy:

```bash
./setup.sh --enms-api-url http://<adapter-host>:8001/api/v1
```

For a HumanEnerDIA stack running on the same laptop but outside this Compose
project:

```bash
./setup.sh --enms-api-url http://host.docker.internal:8001/api/v1
```

For a HumanEnerDIA stack running on the same Docker network:

```bash
./setup.sh --enms-api-url http://enms-analytics:8001/api/v1 --network enms-network
```

If port `5000` is already used:

```bash
./setup.sh --enms-api-url http://<humanerdia-host>:8001/api/v1 --bridge-port 5500
```

On the EnMS side, configure the optional portal voice proxy to call this OVOS
bridge:

```bash
cd HumanEnerDIA-EnMS-v1.0.0
./setup.sh --ovos-bridge-host <ovos-host> --ovos-bridge-port 5000
```

## Verify

```bash
curl -fsS http://localhost:5000/health

curl -sS -X POST http://localhost:5000/query \
  -H 'Content-Type: application/json' \
  -d '{"text":"what is the power of compressor one","session_id":"ovos-release-smoke"}'
```

Expected result:

- `/health` returns JSON with `"status":"healthy"` and `"messagebus_connected":true`
- `/query` returns `"success":true`
- the response mentions `Compressor-1` or a matching backend machine

## Install Into An Existing OVOS Runtime

Use this path only if you already operate OVOS yourself and do not want the
included Docker runtime.

```bash
cd HumanEnerDIA-OVOS-skill-v1.0.0/enms-ovos-skill
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Configure the skill in your OVOS runtime settings:

```json
{
  "enms_api_base_url": "http://<humanerdia-compatible-host>:8001/api/v1",
  "api_timeout_seconds": 30,
  "confidence_threshold": 0.85
}
```

Then restart OVOS and send a query through your OVOS messagebus or bridge.

## Optional LLM Fallback

The default release uses fast heuristic and Adapt routing. It does not include
GGUF model weights.

To enable the optional local fallback parser, place
`Qwen3.5-2B-Q4_K_M.gguf` under `enms-ovos-skill/models/`, set
`INSTALL_LLM_FALLBACK=true` during image build, and rebuild:

```bash
docker compose build --build-arg INSTALL_LLM_FALLBACK=true ovos
docker compose up -d
```

## Clean Reinstall

From the extracted OVOS bundle:

```bash
docker compose down -v --remove-orphans || true
docker rm -f ovos-enms enms-ovos 2>/dev/null || true
docker volume rm ovos-llm_ovos-logs ovos-llm_supervisor-logs ovos-logs supervisor-logs 2>/dev/null || true
docker network rm enms-network 2>/dev/null || true
docker builder prune -af
```

For a dedicated test laptop where all unused Docker state can be removed:

```bash
docker system prune -af --volumes
docker builder prune -af
```
