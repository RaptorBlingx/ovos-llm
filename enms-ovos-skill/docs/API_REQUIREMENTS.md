# API REQUIREMENTS
## Minimum EnMS API Specification for OVOS Integration

This document defines the **minimum** API requirements for an EnMS (Energy Management System) to work with the OVOS voice assistant skill.

---

## 🎯 Overview

The OVOS EnMS Skill uses a **flexible adapter pattern** that works with various API structures. Your EnMS doesn't need to match Humanergy's API exactly - the adapter translates between your API and the skill's expectations.

### Core Principle

**Required:** Your API must provide these core capabilities:
1. List machines/equipment
2. Get machine status
3. Query energy consumption (time-series or aggregated)
4. Factory-wide summaries

**Optional:** Advanced features (baseline predictions, anomalies, ISO 50001) enhance functionality but aren't required.

---

## ✅ Required Endpoints

### 1. List Machines

**Purpose:** Discover all equipment/machines for voice recognition

**Endpoint:** `GET /machines` (or equivalent)

**Minimum Response:**
```json
[
  {
    "id": "machine-uuid-or-name",
    "name": "Compressor-1",
    "type": "compressor",
    "status": "running"
  },
  {
    "id": "boiler-001",
    "name": "Boiler-1",
    "type": "boiler",
    "status": "offline"
  }
]
```

**Required Fields:**
- `id` or `machine_id` - Unique identifier
- `name` or `machine_name` - Human-readable name

**Optional Fields:**
- `type` - Equipment type (compressor, boiler, hvac, etc.)
- `status` - Current status (running, offline, standby)
- `is_active` - Boolean active flag

**Flexibility:** The adapter will normalize these variations:
- `id`, `machine_id`, `uuid`, `identifier`
- `name`, `machine_name`, `display_name`, `label`

---

### 2. Machine Status

**Purpose:** Get current operational state of a machine

**Endpoint:** `GET /machines/{id}/status` OR `GET /machines/status/{name}`

**Minimum Response:**
```json
{
  "machine_name": "Compressor-1",
  "status": "running",
  "power_kw": 24.5,
  "energy_kwh_today": 450.2,
  "last_reading": "2025-12-19T10:30:00Z"
}
```

**Required Fields:**
- `machine_name` or `name` - Machine identifier
- `status` - Operational status (running, offline, standby, error)
- `power_kw` or `current_power` - Current power draw

**Optional Fields:**
- `energy_kwh_today` - Today's consumption
- `temperature`, `pressure`, `load` - Operating conditions
- `last_reading` or `timestamp` - Last data point time

**Voice Queries Enabled:**
- "What's the status of Compressor-1?"
- "Is Boiler-1 running?"

---

### 3. Energy Consumption (Time-Series)

**Purpose:** Query historical energy consumption

**Endpoint:** `GET /machines/{id}/energy` OR `GET /timeseries/energy`

**Parameters:**
- `start_time` - Period start (ISO 8601)
- `end_time` - Period end (ISO 8601)
- `interval` - Aggregation bucket (optional: 1min, 15min, 1hour, 1day)

**Minimum Response:**
```json
{
  "machine_id": "compressor-uuid",
  "machine_name": "Compressor-1",
  "total_kwh": 450.2,
  "avg_power_kw": 18.7,
  "start_time": "2025-12-19T00:00:00Z",
  "end_time": "2025-12-19T23:59:59Z",
  "data": [
    {"timestamp": "2025-12-19T00:00:00Z", "kwh": 18.5, "kw": 18.5},
    {"timestamp": "2025-12-19T01:00:00Z", "kwh": 19.2, "kw": 19.2}
  ]
}
```

**Required Fields:**
- `total_kwh` or `total_energy` - Total consumption in period
- Either:
  - `data` array with time-series points, OR
  - Just `total_kwh` for aggregated queries

**Time-Series Point Format:**
- `timestamp` - ISO 8601 timestamp
- `kwh` or `energy` - Energy consumed in this bucket
- `kw` or `power` - Average power in this bucket

**Voice Queries Enabled:**
- "How much energy did Compressor-1 use today?"
- "Energy consumption of Boiler-1 last week"

---

### 4. Factory-Wide Summary

**Purpose:** Get total consumption across all machines

**Endpoint:** `GET /factory/summary` OR `GET /energy/total`

**Parameters:**
- `start_time` - Optional period start
- `end_time` - Optional period end
- Defaults to "today" if not specified

**Minimum Response:**
```json
{
  "total_energy_kwh": 19456.8,
  "total_power_kw": 810.3,
  "period": "today",
  "active_machines": 12
}
```

**Required Fields:**
- `total_energy_kwh` or `total_kwh` - Total factory consumption

**Optional Fields:**
- `total_power_kw` - Current total power
- `active_machines` - Number of running machines
- `period` - Time period description

**Voice Queries Enabled:**
- "What's the energy consumption?" (implicit factory-wide)
- "Total energy usage today"

---

## 🔧 Optional Endpoints (Enhanced Features)

These endpoints enable advanced voice features but aren't required for basic functionality:

### 5. Significant Energy Uses (SEUs)

**Endpoint:** `GET /seus` OR `GET /energy-consumers`

**Response:**
```json
{
  "seus": [
    {
      "name": "Compressed Air System",
      "machines": ["Compressor-1", "Compressor-2"],
      "total_kwh": 5600.2,
      "category": "production"
    }
  ]
}
```

**Enables:**
- "Energy consumption of Compressed Air System"
- SEU-level queries and analysis

---

### 6. Baseline Predictions

**Endpoint:** `POST /baseline/predict`

**Request:**
```json
{
  "machine_name": "Compressor-1",
  "temperature": 25.0,
  "pressure": 8.5,
  "load_percent": 75.0
}
```

**Response:**
```json
{
  "predicted_kwh": 97.74,
  "confidence": 0.95,
  "model_version": 186
}
```

**Enables:**
- "What's the expected energy for Compressor-1 at 25 degrees?"
- "Predict baseline consumption"

---

### 7. Anomaly Detection

**Endpoint:** `GET /anomalies` OR `GET /anomaly/recent`

**Parameters:**
- `machine_id` - Optional filter
- `severity` - Optional filter (low, medium, high, critical)
- `limit` - Max results

**Response:**
```json
{
  "anomalies": [
    {
      "machine_name": "Boiler-1",
      "severity": "high",
      "deviation_percent": 25.3,
      "detected_at": "2025-12-19T08:15:00Z",
      "description": "Energy 25% above baseline"
    }
  ]
}
```

**Enables:**
- "Are there any anomalies?"
- "Show me high severity anomalies"

---

### 8. Machine Comparison

**Endpoint:** `GET /machines/compare` OR handle via multiple energy queries

**Parameters:**
- `machine_ids` - Comma-separated list
- `start_time`, `end_time` - Period
- `metric` - Comparison metric (energy, power, cost)

**Response:**
```json
{
  "comparison": [
    {"machine": "Compressor-1", "total_kwh": 450.2, "rank": 1},
    {"machine": "Boiler-1", "total_kwh": 380.5, "rank": 2}
  ]
}
```

**Enables:**
- "Compare Compressor-1 and Boiler-1"
- "Which compressor uses more energy?"

---

## 📋 API Design Flexibility

The adapter pattern supports various API designs:

### Response Wrapping

Your API can return data in different wrapper formats:

```json
// Option 1: Direct array
[{machine}, {machine}, ...]

// Option 2: Wrapped in "data"
{"data": [{machine}, ...]}

// Option 3: Wrapped in "machines"
{"machines": [{machine}, ...]}

// Option 4: With metadata
{"success": true, "data": [...], "timestamp": "..."}
```

**The adapter will extract the actual data regardless of wrapper.**

### Timestamp Formats

Supported timestamp formats:
- ISO 8601: `"2025-12-19T10:30:00Z"`
- Unix timestamp: `1703002200`
- Custom format: Define in adapter

### Units

The adapter can convert between units:
- Energy: kWh ↔ MWh ↔ GJ ↔ BTU
- Power: kW ↔ MW ↔ HP
- Configure in `config.yaml` → `terminology`

### Error Handling

Your API should return appropriate HTTP status codes:
- `200` - Success
- `404` - Resource not found (machine doesn't exist)
- `400` - Bad request (invalid parameters)
- `500` - Server error (database down, etc.)
- `503` - Service unavailable (temporary outage)

---

## 🔍 Testing Your API

Use this checklist to verify compatibility:

### 1. Machine Discovery Test

```bash
curl http://your-enms-api:8001/api/v1/machines | jq '.'
```

**Expected:** List of machines with IDs and names

### 2. Status Test

```bash
curl http://your-enms-api:8001/api/v1/machines/{id}/status | jq '.'
```

**Expected:** Status, power, energy fields

### 3. Energy Query Test

```bash
START=$(date -u -d '1 day ago' '+%Y-%m-%dT%H:%M:%SZ')
END=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

curl "http://your-enms-api:8001/api/v1/machines/{id}/energy?start_time=$START&end_time=$END" | jq '.'
```

**Expected:** total_kwh and optional time-series data

### 4. Factory Summary Test

```bash
curl http://your-enms-api:8001/api/v1/factory/summary | jq '.'
```

**Expected:** Factory-wide total energy

---

## 🛠️ Creating a Custom Adapter

If your API doesn't match these patterns exactly, create a custom adapter:

### Step 1: Implement EnMSAdapter Interface

```python
from enms_ovos_skill.adapters import EnMSAdapter

class MyEnMSAdapter(EnMSAdapter):
    async def list_machines(self, **kwargs):
        # Call your API
        response = await self.http_client.get("/your-endpoint")
        
        # Transform to standard format
        machines = []
        for item in response['your_wrapper_key']:
            machines.append({
                "machine_id": item['your_id_field'],
                "machine_name": item['your_name_field'],
                "type": item.get('your_type_field'),
                "status": item.get('your_status_field')
            })
        return machines
    
    # Implement other required methods...
```

### Step 2: Register Adapter

```python
from enms_ovos_skill.adapters import AdapterFactory

AdapterFactory.register('myenms', MyEnMSAdapter)
```

### Step 3: Configure

```yaml
# config.yaml
adapter_type: myenms
api_base_url: http://your-api:8001
```

**See [CUSTOM_ADAPTER_GUIDE.md](CUSTOM_ADAPTER_GUIDE.md) for detailed tutorial.**

---

## 📊 Feature Matrix

| Feature | Required? | Endpoint | Voice Queries |
|---------|-----------|----------|---------------|
| Machine list | ✅ Required | `GET /machines` | Discovery, "status of X" |
| Machine status | ✅ Required | `GET /machines/{id}/status` | "status of X", "is X running?" |
| Energy query | ✅ Required | `GET /machines/{id}/energy` | "energy of X", "X consumption today" |
| Factory summary | ✅ Required | `GET /factory/summary` | "total energy", "factory consumption" |
| SEU list | ⚪ Optional | `GET /seus` | "SEU consumption", "Compressed Air usage" |
| Baseline predict | ⚪ Optional | `POST /baseline/predict` | "expected energy at 25°C" |
| Anomalies | ⚪ Optional | `GET /anomalies` | "any anomalies?", "high severity issues" |
| Comparison | ⚪ Optional | `GET /compare` or manual | "compare X and Y" |
| Reports | ⚪ Optional | `POST /reports/generate` | "generate monthly report" |

---

## 🎯 Quick Compatibility Check

**Your EnMS is compatible if you can answer YES to these:**

1. ✅ Can your API list all machines/equipment?
2. ✅ Can you get current status (power, energy) for a specific machine?
3. ✅ Can you query energy consumption for a time period?
4. ✅ Can you get factory-wide total energy?

**If YES to all 4:** You can use OVOS EnMS Skill with basic features.

**If YES to 1-4 + others:** You get additional voice features (baseline, anomalies, etc.)

---

## 📞 Need Help?

- **Compatibility questions:** Open an issue on GitHub
- **Custom adapter assistance:** See CUSTOM_ADAPTER_GUIDE.md
- **Commercial support:** support@humanergy.com

---

## 📄 License

Apache License 2.0 - This specification and adapters are open source.
