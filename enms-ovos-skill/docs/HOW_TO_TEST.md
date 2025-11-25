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

### 1. `scripts/test_skill_logic.py` ✅ RECOMMENDED FOR AUTOMATED TESTING

**Purpose:** Single-query command-line testing for systematic validation  
**Architecture:** Direct component testing (Parser → Validator → API → Formatter)  
**Status:** ✅ Uses REAL skill logic copied from `__init__.py`, real templates, real API

**How to Run:**
```bash
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
python3 scripts/test_skill_logic.py "QUERY HERE"
```

**Example:**
```bash
python3 scripts/test_skill_logic.py "What's the status of Compressor-1?"
```

**What It Tests:**
- Real `HybridParser` (LLM/Adapt/Heuristic tiers)
- Real `ENMSValidator` (zero-trust validation)
- Real `ENMSClient` (actual HTTP calls to http://10.33.10.109:8001)
- Real `ResponseFormatter` (loads `.dialog` templates from `locale/en-us/dialog/`)
- EXACT API logic from `__init__.py` lines 372-520
- EXACT formatting logic from `__init__.py` lines 547-577

**Output Shows:**
- [STEP 1] Parsing → Intent classification and confidence
- [STEP 2] Validating → Intent validation and machine name resolution
- [STEP 3] API Call → Endpoint called and data keys returned
- [STEP 4] Formatting → Template used and final response
- FINAL RESPONSE → Actual voice response that would be spoken

---

### 2. `scripts/test_skill_chat.py` ✅ RECOMMENDED FOR INTERACTIVE TESTING

**Purpose:** Interactive chat interface for manual exploratory testing  
**Architecture:** Same as test_skill_logic.py but with conversation loop  
**Status:** ✅ Uses EXACT skill logic from `__init__.py`, real templates, real API

**How to Run:**
```bash
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
python3 scripts/test_skill_chat.py
```

**Output Shows:**
```
You: Show me active machines

[Parse] Intent: ranking (confidence: 0.85)
[Validate] ✅ Intent: ranking, Machine: None
[API] Calling /machines (list all machines)
[API] ✅ Data retrieved
[Format] Using ranking.dialog

Skill: We have 8 machines: Boiler-1, Compressor-1, Compressor-EU-1, 
Conveyor-A, HVAC-EU-North, HVAC-Main, Hydraulic-Pump-1, Injection-Molding-1.
```

**Key Features:**
- Type queries interactively
- See full processing pipeline
- Press Ctrl+C to exit
- Restart anytime to test code changes

---

### 3. `scripts/test_gui_standalone.py` ⚠️ LEGACY (Not Currently Used)

**Status:** Exists but not actively maintained  
**Reason:** Browser-based GUI, slower for systematic testing  
**Use Instead:** `test_skill_logic.py` for automation, `test_skill_chat.py` for interactive

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

#### 1. **Activate Virtual Environment**
```bash
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
```

---

#### 2. **Run API Verification First**

For each test query, first verify the API works:

```bash
# Example: EP6 Query - Machine Status
curl -s http://10.33.10.109:8001/api/v1/machines/status/Compressor-1 | jq '.'
```

**Save the JSON output** - you'll compare this with OVOS response.

---

#### 3. **Test with Skill Logic**

Run the query through the skill:

```bash
python3 scripts/test_skill_logic.py "What's the status of Compressor-1?"
```

**What to verify:**
- ✅ Intent classification is correct
- ✅ API endpoint called matches curl endpoint
- ✅ Response data matches curl JSON data
- ✅ Response is voice-friendly (not raw JSON)
- ✅ Template name is shown in output

**Output Example:**
```
[STEP 1] Parsing...
  Intent: machine_status
  Confidence: 0.85

[STEP 2] Validating...
  ✅ Valid - Intent: machine_status, Machine: Compressor-1

[STEP 3] Calling EnMS API...
  → Calling /machines/status/Compressor-1
  ✅ API returned data

[STEP 4] Formatting response...
  → Using standard formatter for intent: machine_status

FINAL RESPONSE:
Compressor-1 is running at 50.84 kilowatts.
```

---

#### 4. **Compare Results**

| Aspect | curl Output | OVOS Response | Match? |
|--------|-------------|---------------|--------|
| Status | `"status": "running"` | "Compressor-1 is running" | ✅ |
| Power | `"power_kw": 50.84` | "at 50.84 kilowatts" | ✅ |
| API Endpoint | `/machines/status/Compressor-1` | Same | ✅ |

---

#### 5. **Mark Results in 1by1.md**

Update the test plan:
- ✅ PASS: All verifications passed
- ❌ FAIL: Wrong endpoint, wrong data, or template error
- ⚠️ PARTIAL: Works but with issues (e.g., wrong intent classification)

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
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate

# Test 1: Health check query
python3 scripts/test_skill_logic.py "Is the energy system online?"

# Expected output:
# [STEP 1] Intent: factory_overview (0.95)
# [STEP 2] ✅ Valid
# [STEP 3] → Calling /health
# [STEP 4] → Using health_check.dialog
# FINAL RESPONSE: Yes, the energy management system is online and healthy...

# Test 2: Machine status query
python3 scripts/test_skill_logic.py "What's the status of Compressor-1?"

# Expected output:
# [STEP 1] Intent: machine_status (0.85)
# [STEP 2] ✅ Valid - Machine: Compressor-1
# [STEP 3] → Calling /machines/status/Compressor-1
# [STEP 4] → Using machine_status.dialog
# FINAL RESPONSE: Compressor-1 is running at XX kilowatts.

# Test 3: Interactive chat
python3 scripts/test_skill_chat.py
# Type: "Show me active machines"
# Expected: We have 8 machines: Boiler-1, Compressor-1, ...
```

**If you see these outputs with template names and correct responses, you're testing REAL skill behavior!** ✅

---

## 🚀 Ready to Start Testing

You now have:
1. ✅ Proper test tools (`test_skill_logic.py`, `test_skill_chat.py`)
2. ✅ Verification methods (template usage, API endpoint tracking)
3. ✅ Understanding of real vs fake responses
4. ✅ Systematic testing methodology
5. ✅ No mocks - testing EXACT skill behavior from `__init__.py`

**Current Test Progress:**
- ✅ EP2: System Statistics (8/8 PASS)
- ✅ EP6: Machine Status (4/4 tested PASS)
- ✅ EP4: Machine List (2/3 PASS)
- ⏳ EP3: Aggregated Stats (Not Implemented)
- ⏳ EP9: Time-Series (Not Implemented)

**See `TEST_SESSION_RESULTS.md` for detailed results and bugs fixed.**

**Proceed to `1by1.md` to continue testing remaining endpoints!**
