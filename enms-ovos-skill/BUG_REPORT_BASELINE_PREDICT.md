# 🐛 Bug Report: Baseline Prediction Returns 0.0 kWh

**Date:** December 3, 2025  
**Reporter:** OVOS Integration Team (Burak)  
**Severity:** HIGH - Breaks voice interface predictions  
**Component:** EnMS API `/api/v1/baseline/predict`

---

## 📋 Summary

The `/baseline/predict` endpoint returns `predicted_energy_kwh: 0.0` when called with partial feature sets that voice users would naturally provide. This makes baseline predictions unusable via OVOS voice interface.

---

## 🔍 Problem Description

### Voice Query
```
User: "Predict energy for Compressor-1 at 500 units production and 22 degrees"
```

### OVOS Request
```json
POST /api/v1/baseline/predict
{
  "seu_name": "Compressor-1",
  "energy_source": "electricity",
  "features": {
    "total_production_count": 500,
    "avg_outdoor_temp_c": 22.0,
    "avg_pressure_bar": 7.0,
    "avg_load_factor": 0.85
  },
  "include_message": false
}
```

### ❌ ACTUAL API Response
```json
{
  "machine_id": "c0000000-0000-0000-0000-000000000001",
  "model_version": 193,
  "features": {
    "total_production_count": 500.0,
    "avg_outdoor_temp_c": 22.0,
    "avg_pressure_bar": 7.0,
    "avg_load_factor": 0.85
  },
  "predicted_energy_kwh": 0.0,  ← WRONG!
  "warnings": []
}
```

### ✅ EXPECTED Response
Should return realistic prediction (like 970.24 kWh) or error message explaining missing features.

---

## 🧪 Test Evidence

### Working curl (with ALL features)
```bash
curl -X POST "http://10.33.10.109:8001/api/v1/baseline/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": "c0000000-0000-0000-0000-000000000001",
    "features": {
      "production_count": 500,
      "outdoor_temp_c": 22,
      "pressure_bar": 7,
      "load_factor": 0.85,
      "throughput_units_per_hour": 500,
      "machine_temp_c": 50
    }
  }'
```

**Result:** `"predicted_energy_kwh": 970.24` ✅

### Failing curl (OVOS features)
```bash
curl -X POST "http://10.33.10.109:8001/api/v1/baseline/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "seu_name": "Compressor-1",
    "energy_source": "electricity",
    "features": {
      "total_production_count": 500,
      "avg_outdoor_temp_c": 22.0,
      "avg_pressure_bar": 7.0,
      "avg_load_factor": 0.85
    }
  }'
```

**Result:** `"predicted_energy_kwh": 0.0` ❌

---

## 🔎 Root Cause Analysis

### Missing Features
The Compressor-1 baseline model appears to require:
- ❌ `throughput_units_per_hour` (not extractable from voice)
- ❌ `machine_temp_c` (not extractable from voice)

### Current Behavior
When required features are missing, API silently returns 0.0 kWh instead of:
1. Using sensible defaults
2. Returning error with explanation
3. Warning about missing features

---

## 💥 Impact

### User Experience
```
User: "Predict energy for Compressor-1 at 500 units production and 22 degrees"
OVOS: "Compressor-1 is predicted to consume 0.0 kilowatt hours with 500 units production, 22.0°C temperature, 7.0 bar pressure, and 85.0% load."

← User thinks system is broken!
```

### Voice Interface Limitation
Voice users cannot provide technical parameters like:
- `throughput_units_per_hour` (too complex to say)
- `machine_temp_c` (not observable by user)

---

## 🎯 Recommended Fixes

### Option 1: Smart Defaults (RECOMMENDED)
```python
# When feature missing, use recent average or typical value
if "machine_temp_c" not in features:
    features["machine_temp_c"] = get_typical_machine_temp(machine_id)
if "throughput_units_per_hour" not in features:
    features["throughput_units_per_hour"] = features.get("total_production_count", 0)
```

### Option 2: Better Error Response
```json
{
  "detail": {
    "error": "MISSING_REQUIRED_FEATURES",
    "message": "Baseline prediction requires additional features for Compressor-1",
    "missing_features": ["machine_temp_c", "throughput_units_per_hour"],
    "suggestion": "These features will use defaults: machine_temp_c=50°C, throughput=500 units/hr"
  }
}
```

### Option 3: Warning Field
```json
{
  "predicted_energy_kwh": 970.24,
  "warnings": [
    "Using default machine_temp_c=50°C (not provided)",
    "Using throughput=production_count (not provided)"
  ]
}
```

---

## 📊 API Inconsistencies Discovered

### Feature Name Variations
| OVOS Sends | API Docs Say | Working curl Uses |
|------------|--------------|-------------------|
| `total_production_count` | `total_production_count` | `production_count` |
| `avg_outdoor_temp_c` | `avg_outdoor_temp_c` | `outdoor_temp_c` |
| `avg_pressure_bar` | `avg_pressure_bar` | `pressure_bar` |
| `avg_load_factor` | `avg_load_factor` | `load_factor` |

**Question:** Which naming convention is correct? API accepts both but docs are unclear.

---

## 🔧 Requested Actions

### Immediate (Critical)
1. **Fix zero prediction bug**: Return error or use defaults when features missing
2. **Add warnings array**: Inform caller about defaulted features
3. **Document required vs optional features**: Per SEU/machine type

### Short-term (Important)
4. **Standardize feature names**: Choose one convention (with/without prefixes)
5. **Update API docs**: Specify which features are REQUIRED for each machine type
6. **Add feature validation**: Return 422 error listing missing required features

### Long-term (Enhancement)
7. **Smart defaults service**: Learn typical values per machine from historical data
8. **Feature importance API**: `GET /baseline/model/{id}/required-features`
9. **Prediction confidence**: Return confidence score based on feature completeness

---

## 📝 Testing Checklist

After fix, verify:
- [ ] Prediction with partial features returns non-zero value
- [ ] Warnings array lists defaulted features
- [ ] Error messages explain missing required features
- [ ] Voice query "predict energy at 500 units and 22 degrees" works
- [ ] Documentation updated with required/optional features per SEU

---

## 🔗 Related Issues

1. **HVAC-Main 0.0 kWh prediction** - Same root cause (R²=0.057 model, but also feature issue)
2. **Feature naming inconsistency** - `avg_*` vs no prefix (see API Inconsistencies table)
3. **SEC formatting bug** - Already fixed on OVOS side (different issue)

---

## 📞 Contact

**OVOS Team:** Burak  
**Testing Environment:** WSL2 + OVOS + EnMS API 10.33.10.109:8001  
**Test Files:** `test_baseline_ovos.json`, `test_baseline_full.json`

---

**Status:** 🟡 AWAITING EnMS FIX  
**Workaround:** None available - voice predictions blocked until API handles missing features
