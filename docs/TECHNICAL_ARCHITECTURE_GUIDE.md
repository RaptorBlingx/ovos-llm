# OVOS-EnMS Technical Architecture Guide

This guide explains how the HumanEnerDIA OVOS integration is structured.

## System Context

Screenshot to add:

```text
docs/images/architecture/ovos-architecture.png
```

```text
Client / Portal / Voice UI
        |
        v
REST Bridge (:5000)
        |
        v
OVOS Messagebus (:8181)
        |
        v
OVOS Core + HumanEnerDIA Skill
        |
        v
HumanEnerDIA Analytics API
```

The REST bridge is intentionally thin. It forwards utterances to the OVOS
messagebus and waits for `speak` and `enms.skill.response` events. The skill
contains the domain parsing, validation, API calls, and response formatting.

## Docker Runtime

The Docker image runs three supervised processes:

| Process | Command | Purpose |
|---|---|---|
| `ovos-messagebus` | `python -m ovos_messagebus` | OVOS event bus |
| `ovos-skills` | `python -m ovos_core` | OVOS core and skill runtime |
| `rest-bridge` | `python /app/bridge/ovos_rest_bridge.py` | HTTP gateway |

Supervisor configuration lives in `supervisord.conf`.

## Main Components

| Path | Purpose |
|---|---|
| `enms-ovos-skill/enms_ovos_skill/__init__.py` | Main OVOS skill implementation |
| `enms-ovos-skill/enms_ovos_skill/lib/intent_parser.py` | Heuristic, Adapt, and optional LLM routing |
| `enms-ovos-skill/enms_ovos_skill/lib/adapt_parser.py` | Adapt vocabulary parser |
| `enms-ovos-skill/enms_ovos_skill/lib/validator.py` | Validation and fuzzy matching |
| `enms-ovos-skill/enms_ovos_skill/lib/api_client.py` | HumanEnerDIA-compatible API client |
| `enms-ovos-skill/enms_ovos_skill/lib/response_formatter.py` | User-facing response formatting |
| `enms-ovos-skill/enms_ovos_skill/lib/machine_registry.py` | Machine and SEU discovery cache |
| `enms-ovos-skill/enms_ovos_skill/adapters/` | Backend adapter layer |
| `enms-ovos-skill/bridge/ovos_rest_bridge.py` | HTTP-to-messagebus bridge |

## Query Lifecycle

1. A client sends `POST /query` or `POST /query/voice`.
2. The REST bridge emits a `recognizer_loop:utterance` message.
3. OVOS core routes the utterance to the HumanEnerDIA skill.
4. The skill parses the utterance through:
   - heuristic regex routing
   - Adapt vocabulary matching
   - optional local LLM fallback
5. The validator checks intent, machine names, and supported parameters.
6. The skill calls the configured HumanEnerDIA-compatible analytics API.
7. The skill emits a spoken response and structured response event.
8. The REST bridge returns a structured JSON response to the client.

## Supported Intent Families

The skill includes handlers for:

- machine status
- power query
- energy query
- factory overview
- ranking and top consumers
- comparison
- cost analysis
- anomaly detection
- forecast
- baseline and baseline models
- baseline explanation
- driver analysis
- SEUs
- KPI
- performance
- production
- report
- system health
- help

See [Query Capabilities](./QUERY_CAPABILITIES.md) for user-facing examples.

## Backend Dependency

The live backend dependency is a HumanEnerDIA-compatible analytics API. The
default path inside the HumanEnerDIA Docker network is:

```text
http://enms-analytics:8001/api/v1
```

When running outside the HumanEnerDIA Docker network, set `ENMS_API_URL` to the
reachable compatible backend URL. For a third-party EnMS, this should be an
adapter/proxy that exposes the compatibility contract documented in
[EnMS API Compatibility](./ENMS_API_COMPATIBILITY.md).

## Model Fallback

The optional local LLM fallback uses GGUF model files through `llama-cpp-python`
when installed. The fallback is not required for standard fast-path queries and
is not bundled by default.

## Screenshot Placeholders

- `docs/images/architecture/ovos-architecture.png`
- `docs/images/architecture/query-lifecycle.png`
