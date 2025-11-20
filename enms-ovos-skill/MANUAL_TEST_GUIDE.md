# 🧪 Manual Testing Guide - OVOS ENMS Skill

## ✅ System Verified & Ready

All components initialized successfully:
- ✓ HybridParser (Heuristic → Adapt → LLM)
- ✓ ENMSValidator (Zero-trust validation)
- ✓ API Client (EnMS REST integration)
- ✓ Response Formatter (Jinja2 templates)
- ✓ Conversation Context (Multi-turn support)
- ✓ Voice Feedback (Natural responses)

**Test Results:**
- Integration Test: 94.4% success (17/18 queries)
- Heuristic Coverage: 77.8% (ultra-fast <1ms)
- LLM Model: Qwen3-1.7B loaded and warm

---

## 🎯 Option 1: Interactive Chat GUI (Recommended)

**Best for:** Real-time testing with visual feedback

### Launch Command:
```bash
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
python scripts/chat_gui.py
```

**Access:** Open browser to `http://localhost:7860`

**Features:**
- Full pipeline visualization
- Debug information panel
- Conversation history
- Real-time latency metrics

### Test Queries to Try:
1. **Quick Queries (Heuristic - <1ms):**
   - "top 5"
   - "Boiler-1 power"
   - "factory overview"
   - "Compressor-1 status"

2. **Natural Language (Adapt/LLM):**
   - "What's the power consumption of Compressor-1?"
   - "Show me energy usage"
   - "Compare Boiler-1 and Compressor-1"

3. **Time-Range Queries (NEW - Fixed!):**
   - "Show me the energy consumption of Compressor-1 from October 27, 3 PM to October 28, 10 AM"
   - "Boiler-1 power yesterday"
   - "What did HVAC-Main consume last week?"
   - "Compressor-1 energy last 24 hours"

4. **Multi-turn Conversation:**
   - "Compressor-1 power"
   - "What about energy?" (should resolve to Compressor-1)
   - "What about Boiler-1?" (should switch machine, keep metric)

---

## 🔬 Option 2: Command-Line Quick Test

**Best for:** Fast pipeline verification

### Command:
```bash
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
python scripts/quick_test.py
```

**What it does:**
- Tests full pipeline with sample query
- Shows each tier's output
- Validates API integration
- Displays formatted response

---

## 🚀 Option 3: Direct Python Testing

**Best for:** Custom query testing

### Command:
```bash
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
python -c "
from lib.intent_parser import HybridParser

# Create parser (LLM loads automatically)
parser = HybridParser()

# Test your query
query = 'YOUR QUERY HERE'
result = parser.parse(query)

print(f'Query: {query}')
print(f'Intent: {result.get(\"intent\")}')
print(f'Tier: {result.get(\"tier\")}')
print(f'Confidence: {result.get(\"confidence\")}')
print(f'Entities: {result.get(\"entities\", {})}')
"
```

Replace `'YOUR QUERY HERE'` with your test query.

---

## 📊 Expected Performance

### Latency by Tier:
- **Heuristic**: <1ms (77% of queries)
- **Adapt**: <2ms (11% of queries)
- **LLM**: 3-15s (11% of queries, first query slower due to model load)

### Machine Names (8 active):
- Boiler-1
- Compressor-1
- Compressor-EU-1
- Conveyor-A
- HVAC-EU-North
- HVAC-Main
- Hydraulic-Pump-1
- Injection-Molding-1

---

## 🎓 Testing Tips

1. **Start simple:** Test "top 5" to verify heuristic tier
2. **Test machine names:** Use exact names (case-sensitive)
3. **Try natural language:** "What's the power of Boiler-1?"
4. **Test conversations:** Ask follow-ups like "What about energy?"
5. **Check edge cases:** Try "show me data" (should ask for clarification)

---

## 🐛 Troubleshooting

**If Chat GUI won't start:**
```bash
pip install gradio
```

**If API errors occur:**
- Verify EnMS API is running: `http://10.33.10.109:8001/api/v1/health`
- Check network connectivity

**If LLM is slow:**
- First query: 15s (model loading) - NORMAL
- Subsequent queries: 3-5s - EXPECTED on CPU
- For <200ms: Need GPU acceleration

---

## 💡 What to Look For

✅ **Good Signs:**
- Heuristic queries return instantly (<1ms)
- Intent correctly identified
- Machine names normalized (e.g., "HVAC" → "HVAC-Main")
- Natural language understood
- Follow-up questions resolve correctly

❌ **Issues to Report:**
- Wrong intent detected
- Machine name not recognized
- API errors
- Unexpected slow responses (>20s)

---

**Ready to test!** Choose your preferred option and start querying! 🚀
