# OVOS-EnMS REST Bridge API Reference

The REST bridge exposes HTTP endpoints for clients that need to send text
queries into OVOS.

Base URL in Docker:

```text
http://localhost:5000
```

## Health

```http
GET /health
```

Response:

```json
{
  "status": "healthy",
  "messagebus_connected": true,
  "timestamp": "2026-05-22T00:00:00.000000"
}
```

`status` is `healthy` only when the REST bridge can see the OVOS messagebus.

## Query

```http
POST /query
POST /query/voice
```

`/query/voice` is an alias for integrations that label voice requests
separately.

Request body:

```json
{
  "text": "What is the status of Compressor-1?",
  "session_id": "demo-session-001",
  "user_id": "operator"
}
```

Legacy request bodies using `utterance` or `query` instead of `text` are also
accepted by the bridge.

Successful response:

```json
{
  "success": true,
  "response": "Compressor-1 is currently running.",
  "intent": "machine_status",
  "confidence": 0.95,
  "data": {},
  "insights": {},
  "timestamp": "2026-05-22T00:00:00.000000",
  "session_id": "demo-session-001"
}
```

Timeout response:

```json
{
  "success": false,
  "response": "Sorry, I didn't receive a response in time. Please try again.",
  "intent": null,
  "confidence": null,
  "data": null,
  "insights": null,
  "timestamp": "2026-05-22T00:00:00.000000",
  "session_id": "demo-session-001"
}
```

The bridge waits up to 90 seconds for a skill response. It can return after a
spoken response is received even if no structured event arrives within the
configured grace period.

## Root Metadata

```http
GET /
```

Returns bridge name, version, messagebus status, and endpoint summary.

## OpenAPI

```http
GET /docs
```

FastAPI-generated API documentation.

## Curl Examples

```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"text":"What is the status of Compressor-1?","session_id":"smoke-001"}'
```

```bash
curl -X POST http://localhost:5000/query/voice \
  -H "Content-Type: application/json" \
  -d '{"utterance":"forecast energy for tomorrow","session_id":"voice-001"}'
```

## Error Conditions

| Condition | HTTP status | Meaning |
|---|---:|---|
| Messagebus unavailable | `503` | OVOS messagebus is not connected |
| Internal bridge error | `500` | Unexpected bridge-side failure |
| Skill timeout | `200` with `success=false` | Bridge did not receive a skill response in time |

## Security Notes

The bridge currently allows broad CORS by default. Restrict CORS and network
exposure before publishing the endpoint outside a trusted network.
