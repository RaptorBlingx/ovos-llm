# EnMS OVOS Skill - Energy Management Voice Assistant

[![License: Apache-2.0 OR GPL-3.0-or-later](https://img.shields.io/badge/License-Apache--2.0%20OR%20GPL--3.0--or--later-blue.svg)](./RELEASE_LICENSE.md)
[![OVOS](https://img.shields.io/badge/OVOS-Compatible-green.svg)](https://openvoiceos.github.io/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Human-centric voice assistant for industrial energy management (ISO 50001). Part of the [WASABI H2020 Project](https://www.wasabi-project.eu/) - HumanEnerDIA experiment.

## 🎯 Features

- **Real-time Energy Monitoring** - Query consumption data for any machine or facility
- **Anomaly Detection** - Voice alerts for unusual energy patterns
- **Predictive Forecasting** - Ask about tomorrow's expected energy usage
- **Machine Status** - Check operational status and power levels
- **Factory Overview** - Get comprehensive energy performance summaries
- **Hybrid NLU Fallback** - Heuristic and Adapt routing backed by a local Qwen3.5-2B GGUF model for harder queries
- **ISO 50001 Compliance** - Built-in support for energy management standards
- **Multi-language Support** - Currently English (en-us), expandable

## 🚀 Quick Start

### Prerequisites

- OVOS framework installed
- EnMS Analytics API running (included in full deployment)
- Python 3.10 or higher

### Installation

```bash
# Install via OVOS skill manager
ovos-skills-manager install enms-ovos-skill

# Or install from source
git clone https://github.com/aplusengineering/enms-ovos-skill.git
cd enms-ovos-skill
pip install -e .
```

### Configuration

Create or edit `~/.config/ovos/skills/enms-ovos-skill/settings.json`:

```json
{
  "enms_api_base_url": "http://your-enms-server:8001/api/v1",
  "llm_model_path": "./models/Qwen3.5-2B-Q4_K_M.gguf",
  "confidence_threshold": 0.85,
  "api_timeout_seconds": 30
}
```

The default Tier-3 local fallback model is `Qwen3.5-2B-Q4_K_M.gguf`. Requests only escalate to this model when the faster heuristic and Adapt tiers cannot resolve the query confidently.

## 🗣️ Voice Commands

### Energy Queries
- "What's the power consumption of Compressor-1?"
- "How much energy did Boiler-1 use yesterday?"
- "Total factory energy consumption"
- "Show me energy for the last 24 hours"

### Machine Status
- "Is HVAC-Main running?"
- "What's the status of Compressor-1?"
- "Check all machines"

### Analysis
- "Top 3 energy consumers"
- "Compare Compressor-1 and Boiler-1"
- "Detect anomalies for Compressor-1 today"

### Forecasting
- "Forecast energy for tomorrow"
- "Predicted consumption for next week"
- "What's the expected energy usage?"

## 🏗️ Architecture

```
Portal/User → REST Bridge → OVOS Messagebus → EnmsSkill
                                                   ↓
                                    HybridParser (3-tier NLU)
                                    ↓         ↓        ↓
          Heuristic  Adapt  Qwen3.5-2B
           (<5ms)   (<10ms) (fallback)
                                    ↓
                              Validator (Zero-trust)
                                    ↓
                              EnMS Analytics API
```

### Performance

- **Fast-Path Queries**: Sub-second live responses for standard operational requests
- **Intent Detection**: Heuristic and Adapt routing stay in the 1-10ms range
- **LLM Fallback**: Typically multi-second when a request escalates to Qwen3.5-2B
- **Intent Accuracy**: 95%+
- **Heuristic Tier**: 1-5ms for 80% of queries

## 🔧 Development

### Running Tests

```bash
cd enms-ovos-skill
pytest tests/ -v
```

### Testing with Docker

```bash
# Full stack deployment
docker compose up -d

# Test query
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the energy consumption?"}'
```

## 📦 Project Structure

```
enms-ovos-skill/
├── enms_ovos_skill/
│   ├── __init__.py              # Main skill class
│   ├── lib/                     # NLU components
│   │   ├── intent_parser.py     # 3-tier hybrid parser
│   │   ├── validator.py         # Zero-trust validation
│   │   ├── api_client.py        # EnMS API integration
│   │   └── ...
│   └── locale/
│       └── en-us/
│           ├── dialog/          # Response templates
│           └── vocab/           # Adapt keywords
├── tests/                       # Unit & integration tests
├── bridge/                      # REST API gateway
├── setup.py                     # Package configuration
├── skill.json                   # OVOS metadata
└── RELEASE_LICENSE.md           # WASABI release licensing
```

## 🤝 Contributing

Contributions are welcome. The WASABI release artifact is offered under Apache-2.0 OR GPL-3.0-or-later; see [RELEASE_LICENSE.md](./RELEASE_LICENSE.md).

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

The WASABI release artifact is licensed under **Apache-2.0 OR GPL-3.0-or-later**. The existing repository license file is preserved for historical GPL distribution context; see [RELEASE_LICENSE.md](./RELEASE_LICENSE.md) for the release grant used for WASABI shop distribution.

**Copyright (C) 2025 A Plus Engineering (Turkey)**

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

## 🏆 Acknowledgments

- **WASABI H2020 Project** - Framework and support
- **OVOS Community** - Open Voice Operating System
- **Green eDIH (Romania)** - Field trial collaboration
- **A Plus Engineering** - Development and maintenance

## 📚 Documentation

- [OVOS Documentation](https://openvoiceos.github.io/)
- [EnMS API Documentation](docs/API.md)
- [Installation Guide](docs/INSTALL.md)
- [Configuration Guide](docs/CONFIGURATION.md)

## 🐛 Bug Reports

Please report issues on [GitHub Issues](https://github.com/aplusengineering/enms-ovos-skill/issues)

## 📧 Contact

- **Email**: info@aplusengineering.com
- **Project**: HumanEnerDIA - WASABI 1st Open Call
- **Website**: [www.aplusengineering.com](https://www.aplusengineering.com)

---

**Made with ❤️ for manufacturing SMEs**
