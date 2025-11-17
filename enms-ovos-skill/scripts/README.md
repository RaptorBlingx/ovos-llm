# EnMS Testing Scripts

Manual testing tools for the OVOS-EnMS skill pipeline.

## Scripts

### 1. `chat_gui.py` - Web Chat Interface

Interactive Gradio-based web UI for manual testing.

**Start:**
```bash
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
python scripts/chat_gui.py
```

**Access:** http://localhost:7862

**Features:**
- Full conversational interface
- Debug panel (shows LLM parsing, validation, API calls)
- Example queries
- Real-time EnMS API integration

**Example queries:**
- "What's the power of Compressor-1?"
- "How much energy did Boiler-1 use today?"
- "Is HVAC-EU-North running?"
- "Factory overview"
- "Top 5 energy consumers"

### 2. `quick_test.py` - CLI Pipeline Tester

Command-line end-to-end pipeline test.

**Run:**
```bash
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
python scripts/quick_test.py
```

**Tests:**
- [Tier 1] LLM parsing (Qwen3-1.7B)
- [Tier 2] Validation (fuzzy matching, confidence)
- [Tier 3] API call (real EnMS data)
- [Tier 4] Response formatting (Jinja2 templates)

**Output:**
```
✅ PIPELINE TEST: SUCCESS!

FINAL RESPONSE:
Compressor-1 is currently using forty-nine kilowatts.
```

## Requirements

All dependencies installed in `venv/`:
- gradio (chat interface)
- llama-cpp-python (LLM inference)
- httpx (API client)
- jinja2 (templates)
- pydantic (validation)

## Architecture

```
User Query
    ↓
[Tier 1] Qwen3 LLM Parser → Intent + Entities + Confidence
    ↓
[Tier 2] Validator → Fuzzy match machines, verify API mapping
    ↓
[Tier 3] API Client → Fetch real data from EnMS
    ↓
[Tier 4] Response Formatter → Jinja2 voice-optimized templates
    ↓
Natural Language Response
```

## Troubleshooting

**GUI won't start (port conflict):**
```bash
export GRADIO_SERVER_PORT=7863
python scripts/chat_gui.py
```

**"Event loop is closed" error:**
- Fixed in latest version
- GUI now uses persistent event loop (self.loop)
- Restart GUI if you see this error

**LLM slow on first run:**
- Model loading takes ~2s (1.2GB GGUF)
- First inference ~15-25s (compiling)
- Subsequent queries ~500ms

**API connection errors:**
- Verify EnMS API running: `curl http://10.33.10.109:8001/api/v1/machines`
- Check network connectivity to 10.33.10.109

## Performance

- **LLM latency:** ~15-25s (cold start), ~500ms (warm)
- **API latency:** ~100-150ms
- **Template rendering:** <1ms
- **Total pipeline:** ~500-700ms (after warm-up)

Next phase will add fast-path NLU (Adapt) to reduce 80% of queries to <200ms.
