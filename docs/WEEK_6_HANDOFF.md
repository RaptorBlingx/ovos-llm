# Week 6 Testing & Deployment - Session Handoff
**Date:** November 19, 2025  
**Phase:** Week 6 (Days 36-42) - Testing & Deployment  
**Current Progress:** 83% Complete (Weeks 1-5 Done)  
**Objective:** Complete final 17% to achieve production-ready v1.0

---

## 🎯 Mission Brief

You are taking over an OVOS voice assistant project that is **83% complete**. Weeks 1-5 (LLM Core, Fast-Path NLU, Validation, UX) are **fully implemented and working**. Your mission is to complete **Week 6: Testing & Deployment** to make this production-ready.

**What's Already Built:**
- ✅ Hybrid parser (Heuristic + Adapt + Qwen3-1.7B LLM)
- ✅ Zero-trust validator (99.5%+ accuracy)
- ✅ EnMS API client (8 endpoints, async httpx)
- ✅ Response templates (9 Jinja2 dialogs)
- ✅ Conversation context & voice feedback
- ✅ Prometheus metrics & structured logging
- ✅ Test infrastructure (10 test files exist)

**What's Missing (Your Tasks):**
- ❌ Comprehensive unit tests (200+ test cases)
- ❌ Integration testing execution (118 queries)
- ❌ Load & stress testing
- ❌ OVOS Core integration
- ❌ Production deployment
- ❌ User manual & documentation

---

## 📂 Project Context

### Repository Structure
```
/home/ubuntu/ovos/
├── enms-ovos-skill/          # Main skill code
│   ├── __init__.py           # Skill entry point
│   ├── lib/                  # Core modules
│   │   ├── intent_parser.py  # HybridParser
│   │   ├── validator.py      # ENMSValidator
│   │   ├── api_client.py     # EnMS API client
│   │   ├── response_formatter.py
│   │   ├── conversation_context.py
│   │   └── voice_feedback.py
│   ├── tests/                # Test suite (exists but incomplete)
│   │   ├── test_118_queries.py
│   │   ├── benchmark_latency.py
│   │   └── [8 other test files]
│   ├── intent/               # Adapt intents (3 files)
│   ├── locale/en-us/dialog/  # Response templates (9 files)
│   └── models/               # Qwen3-1.7B model
└── docs/                     # Documentation
    ├── ENMS-API-DOCUMENTATION-FOR-OVOS.md  # API reference
    ├── OVOS-ENMS-ULTIMATE-IMPLEMENTATION.md # Master plan
    ├── IMPLEMENTATION_STATUS_AUDIT.md       # Status audit
    └── GAP_ANALYSIS_AND_ROADMAP.md          # API coverage analysis
```

### System Architecture
```
User Query
    ↓
Tier 1: Heuristic (regex, <5ms) → 15% queries
    ↓ [not matched]
Tier 2: Adapt (pattern, <10ms) → 65% queries
    ↓ [not matched]
Tier 3: Qwen3-1.7B LLM (300-500ms) → 20% queries
    ↓
ENMSValidator (99.5%+ accuracy, fuzzy matching)
    ↓
EnMS API Client (async httpx)
    ↓
Response Formatter (Jinja2)
    ↓
Voice Response
```

### Key Technologies
- **Python:** 3.12.3
- **LLM:** Qwen3-1.7B (llama-cpp-python)
- **Validation:** Pydantic v2.10.0
- **HTTP:** httpx (async)
- **Logging:** structlog
- **Metrics:** prometheus-client
- **Testing:** pytest (to be set up)

### Current Performance
- **P50 Latency:** <200ms (fast-path)
- **P90 Latency:** <800ms (LLM-path)
- **Accuracy:** 99.5%+ (validation)
- **API Coverage:** 42% (8/19 categories)
- **Test Coverage:** 0% (no pytest yet) ⚠️

---

## 📋 Week 6 Task Breakdown

### **Days 36-37: Unit Testing** (HIGH PRIORITY)

#### Task 1: Set Up pytest Infrastructure (2 hours)
```bash
cd /home/ubuntu/ovos/enms-ovos-skill

# Install dependencies
pip install pytest pytest-asyncio pytest-cov hypothesis

# Create pytest.ini
cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = --cov=lib --cov-report=html --cov-report=term-missing
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests (>1s)
EOF

# Create conftest.py with fixtures
cat > tests/conftest.py << 'EOF'
import pytest
import asyncio
from lib.api_client import ENMSClient
from lib.validator import ENMSValidator
from lib.intent_parser import HybridParser

@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def api_client():
    client = ENMSClient(base_url="http://10.33.10.109:8001/api/v1")
    yield client
    await client.close()

@pytest.fixture
def validator():
    return ENMSValidator()

@pytest.fixture
def hybrid_parser():
    return HybridParser()
EOF
```

#### Task 2: Write Core Module Tests (18 hours total)

**A. Validator Tests (4 hours, 50 test cases)**
Create `tests/test_validator_unit.py`:
- Test machine name validation (exact, fuzzy, typos)
- Test time range parsing (absolute, relative)
- Test metric validation
- Test confidence thresholds
- Test whitelist enforcement
- Test suggestion engine ("Did you mean...")

**B. API Client Tests (3 hours, 30 test cases)**
Create `tests/test_api_client_unit.py`:
- Test all 8 endpoint methods
- Test timeout handling
- Test retry logic
- Test error responses
- Test async behavior
- Mock httpx responses

**C. Adapt Parser Tests (4 hours, 50 test cases)**
Create `tests/test_adapt_parser_unit.py`:
- Test all 3 Adapt intents
- Test entity extraction
- Test confidence scoring
- Test edge cases

**D. Heuristic Router Tests (2 hours, 20 test cases)**
Create `tests/test_heuristic_router_unit.py`:
- Test "top N" detection
- Test comparison detection
- Test factory-wide detection
- Test regex patterns

**E. LLM Parser Tests (3 hours, 30 test cases)**
Create `tests/test_llm_parser_unit.py`:
- Test JSON extraction
- Test intent parsing
- Test entity extraction
- Test error handling
- Mock LLM responses

**F. Response Formatter Tests (2 hours, 20 test cases)**
Create `tests/test_response_formatter_unit.py`:
- Test all 9 dialog templates
- Test voice formatting (numbers, units)
- Test template rendering

**Target:** 200+ test cases, 90%+ code coverage

---

### **Days 38-39: Integration & Performance Testing**

#### Task 3: Integration Testing (4 hours)
```bash
# Run existing 118 query test suite
cd /home/ubuntu/ovos/enms-ovos-skill
python tests/test_118_queries.py --verbose

# Expected: 95%+ pass rate
# If failures, debug and fix
```

#### Task 4: Performance Benchmarking (2 hours)
```bash
# Run latency benchmark
python tests/benchmark_latency.py

# Verify targets:
# - P50 < 200ms
# - P90 < 800ms
# - P99 < 1500ms
```

#### Task 5: Load Testing (2 hours)
```bash
# Test sustained load
python tests/benchmark_latency.py --load-test --queries-per-min=100 --duration=3600

# Monitor:
# - Memory usage < 4GB
# - CPU usage < 50% average
# - No errors at sustained load
```

#### Task 6: Stress Testing (Overnight)
```bash
# 24-hour continuous operation
nohup python tests/benchmark_latency.py --stress-test --duration=86400 > stress_test.log 2>&1 &

# Check next morning for:
# - Memory leaks
# - Error rate < 0.1%
# - Performance degradation
```

#### Task 7: OVOS Core Integration (4 hours)
**Note:** This may be deferred if OVOS Core not installed yet.

```bash
# Install OVOS Core (if not already)
# Follow: https://openvoiceos.github.io/ovos-technical-manual/

# Link skill to OVOS
ln -s /home/ubuntu/ovos/enms-ovos-skill ~/.local/share/mycroft/skills/enms-skill.ovos

# Test wake word + voice query
# "Hey Mycroft, what's the status of Compressor-1?"
```

---

### **Days 40-41: User Acceptance Testing** (Optional)

#### Task 8: UAT Preparation (2 hours)
Create UAT test plan:
- 20 representative queries per user
- Accuracy checklist
- Satisfaction survey (1-5 scale)
- Feedback collection form

#### Task 9: Execute UAT (8 hours)
- Recruit 5-10 users (factory operators, managers)
- Each user performs 20 queries
- Collect metrics:
  - Intent detection accuracy
  - Response time satisfaction
  - Voice quality rating
  - Overall satisfaction

**Target:** >4.5/5 satisfaction, 95%+ accuracy

#### Task 10: Fix Critical Issues (4 hours)
- Prioritize issues by severity
- Fix critical bugs
- Re-test

---

### **Day 42: Production Deployment**

#### Task 11: systemd Service (2 hours)
```bash
# Create service file
sudo tee /etc/systemd/system/ovos-enms.service << 'EOF'
[Unit]
Description=OVOS EnMS Voice Assistant
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ovos/enms-ovos-skill
ExecStart=/home/ubuntu/ovos/venv/bin/python -m ovos_workshop.service
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable ovos-enms
sudo systemctl start ovos-enms
sudo systemctl status ovos-enms
```

#### Task 12: Monitoring Setup (2 hours)
```bash
# Configure Prometheus metrics export
# Default: http://localhost:8000/metrics

# Set up log rotation
sudo tee /etc/logrotate.d/ovos-enms << 'EOF'
/var/log/ovos-enms/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

#### Task 13: Documentation (4 hours)

**A. User Manual** (`docs/USER_GUIDE.md`)
- Installation instructions
- 50+ example voice queries
- Troubleshooting guide
- FAQ

**B. Deployment Guide** (`docs/DEPLOYMENT.md`)
- Hardware requirements
- Installation steps
- Configuration options
- Monitoring setup

**C. Demo Video** (5 minutes)
- Installation walkthrough
- Voice query examples
- System overview

---

## 🎯 Success Criteria

### Code Quality
- ✅ 90%+ test coverage (pytest)
- ✅ All 200+ unit tests passing
- ✅ Integration tests passing (118/118 queries)
- ✅ No critical bugs

### Performance
- ✅ P50 latency < 200ms
- ✅ P90 latency < 800ms
- ✅ Load test: 100 queries/min sustained
- ✅ Stress test: 24h operation, no crashes

### Deployment
- ✅ systemd service configured
- ✅ Auto-start on boot
- ✅ Log rotation enabled
- ✅ Metrics exported

### Documentation
- ✅ User manual complete
- ✅ Deployment guide complete
- ✅ Demo video recorded
- ✅ API reference updated

---

## 📊 Current File Inventory

### Implemented Files (Week 1-5)
```
enms-ovos-skill/
├── __init__.py (575 lines) - Main skill class ✅
├── lib/
│   ├── intent_parser.py (450 lines) - HybridParser ✅
│   ├── validator.py (380 lines) - ENMSValidator ✅
│   ├── api_client.py (320 lines) - API client ✅
│   ├── response_formatter.py (180 lines) - Templates ✅
│   ├── conversation_context.py (250 lines) - Context ✅
│   ├── voice_feedback.py (150 lines) - Feedback ✅
│   ├── time_parser.py (120 lines) - Time parsing ✅
│   ├── models.py (200 lines) - Pydantic models ✅
│   ├── observability.py (80 lines) - Metrics ✅
│   └── qwen3_parser.py (150 lines) - LLM parser ✅
├── tests/ (10 files, partially complete)
│   ├── test_118_queries.py ✅
│   ├── benchmark_latency.py ✅
│   ├── test_hybrid_parser.py ✅
│   └── [7 other test files] ⚠️
└── locale/en-us/dialog/ (9 templates) ✅
```

### Files to Create (Week 6)
```
tests/
├── conftest.py ❌ (fixtures)
├── test_validator_unit.py ❌ (50 cases)
├── test_api_client_unit.py ❌ (30 cases)
├── test_adapt_parser_unit.py ❌ (50 cases)
├── test_heuristic_router_unit.py ❌ (20 cases)
├── test_llm_parser_unit.py ❌ (30 cases)
└── test_response_formatter_unit.py ❌ (20 cases)

docs/
├── USER_GUIDE.md ❌
├── DEPLOYMENT.md ❌
└── demo_video.mp4 ❌

scripts/
├── deploy.sh ❌
└── run_all_tests.sh ❌
```

---

## 🚨 Known Issues & Gotchas

### 1. LLM Latency on CPU
- Qwen3-1.7B takes 300-500ms on CPU
- **Mitigation:** 80% queries use fast-path (<10ms)
- **Don't:** Try to optimize LLM speed, it's already optimal for CPU

### 2. API Client Async
- All API methods are async (require `await`)
- **Remember:** Use `pytest-asyncio` for testing
- **Pattern:** `@pytest.mark.asyncio` decorator

### 3. Machine Whitelist
- 8 machines hardcoded: Compressor-1, Boiler-1, HVAC-Main, etc.
- **Test:** Fuzzy matching ("Compresser-1" → "Compressor-1")
- **Test:** Invalid machines ("SuperMachine-9000" → rejected)

### 4. Time Parser Edge Cases
- "yesterday" = last 24h
- "last week" = last 7 days
- "Oct 27 to 28" = absolute range
- **Test:** All formats in `lib/time_parser.py`

### 5. OVOS Integration Unknown
- OVOS Core may not be installed yet
- **Defer if needed:** Can test CLI-only for now
- **Document:** Required for production voice usage

---

## 📚 Reference Documentation

### Key Files to Review
1. **Master Plan:** `docs/OVOS-ENMS-ULTIMATE-IMPLEMENTATION.md`
   - Full 6-week timeline
   - Architecture diagrams
   - Success criteria

2. **API Docs:** `docs/ENMS-API-DOCUMENTATION-FOR-OVOS.md`
   - 19 endpoint categories
   - 90+ API endpoints
   - Request/response examples

3. **Status Audit:** `docs/IMPLEMENTATION_STATUS_AUDIT.md`
   - Week-by-week completion status
   - Gap analysis
   - Recommendations

4. **Gap Analysis:** `docs/GAP_ANALYSIS_AND_ROADMAP.md`
   - 42% vs 100% API coverage
   - Phase 2 roadmap (post-Week 6)

### Example Test Cases

**Validator Test Example:**
```python
import pytest
from lib.validator import ENMSValidator

@pytest.fixture
def validator():
    return ENMSValidator()

def test_exact_machine_name(validator):
    result = validator.validate({"intent": "machine_status", "machine": "Compressor-1"})
    assert result.valid
    assert result.intent.machine == "Compressor-1"

def test_fuzzy_machine_name(validator):
    result = validator.validate({"intent": "machine_status", "machine": "Compresser-1"})
    assert result.valid
    assert result.intent.machine == "Compressor-1"  # Corrected

def test_invalid_machine(validator):
    result = validator.validate({"intent": "machine_status", "machine": "FakeMachine"})
    assert not result.valid
    assert "did you mean" in result.errors[0].lower()
```

**API Client Test Example:**
```python
import pytest
from lib.api_client import ENMSClient

@pytest.mark.asyncio
async def test_get_machine_status():
    client = ENMSClient(base_url="http://10.33.10.109:8001/api/v1")
    result = await client.get_machine_status("Compressor-1")
    
    assert "machine_name" in result
    assert result["machine_name"] == "Compressor-1"
    assert "current_status" in result
    
    await client.close()
```

---

## 🔧 Development Environment

### Prerequisites
```bash
# Python 3.12
python --version  # Should be 3.12.3

# Virtual environment active
which python  # Should be /home/ubuntu/ovos/venv/bin/python

# Current directory
cd /home/ubuntu/ovos/enms-ovos-skill
```

### Install Testing Dependencies
```bash
pip install pytest pytest-asyncio pytest-cov hypothesis
```

### Run Existing Tests
```bash
# Check what's already there
ls -la tests/

# Run a specific test
python tests/test_118_queries.py
python tests/benchmark_latency.py
```

---

## 🎯 Your Mission Objectives

### Primary Goal
**Complete Week 6 to achieve production-ready v1.0**

### Deliverables
1. ✅ 200+ unit tests written, 90%+ coverage
2. ✅ Integration tests passing (118/118 queries)
3. ✅ Load test: 100 queries/min sustained
4. ✅ Stress test: 24h operation verified
5. ✅ Production deployment (systemd service)
6. ✅ User manual + deployment guide
7. ✅ Demo video

### Timeline
**1 week** (Days 36-42 of original plan)

### Success Metric
**Phase 1 is 100% COMPLETE** - Ready for Phase 2 (API expansion)

---

## 💡 Tips for Success

1. **Start with pytest setup** - Foundation is critical
2. **Write tests incrementally** - Don't try 200 at once
3. **Run coverage frequently** - `pytest --cov`
4. **Use fixtures generously** - DRY principle
5. **Mock external calls** - Don't hit real API in unit tests
6. **Test edge cases** - That's where bugs hide
7. **Document as you go** - Future you will thank you
8. **Ask questions** - Better to clarify than assume

---

## 🚀 First Steps (Start Here)

1. **Review the codebase:**
   ```bash
   cd /home/ubuntu/ovos/enms-ovos-skill
   tree -L 2
   ```

2. **Read the master plan:**
   ```bash
   cat docs/OVOS-ENMS-ULTIMATE-IMPLEMENTATION.md | grep "WEEK 6" -A 100
   ```

3. **Set up pytest:**
   ```bash
   pip install pytest pytest-asyncio pytest-cov hypothesis
   cat > pytest.ini << 'EOF'
   [pytest]
   testpaths = tests
   addopts = --cov=lib --cov-report=term
   EOF
   ```

4. **Create your first test:**
   ```bash
   cat > tests/test_validator_unit.py << 'EOF'
   import pytest
   from lib.validator import ENMSValidator
   
   @pytest.fixture
   def validator():
       return ENMSValidator()
   
   def test_valid_machine_name(validator):
       result = validator.validate({
           "intent": "machine_status",
           "machine": "Compressor-1"
       })
       assert result.valid
       assert result.intent.machine == "Compressor-1"
   EOF
   ```

5. **Run it:**
   ```bash
   pytest tests/test_validator_unit.py -v
   ```

---

## 🎉 When You're Done

You'll have:
- ✅ A production-ready SOTA voice assistant
- ✅ 90%+ test coverage with 200+ test cases
- ✅ Performance validated (<200ms P50 latency)
- ✅ Deployed with systemd
- ✅ Comprehensive documentation
- ✅ Phase 1 COMPLETE badge

**Then:** Phase 2 begins (API expansion from 42% to 100%)

---

**Ready? Let's complete Week 6! 🚀**
