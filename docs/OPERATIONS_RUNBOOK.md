# OVOS-EnMS Operations Runbook

This runbook is for operators maintaining the OVOS runtime after deployment.

## Daily Checks

```bash
docker compose ps
curl -fsS http://localhost:5000/health
```

Expected health response:

```json
{
  "status": "healthy",
  "messagebus_connected": true
}
```

Also verify the HumanEnerDIA backend:

```bash
curl -fsS http://localhost:8001/api/v1/health
```

If OVOS runs on the same Docker network as HumanEnerDIA, the backend URL inside
the OVOS container is usually:

```text
http://enms-analytics:8001/api/v1
```

## Start and Stop

Start:

```bash
docker compose up -d
```

Stop:

```bash
docker compose down
```

Restart:

```bash
docker compose restart
```

Rebuild:

```bash
docker compose build
docker compose up -d
```

## Logs

All logs:

```bash
docker compose logs -f --tail=200
```

Bridge logs:

```bash
docker compose exec ovos tail -f /var/log/ovos/bridge.out.log
docker compose exec ovos tail -f /var/log/ovos/bridge.err.log
```

Skill logs:

```bash
docker compose exec ovos tail -f /var/log/ovos/skills.out.log
docker compose exec ovos tail -f /var/log/ovos/skills.err.log
```

Messagebus logs:

```bash
docker compose exec ovos tail -f /var/log/ovos/messagebus.out.log
docker compose exec ovos tail -f /var/log/ovos/messagebus.err.log
```

## Smoke Test

```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"text":"What is the status of Compressor-1?","session_id":"ops-smoke"}'
```

The response should include `success`, `response`, `timestamp`, and
`session_id`. If backend data is unavailable, the response may be a
clarification or error-style answer from the skill.

## Common Failure Modes

| Symptom | Likely cause | First checks |
|---|---|---|
| `/health` shows `unhealthy` | Messagebus not connected | `docker compose logs ovos`, messagebus logs |
| Query returns 503 | Bridge cannot reach messagebus | Restart container, inspect supervisor logs |
| Query times out | Skill did not respond | Skill logs, backend health, model fallback latency |
| Backend answers fail | `ENMS_API_URL` wrong or backend down | `curl` backend health from host and container |
| LLM fallback very slow | Model enabled and CPU-bound | Monitor CPU/RAM, test fast-path query |
| Machine not found | Backend machine discovery or name mismatch | Ask for machine list, check HumanEnerDIA backend |

## Container Internals

The image runs as the non-root `ovos` user. Important paths:

- `/tmp/enms-ovos-skill`: installed skill source
- `/app/bridge`: REST bridge code
- `/var/log/ovos`: service logs
- `/config/mycroft/mycroft.conf`: OVOS config
- `/models`: expected model mount location if using Docker model paths

## Backup

The OVOS container is stateless except for logs and any mounted models. Back up:

- `.env`
- model files and checksums if using local fallback
- any changed skill settings
- deployment notes for `ENMS_API_URL` and network naming

Do not commit `.env` or GGUF model files.

## Screenshot Placeholders

- `docs/images/operations/docker-compose-ps.png`
- `docs/images/operations/health-response.png`
- `docs/images/operations/logs.png`
