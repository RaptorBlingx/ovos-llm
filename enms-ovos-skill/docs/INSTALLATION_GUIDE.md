# INSTALLATION GUIDE
## OVOS EnMS Skill - Universal Installation for Any EnMS

This guide explains how to install and configure the OVOS EnMS Skill for **your** energy management system, regardless of vendor or implementation.

---

## 🎯 What This Skill Does

Enables voice control of your EnMS using OVOS (Open Voice Operating System):

- **Machine Status**: "Hey Jarvis, what's the status of Compressor-1?"
- **Energy Queries**: "How much energy did the factory use today?"
- **Comparisons**: "Compare energy consumption of Compressor-1 and Boiler-1"
- **Predictions**: "What's the expected energy for Compressor-1 at 25°C?"
- **Anomalies**: "Are there any energy anomalies?"
- **Reports**: "Generate monthly energy report"

---

## ✅ Requirements

### 1. EnMS Requirements

Your energy management system must provide a REST API with these **minimum** endpoints:

| Endpoint | Purpose | Example |
|----------|---------|---------|
| `GET /machines` | List all machines | `[{"id": "uuid", "name": "Compressor-1"}]` |
| `GET /machines/{id}/status` | Machine status | `{"status": "running", "power_kw": 24.5}` |
| `GET /timeseries/energy` | Energy consumption | `{"total_kwh": 450.2, "timeseries": [...]}` |
| `GET /factory/summary` | Factory-wide totals | `{"total_kwh": 19456.8}` |

**Not sure if your EnMS is compatible?** See [API_REQUIREMENTS.md](API_REQUIREMENTS.md) for detailed specs.

### 2. OVOS Installation

- **Option A**: Docker (recommended)  
  → See [../README.md](../README.md) for Docker setup
  
- **Option B**: Native Linux installation  
  → See [OVOS documentation](https://openvoiceos.github.io/ovos-technical-manual/)

### 3. Network Access

- OVOS container/host must reach your EnMS API
- Typical setup: Both on same internal network
- Firewall: Allow traffic on EnMS API port (e.g., 8001)

---

## 🚀 Quick Start (5 minutes)

### Step 1: Clone Repository

```bash
cd /opt/ovos/skills/  # Or your OVOS skills directory
git clone https://github.com/humanergy/ovos-llm.git
cd ovos-llm/enms-ovos-skill
```

### Step 2: Run Interactive Setup

```bash
./setup_ovos_skill.sh
```

This will prompt you for:
- Your EnMS API URL
- Factory name
- Adapter type (Humanergy, generic, or custom)
- Auto-discovery preferences

**Example session:**
```
Select adapter type [1]: 2  (generic)
Enter your EnMS API URL: http://192.168.1.100:8001/api/v1
Enter your factory name: ACME Manufacturing
Auto-discover machines from API? (y/n): y
✓ API connection successful!
✓ Found machines: Compressor-1, Boiler-A, HVAC-North
✓ Configuration saved to config.yaml
```

### Step 3: Install Skill in OVOS

```bash
# If using Docker
docker compose restart ovos

# If native installation
systemctl restart ovos-core
```

### Step 4: Test

Wait 30 seconds for skill initialization, then:

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the energy consumption?"}'
```

**Expected response:**
```json
{
  "response": "The factory consumed 19456.8 kWh today.",
  "intent": "energy_consumption",
  "success": true
}
```

---

## 📝 Manual Configuration

If you prefer manual setup or need advanced customization:

### 1. Copy Template

```bash
cp config.yaml.template config.yaml
```

### 2. Edit config.yaml

```yaml
# Minimum required configuration
adapter_type: humanergy  # or 'generic', 'custom'
api_base_url: http://your-enms-api:8001/api/v1
factory_name: Your Factory Name
auto_discover_machines: true
```

**Key settings to customize:**

| Setting | Purpose | Example Values |
|---------|---------|----------------|
| `adapter_type` | EnMS implementation | `humanergy`, `generic`, `custom` |
| `api_base_url` | Your EnMS API URL | `http://192.168.1.100:8001/api/v1` |
| `factory_name` | Used in voice responses | `ACME Manufacturing` |
| `terminology.energy_unit` | Display units | `kWh`, `MWh`, `GJ`, `BTU` |
| `terminology.machine_term` | Equipment terminology | `machine`, `asset`, `unit` |
| `voice.verbosity` | Response detail level | `low`, `medium`, `high` |

**See [config.yaml.template](../config.yaml.template) for all options.**

### 3. Test API Connection

```bash
curl http://your-enms-api:8001/api/v1/health
curl http://your-enms-api:8001/api/v1/machines | jq '.'
```

### 4. Restart OVOS

```bash
docker compose restart ovos
# or
systemctl restart ovos-core
```

---

## 🔌 Adapter Types

### Humanergy Adapter (Default)

For Humanergy's EnMS installations:

```yaml
adapter_type: humanergy
api_base_url: http://10.33.10.109:8001/api/v1
```

**Features:**
- Full support for all Humanergy endpoints
- Baseline predictions, anomaly detection
- ISO 50001 compliance reports
- Performance opportunities

### Generic Adapter

For other EnMS with standard REST APIs:

```yaml
adapter_type: generic
api_base_url: http://your-enms:8001/api/v1
```

**Features:**
- Works with any EnMS providing minimum required endpoints
- Adapts to various API response structures
- May have reduced features (no baseline predictions, etc.)

### Custom Adapter

For proprietary EnMS or special requirements:

1. **Create adapter class:**

```python
# my_company_adapter.py
from enms_ovos_skill.adapters import EnMSAdapter

class MyCompanyAdapter(EnMSAdapter):
    async def list_machines(self, **kwargs):
        # Your implementation here
        pass
    
    # Implement other required methods...
```

2. **Register adapter:**

```python
# In __init__.py or skill initialization
from enms_ovos_skill.adapters import AdapterFactory
from .my_company_adapter import MyCompanyAdapter

AdapterFactory.register('mycompany', MyCompanyAdapter)
```

3. **Configure:**

```yaml
adapter_type: mycompany
api_base_url: http://your-custom-api:8001
```

**See [CUSTOM_ADAPTER_GUIDE.md](CUSTOM_ADAPTER_GUIDE.md) for detailed instructions.**

---

## 🧪 Testing & Validation

### 1. Test Machine Discovery

```bash
# Check if machines are discovered
docker compose logs ovos | grep "machine_whitelist_refreshed"

# Expected output:
# machine_whitelist_refreshed machines_count=6 from_api=true
```

### 2. Test Voice Queries

Use the interactive test script:

```bash
cd enms-ovos-skill
python scripts/test_skill_chat.py "What's the energy consumption?"
```

**Test different query types:**
```bash
# Machine status
python scripts/test_skill_chat.py "status of Compressor-1"

# Energy query
python scripts/test_skill_chat.py "energy consumption today"

# Comparison
python scripts/test_skill_chat.py "compare Compressor-1 and Boiler-1"

# Baseline prediction
python scripts/test_skill_chat.py "expected energy for Compressor-1 at 25 degrees"
```

### 3. Verify Adapter

Check which adapter loaded:

```bash
docker compose logs ovos | grep "adapter_initialized"

# Expected:
# adapter_initialized adapter_type=HumanergyAdapter base_url=http://...
```

---

## 🛠️ Troubleshooting

### Issue: "Sorry, I didn't receive a response in time"

**Cause:** API timeout or connection failure

**Fix:**
1. Check API is running: `curl http://your-enms-api:8001/api/v1/health`
2. Increase timeout in config.yaml: `api_timeout: 120`
3. Check network connectivity from OVOS container
4. Review logs: `docker compose logs ovos | grep -i error`

### Issue: "Machine not found: compressor-1"

**Cause:** Machine discovery failed or name mismatch

**Fix:**
1. Check machine list: `curl http://your-enms-api:8001/api/v1/machines | jq '.'`
2. Verify auto-discovery: `docker compose logs ovos | grep machine_whitelist`
3. Add fallback machines in config.yaml:
   ```yaml
   fallback_machines:
     - Compressor-1
     - YourMachine-Name
   ```

### Issue: "Unknown adapter type"

**Cause:** Invalid adapter_type in config.yaml

**Fix:**
1. Check available adapters:
   ```python
   from enms_ovos_skill.adapters import AdapterFactory
   print(AdapterFactory.list_adapters())
   ```
2. Use valid type: `humanergy`, `generic`, or registered custom adapter

### Issue: Features not working (baseline, anomalies, etc.)

**Cause:** Your EnMS API doesn't support those endpoints

**Fix:**
1. Check API requirements: [API_REQUIREMENTS.md](API_REQUIREMENTS.md)
2. Disable unsupported features in config.yaml:
   ```yaml
   features:
     baseline_predictions: false  # If /baseline/predict not available
     anomaly_detection: false     # If /anomaly/* not available
   ```

**More help:** See [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)

---

## 📚 Additional Resources

- **[API Requirements](API_REQUIREMENTS.md)** - Minimum EnMS API specification
- **[Custom Adapter Guide](CUSTOM_ADAPTER_GUIDE.md)** - Create adapter for your EnMS
- **[Configuration Reference](CONFIGURATION.md)** - All config.yaml options explained
- **[Architecture Overview](OVOS_ENMS_INTEGRATION.md)** - System design and components
- **[Testing Protocol](test-protocol.md)** - Comprehensive testing guide

---

## 🌍 WASABI Project

This skill is part of the [WASABI Project](https://www.wasabiproject.eu/) - delivering open-source voice assistants for industrial energy management and ISO 50001 compliance.

**Portability Goal:** This skill works with **any** EnMS installation, not just Humanergy. We welcome contributions for additional adapters and improvements!

---

## 📞 Support

- **Issues:** https://github.com/humanergy/ovos-llm/issues
- **Discussions:** https://github.com/humanergy/ovos-llm/discussions
- **Email:** support@humanergy.com (for Humanergy installations)

---

## 📄 License

Apache License 2.0 - See [LICENSE](../LICENSE) for details.
