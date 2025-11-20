# 🧪 How to Test the EnMS OVOS Skill Properly

## ⚠️ CRITICAL: No Mocks, No Hardcoding, Real Behavior Only

This guide ensures you test the **actual skill behavior** without accidentally testing fake/mocked responses.

---

## 🎯 Testing Principles

### What We're Testing
- **Real skill components:** Parser → Validator → API → Templates
- **Real API calls:** Actual HTTP requests to EnMS backend
- **Real templates:** Jinja2 `.dialog` files rendered with API data
- **Real intent classification:** LLM/Adapt/Heuristic routing

### What We're NOT Testing
- ❌ Hardcoded responses in test scripts
- ❌ Mocked API data
- ❌ Manually formatted strings that bypass templates
- ❌ Fake skill logic reimplemented in test code

---

## 🛠️ Test Tools Available

### 1. `scripts/test_gui_standalone.py` ✅ RECOMMENDED

**Purpose:** Interactive browser-based testing  
**Architecture:** Direct skill component testing (no OVOS Core needed)  
**Status:** ✅ Uses real components, real templates, real API

**How to Run:**
```bash
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
PYTHONPATH=/home/ubuntu/ovos/enms-ovos-skill:$PYTHONPATH python3 scripts/test_gui_standalone.py
```

**Open:** http://localhost:7862

**What It Tests:**
- Real `HybridParser` (LLM/Adapt/Heuristic)
- Real `ENMSValidator` (zero-trust validation)
- Real `ENMSClient` (actual HTTP calls to http://10.33.10.109:8001)
- Real `ResponseFormatter` (loads `.dialog` templates from `locale/en-us/dialog/`)
- Real conversation flow

**Verification:**
- Check terminal output shows `[Parsing]`, `[Validating]`, `[API Call]`, `[Formatting]`
- Debug panel shows actual intent, API endpoint called, response
- Response comes from templates, not hardcoded strings

---

### 2. `scripts/quick_test.py` ✅ RECOMMENDED FOR CLI

**Purpose:** Command-line testing for automation  
**Architecture:** Same as GUI - direct component testing  
**Status:** ✅ Uses real templates (fixed Nov 20, 2025)

**How to Run:**
```bash
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
python3 scripts/quick_test.py --query "Check system health"
```

**Output Shows:**
```
[Tier 1] LLM parsing...
  Intent: factory_overview
  Confidence: 0.90

[Tier 2] Validating...
  ✅ Valid - Intent: IntentType.FACTORY_OVERVIEW

[Tier 3] Calling EnMS API...
  ✅ API Response (Health Check):
     Status: healthy
     Active Machines: 8

[Tier 4] Formatting response using templates...
  ✅ Data retrieved successfully
  📄 Template used: health_check.dialog

FINAL RESPONSE (would be spoken):
Yes, the energy management system is online and healthy. 8 machines are currently active with 285 trained baseline models.
```

**Key Indicator:** Look for `📄 Template used: XXX.dialog` - confirms real template rendering!

---

### 3. ~~`scripts/chat_gui.py`~~ ❌ DELETED

**Status:** Deleted on Nov 20, 2025  
**Reason:** Was hardcoding responses, not using real templates  
**Do NOT use:** File no longer exists

---

### 4. `scripts/gui_messagebus.py` ⚠️ REQUIRES OVOS CORE

**Purpose:** Full OVOS integration via WebSocket message bus  
**Status:** Needs OVOS Core installed (not available in current setup)  
**Use Case:** Production environment with full OVOS stack

**Requirements:**
- OVOS Core service running
- Message bus accessible at `ws://localhost:8181/core`
- Skill registered with OVOS

**Not recommended for current testing** - use standalone tools instead.

---

## 📋 Testing Methodology for 1by1.md

### Step-by-Step Process

#### 1. **Start the Test GUI**
```bash
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
PYTHONPATH=/home/ubuntu/ovos/enms-ovos-skill:$PYTHONPATH python3 scripts/test_gui_standalone.py
```

Keep this running in Terminal 1.

---

#### 2. **Open Browser**
Navigate to: http://localhost:7862

---

#### 3. **Run API Verification (Terminal 2)**

For each test query, first verify the API works:

```bash
# Example: Query 1.1 - Health Check
curl -s http://10.33.10.109:8001/api/v1/health | jq '.'
```

**Save the JSON output** - you'll compare this with OVOS response.

---

#### 4. **Test in GUI**

Type the query in the browser GUI, e.g., "Check system health"

**What to verify:**
- ✅ Debug panel shows correct intent
- ✅ Debug panel shows correct API data
- ✅ Response matches API data
- ✅ Response is voice-friendly (not raw JSON)

---

#### 5. **Verify Template Usage (Terminal 1)**

Check the terminal running the GUI - you should see:
```
[Parsing] Check system health
[Validating] Intent: factory_overview
[API Call] Intent: factory_overview, Machine: None
[Formatting] Using templates...
```

**Critical:** If you don't see this output, the test tool is not working correctly!

---

#### 6. **Alternative: CLI Testing**

If you prefer terminal testing:

```bash
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate

# Test query
python3 scripts/quick_test.py --query "Check system health"

# Look for this line in output:
# 📄 Template used: health_check.dialog
```

---

## 🔍 How to Verify Real vs Fake Responses

### ✅ Real Response Indicators

1. **Template filename shown:**
   ```
   📄 Template used: health_check.dialog
   ```

2. **API data structure shown:**
   ```
   [API Call] Intent: factory_overview, Machine: None
   ✅ API Response (Health Check):
      Status: healthy
      Active Machines: 8
      Baseline Models: 285
   ```

3. **Response changes when API data changes:**
   - If you modify API data, response should change
   - If you modify template file, response should change

4. **Template files exist and are being read:**
   ```bash
   ls -l locale/en-us/dialog/*.dialog
   # Should show: health_check.dialog, factory_overview.dialog, etc.
   ```

---

### ❌ Fake Response Indicators (RED FLAGS)

1. **Hardcoded strings in test script:**
   ```python
   # BAD - hardcoded response
   response = f"Yes, the system is healthy..."
   ```

2. **No template filename shown in output**

3. **Response never changes even when template/API changes**

4. **Test script has response formatting logic:**
   ```python
   # BAD - test script formatting responses
   if response_type == 'health':
       response = f"System is {status}..."
   ```

---

## 🐛 Common Issues & Fixes

### Issue 1: "Template not found"

**Symptom:** Error about missing `.dialog` file  
**Cause:** Template files not in correct location  
**Fix:**
```bash
ls locale/en-us/dialog/
# Should show: health_check.dialog, factory_overview.dialog, etc.
```

---

### Issue 2: Response doesn't match API data

**Symptom:** API returns 8 machines, response says 5  
**Possible Causes:**
1. Template has wrong variable name
2. API data mapping is incorrect
3. Using cached/old data

**Debug:**
- Check debug panel in GUI - shows API data received
- Check template file - verify variable names match
- Restart GUI to clear any caches

---

### Issue 3: Same response for different queries

**Symptom:** All queries return same generic response  
**Cause:** Fallback response being used instead of templates  
**Fix:**
- Check logs for template errors
- Verify intent classification is correct
- Check API endpoint is reachable

---

## 📝 Test Plan Execution Checklist

For each query in `1by1.md`:

- [ ] 1. Run `curl` command → Save JSON output
- [ ] 2. Test query in GUI → Check debug panel
- [ ] 3. Verify intent classification matches expected
- [ ] 4. Verify API endpoint called matches curl endpoint
- [ ] 5. Verify response data matches curl JSON data
- [ ] 6. Verify response is voice-friendly (not raw JSON)
- [ ] 7. Check terminal shows template being used
- [ ] 8. If PASS: Mark ✅ in test plan
- [ ] 9. If FAIL: Document issue, fix code, re-test

---

## 🎯 Quick Verification Test

Run this to confirm your setup is working:

```bash
# Terminal 1: Start GUI
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
PYTHONPATH=/home/ubuntu/ovos/enms-ovos-skill:$PYTHONPATH python3 scripts/test_gui_standalone.py

# Terminal 2: Test API
curl -s http://10.33.10.109:8001/api/v1/health | jq '.active_machines'
# Should show: 8

# Browser: http://localhost:7862
# Type: "Check system health"
# Expected response: "Yes, the energy management system is online and healthy. 8 machines are currently active with 285 trained baseline models."

# Terminal 1 should show:
# [Parsing] Check system health
# [Validating] Intent: factory_overview
# [API Call] Intent: factory_overview, Machine: None
# [Formatting] Using templates...
```

**If you see this output, you're testing the REAL skill behavior!** ✅

---

## 🚀 Ready to Start Testing

You now have:
1. ✅ Proper test tools (`test_gui_standalone.py`, `quick_test.py`)
2. ✅ Verification methods (template usage indicators)
3. ✅ Understanding of real vs fake responses
4. ✅ Checklist for each test query

**Proceed to `1by1.md` and start testing from Batch 1, EP1, Query 1.1!**
