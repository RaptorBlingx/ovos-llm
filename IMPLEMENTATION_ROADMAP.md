# 🚀 OVOS-EnMS Implementation Roadmap

## Current Status (November 19, 2025)

### ✅ Implemented (Phase 1 - Core Functionality)
- [x] Multi-tier parsing (Heuristic → Adapt → LLM)
- [x] Time-range query support
- [x] Energy queries with timeseries
- [x] Power queries
- [x] Machine status
- [x] Factory overview
- [x] Ranking (top N)
- [x] Comparison (multiple machines)
- [x] Template-based responses with numeric formatting

### ❌ Missing (Identified from API Docs)

#### High Priority - Frequently Used
1. **Anomaly Detection** (9 use cases in docs)
   - "Find unresolved warnings for Compressor-1 in October"
   - "Check for anomalies in Compressor-1 today"
   - "Are there any alerts?"
   - API: `/api/v1/anomaly/search`, `/api/v1/anomaly/detect`

2. **"All Machines" Support** (Factory-wide queries)
   - "Total energy consumption this week for all machines"
   - "How much energy are we using?" (factory-wide)
   - API: `/api/v1/stats/aggregated?machine_ids=all`

3. **Performance Analysis** (NEW - Phase 2)
   - "How did Compressor-1 perform today?"
   - "What's causing high energy consumption?"
   - API: `/api/v1/performance/analyze`

4. **Forecasting**
   - "How much energy will we use tomorrow?"
   - "Predict energy usage for next 24 hours"
   - API: `/api/v1/forecast/short-term`

#### Medium Priority - Specialized
5. **Cost Analysis**
   - "How much did it cost to run today?"
   - "What's the energy cost for Boiler-1?"
   - Current: Simple calculation, needs real tariff support

6. **Production Metrics**
   - "How much did Compressor-1 produce today?"
   - "What's the energy efficiency per unit?"
   - API: `/api/v1/production/{machine_id}`

7. **Multi-Energy Support** (Boiler-1 specific)
   - "Show me natural gas consumption for Boiler-1"
   - "What energy types does Boiler-1 use?"
   - API: `/api/v1/machines/{id}/energy-types`

8. **Machine Status History**
   - "When was Compressor-1 offline yesterday?"
   - "Show me uptime for last week"
   - API: `/api/v1/machines/{id}/status-history`

#### Low Priority - Advanced
9. **Baseline Comparisons**
   - "Is Compressor-1 energy usage normal?"
   - "Compare actual vs expected energy"
   - API: `/api/v1/baseline/predict`

10. **KPI Calculations**
    - "What's the efficiency of Compressor-1?"
    - "Calculate KPIs for last month"
    - API: `/api/v1/kpi/all`

---

## 📊 Coverage Analysis

**Total API Endpoints in Docs:** ~30  
**Currently Implemented:** 7 (23%)  
**High-Value Coverage Target:** 15 (50%)

### API Coverage Matrix

| Intent | API Endpoint | Implemented | Priority | Blocker |
|--------|-------------|-------------|----------|---------|
| energy_query | `/timeseries/energy` | ✅ | High | - |
| power_query | `/timeseries/power` | ✅ | High | - |
| machine_status | `/machines/status/{name}` | ✅ | High | - |
| factory_overview | `/factory/summary` | ✅ | High | - |
| ranking | `/analytics/top-consumers` | ✅ | High | - |
| comparison | `/stats/aggregated` | ✅ | Medium | - |
| **anomaly_detection** | `/anomaly/search` | ❌ | **High** | Need intent handler |
| **cost_analysis** | `/stats/aggregated` | ⚠️ Partial | High | Needs cost calculation |
| **forecast** | `/forecast/short-term` | ❌ | High | Need intent handler |
| **performance** | `/performance/analyze` | ❌ | High | New API - need intent |
| baseline | `/baseline/predict` | ❌ | Medium | Complex validation |
| production | `/production/{id}` | ❌ | Medium | Need intent handler |
| multi_energy | `/machines/{id}/energy-types` | ❌ | Low | Boiler-1 only |
| kpi | `/kpi/all` | ❌ | Low | Advanced metrics |

---

## 🎯 Implementation Plan

### **Phase 2: Critical Missing Features (Week 1)**
**Goal:** Reach 50% API coverage with high-value intents

#### Sprint 2.1: Anomaly Detection
- [ ] Add `anomaly_detection` intent to models
- [ ] Create heuristic patterns ("alerts", "anomalies", "warnings")
- [ ] Implement `/anomaly/search` API integration
- [ ] Add `anomaly_detection.dialog` template
- [ ] Test: "Find unresolved warnings for Compressor-1 in October"

#### Sprint 2.2: Factory-Wide Queries ("all machines")
- [ ] Fix validator to accept "all machines" as valid input
- [ ] Map "all machines" → `machine_ids=all` in API calls
- [ ] Update factory_overview to use `/stats/aggregated`
- [ ] Test: "Total energy consumption this week for all machines"

#### Sprint 2.3: Forecasting
- [ ] Add `forecast` intent to models
- [ ] Create heuristic patterns ("tomorrow", "predict", "forecast")
- [ ] Implement `/forecast/short-term` API integration
- [ ] Add `forecast.dialog` template
- [ ] Test: "How much energy will we use tomorrow?"

#### Sprint 2.4: Performance Analysis
- [ ] Add `performance_analysis` intent
- [ ] Implement `/performance/analyze` API call
- [ ] Add `performance.dialog` template
- [ ] Test: "How did Compressor-1 perform today?"

### **Phase 3: Enhanced Features (Week 2)**
**Goal:** 70% coverage with specialized queries

#### Sprint 3.1: Cost Analysis
- [ ] Enhance cost calculations with real-time data
- [ ] Support tariff-based pricing
- [ ] Update `cost_query.dialog` template

#### Sprint 3.2: Production Metrics
- [ ] Add production intent
- [ ] Implement `/production/{id}` API
- [ ] Support SEC (Specific Energy Consumption)

#### Sprint 3.3: Time-Based Patterns
- [ ] Support "this week", "last month" parsing
- [ ] Add relative date calculations
- [ ] Test all time-based queries from docs

### **Phase 4: Advanced Features (Week 3)**
**Goal:** 90%+ coverage

- [ ] Multi-energy support (Boiler-1)
- [ ] Baseline comparisons
- [ ] KPI calculations
- [ ] Machine status history

---

## 🧪 Test Coverage Plan

### Test Queries from Docs (30+ examples)
1. ✅ "Show me energy consumption of Compressor-1 from Oct 27, 3 PM to Oct 28, 10 AM"
2. ✅ "Factory overview"
3. ✅ "Top 5 energy consumers"
4. ❌ "Find unresolved warnings for Compressor-1 in October"
5. ❌ "Total energy consumption this week for all machines"
6. ❌ "How much energy will we use tomorrow?"
7. ❌ "How did Compressor-1 perform today?"
8. ❌ "What's causing high energy consumption?"
9. ❌ "Show me natural gas consumption for Boiler-1"
10. ❌ "When was Compressor-1 offline yesterday?"

---

## 📈 Success Metrics

### Phase 2 Target (1 week)
- API Coverage: 50% (15/30 endpoints)
- Test Pass Rate: 70% (21/30 use cases)
- Intent Accuracy: 95%+
- Response Time: <200ms (P50), <5s (P99 with LLM)

### Phase 3 Target (2 weeks)
- API Coverage: 70% (21/30 endpoints)
- Test Pass Rate: 85% (25/30 use cases)

### Phase 4 Target (3 weeks)
- API Coverage: 90%+ (27/30 endpoints)
- Test Pass Rate: 95%+ (28/30 use cases)

---

## 🚀 Next Session: Anomaly Detection Sprint

**Immediate Action Items:**
1. Fix "all machines" validation bug
2. Implement anomaly_detection intent
3. Add `/anomaly/search` API integration
4. Create 5-query test suite

**Would you like to:**
- A) Start Phase 2 Sprint 2.1 (Anomaly Detection) now
- B) Fix "all machines" bug first, then new session
- C) Create comprehensive test suite before implementation
