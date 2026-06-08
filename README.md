# HumanEnerDIA OVOS Skill

This package is the OVOS assistant layer for HumanEnerDIA. It lets users ask
natural-language questions such as machine status, power, energy, anomalies,
forecasts, KPIs, and ISO 50001 context.

It is not the HumanEnerDIA backend. The assistant must connect to a reachable
HumanEnerDIA analytics API.

## Which Product Do I Need?

- Use `HumanEnerDIA-full-stack-v1.0.0` when you want the whole system:
  portal, database, analytics, Grafana, simulator, and embedded OVOS runtime.
- Use `HumanEnerDIA-OVOS-skill-v1.0.0` when HumanEnerDIA is already running
  somewhere and you want to run only the OVOS assistant layer.
- Use the skill-only install path only if you already operate your own OVOS
  runtime and messagebus.

## What This Bundle Includes

- Headless OVOS runtime Docker image definition
- Docker Compose service for the OVOS messagebus, skill runtime, and REST bridge
- HumanEnerDIA OVOS skill source under `enms-ovos-skill/`
- REST bridge at `http://localhost:5000`
- Safe `.env.example`, install guide, and release license

The bundle excludes HumanEnerDIA backend services, live `.env` files, logs,
caches, tests, internal development documents, and optional GGUF model weights.

## Quick Start

Extract the Wasabi ZIP:

```bash
unzip HumanEnerDIA-OVOS-skill-v1.0.0.zip
cd HumanEnerDIA-OVOS-skill-v1.0.0
```

Run OVOS against a HumanEnerDIA backend:

```bash
./setup.sh --enms-api-url http://<humanerdia-host>:8001/api/v1
```

Common backend URL choices:

```bash
# HumanEnerDIA on another machine
./setup.sh --enms-api-url http://192.168.1.50:8001/api/v1

# HumanEnerDIA on this same laptop
./setup.sh --enms-api-url http://host.docker.internal:8001/api/v1

# HumanEnerDIA on the same Docker network
./setup.sh --enms-api-url http://enms-analytics:8001/api/v1 --network enms-network

# If port 5000 is already used
./setup.sh --enms-api-url http://192.168.1.50:8001/api/v1 --bridge-port 5500
```

## Verify

```bash
curl -fsS http://localhost:5000/health

curl -sS -X POST http://localhost:5000/query \
  -H 'Content-Type: application/json' \
  -d '{"text":"what is the power of compressor one","session_id":"ovos-smoke"}'
```

Expected result:

- health reports `"status":"healthy"`
- `messagebus_connected` is `true`
- the query returns `"success":true`
- the response mentions `Compressor-1` or another matching backend machine

## Integration Model

```text
User / Portal / API client
        |
        v
OVOS REST bridge (:5000)
        |
        v
OVOS messagebus (:8181)
        |
        v
HumanEnerDIA OVOS skill
        |
        v
HumanEnerDIA analytics API (:8001/api/v1)
```

The REST bridge does not answer energy questions by itself. It forwards the
query into OVOS, the skill parses and validates it, and the skill calls the
HumanEnerDIA analytics API.

## Existing OVOS Runtime

If you already operate OVOS and only want the skill package:

```bash
cd enms-ovos-skill
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Configure your OVOS skill settings with:

```json
{
  "enms_api_base_url": "http://<humanerdia-host>:8001/api/v1",
  "api_timeout_seconds": 30,
  "confidence_threshold": 0.85
}
```

Restart OVOS, then test through your runtime's messagebus or bridge.

## Example Questions

- "What is the power of Compressor-1?"
- "Is HVAC-Main running?"
- "How much energy did Boiler-1 use yesterday?"
- "Show me the top three energy consumers."
- "Any anomalies today?"
- "What is tomorrow's energy forecast?"
- "Give me a factory overview."

## Optional LLM Fallback

The default release uses fast heuristic and Adapt routing. It does not include
large GGUF model files.

If you want local LLM fallback, place `Qwen3.5-2B-Q4_K_M.gguf` under
`enms-ovos-skill/models/`, build with `INSTALL_LLM_FALLBACK=true`, and expect
fallback queries to be slower than the standard fast path.

## More Detail

Read `INSTALL.md` for step-by-step deployment, cleanup, and existing-OVOS
installation instructions.

## License

The Wasabi release artifact is licensed under
`Apache-2.0 OR GPL-3.0-or-later`. See
`enms-ovos-skill/RELEASE_LICENSE.md`.
