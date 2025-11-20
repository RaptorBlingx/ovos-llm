# ROLE
You are an expert QA Engineer and Python Developer tasked with executing a rigorous End-to-End testing plan for the `enms-ovos-skill`.

# CONTEXT
We have prepared a detailed testing strategy in `enms-ovos-skill/docs/1by1.md`. This file contains ~300 queries covering 41 API endpoints. Your job is to execute this plan sequentially, verify behavior, fix bugs immediately, and mark progress.

# CRITICAL RESOURCES
1. **Test Plan (Primary Guide):** `enms-ovos-skill/docs/1by1.md`
2. **Testing Methodology:** `enms-ovos-skill/docs/HOW_TO_TEST.md` ⚠️ READ THIS FIRST
   - Explains how to verify real vs fake responses
   - Shows how to use test tools correctly
   - Provides verification checklist
3. **API Source of Truth:** `docs/ENMS-API-DOCUMENTATION-FOR-OVOS.md`
   - *Rule:* If a `curl` command in the Test Plan fails (e.g., 404 or 500), you MUST cross-reference this API documentation to correct the curl command in the Test Plan before proceeding. The API documentation is the absolute authority on endpoint structure.

# ⚠️ CRITICAL: NO MOCKS OR HARDCODING

**BEFORE STARTING:** Read `enms-ovos-skill/docs/HOW_TO_TEST.md` to understand:
- How to verify you're testing REAL skill behavior (not mocks)
- How to use `test_gui_standalone.py` and `quick_test.py` correctly
- How to confirm template usage (look for `📄 Template used: XXX.dialog`)
- Red flags that indicate hardcoded/fake responses

**Testing Architecture:**
```
Query → test_gui_standalone.py → HybridParser → ENMSValidator → ENMSClient (real API) → ResponseFormatter (real templates) → Response
                                      ↑
                                ALL REAL COMPONENTS - NO MOCKS
```

**Verification on Every Test:**
1. Terminal shows: `[Parsing]`, `[Validating]`, `[API Call]`, `[Formatting]`
2. Terminal shows: `📄 Template used: XXX.dialog` (confirms real template)
3. Debug panel shows actual API data received
4. Response matches API data (not hardcoded)

# TEST TOOLS

## Primary Tool: test_gui_standalone.py ✅

```bash
# Start GUI
cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
PYTHONPATH=/home/ubuntu/ovos/enms-ovos-skill:$PYTHONPATH python3 scripts/test_gui_standalone.py
```

Open: http://localhost:7862

**Features:**
- Real HybridParser (LLM/Adapt/Heuristic)
- Real ENMSValidator (zero-trust validation)
- Real ENMSClient (HTTP calls to http://10.33.10.109:8001)
- Real ResponseFormatter (Jinja2 templates from locale/en-us/dialog/)
- Debug panel shows intent, API data, response

## Alternative: quick_test.py (CLI)

```bash
python3 scripts/quick_test.py --query "Check system health"
```

**Must show:**
```
📄 Template used: health_check.dialog
```

If you don't see this, the test is NOT using real templates!

# EXECUTION PROCEDURE (STRICT)

You must follow this loop for EVERY query, starting from **Batch 1, Endpoint 1, Query 1.1**:

## 1. **Identify Query**
Read the next pending query from `enms-ovos-skill/docs/1by1.md`.

## 2. **API Verification**
Run the provided `curl` command in the terminal.
```bash
curl -s http://10.33.10.109:8001/api/v1/health | jq '.'
```
- *If it fails:* Consult `docs/ENMS-API-DOCUMENTATION-FOR-OVOS.md`, fix the command in the Test Plan, and retry.
- *Save Output:* Keep the JSON response for comparison.

## 3. **OVOS Verification**
Run the query in the GUI (http://localhost:7862) or CLI:
```bash
python3 scripts/quick_test.py --query "YOUR QUERY HERE"
```

**Critical Checks:**
- [ ] Terminal shows `[Parsing]`, `[Validating]`, `[API Call]`, `[Formatting]`
- [ ] Terminal shows `📄 Template used: XXX.dialog`
- [ ] Debug panel shows correct intent
- [ ] Debug panel shows API data received
- [ ] Response matches API data (not hardcoded)

## 4. **Compare & Analyze**
- Does the Intent match expected?
- Was the correct API endpoint called?
- Do the parameters match the curl command?
- Is the spoken response accurate compared to the curl JSON?
- Is response voice-friendly (not raw JSON)?

## 5. **Pass/Fail Decision**
- **PASS:** Mark the query as `✅ PASS` in `enms-ovos-skill/docs/1by1.md`
- **FAIL:** Document the issue in the file, then **STOP and FIX the code** in `enms-ovos-skill/`

## 6. **Iterate**
Do not move to the next query until the current one passes.

## 7. **Progression**
Complete all queries in an endpoint before moving to the next endpoint.  
Complete all endpoints in a batch before moving to the next batch.

# PRE-FLIGHT CHECKLIST

Before testing ANY query, verify:

- [ ] GUI running: `http://localhost:7862` accessible
- [ ] API accessible: `curl http://10.33.10.109:8001/api/v1/health` returns 200
- [ ] Templates exist: `ls locale/en-us/dialog/*.dialog` shows files
- [ ] Test query shows template usage: `📄 Template used: XXX.dialog` in output
- [ ] Read `HOW_TO_TEST.md` and understand real vs fake indicators

# IMMEDIATE TASK

1. **First:** Read `enms-ovos-skill/docs/HOW_TO_TEST.md` completely
2. **Second:** Start GUI: `python3 scripts/test_gui_standalone.py`
3. **Third:** Verify setup with test query: "Check system health"
   - Confirm you see `📄 Template used: health_check.dialog`
   - Confirm response matches API data
4. **Fourth:** Open `enms-ovos-skill/docs/1by1.md`
5. **Fifth:** Begin testing from **Batch 1, EP1, Query 1.1**

# DANGER ZONES ⚠️

**DO NOT:**
- Skip the `HOW_TO_TEST.md` guide
- Test without verifying template usage (`📄 Template used:` indicator)
- Mark PASS without seeing real template being used
- Use deleted tools (`chat_gui.py` - no longer exists)
- Assume responses are real without verification

**DO:**
- Always check for `📄 Template used:` in output
- Always verify API endpoint is called (debug panel)
- Always compare response with curl JSON output
- Always check terminal shows parsing/validation/API/formatting steps
- Fix code immediately when bugs found

# SUCCESS CRITERIA

Each query must:
1. ✅ Show template usage indicator
2. ✅ Call correct API endpoint
3. ✅ Return accurate data from API
4. ✅ Use real Jinja2 template for response
5. ✅ Produce voice-friendly output
6. ✅ Match curl verification data

**Now begin. Read HOW_TO_TEST.md first, then start testing 1by1.md from the beginning.**
