# 🔬 OVOS EnMS Testing Protocol - MANDATORY RULES

**Date Created:** 2025-11-21  
**Last Updated:** 2025-11-21 (Session 2)  
**Purpose:** Ensure systematic testing with EXACT matching between curl and OVOS  
**Current Focus:** Batches 5-12 (Baseline, KPIs, Forecasting, Analytics)

---

## 🎯 MISSION: Test Batches 5-12 Systematically

**Goal:** Complete testing of ALL API endpoints (Batches 5-12)  
**Starting Coverage:** 37% (112 PASS / 3 FAIL)  
**Target Coverage:** 100% - ALL batches must be tested and working  
**Method:** One query at a time, implement missing endpoints if needed, fix immediately, document thoroughly

---

## ⚠️ CRITICAL RULES - NEVER VIOLATE

### 1. Test Script Usage - READ CAREFULLY

**TWO different scripts with DIFFERENT purposes:**

#### `test_skill_logic.py` - FOR AUTOMATED TESTING (YOU USE THIS)
- **Purpose:** Non-interactive automated testing
- **Who uses it:** YOU (the AI agent)
- **How to run:** `python3 scripts/test_skill_logic.py "query text"`
- **Output:** Detailed logs showing intent, API call, response
- **Why:** Can be called from command line without user interaction

#### `test_skill_chat.py` - FOR USER VERIFICATION (MUST MATCH)
- **Purpose:** Interactive chat interface
- **Who uses it:** HUMAN USER (to verify your work)
- **How to run:** `python3 scripts/test_skill_chat.py` then type queries
- **Output:** Conversational responses (simulates OVOS GUI)
- **Why:** User will run this to verify behavior matches what you documented

**CRITICAL SYNCHRONIZATION RULE:**
```
test_skill_logic.py (what you test) 
    MUST MATCH EXACTLY 
test_skill_chat.py (what user verifies)
    MUST MATCH EXACTLY
__init__.py (production skill code)
```

**When you fix bugs, update ALL THREE files to keep them synchronized!**

### 2. Query Source - EXACT TEXT ONLY
- ✅ **USE:** Exact "OVOS Query" text from 1by1.md (copy-paste, in quotes)
- ❌ **DON'T:** Paraphrase, modify, or create your own queries
- **EXCEPTION:** Only create new queries AFTER existing query PASSES
- **EXAMPLE:** `"What's the expected energy for Compressor-1?"` (exact from doc)

### 3. Testing Order - STRICT SEQUENCE
- ✅ **DO:** One query at a time, complete before moving to next
- ✅ **DO:** Fix ALL failures immediately before continuing
- ✅ **DO:** Complete one endpoint before moving to next endpoint
- ✅ **DO:** Complete one batch before moving to next batch
- ❌ **DON'T:** Skip queries or jump around
- ❌ **DON'T:** Leave failing tests behind
- ❌ **DON'T:** Test multiple queries in parallel

**ITERATION LOOP (repeat until PASS):**
```
1. SELECT next ⏳ NOT TESTED query from 1by1.md
2. RUN test_skill_logic.py with exact query
3. RUN curl command from 1by1.md
4. COMPARE outputs (intent, API, params, data, voice)
5. IF PASS → Document & move to next query
6. IF FAIL → Fix code → Re-test → Repeat step 2
```

**NEVER move forward while ANY query shows ❌ FAIL!**

### 4. Comparison Requirements
**ALL must match EXACTLY:**
1. Intent type (exact IntentType enum)
2. API endpoint path (character-for-character)
3. API parameters (all required params present)
4. Response data (values match curl output)
5. Voice output (natural, matches data)

### 5. Code Synchronization
**When fixing bugs, update ALL 3:**
1. `__init__.py` - Main skill logic
2. `test_skill_chat.py` - Interactive test (user runs this)
3. `test_skill_logic.py` - Unit tests

### 6. Documentation Updates
**After EVERY test:**
1. Mark status in 1by1.md (`✅ PASS` or `❌ FAIL`)
2. Add actual results (curl output, OVOS response)
3. Update progress table percentages
4. Document fixes in session log

---

## 📋 Testing Protocol (Execute for EVERY Query)

### Step 1: SELECT
```bash
# Find next ⏳ NOT TESTED or ❌ FAIL in current batch
cd /home/ubuntu/ovos/enms-ovos-skill
grep -n "⏳ NOT TESTED\|❌ FAIL" docs/1by1.md | head -5
```

**Action:** Identify the query number (e.g., EP18.1, EP27.3) and exact OVOS Query text

### Step 2: TEST with test_skill_logic.py
```bash
# Use EXACT "OVOS Query" from 1by1.md
cd /home/ubuntu/ovos/enms-ovos-skill
python3 scripts/test_skill_logic.py "exact OVOS Query text here"
```

**Action:** 
- Copy exact query text from 1by1.md (including quotes)
- Run test_skill_logic.py
- Save output showing: Intent, Confidence, API called, Parameters, Response

### Step 3: CURL
```bash
# Run EXACT curl command from 1by1.md
# This shows what the API actually returns
curl ... | jq '.' > /tmp/curl_output.json
```

**Action:**
- Copy exact curl command from 1by1.md for this query
- Run it to see raw API response
- Save output for comparison

### Step 4: COMPARE
**Check ALL of these (must ALL match):**
- [ ] Intent matches expected (from verification checklist in 1by1.md)
- [ ] API endpoint exact match (not similar, EXACT path)
- [ ] All parameters present and correct (machine_id, time ranges, etc.)
- [ ] Response data matches curl values (within rounding: 97.7 ≈ 97.74)
- [ ] Voice output is natural and accurate

**PASS Criteria:** ALL 5 checkboxes must be ✓  
**FAIL Criteria:** ANY checkbox is ✗ = MUST FIX

### Step 5: FIX (if needed)
```bash
# If ANY comparison fails:
1. Identify root cause (wrong intent? wrong API? missing param?)
2. Fix in __init__.py (main logic)
3. Update test_skill_chat.py (keep synchronized)
4. Update test_skill_logic.py (keep synchronized)
5. Re-test from Step 2 until PASS
```

**Common fixes:**
- Wrong intent → Add/update heuristic pattern in `lib/intent_parser.py`
- Wrong API → Update intent handler in `__init__.py`
- Missing param → Update validator in `lib/validator.py`
- Wrong data → Update response formatter in `lib/response_formatter.py`

**CRITICAL:** After fixing, RE-TEST the same query. Do NOT move forward until PASS.

### Step 6: DOCUMENT
```bash
# Update 1by1.md with results:
1. Add curl output under "Actual Results:"
2. Add OVOS response (from test_skill_logic.py output)
3. Add Intent and API called
4. Mark verification checkboxes [x]
5. Set Status: ✅ PASS or ❌ FAIL
6. Add Test Date: 2025-11-21 HH:MM UTC
7. If FAIL, add "Issues:" and "TODO:" sections
```

**Example documentation:**
```markdown
**Actual Results:**
- curl Output: `{"predicted_energy_kwh": 97.74, ...}`
- OVOS Response: `"Compressor-1 is predicted to consume 97.7 kWh"`
- Intent: `baseline` (confidence: 0.95, heuristic tier)
- API: `POST /baseline/predict`

**Verification:**
- [x] Intent: BASELINE ✅
- [x] API: POST /baseline/predict ✅
- [x] Value: 97.7 kWh ≈ 97.74 kWh ✅
- [x] Voice: Natural and accurate ✅

**Status:** ✅ PASS
**Test Date:** 2025-11-21 14:30 UTC
```

---

## 🎯 Current Priority: BATCHES 5-12

### Batch 5: Baseline Prediction (CRITICAL - 58% complete)
- EP17: GET /baseline/models (38% - 3/8 PASS)
- EP18: POST /baseline/predict ⭐ (58% - 7/12 PASS) 
- EP19: GET /baseline/model/{id} (0% - NOT STARTED)
- EP20: POST /baseline/train-seu (0% - NOT STARTED)

### Batch 6: KPIs & Performance Analytics (0% complete)
- EP21: GET /kpi/all (0% - NOT STARTED)
- EP22: GET /kpi/energy-cost (0% - NOT STARTED)
- EP23-26: Performance endpoints (0% - NOT STARTED)

### Batch 7: Forecasting (30% complete)
- EP27: GET /forecast/short-term (30% - 3/10 PASS)
- EP28: GET /forecast/demand (0% - NOT STARTED)

### Batch 8: Factory & Analytics (50% complete)
- EP29: GET /seus (0% - NOT STARTED)
- EP30: GET /factory/summary (0% - NOT STARTED)
- EP31: GET /analytics/top-consumers ⭐ (50% - 6/12 PASS)

### Batch 9: Multi-Energy Support (0% complete)
- EP33-35: Energy types endpoints (0% - NOT STARTED)

### Batches 10-12: Deprecated & Compliance (0% complete)
- EP36-44: Deprecated OVOS endpoints, Alerts, ISO 50001 (0% - NOT STARTED)

**Testing Strategy:**
1. **START:** Complete Batch 5 first (baseline is critical)
2. **CONTINUE:** Batch 6 (test all KPI queries - implement if needed)
3. **CONTINUE:** Batch 7 (forecasting partially working - complete remaining)
4. **CONTINUE:** Batch 8 (analytics partially working - complete remaining)
5. **CONTINUE:** Batch 9 (multi-energy support - implement and test)
6. **CONTINUE:** Batches 10-12 (alerts, compliance - implement and test)

**Success Criteria:**
- [ ] Batch 5: 100% (all baseline queries PASS)
- [ ] Batch 6: 100% (all KPI queries PASS - implement endpoints if needed)
- [ ] Batch 7: 100% (all forecasting queries PASS)
- [ ] Batch 8: 100% (all analytics queries PASS)
- [ ] Batch 9: 100% (all multi-energy queries PASS)
- [ ] Batches 10-12: 100% (all compliance/alerts queries PASS)
- [ ] Overall: 100% total coverage (ALL batches complete)

---

## 📚 Source of Truth

**API Documentation:** `docs/ENMS-API-DOCUMENTATION-FOR-OVOS.md`
- Use this for ALL API endpoint details
- Check parameter names, types, formats
- Verify expected response structure
- When confused, READ THIS FIRST

**Testing Plan:** `docs/1by1.md`
- Contains exact OVOS queries to test
- curl commands for comparison
- Verification checklists
- Progress tracking

---

## 🚨 Common Mistakes to Avoid

1. ❌ **Using test_skill_chat.py for testing** → Use test_skill_logic.py instead
2. ❌ **Creating your own query text** → Copy exact text from 1by1.md
3. ❌ **Skipping queries or batches** → Complete sequentially
4. ❌ **Marking PASS without verifying ALL 5 comparison points** → All must match
5. ❌ **Forgetting to update test_skill_chat.py after fixing __init__.py** → Keep synchronized
6. ❌ **Moving forward while previous query still FAILS** → Fix immediately
7. ❌ **Not documenting test results in 1by1.md** → Update after every test
8. ❌ **Skipping endpoints because they appear unimplemented** → Implement them, then test
9. ❌ **Batch testing without individual verification** → Test one at a time
10. ❌ **Modifying curl commands** → Use exact commands from 1by1.md
11. ❌ **Assuming endpoint doesn't exist without checking API** → Verify with curl first
12. ❌ **Moving to next batch before completing current batch** → Must reach 100% before proceeding

---

## 🔄 Session Workflow

**START OF SESSION:**
1. Read TESTING_PROTOCOL.md (this file)
2. Read 1by1.md to understand progress
3. Read ENMS-API-DOCUMENTATION-FOR-OVOS.md for API details
4. Identify current batch and next untested query

**FOR EACH QUERY:**
1. SELECT next ⏳ NOT TESTED query
2. TEST with test_skill_logic.py
3. CURL to get API response
4. COMPARE all 5 checkpoints
5. FIX if any checkpoint fails (re-test until PASS)
6. DOCUMENT results in 1by1.md
7. REPEAT for next query

**END OF SESSION:**
1. Count total PASS/FAIL queries
2. Update progress table in 1by1.md
3. Document session summary
4. Provide handover notes for next session

**NEVER:**
- Skip failing queries
- Test multiple queries without documenting
- Modify code without updating all 3 files
- Move to next batch with incomplete current batch

---

## 📊 Progress Tracking

**How to count:**
```bash
# Count PASS
grep -c "✅ PASS" docs/1by1.md

# Count FAIL
grep -c "❌ FAIL" docs/1by1.md

# Find NOT TESTED in current batch
sed -n '/^## 🧪 BATCH 5:/,/^## 🧪 BATCH 6:/p' docs/1by1.md | grep -c "⏳ NOT TESTED"
```

**Update progress table:**
- After completing each endpoint, update the table in 1by1.md
- Calculate percentage: (PASS / Total Queries) × 100
- Update status: ⏳ Not Started → 🔄 In Progress → ✅ Complete
