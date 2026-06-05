# EnMS OVOS Skill - Energy Management Voice Assistant

[![License: Apache-2.0 OR GPL-3.0-or-later](https://img.shields.io/badge/License-Apache--2.0%20OR%20GPL--3.0--or--later-blue.svg)](./RELEASE_LICENSE.md)
[![OVOS](https://img.shields.io/badge/OVOS-Compatible-green.svg)](https://openvoiceos.github.io/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

HumanEnerDIA is an OVOS skill for industrial energy management and ISO 50001
workflows. It connects an OVOS runtime to a reachable HumanEnerDIA/EnMS
analytics API so operators can ask about machine status, power, energy,
anomalies, forecasts, KPIs, reports, and action-plan context.

## What This ZIP Includes

- OVOS skill package
- REST bridge source under `bridge/`
- safe configuration templates
- tests and helper scripts
- WASABI release license

The ZIP does not include the HumanEnerDIA backend, a full OVOS runtime, Docker
volumes, local credentials, logs, caches, or optional GGUF model files.

## Requirements

- Python 3.10+
- Open Voice OS compatible runtime and messagebus
- HumanEnerDIA/EnMS analytics API endpoint
- Optional `Qwen3.5-2B-Q4_K_M.gguf` for Tier-3 local LLM fallback

For a clean-machine OVOS runtime experiment, use the companion repository:

```bash
git clone https://github.com/RaptorBlingx/ovos-llm.git
cd ovos-llm
cp .env.example .env
sed -i 's|^ENMS_API_URL=.*|ENMS_API_URL=http://host.docker.internal:8001/api/v1|' .env
docker network create enms-network || true
docker compose build
docker compose up -d
```

## Install Into Existing OVOS

From the extracted WASABI ZIP directory:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Create or edit the OVOS skill settings used by your runtime:

```json
{
  "enms_api_base_url": "http://your-enms-server:8001/api/v1",
  "api_timeout_seconds": 30,
  "confidence_threshold": 0.85
}
```

Start the OVOS runtime and REST bridge for that installation, then smoke test:

```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"text":"what is the power of compressor one","session_id":"skill-smoke"}'
```

Expected result: the bridge returns `success: true` and a response about
`Compressor-1` or a matching machine-status result.

## Voice Commands

Energy queries:

- "What's the power consumption of Compressor-1?"
- "How much energy did Boiler-1 use yesterday?"
- "Total factory energy consumption"
- "Show me energy for the last 24 hours"

Machine status:

- "Is HVAC-Main running?"
- "What's the status of Compressor-1?"
- "Check all machines"

Analysis:

- "Top 3 energy consumers"
- "Compare Compressor-1 and Boiler-1"
- "Detect anomalies for Compressor-1 today"

Forecasting:

- "Forecast energy for tomorrow"
- "Predicted consumption for next week"
- "What's the expected energy usage?"

## Architecture

```text
Portal/User -> REST Bridge -> OVOS Messagebus -> EnmsSkill
                                                     |
                                                     v
                                      HybridParser (3-tier NLU)
                                      |        |        |
                                      v        v        v
                                 Heuristic   Adapt   Qwen3.5-2B
                                                     fallback
                                      |
                                      v
                              Validator -> EnMS Analytics API
```

## Performance

- Fast-path queries: sub-second live responses for standard operational
  requests
- Intent detection: heuristic and Adapt routing normally stay in the 1-10 ms
  range
- LLM fallback: multi-second when a request escalates to Qwen3.5-2B
- Heuristic tier: handles most routine operational queries

## Project Structure

```text
enms-ovos-skill/
├── enms_ovos_skill/
│   ├── __init__.py
│   ├── lib/
│   └── locale/
├── bridge/
├── scripts/
├── setup.py
├── skill.json
└── RELEASE_LICENSE.md
```

## License

The WASABI release artifact is licensed under
`Apache-2.0 OR GPL-3.0-or-later`. The existing repository license file is
preserved for historical GPL distribution context; see
[`RELEASE_LICENSE.md`](./RELEASE_LICENSE.md) for the release grant used for
WASABI shop distribution.
