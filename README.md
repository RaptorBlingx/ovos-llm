# OVOS-EnMS Integration

**Open Voice OS for Industrial Energy Management System**

> A state-of-the-art voice assistant integrating OVOS with the WASABI EU Energy Management System (EnMS), achieving 95%+ query coverage, <200ms P50 latency, and 99.5%+ accuracy with zero hallucination tolerance.

---

## 📋 Project Overview

This project delivers an **external OVOS skill** (`ovos-skill-enms`) that enables natural language voice queries for industrial energy management:

- "How much energy did Compressor-1 use in the last 24 hours?"
- "Compare energy consumption between Boiler-1 and HVAC-Main this week"
- "Forecast energy consumption for tomorrow"
- "Show me the top 3 energy consumers today"

**Key Features:**
- ✅ LLM-first architecture with grammar-constrained intent parsing
- ✅ Zero-trust validation (99.5%+ hallucination prevention)
- ✅ Multi-tier adaptive routing (fast-path + LLM fallback)
- ✅ 100% offline operation (no cloud, no GPU required)
- ✅ Industrial-grade reliability with circuit breakers and graceful degradation

---

## 🗂️ Documentation

All project documentation is in the [`docs/`](./docs) folder:

- **[Master Plan](./docs/OVOS-ENMS-ULTIMATE-IMPLEMENTATION.md)** - Complete 6-week implementation roadmap with phases, milestones, and agent workflow
- **[EnMS API Documentation](./docs/ENMS-API-DOCUMENTATION-FOR-OVOS.md)** - Complete API reference for all 90+ EnMS endpoints
- **[Test Questions](./docs/test-questions.md)** - 118+ test queries covering all use cases

---

## 🏗️ Architecture

```
User (Voice/Text)
    ↓
OVOS Core (STT, TTS, Wake Word)
    ↓
ovos-skill-enms (This Project)
    ├─ Tier 1: Qwen3-1.7B LLM Parser (grammar-constrained JSON)
    ├─ Tier 2: Zero-Trust Validator (Pydantic + whitelists)
    ├─ Tier 3: API Executor (httpx async + circuit breakers)
    ├─ Tier 4: Response Generator (Jinja2 templates)
    └─ Tier 5: Fast-Path NLU (Adapt/Padatious - future optimization)
    ↓
EnMS API (90+ REST endpoints)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- OVOS Core v2.1.1
- Access to EnMS API
- 8GB RAM, 4+ CPU cores

### Development Setup

```bash
# Clone the repository
git clone git@github.com:RaptorBlingx/ovos-llm.git
cd ovos-llm

# Install dependencies (coming in Phase 1)
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure EnMS API endpoint
# (Instructions coming in Phase 1)
```

---

## 📅 Implementation Status

**Current Phase:** Phase 1 – LLM Core & EnMS Integration  
**Current Milestone:** Week 1 – Skill Scaffold + LLM Parser + Validator  
**Overall Progress:** 0% (0/4 phases completed)

See the [Master Plan](./docs/OVOS-ENMS-ULTIMATE-IMPLEMENTATION.md) for detailed timeline and task tracking.

---

## 🎯 Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Query Coverage | 95%+ | 🔲 Not started |
| P50 Latency | <200ms | 🔲 Not started |
| P90 Latency | <800ms | 🔲 Not started |
| Accuracy | 99%+ | 🔲 Not started |
| Hallucination Rate | <0.5% | 🔲 Not started |
| Test Coverage | 90%+ | 🔲 Not started |

---

## 🤝 Contributing

This project follows a structured 6-week implementation plan managed by AI agents. See the [Agent Workflow](./docs/OVOS-ENMS-ULTIMATE-IMPLEMENTATION.md#-agent-workflow-for-ai-implementation-agents) section in the master plan.

---

## 📄 License

[To be determined]

---

## 🔗 Links

- [OVOS Documentation](https://openvoiceos.github.io/ovos-technical-manual/)
- [WASABI EU Project](https://wasabiproject.eu/)
- [Master Implementation Plan](./docs/OVOS-ENMS-ULTIMATE-IMPLEMENTATION.md)

---

**Built with ❤️ for industrial energy optimization**
