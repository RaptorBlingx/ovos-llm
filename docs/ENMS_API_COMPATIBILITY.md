# EnMS API Compatibility

`HumanEnerDIA-OVOS-skill-v1.0.0` is an OVOS assistant runtime. It can be used
without buying or running the HumanEnerDIA full stack only when the target EnMS
provides a HumanEnerDIA-compatible REST API, either natively or through a small
adapter/proxy service.

The release is not a universal direct connector for every EnMS vendor API.
Most production query paths call the HumanEnerDIA-compatible API client, so the
integration boundary for v1.0.0 is the REST API contract below.

## Recommended Third-Party Integration

```text
OVOS REST bridge
        |
        v
HumanEnerDIA OVOS skill
        |
        v
Customer adapter/proxy exposing /api/v1
        |
        v
Customer EnMS / historian / BMS / SCADA / database
```

Run the OVOS product with:

```bash
./setup.sh --enms-api-url http://<adapter-host>:8001/api/v1
```

The adapter should normalize the customer's EnMS data into the field names and
shapes expected by the skill. It may be a lightweight FastAPI, Node.js, Java, or
gateway service. It does not need to run OVOS.

## Minimum Smoke-Test Contract

A practical first integration should support these endpoints:

```text
GET /health
GET /api/v1/machines
GET /api/v1/machines/status/{machine_name}
GET /api/v1/factory/summary
GET /api/v1/stats/system
GET /api/v1/analytics/top-consumers
```

These endpoints are enough for basic machine status, power, factory overview,
and top-consumer questions.

## Expected Response Shapes

`GET /health`

```json
{
  "status": "healthy"
}
```

`GET /api/v1/machines`

```json
[
  {
    "id": "compressor-1",
    "machine_name": "Compressor-1",
    "name": "Compressor-1",
    "type": "compressor",
    "status": "running",
    "is_active": true
  }
]
```

`GET /api/v1/machines/status/Compressor-1`

```json
{
  "machine_name": "Compressor-1",
  "status": "running",
  "current_power_kw": 49.9,
  "energy_today_kwh": 412.5,
  "last_reading_time": "2026-06-08T10:00:00Z"
}
```

`GET /api/v1/factory/summary`

```json
{
  "total_energy_kwh": 19456.8,
  "total_power_kw": 810.3,
  "active_machines": 12,
  "period": "today"
}
```

`GET /api/v1/stats/system`

```json
{
  "total_energy_kwh": 19456.8,
  "total_power_kw": 810.3,
  "active_machines": 12,
  "machine_count": 15
}
```

`GET /api/v1/analytics/top-consumers?limit=3`

```json
{
  "top_consumers": [
    {
      "machine_name": "Compressor-1",
      "energy_kwh": 412.5,
      "power_kw": 49.9
    }
  ]
}
```

## Advanced Features

Advanced questions require additional HumanEnerDIA-compatible endpoints, such
as time-series, anomalies, forecasts, KPIs, reports, ISO 50001 action plans,
baseline models, and performance analysis. If those endpoints are not provided,
basic queries can still work but advanced questions will return API errors or
limited responses.

## Readiness Statement

Ready in v1.0.0:

- OVOS runtime packaging
- HumanEnerDIA-compatible API integration
- Third-party EnMS use through a compatibility proxy
- Existing OVOS runtime installation

Not ready as a zero-config v1.0.0 feature:

- Direct connection to arbitrary vendor EnMS APIs
- Runtime selection of a production generic adapter
- Fully documented native adapter SDK for every advanced query path

