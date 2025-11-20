# OVOS EnMS Skill - Comprehensive Gap Analysis & Implementation Plan

**Date:** November 19, 2025
**Source Document:** `docs/ENMS-API-DOCUMENTATION-FOR-OVOS.md`
**Goal:** 100% Coverage of EnMS API ("Anything and Everything")

---

## 📊 Executive Summary

| Category | Total Endpoints | Implemented | Missing | Coverage |
|----------|-----------------|-------------|---------|----------|
| System Health | 2 | 1 | 1 | 50% |
| Machines | 3 | 3 | 0 | 100% |
| Time-Series | 4 | 3 | 1 | 75% |
| Anomaly Detection | 3 | 1* | 2 | 33% |
| Baseline Models | 4 | 0 | 4 | 0% |
| KPIs | 1 | 0 | 1 | 0% |
| Forecasting | 1 | 0 | 1 | 0% |
| Voice Training | 1 | 0 | 1 | 0% |
| **TOTAL** | **19** | **8** | **11** | **42%** |

*\*Partially implemented via machine status summary*

---

## 🔍 Detailed Endpoint Analysis

### 1. System Health & Statistics
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/health` | GET | ❌ Missing | Need `system.health.intent` |
| `/stats/system` | GET | ✅ Implemented | Covered by `factory.overview.intent` |

### 2. Machines API
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/machines` | GET | ✅ Implemented | Used internally for whitelist & `ranking.intent` |
| `/machines/{id}` | GET | ✅ Implemented | Used internally |
| `/machines/status/{name}` | GET | ✅ Implemented | Core of `machine.status.intent` |

### 3. Time-Series Data
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/timeseries/energy` | GET | ✅ Implemented | `energy.query.intent` (with time range) |
| `/timeseries/power` | GET | ✅ Implemented | `power.query.intent` (with time range) |
| `/timeseries/latest/{id}` | GET | ✅ Implemented | Used in `machine.status.intent` |
| `/timeseries/multi-machine/energy` | GET | ❌ Missing | Need `comparison.intent` upgrade (currently loops single calls) |

### 4. Anomaly Detection
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/anomaly/detect` | POST | ❌ Missing | Trigger detection on demand |
| `/anomaly/recent` | GET | ❌ Missing | List recent anomalies with filters |
| `/anomaly/active` | GET | ❌ Missing | "Are there any active alerts?" |
| *General* | - | ⚠️ Partial | `machine.status` shows anomaly count, but no details |

### 5. Baseline Models
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/baseline/models` | GET | ❌ Missing | "List models for Compressor-1" |
| `/baseline/predict` | POST | ❌ Missing | "What should the energy be?" (What-if analysis) |
| `/baseline/model/{id}` | GET | ❌ Missing | "Explain the model" |
| *Explanations* | - | ❌ Missing | Voice-friendly model explanations |

### 6. KPIs & Performance
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/kpi/all` | GET | ❌ Missing | SEC, Load Factor, Carbon Intensity |

### 7. Energy Forecasting
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/forecast/demand` | GET | ❌ Missing | "Forecast demand for next 4 hours" |

### 8. Voice Training (The "Killer Feature")
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/baseline/train-seu` | POST | ❌ Missing | "Train baseline for Compressor-1" |

---

## 🛠️ Implementation Roadmap (Phase 2)

To achieve "Anything and Everything", we need to implement the following:

### Priority 1: The "Missing Core" (Anomalies & KPIs)
1.  **New Intent**: `anomaly.query.intent`
    -   "Show me recent anomalies"
    -   "Any active alerts?"
    -   "Check for anomalies in Compressor-1" (Trigger)
2.  **New Intent**: `kpi.query.intent`
    -   "What is the load factor?"
    -   "Show me the carbon intensity"
    -   "Calculate SEC for Boiler-1"

### Priority 2: Advanced Analytics (Forecasting & Baselines)
3.  **New Intent**: `forecast.query.intent`
    -   "What will the energy usage be tomorrow?"
    -   "Forecast demand for next 4 hours"
4.  **New Intent**: `baseline.query.intent`
    -   "List baseline models"
    -   "Explain the active model"
    -   "What is the expected energy?"

### Priority 3: Interactive Features (Training)
5.  **New Intent**: `model.train.intent`
    -   "Train baseline for Compressor-1"
    -   "Train electricity model using production and temperature"

### Priority 4: Multi-Energy Support
6.  **Refactor**: Update all intents to support `energy_source` entity.
    -   "Show **gas** consumption for Boiler-1"
    -   "How much **steam** did we use?"
    -   Currently defaults to electricity/power.

---

## 📝 Action Plan

1.  **Update `lib/api_client.py`**: Add all missing methods (`get_anomalies`, `trigger_detection`, `get_kpis`, `get_forecast`, `train_model`, `get_baselines`).
2.  **Update `lib/models.py`**: Add Pydantic models for new responses.
3.  **Create New Intents**: Define `.intent` files for the 5 new intent types.
4.  **Create New Dialogs**: Write Jinja2 templates for the new responses.
5.  **Update `lib/intent_parser.py`**: Register new intents.
6.  **Update `__init__.py`**: Add handlers for new intents.

This plan will bring the skill from **42%** to **100%** API coverage.

---

## 💡 My Thoughts & Strategic Recommendations

### What We're Missing (Critical Gaps)

**1. The "Killer Features" Not Yet Voice-Enabled:**
- **Baseline Training** (`/baseline/train-seu`) - This is Mr. Umut's vision! "Hey OVOS, train Compressor-1 baseline" should work.
- **Model Explanations** - "Explain why energy is high" using ML model coefficients in natural language.
- **Forecasting** - "What will tomorrow look like?" is a common factory manager question.

**2. User Experience Gaps:**
- No multi-energy support yet (Gas, Steam, Compressed Air) - currently electricity-only.
- Multi-machine comparison uses inefficient loop instead of batch endpoint.
- Missing proactive alerts ("Hey, Boiler-1 has a critical anomaly!").

**3. Observability Gaps:**
- KPIs (SEC, Load Factor, Carbon) are core ISO 50001 metrics but not voice-accessible.
- System health check missing (should be first query: "Is EnMS online?").

### What's Working Well (Keep Doing This)

✅ **Time-Series Queries** - The `time_parser.py` + API integration is excellent.  
✅ **Hybrid Parser Architecture** - 80% fast-path, 20% LLM is optimal.  
✅ **Validation Layer** - Zero hallucinations in production.  
✅ **Response Templates** - Voice-optimized numeric formatting is perfect.  

### Recommended Priority Order (Revised)

**Phase 2A: Quick Wins (Week 1-2)**
1. **System Health Intent** - Trivial to implement, high value for monitoring.
2. **Multi-Machine Batch Comparison** - Replace loop with `/timeseries/multi-machine/energy`.
3. **Active Anomalies Intent** - "Any alerts?" is a common query, API ready.

**Phase 2B: High-Value Analytics (Week 3-4)**
4. **KPI Queries** - ISO 50001 compliance, factory managers love this.
5. **Recent Anomalies** - Historical troubleshooting.
6. **Baseline Model Listing** - "Which models exist?"

**Phase 2C: Advanced Features (Week 5-6)**
7. **Forecasting** - Predictive queries.
8. **Baseline Predictions** - "What-if" analysis.
9. **Model Explanations** - Transparency for ML decisions.

**Phase 2D: Interactive (Week 7-8)**
10. **Voice Training** - The grand finale. This needs careful UX design for feature selection.

**Phase 3: Multi-Energy Refactor (Week 9-10)**
11. **Energy Source Entity** - Add `energy_source` to all intents.
12. **Update Templates** - Handle units (m³ for gas, kg for steam).

### Implementation Complexity Estimates

| Feature | API Complexity | NLU Complexity | Template Complexity | Total Effort |
|---------|----------------|----------------|---------------------|--------------|
| System Health | 🟢 Trivial | 🟢 Simple | 🟢 Simple | 4 hours |
| Multi-Machine Batch | 🟢 Easy | 🟡 Medium | 🟡 Medium | 8 hours |
| Active Anomalies | 🟢 Easy | 🟢 Simple | 🟢 Simple | 6 hours |
| KPI Queries | 🟡 Medium | 🟡 Medium | 🟡 Medium | 12 hours |
| Recent Anomalies | 🟡 Medium | 🟡 Medium | 🟡 Medium | 10 hours |
| Baseline Listing | 🟡 Medium | 🟢 Simple | 🟡 Medium | 8 hours |
| Forecasting | 🟡 Medium | 🟡 Medium | 🔴 Complex | 16 hours |
| Baseline Predict | 🟡 Medium | 🔴 Complex | 🟡 Medium | 14 hours |
| Model Explanations | 🟢 Easy | 🟢 Simple | 🔴 Complex | 12 hours |
| Voice Training | 🔴 Complex | 🔴 Complex | 🟡 Medium | 20 hours |
| Multi-Energy | 🟢 Easy | 🟡 Medium | 🟡 Medium | 16 hours |

**Total: ~126 hours (3-4 weeks full-time, 6-8 weeks part-time)**

### Risks & Mitigation

**Risk 1: Feature Creep**
- **Mitigation**: Stick to the priority order. Ship Phase 2A first, gather feedback, iterate.

**Risk 2: Voice Training UX Complexity**
- **Problem**: "Train Compressor-1 using production, temperature, pressure" - how to handle 22 available features?
- **Mitigation**: 
  - Default: Auto-select features (empty list) for 97-99% accuracy.
  - Advanced: Multi-turn dialog ("Which features? Say 'production and temperature' or 'auto-select'").

**Risk 3: Multi-Energy Confusion**
- **Problem**: User says "Boiler-1 energy" but Boiler-1 has 3 energy sources (electricity, gas, steam).
- **Mitigation**: 
  - Default to primary energy source (gas for boilers).
  - Clarification: "Did you mean gas, electricity, or steam?"

**Risk 4: Testing Overhead**
- **Problem**: 11 new intents × 10 test cases = 110 new tests.
- **Mitigation**: 
  - Reuse test infrastructure from Week 4.
  - Prioritize happy path tests first, edge cases later.

### Success Criteria (How We Know We're Done)

**Functional:**
- [ ] All 19 endpoint categories have at least one working voice query.
- [ ] 118 test queries (existing) + 50 new queries = 168 total passing.
- [ ] Multi-energy support works for all 4 energy sources.

**Non-Functional:**
- [ ] P50 latency still <200ms (validate new intents don't slow down fast path).
- [ ] No hallucinations in 1000-query stress test.
- [ ] User satisfaction >4.5/5 after UAT with 5 new intent types.

**Documentation:**
- [ ] User manual updated with all new voice commands.
- [ ] API client has docstrings for all new methods.
- [ ] Dialog templates have voice-optimized examples.

### Next Immediate Steps (If We Start Today)

**Day 1 (Today):**
1. Create `system.health.intent` file.
2. Add `get_health()` method to `api_client.py`.
3. Add `system_health.dialog` template.
4. Test with "Is EnMS online?"
5. **Deliverable**: First new intent working end-to-end.

**Day 2:**
6. Upgrade `comparison.intent` to use `/timeseries/multi-machine/energy`.
7. Test with "Compare Compressor-1 and Boiler-1 energy today".
8. **Deliverable**: 2x faster comparison queries.

**Day 3:**
9. Create `anomaly.query.intent` with 3 sub-intents (active, recent, trigger).
10. Add anomaly methods to `api_client.py`.
11. Test with "Any active alerts?"
12. **Deliverable**: Anomaly detection fully voice-enabled.

**By End of Week 1**: +3 intents, 50% → 58% coverage.

---

## 🎯 Bottom Line

**Current State**: Solid foundation (42% coverage), production-ready architecture.

**Goal**: 100% coverage = "Anything and Everything" from the API docs.

**Strategy**: Incremental releases (Phase 2A/B/C/D) to avoid big-bang integration risk.

**Timeline**: 6-8 weeks to full coverage with proper testing.

**My Recommendation**: Start with Phase 2A (System Health + Multi-Machine + Active Anomalies) this week. Ship it. Gather feedback. Then proceed to Phase 2B.

**Why This Matters**: EnMS has 90+ endpoints, but we've focused on the **most common voice queries first** (status, energy, cost). Now we're filling the gaps to handle **advanced analytics** (KPIs, forecasting) and **interactive ML** (training, predictions) - this is where OVOS truly differentiates from a dashboard.
