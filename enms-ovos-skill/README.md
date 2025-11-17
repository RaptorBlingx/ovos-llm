# EnMS OVOS Skill

Industrial voice assistant for Energy Management System (EnMS) integration.

## Features

- Real-time energy monitoring
- Machine status queries  
- Factory-wide overview
- Anomaly detection
- Energy forecasting
- Cost analysis
- Voice-optimized responses

## Architecture

- **Tier 1**: Qwen3-1.7B LLM (natural language understanding)
- **Tier 2**: Zero-trust validator (Pydantic schemas)
- **Tier 3**: EnMS API client (httpx, circuit breaker)
- **Tier 4**: Response formatter (Jinja2 templates)
- **Tier 5**: Fast-path NLU (Adapt/Padatious) - Coming Week 3

## Installation

```bash
cd enms-ovos-skill
pip install -r requirements.txt
```

## Configuration

Edit `settingsmeta.yaml` to configure:
- EnMS API URL
- LLM model path
- Confidence thresholds
- Response settings

## Example Queries

- "What's the power consumption of Compressor-1?"
- "How much energy did Boiler-1 use yesterday?"
- "Is HVAC-Main running?"
- "Show me factory overview"
- "Top 3 energy consumers"

## Development Status

- [x] Week 1 Days 1-2: Skill scaffold
- [ ] Week 1 Days 3-4: EnMS API client
- [ ] Week 1 Days 5-7: LLM parser + validator
- [ ] Week 2: Dialog templates + observability
- [ ] Week 3: Fast-path NLU
- [ ] Week 4-6: Testing, optimization, deployment

## License

Apache-2.0
