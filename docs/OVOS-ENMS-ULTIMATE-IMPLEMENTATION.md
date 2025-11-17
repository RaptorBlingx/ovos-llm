# 🚀 ULTIMATE OVOS-ENMS IMPLEMENTATION PLAN
## TRUE SOTA Voice Assistant for WASABI EU Energy Management System

**Project**: Open Voice OS for Industrial Energy Management  
**Version**: 1.0 FINAL  
**Date**: November 17, 2025  
**Status**: Master Plan (Authoritative Roadmap)  

---

## 🧭 Master Plan Control Section

- **Last Updated:** 2025-11-17 14:30 UTC  
- **Overall Progress:** 35% ██████████████░░░░░░ (Week 3 COMPLETE ✅)  
- **Current Phase:** Phase 2 – Fast-Path NLU (Adapt/Heuristics)  
- **Current Milestone:** Week 4 Days 22-23 – Entity Validation  

### Phase Overview

1. [x] **Phase 1 – LLM Core & EnMS Integration** (COMPLETE ✅)  
2. [-] **Phase 2 – Fast-Path NLU (Adapt/Padatious/Heuristics)** (Week 3 COMPLETE ✅)  
3. [ ] **Phase 3 – UX & Observability**  
4. [ ] **Phase 4 – Testing, Optimization & Deployment**  

---

## 🔌 Integration Model (OVOS ↔ ENMS)

- OVOS Core (wake word, STT, TTS, bus, skill loader) is treated as a **black box**.  
- This project delivers a single external skill: **`ovos-skill-enms`**.  
- OVOS discovers and loads the skill via `skill.json` and the normal OVOS skill mechanism.  
- All logic described in this plan (Tiers 1–6, LLM, validator, API client, templates) lives **inside this skill**.  
- No forks or modifications of OVOS Core are required.  

---

## 🎯 Executive Summary

Building a **state-of-the-art voice assistant** that achieves:
- ✅ **95%+ query coverage** - handles simple to complex queries
- ✅ **<200ms P50 latency** - feels instant for 80% of queries
- ✅ **99.5%+ accuracy** - zero hallucination tolerance via validation
- ✅ **100% offline** - no cloud, no GPU required
- ✅ **Voice + Text** - seamless multi-modal input
- ✅ **Industrial-grade** - production reliability with graceful degradation

### Why This is TRUE SOTA

| Aspect | Basic Systems | Our SOTA System |
|--------|--------------|-----------------|
| Architecture | Single LLM approach | Multi-tier adaptive routing |
| Speed | 2-3s per query | <200ms (80% queries) |
| Safety | Trusts LLM output | 99.5%+ hallucination prevention |
| Reliability | Crashes on errors | Circuit breakers, graceful degradation |
| Observability | Print statements | Structured logs, metrics, tracing |
| Testing | Manual only | 90%+ automated coverage |
| Type Safety | Dynamic types | Pydantic + mypy validation |

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │   Voice    │  │    Text    │  │    GUI     │               │
│  │  (Mic)     │  │  (CLI/Web) │  │  (Future)  │               │
│  └────────────┘  └────────────┘  └────────────┘               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  OVOS CORE PLATFORM (v2.1.1)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │     STT      │  │  Wake Word   │  │     TTS      │         │
│  │faster-whisper│  │   (Porcupine)│  │    Piper     │         │
│  │   v1.2.1     │  │              │  │  (ONNX)      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              ENMS SKILL (Our SOTA Implementation)                │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  🧠 TIER 1: QWEN3-1.7B LLM (LLM-First Core)              │  │
│  │  ├─ llama.cpp inference (optimized C++)                   │  │
│  │  ├─ Grammar-constrained JSON output                       │  │
│  │  ├─ 300-500ms latency (CPU only)                          │  │
│  │  ├─ Natural language understanding                        │  │
│  │  └─ 85-95% raw accuracy before validation                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  🛡️ TIER 2: ZERO-TRUST VALIDATOR (Hallucination Blocker)│  │
│  │  ├─ Pydantic schema validation                            │  │
│  │  ├─ Entity whitelist enforcement                          │  │
│  │  ├─ Machine name fuzzy matching                           │  │
│  │  ├─ Time range parsing & validation                       │  │
│  │  ├─ Confidence threshold filtering (>0.85)                │  │
│  │  ├─ API endpoint mapping verification                     │  │
│  │  └─ 99.5%+ hallucination blocking ✅                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                     [Validated]                                  │
│                           │                                      │
│                           ▼                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  🔌 TIER 3: API EXECUTOR (Reliable)                      │  │
│  │  ├─ httpx async client                                    │  │
│  │  ├─ Connection pooling                                    │  │
│  │  ├─ Circuit breaker pattern (prevent cascades)            │  │
│  │  ├─ Automatic retries (exponential backoff)               │  │
│  │  ├─ Timeout management (30s default)                      │  │
│  │  └─ Error recovery & fallback                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  💬 TIER 4: RESPONSE GENERATOR (Voice-Optimized)         │  │
│  │  ├─ Jinja2 template engine                                │  │
│  │  ├─ Voice-optimized formatting                            │  │
│  │  ├─ Context-aware responses                               │  │
│  │  ├─ Number pronunciation (47.98 kW → "forty-eight kW")    │  │
│  │  ├─ 100% data from API (NO LLM generation)                │  │
│  │  └─ <1ms latency ⚡                                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  🎯 TIER 5: FAST-PATH NLU (Adapt / Heuristics / Padatious)│ │
│  │  ├─ Deterministic pattern matching for frequent patterns   │ │
│  │  ├─ Example-based intents for canonical queries            │ │
│  │  ├─ <10ms latency ⚡                                       │ │
│  │  └─ Shares the same Intent schema as LLM parser           │ │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  📊 OBSERVABILITY LAYER (Cross-cutting)                  │  │
│  │  ├─ Structured logging (structlog)                        │  │
│  │  ├─ Prometheus metrics (latency, errors, coverage)        │  │
│  │  ├─ Performance profiling                                 │  │
│  │  ├─ Query analytics & routing stats                       │  │
│  │  └─ Alerting on SLO violations                            │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ENMS API (External System)                    │
│  ├─ 90+ REST endpoints                                           │
│  ├─ Real-time energy data (timeseries)                           │
│  ├─ Machine status & metadata                                    │
│  ├─ Anomaly detection (Isolation Forest)                         │
│  ├─ Forecasting (Prophet)                                        │
│  └─ ISO 50001 compliance reporting                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack (Verified November 2025)

### Core Platform
```yaml
Runtime: Python 3.12 (latest stable, 15% faster than 3.10)
OVOS Core: v2.1.1 (released Nov 5, 2025)
ovos-workshop: v8.0.0

Speech-to-Text: faster-whisper v1.2.1
  - 4-8x faster than base Whisper on CPU
  - ~1GB RAM usage
  - CTranslate2 optimized backend

Text-to-Speech: ovos-tts-plugin-piper (Nov 2025)
  - ONNX Runtime v1.23.2 optimized
  - <100ms generation
  - Multiple voice models

Wake Word: ovos-ww-plugin-precise
  - Or Porcupine for commercial use
```

### LLM Stack
```yaml
Model: Qwen/Qwen3-1.7B-Instruct
  - Size: 1.7B parameters
  - Format: GGUF Q4_K_M (4-bit quantization)
  - Disk: ~1.2GB
  - RAM: 2-3GB during inference
  - Speed: 300-500ms on 4-core CPU

Inference Engine: llama-cpp-python v0.3.16
  - Best CPU performance
  - Grammar-constrained generation (anti-hallucination)
  - Metal/CUDA support (if GPU added later)
  - Active development
```

### Validation & Data
```yaml
Schema Validation: Pydantic v2.10.0
  - Type-safe data validation
  - Fast performance
  - Excellent error messages

Structured Output: llama.cpp grammar constraints
  - Forces valid JSON syntax
  - Mathematically prevents invalid output
  - Zero additional dependencies
```

### HTTP & Async
```yaml
HTTP Client: httpx v0.27.0+
  - Async support (2x faster than requests)
  - HTTP/2 support
  - Connection pooling
  - Advanced timeout management

Retry Logic: tenacity v8.0.0+
  - Exponential backoff
  - Circuit breaker pattern
  - Configurable retry strategies
```

### Observability
```yaml
Logging: structlog v24.0.0+
  - Structured JSON logs
  - Context preservation
  - Fast performance

Metrics: prometheus-client v0.20.0+
  - Latency histograms
  - Error counters
  - Query distribution tracking
```

### Development Tools
```yaml
Linter: Ruff v0.7.0+ (replaces flake8, black, isort)
  - 10-100x faster than pylint
  - All-in-one tool
  - Written in Rust

Type Checker: mypy v1.13.0+
  - Static type checking
  - IDE integration

Testing: pytest v8.0.0+ with pytest-asyncio
  - Unit tests
  - Integration tests
  - Property-based testing (hypothesis)
  - 90%+ coverage target
```

---

## 📅 6-Week Implementation Timeline

### **WEEK 1: Foundation & LLM Core (Phase 1, Part 1)**
**Goal**: External OVOS skill with LLM-based intent parsing and validation, end-to-end EnMS calls.

#### Days 1-2: Environment & Skill Scaffold
- [ ] Install OVOS Core v2.1.1 on development system (deferred to integration phase)
- [ ] Configure faster-whisper v1.2.1 for STT (deferred to integration phase)
- [ ] Configure ovos-tts-plugin-piper for TTS (deferred to integration phase)
- [ ] Test wake word detection (deferred to integration phase)
- [ ] Verify ENMS API access and authentication (deferred to Days 3-4)
- [x] Setup Python 3.12 virtual environment (Python 3.12.3 confirmed)
- [ ] Install core dependencies (deferred to Days 3-4 when needed)
- [x] Create `enms-ovos-skill/` skeleton (`__init__.py`, `skill.json`, `settingsmeta.yaml`)
- [x] Setup structured logging with structlog

#### Days 3-4: ENMS API Client (Tier 3)
- [x] Create `lib/api_client.py` with httpx AsyncClient
- [x] Implement core endpoints used in Phase 1 (health, system stats, machines list, forecast)
- [x] Add timeout and basic retry logic
- [x] Manually test calls against EnMS (curl vs client parity) - API healthy, 8 machines active

#### Days 5-7: LLM Parser + Validation (Tiers 1–2)
- [x] Download Qwen3-1.7B-Q4_K_M.gguf (1.2GB from bartowski/Qwen_Qwen3-1.7B-GGUF)
- [x] Install llama-cpp-python v0.3.16
- [x] Create `lib/qwen3_parser.py` with robust JSON extraction (brace counting)
- [x] Define Pydantic intent models in `lib/models.py`
- [x] Create `lib/validator.py` (8 machine whitelist, fuzzy matching, time parser)
- [x] Wire skill: utterance → LLM parser → validator → EnMS API → response
- [x] Test 20 core queries end-to-end (100% accuracy achieved)

**Week 1 Deliverable**: ✅ LLM-first pipeline working end-to-end (no Adapt/Padatious yet).

---

### **WEEK 2: LLM Refinement, Dialog Templates & Basic Observability (Phase 1, Part 2)**
**Goal**: Robust LLM parsing, voice-optimized responses, and basic logging/metrics.

#### Days 8-10: Prompt & Schema Refinement
- [x] Design concise system prompt and few-shot examples (7 examples)
- [x] Optimize JSON intent schema for EnMS (11 intent types)
- [x] Implement error handling and timeouts for LLM calls
- [x] Achieve stable parsing on 8 representative queries (100% accuracy ✅)

#### Days 11-12: Response Generation (Tier 4)
- [x] Implement `lib/response_formatter.py` with Jinja2
- [x] Add initial dialog templates (8 templates: status, energy, cost, forecast, ranking, comparison, anomaly, factory overview)
- [x] Voice-optimized number and unit formatting (voice_number, voice_unit, voice_time filters)

#### Days 13-14: Observability Basics
- [x] Integrate structlog-based logging (already complete from Week 1)
- [x] Add Prometheus metrics (latency histograms, error counters, routing distribution)
- [x] Measure current latency distribution (P50, P90 via histograms)

**Week 2 Deliverable**: ✅ LLM-based assistant with metrics, voice-optimized responses, 100% accuracy.

---

### **WEEK 3: Fast-Path NLU (Phase 2 – Adapt/Heuristics/Padatious)**
**Goal**: Introduce fast deterministic/heuristic paths to reduce latency for common queries.

#### Days 15-16: Heuristic Router
- [x] Implement `HybridParser` orchestrator in `lib/intent_parser.py`
- [x] Add cheap regex/pattern rules for "top N", simple status, factory overview
- [x] Decide routing policy (fast path vs LLM) and confidence thresholds

#### Days 17-18: Adapt / Padatious (Optional but Recommended)
- [x] Add Adapt and/or Padatious intent definitions for most frequent patterns
- [x] Implement handlers that build the same Intent model as LLM parser
- [x] Ensure behavior parity between Adapt/Padatious and LLM for overlapping cases

#### Days 19-21: Optimization & Tests
- [x] Benchmark latency with router enabled
- [x] Target: majority of frequent queries resolved without LLM
- [x] Add unit tests for router and Adapt/Padatious paths
- [x] Update metrics to track Tier 1/2/3 distribution

**Week 3 Deliverable**: ✅ Hybrid parser with fast path for common queries, LLM as fallback.

---

### **WEEK 4: Validation Layer Hardening (Phase 2)**
**Goal**: 99.5%+ hallucination prevention

#### Days 22-23: Entity Validation
- [ ] Create `validator.py` with ENMSValidator class
- [ ] Implement Pydantic schemas for all intents
- [ ] Build machine name whitelist (8 machines)
- [ ] Implement fuzzy matching for typos
- [ ] Add metric validation (energy, power, cost, etc.)
- [ ] Create time range parser (handles relative & absolute)

#### Days 24-25: Whitelist Enforcement
- [ ] Load machine list from ENMS API
- [ ] Implement auto-refresh (daily at midnight)
- [ ] Add confidence threshold filtering (>0.85)
- [ ] Create suggestion engine ("Did you mean...?")
- [ ] Test all hallucination scenarios
- [ ] Verify rejection of invalid entities

#### Days 26-28: Integration Testing
- [ ] Test all 118 queries from test-questions.md
- [ ] Measure hallucination prevention rate
- [ ] Test clarification dialog flow
- [ ] Verify validation doesn't block valid queries
- [ ] Performance profiling (measure overhead)
- [ ] Edge case handling

**Week 4 Deliverable**: Validated system with 99.5%+ accuracy

---

### **WEEK 5: Response Generation & UX Polish (Phase 3 – UX & Observability)**
**Goal**: Natural, voice-optimized responses

#### Days 29-30: Template System
- [ ] Create Jinja2 template engine
- [ ] Design response templates for all intents:
  - `machine_status.dialog`
  - `energy_query.dialog`
  - `cost_analysis.dialog`
  - `comparison.dialog`
  - `ranking.dialog`
  - `anomaly.dialog`
  - `factory_overview.dialog`

- [ ] Implement voice-optimized formatting:
  - Number pronunciation (47.984 → "forty-eight")
  - Unit handling (kWh → "kilowatt hours")
  - Time formatting ("2 hours ago" vs timestamps)
  - Large number formatting ("5.2 megawatt hours")

- [ ] Test template rendering with real API data

#### Days 31-32: Conversation Context
- [ ] Implement session state management
- [ ] Add follow-up question handling
- [ ] Context carryover ("What about Boiler-1?")
- [ ] Clarification dialogs ("Did you mean...?")
- [ ] Multi-turn conversation support
- [ ] Test conversation flow

#### Days 33-35: UX Polish
- [ ] Add voice feedback ("Let me check...")
- [ ] Progress indicators for slow queries (>500ms)
- [ ] Friendly error messages
- [ ] Confirmation flows for critical actions
- [ ] Help system ("What can you do?")
- [ ] Example queries dialog
- [ ] Test user experience flow

**Week 5 Deliverable**: Production-ready UX

---

### **WEEK 6: Testing, Optimization & Deployment (Phase 4)**
**Goal**: Production-ready with comprehensive testing

#### Days 36-37: Unit Testing
- [ ] Write pytest unit tests for:
  - Adapt parser (50+ test cases)
  - Heuristic router (20+ test cases)
  - LLM parser (30+ test cases)
  - Validator (50+ test cases)
  - API client (30+ test cases)
  - Response formatter (20+ test cases)

- [ ] Achieve 90%+ code coverage
- [ ] Setup pytest-asyncio for async tests
- [ ] Add property-based tests (hypothesis)

#### Days 38-39: Integration Testing
- [ ] End-to-end query testing (118 queries)
- [ ] Multi-turn conversation tests
- [ ] Error scenario testing (API down, timeout, etc.)
- [ ] Performance benchmarking:
  - P50 latency < 200ms
  - P90 latency < 800ms
  - P99 latency < 1500ms
  - Memory < 4GB
  - CPU < 50% average

- [ ] Load testing (100 queries/minute)
- [ ] Stress testing (24-hour continuous operation)

#### Days 40-41: User Acceptance Testing
- [ ] Recruit 10 test users
- [ ] Each user performs 20 queries
- [ ] Collect metrics:
  - Intent detection accuracy
  - Response time satisfaction
  - Voice quality rating
  - Overall satisfaction (>4.5/5 target)

- [ ] Gather qualitative feedback
- [ ] Identify improvement areas
- [ ] Fix critical issues

#### Day 42: Production Deployment
- [ ] Deploy to production hardware
- [ ] Configure systemd service for auto-start
- [ ] Setup log rotation
- [ ] Configure Prometheus metrics export
- [ ] Setup Grafana dashboards (optional)
- [ ] Create monitoring alerts
- [ ] Write deployment documentation
- [ ] Create user manual
- [ ] Record demo video

**Week 6 Deliverable**: Production-ready SOTA OVOS system

---

## 📂 Project Structure

```
enms-ovos-skill/
├── __init__.py                    # OVOSSkill entry point
├── skill.json                     # Skill metadata
├── settingsmeta.yaml              # Settings configuration
├── requirements.txt               # Python dependencies
├── README.md                      # Project documentation
│
├── intent/                        # Adapt intent definitions
│   ├── machine_status.intent
│   ├── energy_query.intent
│   ├── power_query.intent
│   ├── cost_query.intent
│   ├── comparison.intent
│   ├── ranking.intent
│   ├── anomaly.intent
│   └── factory_overview.intent
│
├── entities/                      # Entity definitions
│   ├── machine.entity             # 8 machine names
│   ├── metric.entity              # Metrics
│   ├── time_range.entity          # Time expressions
│   └── number.entity              # Numbers for rankings
│
├── locale/                        # Localization
│   └── en-us/
│       ├── dialog/                # Response templates
│       │   ├── machine_status.dialog
│       │   ├── energy_query.dialog
│       │   ├── cost_analysis.dialog
│       │   ├── comparison.dialog
│       │   ├── ranking.dialog
│       │   ├── anomaly.dialog
│       │   ├── factory_overview.dialog
│       │   ├── checking.dialog    # "Let me check..."
│       │   ├── error.general.dialog
│       │   └── help.dialog
│       │
│       └── vocab/
│           ├── energy.voc         # "energy", "power", "consumption"
│           ├── status.voc         # "status", "running", "online"
│           ├── cost.voc           # "cost", "expense", "price"
│           └── comparison.voc     # "compare", "vs", "versus"
│
├── lib/                           # Core implementation
│   ├── __init__.py
│   │
│   ├── intent_parser.py           # Hybrid parser orchestrator
│   │   ├── HybridParser           # Main parser class
│   │   ├── AdaptParser            # Tier 1 wrapper
│   │   ├── HeuristicRouter        # Tier 2 quick patterns
│   │   └── Qwen3Parser            # Tier 3 LLM
│   │
│   ├── validator.py               # Hallucination prevention
│   │   ├── ENMSValidator          # Main validator
│   │   ├── EntityValidator        # Entity whitelisting
│   │   ├── TimeRangeParser        # Time parsing
│   │   └── ConfidenceScorer       # Confidence thresholds
│   │
│   ├── api_client.py              # ENMS API integration
│   │   ├── ENMSClient             # Async HTTP client
│   │   ├── EndpointMapper         # Intent → API URL
│   │   ├── CircuitBreaker         # Failure prevention
│   │   └── RetryHandler           # Exponential backoff
│   │
│   ├── response_formatter.py     # Response generation
│   │   ├── TemplateEngine         # Jinja2 wrapper
│   │   ├── VoiceOptimizer         # Voice-friendly formatting
│   │   └── ContextManager         # Session state
│   │
│   ├── models.py                  # Pydantic data models
│   │   ├── Intent                 # Intent structure
│   │   ├── Entities               # Entity structure
│   │   ├── APIResponse            # API response models
│   │   └── ValidationResult       # Validation output
│   │
│   └── utils.py                   # Utilities
│       ├── time_parser.py         # Time expressions
│       ├── number_formatter.py    # Voice-optimized numbers
│       └── logger.py              # Structured logging
│
├── models/                        # LLM models
│   └── qwen3-1.7b-instruct-q4_k_m.gguf
│
├── config/                        # Configuration files
│   ├── enms_api.yaml              # API endpoints and settings
│   ├── llm_config.yaml            # LLM parameters
│   ├── validation.yaml            # Validation rules
│   └── prompts.yaml               # System prompts
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_adapt_parser.py       # Unit tests for Adapt
│   ├── test_heuristic_router.py   # Unit tests for router
│   ├── test_llm_parser.py         # Unit tests for LLM
│   ├── test_validator.py          # Unit tests for validator
│   ├── test_api_client.py         # Unit tests for API
│   ├── test_response_formatter.py # Unit tests for formatter
│   ├── test_integration.py        # End-to-end tests
│   ├── test_queries.yaml          # 118 test queries
│   └── conftest.py                # Pytest fixtures
│
├── docs/                          # Documentation
│   ├── API_REFERENCE.md           # API documentation
│   ├── USER_GUIDE.md              # User manual
│   ├── DEVELOPMENT.md             # Developer guide
│   ├── ARCHITECTURE.md            # System architecture
│   └── DEPLOYMENT.md              # Deployment guide
│
├── scripts/                       # Utility scripts
│   ├── benchmark_llm.py           # LLM performance testing
│   ├── update_whitelists.py       # Refresh entity lists
│   └── generate_test_report.py    # Test results analysis
│
└── .github/                       # CI/CD
    └── workflows/
        ├── test.yml               # Run tests on PR
        └── deploy.yml             # Deploy to production
```

---

## 🎯 Success Metrics & KPIs

### Performance Targets

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Query Coverage** | 95%+ | 118 test queries pass |
| **P50 Latency** | <200ms | 80% via Adapt (<10ms) |
| **P90 Latency** | <800ms | 20% via LLM (~500ms) |
| **P99 Latency** | <1500ms | Complex edge cases |
| **Accuracy** | 99%+ | Correct intent + entities + API call |
| **Hallucination Rate** | <0.5% | Validation rejection rate |
| **Uptime** | 99%+ | 24/7 operation without crashes |
| **User Satisfaction** | >4.5/5 | UAT with 10+ users |
| **Memory Usage** | <4GB | Continuous monitoring |
| **CPU Usage** | <50% avg | On 4-core system |

### Testing Methodology

**Unit Tests** (70% of test effort):
- 200+ test cases covering all modules
- 90%+ code coverage
- Fast execution (<10s total)
- Run on every commit

**Integration Tests** (20% of test effort):
- 118 queries from test-questions.md
- End-to-end flow testing
- API mock server for reliability
- Run before deployment

**User Acceptance Testing** (10% of test effort):
- 10 users × 20 queries = 200 real queries
- Measure accuracy, speed, satisfaction
- Qualitative feedback collection
- Run before major releases

**Stress Testing**:
- 100 queries/minute sustained for 1 hour
- Memory leak detection (24h continuous operation)
- Error rate monitoring
- Recovery time measurement

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] All unit tests passing (90%+ coverage)
- [ ] All integration tests passing (118/118 queries)
- [ ] Performance benchmarks met (P50 < 200ms)
- [ ] User acceptance criteria passed (>4.5/5)
- [ ] Documentation complete (API, User Guide, Architecture)
- [ ] Security review done (no hardcoded credentials)
- [ ] Dependency audit (no vulnerabilities)

### Production Hardware Requirements
- [ ] CPU: 4+ cores (ARM/x86_64)
- [ ] RAM: 8GB (4GB minimum with swap)
- [ ] Storage: 10GB available
- [ ] OS: Linux (Ubuntu 22.04+, Raspberry Pi OS)
- [ ] Network: Access to ENMS API
- [ ] Audio: Microphone + speakers for voice

### Installation
- [ ] Install OVOS Core v2.1.1
- [ ] Install skill from repository
- [ ] Download Qwen3-1.7B model
- [ ] Configure ENMS API endpoints
- [ ] Test wake word activation
- [ ] Test sample queries
- [ ] Configure systemd service
- [ ] Enable auto-start on boot

### Post-Deployment
- [ ] Monitor error logs (first 24h critical)
- [ ] Track query distribution (Tier 1/2/3 usage)
- [ ] Measure response times (verify SLOs)
- [ ] Collect user feedback
- [ ] Setup alerting (email/Slack on errors)
- [ ] Schedule weekly maintenance window

---

## 📊 Query Distribution Prediction

Based on test-questions.md analysis:

```
┌─────────────────────────────────────────────────────────────┐
│                  Query Distribution by Tier                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  TIER 1 (Adapt): 70-80% coverage                            │
│  ████████████████████████████████████████████████████ 75%   │
│  - Simple machine queries                                    │
│  - Status checks                                             │
│  - Single metric queries                                     │
│  - Common time ranges                                        │
│  Latency: <10ms                                             │
│                                                               │
│  TIER 2 (Heuristic): 10-15% coverage                        │
│  ████████████ 12%                                           │
│  - "top N" queries                                           │
│  - Comparison queries                                        │
│  - Factory-wide queries                                      │
│  Latency: <5ms                                              │
│                                                               │
│  TIER 3 (LLM): 10-15% coverage                              │
│  ████████████ 13%                                           │
│  - Complex temporal queries                                  │
│  - Multi-entity extraction                                   │
│  - Ambiguous queries                                         │
│  Latency: 300-500ms                                         │
│                                                               │
│  Average Latency: ~120ms (weighted)                         │
│  User Perception: "Instant" ⚡                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔒 Hallucination Prevention Strategy

### The Critical Principle

**LLM NEVER generates final answers. It only parses intent into structured data that gets validated before execution.**

### Five-Layer Defense

1. **Structured Output Only** - LLM outputs JSON, not natural language
2. **Grammar Constraints** - Physically impossible to generate invalid JSON
3. **Schema Validation** - Pydantic enforces type safety
4. **Entity Whitelisting** - Only known machines, metrics, APIs allowed
5. **Template Responses** - Final answer uses real API data, not LLM generation

### Example Flow

```
User: "What's the power consumption of SuperCompressor-9000?"
                              ↓
LLM: {"intent": "energy_query", "machine": "SuperCompressor-9000"}
                              ↓
Validator: ❌ REJECTED - "SuperCompressor-9000" not in whitelist
                              ↓
Response: "I don't have a machine called 'SuperCompressor-9000'. 
          Did you mean Compressor-1 or Compressor-EU-1?"
```

**Result**: Hallucination blocked before affecting user or system.

---

## 🎓 Development Best Practices

### Code Quality Standards

**Type Safety**:
```python
from typing import Dict, Optional
from pydantic import BaseModel

class Intent(BaseModel):
    """Type-safe intent structure"""
    intent: str
    machine: Optional[str] = None
    metric: Optional[str] = None
    confidence: float

# Usage - automatically validated
intent = Intent(intent="energy_query", confidence=0.95)
```

**Async-First**:
```python
import asyncio
import httpx

async def execute_query(intent: Intent) -> Response:
    """Non-blocking API calls"""
    async with httpx.AsyncClient() as client:
        response = await client.get(build_url(intent))
        return response.json()
```

**Structured Logging**:
```python
import structlog

logger = structlog.get_logger()

# Automatically includes context
logger.info("query_processed", 
            intent=intent.intent,
            tier="adapt",
            latency_ms=12.5)
```

**Error Handling**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), 
       wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_enms_api(endpoint: str) -> Dict:
    """Automatic retries with exponential backoff"""
    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint, timeout=30.0)
        response.raise_for_status()
        return response.json()
```

### Testing Patterns

**Property-Based Testing**:
```python
from hypothesis import given, strategies as st

@given(st.text())
def test_validator_rejects_invalid_machines(query: str):
    """Property: Validator must reject ALL invalid machine names"""
    result = validator.validate({"machine": query})
    if result.valid:
        assert result.machine in KNOWN_MACHINES
```

**Async Test Fixtures**:
```python
import pytest
import pytest_asyncio

@pytest_asyncio.fixture
async def api_client():
    """Reusable async test fixture"""
    client = ENMSClient()
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_energy_query(api_client):
    result = await api_client.get_energy("Compressor-1")
    assert result.power_kw > 0
```

---

## 🔄 Maintenance & Evolution

### Weekly Tasks
- [ ] Review error logs for patterns
- [ ] Check performance metrics (latency, errors)
- [ ] Analyze query distribution (Tier 1/2/3 usage)
- [ ] Monitor user feedback
- [ ] Minor bug fixes and optimizations

### Monthly Tasks
- [ ] Update machine whitelist from API
- [ ] Performance optimization based on usage data
- [ ] Promote common LLM patterns to Adapt rules
- [ ] Review and update documentation
- [ ] Security dependency updates

### Quarterly Tasks
- [ ] Major version update planning
- [ ] New feature development
- [ ] User training sessions
- [ ] Architecture review and optimization
- [ ] Model fine-tuning (if needed)

### Continuous Improvement Loop

```
1. Monitor → 2. Analyze → 3. Optimize → 4. Deploy → [Repeat]
     │              │             │            │
     │              │             │            └── A/B testing
     │              │             └── Code changes, rule updates
     │              └── Identify bottlenecks, patterns
     └── Logs, metrics, user feedback
```

---

## 💡 Advanced Optimizations (Optional)

### Performance Enhancements

**1. Response Caching**:
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_machine_status(machine: str, time: datetime) -> Dict:
    """Cache recent queries (5-minute TTL)"""
    return api_client.get_status(machine)
```

**2. Predictive Preloading**:
```python
async def preload_common_data():
    """Warm cache with likely queries during idle time"""
    await asyncio.gather(
        api_client.get_factory_summary(),
        api_client.get_top_consumers(limit=5),
        api_client.get_recent_anomalies()
    )
```

**3. Model Quantization Upgrade**:
- Current: Q4_K_M (4-bit)
- Upgrade: Q8_0 (8-bit) if RAM allows
- Benefit: 10-15% better accuracy, 20% slower

**4. Speculative Decoding**:
```python
# Use smaller draft model + main model
# 1.5-2x faster generation
# Requires llama.cpp advanced features
```

### Feature Enhancements

**1. Multi-Language Support**:
- Add `locale/de-de/` for German
- Add `locale/fr-fr/` for French
- OVOS handles language switching automatically

**2. Proactive Alerts**:
```python
async def monitor_anomalies():
    """Push notifications for critical events"""
    while True:
        anomalies = await api_client.get_recent_anomalies()
        if any(a.severity == "critical" for a in anomalies):
            await speak("Alert: Critical anomaly detected in Boiler-1")
        await asyncio.sleep(300)  # Check every 5 minutes
```

**3. Conversational Memory**:
```python
class ConversationContext:
    """Remember last N queries for context"""
    def __init__(self, max_history=5):
        self.history = []
    
    def add(self, query: str, intent: Intent):
        self.history.append((query, intent))
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
    def get_last_machine(self) -> Optional[str]:
        """Enable 'what about that one?' queries"""
        for query, intent in reversed(self.history):
            if intent.machine:
                return intent.machine
        return None
```

---

## 📚 Documentation Deliverables

### Technical Documentation
1. **Architecture Guide** (`docs/ARCHITECTURE.md`)
   - System design and component interaction
   - Data flow diagrams
   - Tier routing logic

2. **API Reference** (`docs/API_REFERENCE.md`)
   - All classes and functions
   - Type signatures and examples
   - Error handling patterns

3. **Development Guide** (`docs/DEVELOPMENT.md`)
   - Setup instructions
   - Coding standards
   - Testing procedures
   - Contribution guidelines

4. **Deployment Guide** (`docs/DEPLOYMENT.md`)
   - Hardware requirements
   - Installation steps
   - Configuration options
   - Troubleshooting

### User Documentation
1. **Quick Start Guide**
   - Installation in 5 minutes
   - First query walkthrough
   - Basic usage examples

2. **User Manual** (`docs/USER_GUIDE.md`)
   - Complete feature reference
   - 100+ example queries
   - Voice tips and tricks
   - FAQ section

3. **Video Tutorials**
   - Installation demo (5 min)
   - Query examples (10 min)
   - Troubleshooting (5 min)

---

## 🎯 Final Definition of Success

**The system achieves TRUE SOTA when:**

1. ✅ **Users prefer voice over dashboard** - 50%+ of queries via voice
2. ✅ **Query accuracy is 99%+** - Validated in production logs
3. ✅ **Response feels instant** - P50 < 200ms (subjective "instant")
4. ✅ **Zero hallucination incidents** - No false data in production
5. ✅ **System runs 24/7** - No manual intervention required
6. ✅ **Users say "it just works"** - >4.5/5 satisfaction rating
7. ✅ **Coverage is comprehensive** - 95%+ queries handled
8. ✅ **Maintenance is minimal** - <2 hours/week after stabilization

---

## 🚀 Ready to Build

### Immediate Next Steps

1. **Review & Approve** (Today)
   - Review this plan with stakeholders
   - Confirm technical decisions
   - Approve timeline and resources

2. **Setup Environment** (Day 1)
   - Install OVOS Core
   - Configure development system
   - Verify ENMS API access

3. **Start Phase 1** (Day 2)
   - Create skill scaffold
   - Define first 3 intents
   - Test basic query

4. **Daily Standups**
   - Track progress against timeline
   - Identify blockers early
   - Adjust plan as needed

5. **Weekly Demos**
   - Show progress to stakeholders
   - Gather feedback
   - Validate approach

### Resources Needed

**Hardware**:
- Development machine: 8GB+ RAM, 4+ CPU cores
- Test device: Same as production target
- Optional: Pi 4/5 for testing

**Access**:
- ENMS API credentials
- GitHub repository (for code hosting)
- Documentation platform (wiki, Notion, etc.)

**Time Commitment**:
- Full-time: 6 weeks (recommended)
- Part-time: 12 weeks (20 hours/week)

**Team**:
- 1 developer (primary)
- 1 QA tester (part-time)
- 10 users for UAT (1 hour each)

---

## 🎖️ This is Not a Toy Project

This is an **industrial-grade, production-ready, state-of-the-art voice assistant** that:

- Follows **2025 best practices** (not outdated tutorials)
- Uses **actively maintained technologies** (verified November 2025)
- Implements **multi-tier adaptive routing** (not single LLM approach)
- Enforces **zero-trust validation** (99.5%+ hallucination prevention)
- Provides **production reliability** (circuit breakers, graceful degradation)
- Includes **comprehensive observability** (structured logs, metrics, tracing)
- Has **90%+ test coverage** (unit, integration, E2E, property-based)
- Meets **real SLOs** (P50 < 200ms, 99%+ uptime)

**This is TRUE SOTA. Let's build it! 🚀**

---
## 🤖 Agent Workflow (For AI Implementation Agents)

This section defines how an AI agent should use this master plan during implementation.

### Core Loop

1. **Open `[Master Plan].md`**  
  Always treat this file as the single source of truth for phases, milestones, and tasks.

2. **Locate the current milestone**  
  Use the **Master Plan Control Section** at the top to find:  
  - `Current Phase`  
  - `Current Milestone` (e.g., "Week 1 – Skill Scaffold + LLM Parser + Validator").

3. **Work through tasks in listed order**  
  For the active week/milestone, process checklist items top-to-bottom unless there is a hard dependency that requires reordering.

4. **Mark completed tasks with `[x]`**  
  Whenever a task is finished, immediately update its checkbox from `[ ]` to `[x]` in this file.

5. **Append key decisions or notes to `Decision_Log.md`**  
  - If a new trade-off, design change, or deviation from the plan occurs, append a short entry to `Decision_Log.md` with:  
    `YYYY-MM-DD – [Phase/Week] – Decision – Rationale`.  
  - Keep this log concise but complete.

6. **Update the `Last Updated` timestamp**  
  After any non-trivial set of changes (e.g., finishing a task or milestone), update the **Last Updated** field in the Master Plan Control Section.

7. **Update your TODO list**  
  Keep the agent’s internal TODO/task list in sync with:  
  - The current week’s checklist items.  
  - Any newly discovered subtasks that support these items.

8. **Consult the `docs` folder when needed**  
  - Before implementing larger components, check `docs/` (e.g., `ARCHITECTURE.md`, `API_REFERENCE.md`, `DEVELOPMENT.md`) for additional context.  
  - Ensure that new code and changes remain aligned with the documented architecture.

9. **After finishing the current task or milestone, immediately move on**  
  - Do not wait for a new user prompt if the next task/milestone is clearly defined in this plan.  
  - When a milestone is completed, mark its checkbox in the **Phase Overview** and proceed to the next milestone or phase.

---

### After Each Milestone

- Verify that all **completion criteria** for the week/milestone are satisfied.  
- If a metrics dashboard exists, update or export relevant metrics (latency, coverage, test pass rate).  
- Adjust the **Overall Progress** and, if appropriate, update phase checkboxes in the **Phase Overview**.  
- Commit changes using a clear message, e.g. `"Milestone: Week 1 – LLM Core completed"`.  
- Ensure related documentation in `docs/` is updated if any architecture or behavior changed.

---

### At Phase Completion

- Recalculate and update **Overall Progress**.  
- Summarize key metrics achieved in that phase (accuracy, latency, coverage).  
- Add a short **Lessons Learned** subsection at the end of this file or in a dedicated `LESSONS_LEARNED.md`.  
- Review and update any related `.md` files in `docs/` that depend on this phase’s work.

---

### Agent Responsibilities

- Track progress and detect **incomplete steps** within the current milestone.  
- Remind when **milestone/phase transitions** occur (e.g., Week 1 → Week 2).  
- Suggest concise commit messages and progress summaries when milestones are completed.  
- Flag outdated timestamps, missing Decision Log entries, or stale TODOs.  
- Proactively move to the **next milestone** as defined in this plan when the current one is done.

---

**Questions? Need clarification? Ready to start coding?**
