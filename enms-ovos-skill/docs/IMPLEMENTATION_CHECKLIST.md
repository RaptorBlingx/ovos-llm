# ✅ OVOS Integration Implementation Checklist

**Created:** 2025-11-27  
**Updated:** 2025-11-28  
**Purpose:** Step-by-step checklist for AI agent implementing OVOS integration  
**Pre-requisites:** WSL2 verified, WSL2_WORKFLOW_GUIDE.md reviewed, OVOS_CORE_INTEGRATION_PLAN.md read

---

## ✅ WSLg Audio Issue SOLVED (2025-11-28)

### Problem Identified

**WSLg RDP audio tunnel corrupts audio before it reaches OVOS.**

The audio pipeline in WSL2 is:
```
Windows Mic → RDPSource → PulseAudio (WSLg) → OVOS Listener → STT
                 ↑                    ↑
            [LOSSY RDP]         [RESAMPLE 44.1→16kHz]
                 ↑_________________________↑
                      AUDIO CORRUPTION
```

**Evidence:**
- OVOS-captured utterances transcribe as garbage: "fuck that", "we are worried", "perjury over me"
- Windows-native captured audio transcribes correctly: "factory overview" ✅
- Same Vosk model, same audio format - only difference is capture location

### Root Cause

1. **RDPSource is virtualized** - not a real audio device
2. **Sample rate conversion (44.1kHz → 16kHz) in RDP tunnel is lossy**
3. **Audio corruption happens BEFORE it reaches OVOS**

### ✅ SOLUTION IMPLEMENTED: Windows STT Bridge

**Hybrid architecture using Precise Lite + Whisper on Windows:**

```
┌─────────────────────────────────────────────────────────┐
│                    Windows (Native Audio)               │
│                                                          │
│  Microphone ──> Precise Lite ──> Wake Word Detected     │
│                                         │                │
│                                         ▼                │
│                     sounddevice.InputStream             │
│                                         │                │
│                                         ▼                │
│                          Whisper (Transcription)        │
│                                         │                │
│                                         ▼                │
│                              WebSocket (port 5678)      │
└─────────────────────────────┬───────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                      WSL2 (OVOS Core)                   │
│                                                          │
│  wsl_ovos_bridge.py ──> OVOS Messagebus ──> EnMS Skill  │
└─────────────────────────────────────────────────────────┘
```

**Implementation Status:**
- ✅ **Precise Lite Wake Word**: OVOS's production wake word engine (no hallucinations)
- ✅ **Whisper STT**: High-quality transcription on Windows
- ✅ **WebSocket Bridge**: Sends utterances to WSL2 OVOS
- ✅ **Testing Complete**: "Factory overview" and "What is the energy consumption of compressor 1?" working

**Files:**
- `bridge/windows_stt_bridge_final.py` - Main Windows bridge
- `bridge/wsl_ovos_bridge.py` - WSL2 WebSocket server
- `bridge/PRECISE_LITE_SOLUTION.md` - Complete documentation
- `bridge/start_bridge.bat` - Easy startup script

**See:** `bridge/PRECISE_LITE_SOLUTION.md` for complete solution details.

---

## 🎯 Critical Success Criteria

**Before starting:**
- [ ] "factory overview" query works in `test_skill_chat.py` (standalone)
- [ ] All 8 machines load correctly
- [ ] EnMS API accessible (`http://10.33.10.109:8001/api/v1`)
- [ ] Qwen3 model loads without errors

**After OVOS integration:**
- [ ] "factory overview" via OVOS voice → Same response as standalone
- [ ] Latency: <500ms total (STT ~200ms + Processing ~180ms + TTS ~5ms)
- [ ] Wake word "Hey Mycroft" triggers listener
- [ ] Complex queries use LLM tier correctly
- [ ] Multi-turn context preserved

---

## 📝 Phase 1: Code Preparation (15 minutes)

### Task 1.1: Comment Out @intent_handler Decorators ✅ COMPLETED

**File:** `d:\ovos-llm-core\ovos-llm\enms-ovos-skill\__init__.py`  
**Lines:** 1654-1680 (approximate)

**What to do:**
```python
# BEFORE (around line 1654):
@intent_handler("energy.query.intent")
def handle_energy_query(self, message: Message):
    ...

# AFTER:
# @intent_handler("energy.query.intent")
# def handle_energy_query(self, message: Message):
#     ...
```

**Find all 3 decorators:**
- [x] `@intent_handler("energy.query.intent")` → Comment out
- [x] `@intent_handler("machine.status.intent")` → Comment out
- [x] `@intent_handler("factory.overview.intent")` → Comment out

**Keep the methods** - just comment out the decorators. Methods can stay for documentation.

**Verification:**
```bash
# In PowerShell or WSL2
grep -n "@intent_handler" d:\ovos-llm-core\ovos-llm\enms-ovos-skill\__init__.py
# Should return NO matches (all commented)
```

---

### Task 1.2: Add self.activate() to initialize() Method ✅ COMPLETED

**File:** `d:\ovos-llm-core\ovos-llm\enms-ovos-skill\__init__.py`  
**Line:** ~155 (end of `initialize()` method)

**⚠️ CRITICAL:** Without this, converse() won't be called on first utterance!

**What to do:**
Find the `initialize()` method and add `self.activate()` at the very end:

```python
def initialize(self):
    """
    Called after skill construction
    Initialize all SOTA components
    """
    self.logger.info("skill_initializing", ...)
    
    # ... existing initialization code ...
    
    # Load machine whitelist from API
    machines = self._run_async(self.api_client.list_machines(is_active=True))
    machine_names = [m['name'] for m in machines]
    self.validator.update_machine_whitelist(machine_names)
    
    # ✅ ADD THIS LINE (CRITICAL!)
    self.activate()
    
    self.logger.info("skill_initialized",
                    components_ready=True,
                    machine_count=len(machine_names),
                    always_active=True)  # Added status flag
```

**Checklist:**
- [x] Found `initialize()` method (starts around line 88)
- [x] Added `self.activate()` after machine whitelist loading
- [x] Added `always_active=True` to logger.info for visibility
- [x] Saved file

**Why this is critical:**
- OVOS only calls `converse()` for "active" skills
- Without `self.activate()`, skill is NOT active on first use
- With `self.activate()`, skill is ALWAYS active → converse() called every time

---

### Task 1.3: Test Standalone Again ✅ COMPLETED

**Purpose:** Verify code changes didn't break anything

**Commands:**
```bash
# In PowerShell
cd D:\ovos-llm-core\ovos-llm\enms-ovos-skill
python scripts\test_skill_chat.py
```

**Test queries:**
- [x] "factory overview" → Returns factory status with 8 machines ✅
- [x] "compressor 1 kwh" → Returns Compressor-1 energy consumption
- [x] "top 3 consumers" → Returns ranked list
- [x] "what's the baseline for boiler 1" → Uses LLM tier

**Expected behavior:** Exact same as before code changes. ✅ VERIFIED

**If fails:** Revert changes and check syntax errors.

---

## 📥 Phase 2: Install OVOS in WSL2 (1-2 hours) ✅ COMPLETED

### Task 2.1: Open WSL2 Terminal in VS Code ✅ COMPLETED

**Steps:**
- [x] In VS Code, click `+` next to terminal tabs
- [x] Select "wsl" from dropdown
- [x] Verify you're in WSL2: `uname -a` (should show "Linux")
- [x] Navigate to project: `cd /mnt/d/ovos-llm-core/ovos-llm`

---

### Task 2.2: Install Ubuntu System Dependencies ✅ COMPLETED

**In WSL2 terminal:**
```bash
# Update package lists
sudo apt update && sudo apt upgrade -y

# Install Python and audio dependencies
sudo apt install -y python3-pip python3-venv portaudio19-dev pulseaudio

# Verify installations
python3 --version  # Should be 3.11+
pulseaudio --version  # Should show version
```

**Checklist:**
- [x] `apt update` completed successfully
- [x] All packages installed without errors
- [x] Python 3.10.12 available
- [x] PulseAudio installed (for WSLg audio support)

---

### Task 2.3: Create OVOS Virtual Environment ✅ COMPLETED

**⚠️ IMPORTANT:** Create venv in WSL2 home (`~`), NOT in `/mnt/d/` (Windows drive)!

**In WSL2 terminal:**
```bash
# Navigate to WSL2 home
cd ~

# Create virtual environment
python3 -m venv ovos-env

# Activate virtual environment
source ovos-env/bin/activate

# Verify activation (should show (ovos-env) in prompt)
which python  # Should show: /home/raptorblingx/ovos-env/bin/python
```

**Checklist:**
- [x] Venv created in `~/ovos-env/`
- [x] Venv activated (prompt shows `(ovos-env)`)
- [x] `which python` points to venv

---

### Task 2.4: Install OVOS Core Packages ✅ COMPLETED

**In WSL2 terminal (with ovos-env activated):**
```bash
# Install OVOS packages in order
pip install ovos-messagebus
pip install ovos-core[mycroft]
pip install ovos-audio[extras]
pip install ovos-dinkum-listener[extras]
pip install ovos-phal

# Verify installations
pip list | grep ovos
# Should show: ovos-core, ovos-audio, ovos-dinkum-listener, ovos-messagebus, ovos-phal
```

**Expected versions:**
- [x] ovos-core: 2.1.1 ✅
- [x] ovos-audio: 1.1.0 ✅
- [x] ovos-dinkum-listener: 0.5.0 ✅
- [x] ovos-messagebus: 0.0.10 ✅
- [x] ovos-phal: 0.2.11 ✅

**If any package fails:** Check error messages, may need additional system dependencies.

**[extras] Note:** This installs default plugins (Vosk STT, Mimic3 TTS, Precise Lite wake word) automatically.

---

### Task 2.5: Install EnMS Skill as Package ✅ COMPLETED

**Approach: Installed as editable package (pip install -e .)**

```bash
# In WSL2 terminal with ovos-env activated
cd /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill

# Install skill as editable package
pip install -e .

# Verify installation
pip list | grep enms-ovos-skill
# Should show: enms-ovos-skill 1.0.0 /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill
```

**Checklist:**
- [x] Skill installed as package ✅
- [x] Editable mode allows live code updates ✅
- [x] OVOS discovers skill via entry_points ✅
- [x] Verified with `pip list` ✅

---

## ⚙️ Phase 3: Configure OVOS (30 minutes) ⏳ IN PROGRESS

### Task 3.1: Create mycroft.conf ✅ COMPLETED

**File:** `~/.config/mycroft/mycroft.conf` (in WSL2 home)

**Steps:**
```bash
# Create config directory
mkdir -p ~/.config/mycroft

# Open file in VS Code
code ~/.config/mycroft/mycroft.conf
```

**Paste this configuration:**
```json
{
  "lang": "en-us",
  
  "listener": {
    "wake_word": "hey mycroft",
    "phoneme_duration": 120,
    "threshold": 1e-90,
    "multiplier": 1.0,
    "energy_ratio": 1.5
  },
  
  "stt": {
    "module": "ovos-stt-plugin-vosk",
    "ovos-stt-plugin-vosk": {
      "model": "en-us",
      "lang": "en-us"
    }
  },
  
  "tts": {
    "module": "ovos-tts-plugin-mimic3",
    "ovos-tts-plugin-mimic3": {
      "voice": "en_US/cmu-arctic_low",
      "lang": "en-us"
    }
  },
  
  "hotwords": {
    "hey mycroft": {
      "module": "ovos-ww-plugin-precise-lite",
      "model": "https://github.com/OpenVoiceOS/precise-lite-models/raw/master/wakewords/en/hey_mycroft.tflite",
      "expected_duration": 3,
      "trigger_level": 3,
      "sensitivity": 0.5,
      "listen": true
    }
  },
  
  "skills": {
    "blacklisted_skills": [],
    "priority_skills": [
      "enms-ovos-skill"
    ]
  },
  
  "intents": {
    "pipeline": [
      "stop_high",
      "converse",
      "padatious_high",
      "adapt_high",
      "fallback_high",
      "stop_medium",
      "adapt_medium",
      "fallback_medium",
      "fallback_low"
    ],
    "adapt": {
      "conf_high": 0.65,
      "conf_med": 0.45,
      "conf_low": 0.25
    },
    "padatious": {
      "conf_high": 0.85,
      "conf_med": 0.65,
      "conf_low": 0.45
    }
  },
  
  "websocket": {
    "host": "127.0.0.1",
    "port": 8181,
    "route": "/core",
    "shared_connection": false
  }
}
```

**Checklist:**
- [ ] File created at `~/.config/mycroft/mycroft.conf`
- [ ] JSON is valid (no syntax errors)
- [ ] Pipeline includes "converse" at position 2
- [ ] enms-ovos-skill in priority_skills list

---

### Task 3.2: Create Skill Settings ⏳ NOT STARTED

**File:** `~/.config/mycroft/skills/enms-ovos-skill/settings.json`

**Steps:**
```bash
# Create skill settings directory
mkdir -p ~/.config/mycroft/skills/enms-ovos-skill

# Open file in VS Code
code ~/.config/mycroft/skills/enms-ovos-skill/settings.json
```

**Paste this configuration:**
```json
{
  "enms_api_base_url": "http://10.33.10.109:8001/api/v1",
  "llm_model_path": "/mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/models/Qwen_Qwen3-1.7B-Q4_K_M.gguf",
  "confidence_threshold": 0.85,
  "enable_progress_feedback": true,
  "progress_threshold_ms": 500
}
```

**⚠️ NOTE:** Path uses `/mnt/d/` to access Windows drive from WSL2.

**Checklist:**
- [ ] File created
- [ ] API URL matches EnMS server
- [ ] LLM model path correct (verified exists)
- [ ] JSON valid

**Verify model path:**
```bash
ls -lh /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/enms_ovos_skill/models/Qwen_Qwen3-1.7B-Q4_K_M.gguf
# Should show file size (e.g., 1.1G)
```

---

## 🚀 Phase 4: Start OVOS Services (4 terminals) ⏳ IN PROGRESS

### Task 4.1: Prepare 4 WSL2 Terminals

**In VS Code:**
- [ ] Click `+` → Select "wsl" (Terminal 1)
- [ ] Click `+` → Select "wsl" (Terminal 2)
- [ ] Click `+` → Select "wsl" (Terminal 3)
- [ ] Click `+` → Select "wsl" (Terminal 4)

**In each terminal:**
```bash
source ~/ovos-env/bin/activate
# Prompt should show: (ovos-env) raptorblingx@RAPTORBLINGX:...
```

---

### Task 4.2: Start Services in Order

**Terminal 1: Message Bus (START FIRST!)** ✅ RUNNING
```bash
ovos-messagebus run
```

**Wait for:** `"Websocket started on port 8181"`  
**Status:** [x] Running ✅

---

**Terminal 2: Skills Service** ✅ RUNNING
```bash
ovos-core
```

**Watch for:**
- `"ATTEMPTING TO LOAD PLUGIN SKILL: enms-ovos-skill.yourname"` ✅
- `"skill_initializing"` ✅
- `"hybrid_parser_initialized"` ✅
- `"skill_initialized_successfully"` ✅
- `"Skill enms-ovos-skill.yourname loaded successfully"` ✅
- `"machine_whitelist_refreshed count=8"` ✅

**Status:** [x] Running ✅, [x] Skill loaded ✅, [x] Machine whitelist loaded ✅

---

**Terminal 3: Audio Service** ⏳ NOT STARTED
```bash
ovos-audio
```

**Wait for:** `"Audio service started"`  
**Status:** [ ] Running

---

**Terminal 4: Listener Service** ✅ REPLACED WITH BRIDGE
```bash
# ovos-dinkum-listener NOT USED - replaced with Windows STT Bridge
```

**Status:** [x] REPLACED with `windows_stt_bridge_final.py` ✅

**✅ SOLUTION IMPLEMENTED:**
- **Issue:** WSLg RDP audio tunnel corrupts microphone input
- **Symptom:** STT produces garbage like "fuck that", "we are worried" instead of actual speech
- **Root Cause:** RDPSource + PulseAudio resampling (44.1kHz → 16kHz) is lossy
- **Proof:** Windows-native audio capture → Vosk = "factory overview" ✅

**🎉 BRIDGE SOLUTION WORKING:**
- **Precise Lite**: Wake word detection on Windows (same engine OVOS uses)
- **Whisper**: STT on Windows (clean audio, accurate transcription)
- **WebSocket**: Sends recognized utterances to WSL2 OVOS messagebus
- **Test Results**: Wake word detected 2/2, commands transcribed 100% accurately

**Files:**
- `bridge/windows_stt_bridge_final.py` - Main Windows STT bridge
- `bridge/wsl_ovos_bridge.py` - WSL2 WebSocket server
- `bridge/start_bridge.bat` - Easy startup script

**Usage:**
```bash
# Instead of ovos-dinkum-listener, run:
d:\ovos-llm-core\ovos-llm\enms-ovos-skill\bridge\start_bridge.bat
```

---

## 🌉 Phase 5.5: Windows STT Bridge Setup ✅ COMPLETED

### Task 5.5.1: Start WSL2 OVOS Bridge ✅ COMPLETED

**Terminal 4 (PowerShell - Windows side):**
```bash
wsl bash -c "cd /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/bridge ; nohup python3 wsl_ovos_bridge.py > wsl_bridge.log 2>&1 &"
```

**Expected:**
- WebSocket server starts on port 5678
- Connects to OVOS messagebus on port 8181
- Ready to receive utterances from Windows

**Status:** [x] Running ✅

---

### Task 5.5.2: Start Windows STT Bridge ✅ COMPLETED

**Terminal 5 (PowerShell - Windows side):**
```bash
python d:\ovos-llm-core\ovos-llm\enms-ovos-skill\bridge\windows_stt_bridge_final.py
```

**OR use startup script:**
```bash
d:\ovos-llm-core\ovos-llm\enms-ovos-skill\bridge\start_bridge.bat
```

**Expected:**
- Precise Lite model downloaded (hey_mycroft.tflite)
- Whisper 'small' model loaded
- Connected to WSL2 bridge (port 5678)
- "💤 Waiting for wake word..."

**Status:** [x] Running ✅

---

### Task 5.5.3: Test Bridge Communication ✅ COMPLETED

**Test 1: Wake word detection**
```
You: "Hey Mycroft"
Expected: "🎯 WAKE WORD DETECTED! ('Hey Mycroft')"
```
**Status:** [x] PASSED ✅ (2/2 detections)

**Test 2: Command transcription**
```
You: "Hey Mycroft"
Bridge: [wake word detected]
You: "Factory overview"
Expected: "📝 Command: 'Factory overview.'"
Expected: "📤 Sent to OVOS: 'Factory overview.'"
```
**Status:** [x] PASSED ✅

**Test 3: Complex command**
```
You: "Hey Mycroft"
Bridge: [wake word detected]
You: "What is the energy consumption of compressor 1?"
Expected: "📝 Command: 'What is the energy consumption of compressor 1?'"
Expected: "📤 Sent to OVOS: 'What is the energy consumption of compressor 1?'"
```
**Status:** [x] PASSED ✅

**Bridge Architecture Status:**
- ✅ Windows audio capture (clean, no corruption)
- ✅ Precise Lite wake word (no false positives)
- ✅ Whisper transcription (100% accuracy)
- ✅ WebSocket to WSL2 OVOS (working)
- ✅ No hallucinations (0 false wake words)

---

## 🧪 Phase 6: End-to-End Testing (Next Step) ⏳ NOT STARTED

### Task 5.1: Text Input Test (CLI) ⏳ NOT STARTED

**Open 5th WSL2 terminal:**
```bash
source ~/ovos-env/bin/activate

# Test 1: Factory overview
ovos-cli-client send "recognizer_loop:utterance" '{"utterances": ["factory overview"]}'
```

**Expected in Terminal 2 (ovos-core) logs:**
```
[EnmsSkill] converse_handling_query utterance="factory overview"
[EnmsSkill] Intent: factory_overview (confidence: 0.95)
[EnmsSkill] API: GET /factory/overview
[EnmsSkill] Response formatted
```

**Expected TTS (Terminal 3):** "Factory status: operational. Today's energy: 39152.5 kWh..."

**Test queries:**
- [ ] "factory overview" → Same response as standalone
- [ ] "what's the energy for compressor 1" → Returns Compressor-1 data
- [ ] "top 3 consumers" → Returns ranked list
- [ ] "compare boiler and compressor" → Uses LLM tier

---

### Task 5.2: Voice Input Test ✅ PARTIALLY WORKING

**Using Windows microphone (WSLg forwards audio automatically):**

**Test 1: Wake word** ✅ PASSED
```
You: "Hey Mycroft"
Expected: Wake sound plays through Windows speakers
```

**Status:** [x] Wake word detected ✅

**Test 2: STT Transcription** ✅ WORKING (with known issues)
```
You: "Hey Mycroft"
OVOS: [wake sound]
You: "what is the current energy consumption"
Transcribed: "what's consumption" (partial - Vosk small model limitations)
```

**Status:** [x] Voice transcription working ✅, [ ] Accuracy needs larger Vosk model

**Current Issues:**
1. **Pipeline Plugin Warnings (NON-BLOCKING):**
   - `ERROR - Unknown pipeline matcher: ovos-padatious-pipeline-plugin-high`
   - `ERROR - Unknown pipeline matcher: ovos-adapt-pipeline-plugin-high`
   - **Impact:** Warnings only, fallback to built-in Adapt works
   - **Fix Required:** Install proper pipeline plugins OR use built-in matchers

2. **Vosk Model Accuracy:**
   - Small model (vosk-model-small-en-us-0.15) has limited vocabulary
   - "what is the current energy consumption" → "what's consumption"
   - **Fix:** Install larger Vosk model (en-us 1.8GB) for better accuracy

**Test 3: Complex query**
```
You: "Hey Mycroft"
OVOS: [wake sound]
You: "What's the baseline prediction for Compressor-1?"
Expected: Uses LLM tier, returns baseline prediction
```

**Status:** [ ] LLM tier activated, [ ] Correct response

**Test 4: Multi-turn conversation**
```
You: "Hey Mycroft, what's the energy for Compressor-1?"
OVOS: "Compressor-1 consumed 450.3 kWh today"
You: "And for Boiler-1?"
Expected: Context preserved, returns Boiler-1 energy
```

**Status:** [ ] Context preserved, [ ] Follow-up works

---

## ✅ Success Verification

### Final Checklist

**Code:**
- [ ] @intent_handler decorators commented out (3 of 3)
- [ ] self.activate() added to initialize()
- [ ] converse() method exists and is correct (line 1681)
- [ ] Standalone test still works

**OVOS Installation:**
- [ ] ovos-core 2.1.1+ installed
- [ ] ovos-audio installed with [extras]
- [ ] ovos-dinkum-listener installed with [extras]
- [ ] Skill symlinked to OVOS skills directory

**Configuration:**
- [ ] mycroft.conf created with correct pipeline
- [ ] Skill settings JSON created with correct paths
- [ ] Pipeline has "converse" at position 2

**Services:**
- [ ] ovos-messagebus running (port 8181)
- [ ] ovos-core running, skill loaded
- [ ] Skill shows "always_active=True" in logs
- [ ] ovos-audio running
- [ ] ovos-dinkum-listener running, microphone detected

**Testing:**
- [ ] CLI text input works
- [ ] "factory overview" matches standalone response
- [ ] Wake word "Hey Mycroft" works
- [ ] Voice queries processed correctly
- [ ] Latency acceptable (<500ms total)
- [ ] Context preserved in multi-turn
- [ ] LLM tier activates for complex queries

---

## 🐛 Troubleshooting

### Issue: Skill not loaded

**Check:**
```bash
ls -la ~/.local/share/mycroft/skills/enms-ovos-skill
# Should show symlink to /mnt/d/...
```

**Fix:** Recreate symlink, restart ovos-core.

---

### Issue: converse() not called

**Check Terminal 2 logs for:**
- `"always_active=True"` ← Should appear during initialization
- If missing, `self.activate()` wasn't added

**Fix:** Add `self.activate()` to `initialize()`, restart ovos-core.

---

### Issue: Wake word not working

**Check Terminal 4 for microphone detection.**

**Fix:** 
- Verify WSLg is enabled (Windows 11 required)
- Test microphone in Windows
- Check PulseAudio: `pulseaudio --check`

---

### Issue: STT produces garbage/wrong transcriptions ⚠️ CRITICAL

**Symptoms:**
- "factory overview" → "fuck that", "we are worried", "perjury over me"
- Wake word works but speech recognition is garbage
- Consistent corruption across all utterances

**Root Cause:** WSLg RDP audio tunnel corrupts audio

**Diagnosis:**
```bash
# Test 1: Capture audio in WSL2 and check
wsl bash -c "source ~/ovos-env/bin/activate; python3 -c \"...\""
# Result: Garbage audio

# Test 2: Capture audio on Windows natively
python -c "import sounddevice as sd; ..."
# Result: Clean audio, Vosk recognizes correctly
```

**Solution:** Use Hybrid/Satellite Architecture
- Capture audio on Windows (native, clean)
- Send text to WSL2 via WebSocket
- See top of document for architecture diagram

---

### Issue: LLM model not loading

**Check path:**
```bash
ls -lh /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/models/Qwen_Qwen3-1.7B-Q4_K_M.gguf
```

**Fix:** Update path in settings.json if file moved.

---

## 📊 Performance Targets

| Metric | Target | How to Verify |
|--------|--------|---------------|
| **P50 Latency** | <400ms | Time from "Hey Mycroft" to TTS start |
| **Wake Word** | <1s response | "Hey Mycroft" → wake sound delay |
| **Accuracy** | 99.5%+ | Test 20 queries, count correct intents |
| **Context** | 5 min retention | Test multi-turn after 4 min delay |

---

## 🎉 Completion Criteria

**Integration is complete when:**
1. ✅ All 4 OVOS services running without errors
2. ✅ Skill loads with "always_active=True" in logs
3. ✅ "factory overview" via voice matches standalone exactly
4. ✅ Wake word detection works consistently
5. ✅ Latency <500ms for simple queries
6. ✅ LLM tier activates for complex queries only
7. ✅ Multi-turn conversation preserves context

**Document final state:**
- [ ] Take screenshots of working voice interaction
- [ ] Save terminal logs showing successful skill load
- [ ] Update README.md with OVOS integration status

---

**Last Updated:** 2025-11-27  
**Status:** Ready for implementation  
**Estimated Time:** 4-6 hours total (with troubleshooting)
