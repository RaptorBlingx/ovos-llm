# EnMS OVOS Skill - Energy Management Voice Assistant

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![OVOS](https://img.shields.io/badge/OVOS-Compatible-green.svg)](https://openvoiceos.github.io/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Human-centric voice assistant for industrial energy management (ISO 50001). Part of the [WASABI H2020 Project](https://www.wasabi-project.eu/) - HumanEnerDIA experiment.

## 🎯 Features

- **Real-time Energy Monitoring** - Query consumption data for any machine or facility
- **Anomaly Detection** - Voice alerts for unusual energy patterns
- **Predictive Forecasting** - Ask about tomorrow's expected energy usage
- **Machine Status** - Check operational status and power levels
- **Factory Overview** - Get comprehensive energy performance summaries
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
  "confidence_threshold": 0.85,
  "api_timeout_seconds": 30
}
```

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
                              Heuristic  Adapt   LLM
                               (<5ms)   (<10ms) (300ms)
                                    ↓
                              Validator (Zero-trust)
                                    ↓
                              EnMS Analytics API
```

### Performance

- **P50 Latency**: <200ms (actual: ~142ms)
- **P90 Latency**: <500ms
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
└── LICENSE                      # GPL-3.0
```

## 🤝 Contributing

Contributions are welcome! This is an open-source project under GPL-3.0.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details.

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
