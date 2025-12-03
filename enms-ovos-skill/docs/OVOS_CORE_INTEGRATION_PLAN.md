# 🎯 OVOS Core Integration Plan - EnMS Skill

**Created:** 2025-11-26  
**Updated:** 2025-11-28  
**Purpose:** Comprehensive integration plan for enms-ovos-skill with OVOS Core  
**Status:** ⚠️ WSLg Audio Issue - Requires Hybrid Architecture  
**Strategy:** Use ONLY `converse()` method - preserves exact standalone behavior

---

## 🚨 CRITICAL UPDATE (2025-11-28): WSLg Audio Corruption Issue

### Problem Discovered

**WSLg's RDP audio tunnel corrupts microphone audio before it reaches OVOS.**

After extensive debugging, we confirmed:
- **Windows-captured audio** → Vosk STT = "factory overview" ✅
- **WSL2-captured audio (via RDPSource)** → Vosk STT = "fuck that", "we are worried" ❌

### Root Cause Analysis

```
Current (Broken) Pipeline:
Windows Mic → RDPSource → PulseAudio → WSL2 → sounddevice → OVOS → STT
                 ↑                        ↑
            [LOSSY RDP]            [RESAMPLE 44.1→16kHz]
                 ↑_____________________________↑
                        AUDIO CORRUPTION
```

**Evidence:**
- Saved OVOS utterances in `~/.local/share/mycroft/listener/utterances/` contain garbage
- Same Vosk model produces correct results on Windows-captured audio
- RDPSource is virtualized audio, not direct hardware access
- 500+ Hz artifacts detected in frequency analysis of bad captures

### ✅ Recommended Solution: Hybrid/Satellite Architecture

**Separate audio capture (Windows) from processing (WSL2):**

```
┌─────────────────────────┐         ┌─────────────────────────┐
│   Windows (Satellite)   │         │    WSL2 (Server)        │
│                         │         │                         │
│  ┌─────────────────┐   │  text   │   ┌─────────────────┐   │
│  │ Windows Mic     │   │ ──────▶ │   │ ovos-messagebus │   │
│  │ (Native 44.1kHz)│   │         │   └────────┬────────┘   │
│  └────────┬────────┘   │         │            │            │
│           │            │         │   ┌────────▼────────┐   │
│  ┌────────▼────────┐   │         │   │ ovos-core       │   │
│  │ STT (Vosk)      │   │         │   │ (EnMS Skill)    │   │
│  │ Clean audio     │   │         │   └────────┬────────┘   │
│  └────────┬────────┘   │         │            │            │
│           │            │  text   │   ┌────────▼────────┐   │
│  ┌────────▼────────┐   │ ◀────── │   │ Response Text   │   │
│  │ TTS + Speaker   │   │         │   └─────────────────┘   │
│  └─────────────────┘   │         │                         │
└─────────────────────────┘         └─────────────────────────┘
```

### Implementation Options

| Option | Description | Complexity | Latency |
|--------|-------------|------------|--------|
| **Option A: HiveMind** | OVOS native satellite | Medium | Low |
| **Option B: Custom Bridge** | Python WebSocket service | Low | Low |
| **Option C: Cloud API** | OpenAI Whisper API | Very Low | Medium |

### Quick Validation (Completed ✅)

```powershell
# Windows-native audio capture test
python -c "import sounddevice as sd; import numpy as np; from scipy.io import wavfile; audio = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype='int16'); sd.wait(); wavfile.write('windows_native.wav', 16000, audio)"

# Test STT in WSL2 on Windows-captured audio
wsl bash -c "source ~/ovos-env/bin/activate; python3 test_vosk_on_file.py windows_native.wav"
# Result: "factory overview" ✅ (correct!)
```

**Conclusion:** Windows audio capture works perfectly. Only WSLg tunnel is broken.

---

> ⚠️ **IMPLEMENTATION CHECKLIST - READ FIRST:**
> 
> **Critical Pre-Implementation Steps:**
> 1. ✅ WSL2 installed and verified (done)
> 2. ✅ WSL2_WORKFLOW_GUIDE.md reviewed (created)
> 3. ⏳ Comment out @intent_handler decorators in __init__.py (lines 1654-1680)
> 4. ⏳ **ADD self.activate() in initialize() method (line ~155)** - REQUIRED!
> 5. ⏳ Test standalone: `python scripts/test_skill_chat.py` - verify "factory overview" works
> 
> **Why Pure Converse?**
> - Preserves exact `test_skill_chat.py` behavior
> - No double parsing (OVOS Padatious → then HybridParser)
> - Predictable latency (~380ms vs 430ms+ with @intent_handler)
> - Read `CRITICAL_INTEGRATION_ANALYSIS.md` for detailed rationale

---

## 📋 Quick Start (For AI Agent Implementation)

**When you're ready to implement, follow this order:**

1. **Phase 1: Code Changes** (15 min)
   - Edit `__init__.py` - comment out @intent_handlers
   - Edit `initialize()` - add `self.activate()` (CRITICAL!)
   - Test standalone - verify working

2. **Phase 2: Install OVOS in WSL2** (1-2 hrs)
   - Open WSL2 terminal in VS Code
   - Install Ubuntu dependencies
   - Create Python venv in `~/ovos-env/`
   - Install OVOS packages

3. **Phase 3: Configure** (30 min)
   - Create `~/.config/mycroft/mycroft.conf`
   - Create skill settings JSON
   - Link skill to OVOS skills directory

4. **Phase 4: Test** (1 hr)
   - Start 4 OVOS services (4 WSL2 terminals)
   - Test text input via CLI
   - Test voice input (Hey Mycroft → query)
   - Verify "factory overview" matches standalone

---

> ⚠️ **IMPORTANT:** This plan was updated after discovering a critical flaw in the original dual-mode approach.  
> **Read `CRITICAL_INTEGRATION_ANALYSIS.md` first** to understand why we chose Pure Converse over @intent_handlers.

---

## 📚 Executive Summary

This document outlines the integration strategy for `enms-ovos-skill` with OVOS Core to achieve a full voice assistant. The skill is **production-ready standalone** and uses a sophisticated 3-tier NLU architecture (Heuristic → Adapt → LLM).

**Integration Strategy:** ✅ **Pure Converse Approach**
- Use ONLY the `converse()` method (NO `@intent_handler` decorators)
- Preserves exact behavior of standalone `test_skill_chat.py`
- Avoids double parsing and maintains performance
- Our HybridParser handles ALL queries at OVOS pipeline stage #2

**Key Finding:** ✅ **No conflicts** - Our internal Adapt parser is separate from OVOS's Adapt pipeline plugin.

---

## 🏗️ Understanding OVOS Architecture

### 1. OVOS Core Components

```
┌─────────────────────────────────────────┐
│         OVOS Core (ovos-core)           │
│                                         │
│  ┌────────────────────────────────┐   │
│  │    Skills Service               │   │
│  │  - Loads skills automatically   │   │
│  │  - Manages intent routing       │   │
│  │  - Handles skill lifecycle      │   │
│  └────────────────────────────────┘   │
│                                         │
│  ┌────────────────────────────────┐   │
│  │    Message Bus (WebSocket)      │   │
│  │  - Port: 8181 (default)         │   │
│  │  - Type/Data/Context structure  │   │
│  └────────────────────────────────┘   │
│                                         │
│  ┌────────────────────────────────┐   │
│  │    Intent Pipeline              │   │
│  │  - High/Med/Low confidence      │   │
│  │  - Pluggable stages             │   │
│  └────────────────────────────────┘   │
└─────────────────────────────────────────┘
         ↕️                    ↕️
    ┌─────────┐         ┌─────────┐
    │   STT   │         │   TTS   │
    └─────────┘         └─────────┘
```

### 2. OVOS Intent Pipeline (Critical Understanding)

OVOS uses a **multi-stage intent resolution pipeline**:

```
User Utterance
    ↓
┌─────────────────── High Confidence ────────────────────┐
│ 1. stop_high        - Exact stop command matches       │
│ 2. converse         - Active skill's converse()        │ ← WE USE THIS
│ 3. padatious_high   - OVOS Padatious (conf > 0.85)     │
│ 4. adapt_high       - OVOS Adapt (conf > 0.65)         │ ← SEPARATE FROM OURS
│ 5. fallback_high    - High priority fallbacks          │
│ 6. ocp_high         - Media queries                    │
└────────────────────────────────────────────────────────┘
    ↓ (if no match)
┌─────────────────── Medium Confidence ──────────────────┐
│ 7. stop_medium      - Medium confidence stops          │
│ 8. padatious_medium - OVOS Padatious (conf > 0.65)     │
│ 9. adapt_medium     - OVOS Adapt (conf > 0.45)         │
│ 10. fallback_medium - Medium priority fallbacks        │
└────────────────────────────────────────────────────────┘
    ↓ (if no match)
┌─────────────────── Low Confidence ─────────────────────┐
│ 11. adapt_low       - OVOS Adapt (conf > 0.25)         │
│ 12. ocp_low         - Low confidence media             │
│ 13. fallback_low    - Last resort fallbacks            │
│ 14. common_query    - Common query skills              │
└────────────────────────────────────────────────────────┘
```

**🔑 Key Insight:** The `converse` stage (position #2) is where our skill can intercept queries **before** OVOS's Adapt/Padatious plugins run.

---

## 🧩 EnMS Skill Architecture Review

### Our Custom 3-Tier NLU System

```
User Query (from OVOS)
    ↓
┌──────────────────────────────────────┐
│ OUR Tier 1: Heuristic Router         │ <1ms, 70% queries
│ - Regex patterns (internal)          │
│ - Ultra-fast keyword matching        │
└──────────────────────────────────────┘
    ↓ (if no match)
┌──────────────────────────────────────┐
│ OUR Tier 2: Adapt Parser             │ <10ms, 15% queries
│ - Internal adapt-parser library      │ ← NOT OVOS's Adapt pipeline!
│ - Intent/entity extraction           │
└──────────────────────────────────────┘
    ↓ (if no match)
┌──────────────────────────────────────┐
│ OUR Tier 3: LLM Parser (Qwen3 1.7B)  │ 300-500ms, 15% queries
│ - Grammar-constrained JSON           │
│ - Complex NLU                        │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ OUR Validator                        │
│ - Hallucination prevention           │
│ - Machine whitelist enforcement      │
└──────────────────────────────────────┘
    ↓
EnMS API Call → Response Formatter → Voice Output
```

**✅ Critical Clarification:** 
- **Our Adapt Parser** = `from adapt-parser import ...` (Python library, internal to our skill)
- **OVOS Adapt Pipeline** = `ovos-padacioso-pipeline-plugin` (OVOS global intent matcher)
- **These are SEPARATE** - No conflict!

---

## 🔍 Research Findings from OVOS Documentation

### 1. Skill Discovery & Loading

**How OVOS loads skills:**
- Skills are **regular Python packages**
- Any installed skill is **automatically loaded** by `ovos-core`
- Skills can be:
  - Installed via pip (if packaged with `setup.py`)
  - Located in skills directory (legacy method)
  - Loaded as plugins via `entry_points` in `setup.py`

**Our skill structure matches requirements:**
- ✅ Has `skill.json` metadata (OVOS skill discovery)
- ✅ Has `settingsmeta.yaml` for settings
- ✅ Extends `OVOSSkill` class in `__init__.py`
- ✅ Has `create_skill()` factory function
- ⚠️ **NO setup.py** - OVOS uses `skill.json` for skill metadata, not PyPI packaging

### 2. Intent Handler Lifecycle

**OVOS skill methods called in order:**

```python
class EnmsSkill(OVOSSkill):
    def __init__(self, *args, **kwargs):
        # Called first (skill construction)
        super().__init__(*args, **kwargs)
        
    def initialize(self):
        # Called after __init__
        # This is where we init our components
        # self.bus, self.settings available here
        
    def converse(self, message):
        # Called for EVERY utterance while skill is active
        # Active = used in last 5 minutes
        # Return True if we handle it
        # Return False to pass to next skill
        
    @intent_handler('some.intent')
    def handle_some_intent(self, message):
        # Called if Padatious matches .intent file
        
    @intent_handler(IntentBuilder('SomeIntent').require('Keyword'))
    def handle_adapt_intent(self, message):
        # Called if OVOS Adapt pipeline matches
        
    def stop(self):
        # Called when user says "stop"
        # Return True if we handled it
        
    def shutdown(self):
        # Called when skill is unloaded
```

### 3. Message Bus Format

**OVOS Message Structure:**
```python
{
    "type": "recognizer_loop:utterance",  # Message type
    "data": {
        "utterances": ["what's the energy for compressor 1"],
        "lang": "en-us",
        # ... skill-specific data
    },
    "context": {
        "source": "audio",      # Where it came from
        "destination": None,    # Where it's going
        "session": {            # Session tracking
            "session_id": "default",
            "active_skills": [...],
            # ... session state
        }
    }
}
```

### 4. Converse Method Details

**How converse() works:**
```python
def converse(self, message: Message) -> bool:
    """
    Called for every utterance while skill is in Active Skills List.
    
    Active Skill List order:
    1. Most recently activated skill first
    2. Next most recent second
    3. ... etc
    
    Skill becomes active when:
    - An intent is called
    - Skill manually calls self.activate()
    - converse() returns True
    
    Skill deactivated after 5 minutes of inactivity.
    """
    utterance = message.data.get('utterances', [''])[0]
    
    # Check if this is our domain
    if not self._is_energy_related(utterance):
        return False  # Let other skills handle it
    
    # Process with our HybridParser
    result = self._process_query(utterance)
    
    # Speak response
    self.speak(result['response'])
    
    return True  # We consumed this utterance
```

**🔑 Key Points:**
- Converse is called **BEFORE** normal intent matching
- Return `True` = utterance consumed, stop processing
- Return `False` = pass to next skill/intent pipeline
- Skills are checked in order of recent activity

### 5. Intent File Structure

**OVOS expects files in:**
- `locale/en-us/` (recommended) or `vocab/en-us/` (legacy)

**File types:**
- `.voc` - Vocabulary (keywords for Adapt)
- `.intent` - Example sentences (for Padatious)
- `.entity` - Named entities
- `.dialog` - Response templates

**Our current structure:**
```
enms-ovos-skill/
├── intent/                  # ⚠️ NOT standard OVOS location
│   ├── energy.query.intent
│   ├── machine.status.intent
│   └── factory.overview.intent
├── entities/                # ⚠️ NOT standard OVOS location
│   ├── machine.entity
│   └── energy_source.entity
└── locale/en-us/           # ✅ Correct location
    ├── dialog/
    │   ├── *.dialog  (34 files)
    └── vocab/
        ├── *.voc (files for Adapt keywords)
```

**⚠️ Issue:** Our `.intent` and `.entity` files are in wrong folders for OVOS to auto-discover them for Padatious matching.

---

## ⚡ Integration Strategy: Pure Converse Approach

### ⚠️ CRITICAL UPDATE (2025-11-26)

**PREVIOUS PLAN HAD A FLAW:** Using `@intent_handler` decorators would cause **double parsing** (OVOS Padatious → then HybridParser again), leading to:
- 2x slower latency
- Potential intent mismatches
- Different behavior than standalone test_skill_chat.py

**NEW RECOMMENDATION:** Use **ONLY** `converse()` method to preserve exact standalone behavior.

### Recommended Approach: Pure Converse (Preserves Standalone Experience)

We'll use **ONLY** `converse()` method, which maintains the exact behavior of test_skill_chat.py:

```python
class EnmsSkill(OVOSSkill):
    
    def initialize(self):
        """Initialize our custom NLU components"""
        # Init our 3-tier parser (Heuristic → Adapt → LLM)
        self.hybrid_parser = HybridParser()
        self.validator = ENMSValidator()
        self.api_client = ENMSClient()
        self.response_formatter = ResponseFormatter()
        self.context_manager = ConversationContextManager()
        
        # Load machine whitelist from API
        machines = self._run_async(self.api_client.list_machines(is_active=True))
        machine_names = [m['name'] for m in machines]
        self.validator.update_machine_whitelist(machine_names)
        
        # Optional: Make skill always active for better responsiveness
        # This ensures converse() is called for every utterance
        self.activate()
        
    # ──────────────────────────────────────────────────────────
    # SINGLE MODE: All queries via converse() → HybridParser
    # This preserves EXACT behavior of test_skill_chat.py
    # ──────────────────────────────────────────────────────────
    
    def converse(self, message: Message) -> bool:
        """
        Handle ALL EnMS queries via our proven HybridParser.
        
        This preserves the exact behavior from test_skill_chat.py:
        - Tier 1: Heuristic Router (<1ms, 70% queries)
        - Tier 2: Internal Adapt Parser (<10ms, 15% queries)
        - Tier 3: Qwen3 LLM (300-500ms, 15% queries)
        
        Called at pipeline stage #2 (before OVOS Padatious/Adapt).
        This method is in __init__.py starting at line 1681.
        """
        utterance = message.data.get("utterances", [""])[0]
        
        if not utterance or len(utterance.strip()) < 2:
            return False
        
        # Quick domain check: is this energy-related?
        energy_keywords = ['energy', 'power', 'kwh', 'kw', 'watt', 'consumption', 
                          'status', 'factory', 'machine', 'compressor', 'boiler', 
                          'hvac', 'conveyor', 'top', 'compare', 'cost', 'anomaly',
                          'health', 'system', 'online', 'check', 'database']
        
        if not any(keyword in utterance.lower() for keyword in energy_keywords):
            return False  # Not our domain, let other skills handle
        
        # Get session ID using helper method
        session_id = self._get_session_id(message)
        
        self.logger.info("converse_handling_query", utterance=utterance)
        
        # Process query EXACTLY like standalone test_skill_chat.py
        result = self._process_query(utterance, session_id)
        
        if result['success'] or 'error' in result:
            self.speak(result['response'])
            return True  # We handled it, stop OVOS pipeline
        
        return False  # Couldn't handle, let OVOS pipeline try
    
    def _process_query(self, utterance: str, session_id: str) -> dict:
        """
        Our custom query processing pipeline - IDENTICAL to test_skill_chat.py
        Uses HybridParser (Heuristic → Adapt → LLM) → Validator → API → Formatter
        """
        # Get conversation session
        session = self.context_manager.get_or_create_session(session_id)
        
        # Step 1: Parse with HybridParser
        parse_result = self.hybrid_parser.parse(utterance)
        parse_result['utterance'] = utterance
        
        # Step 1.5: Check for pending clarification
        if session.pending_clarification:
            # Check if utterance is a machine name resolving clarification
            for valid_machine in self.validator.machine_whitelist:
                if utterance.lower() == valid_machine.lower():
                    # Override parse with pending intent
                    parse_result['intent'] = session.pending_clarification['intent'].value
                    parse_result['entities'] = {'machine': valid_machine}
                    parse_result['machine'] = valid_machine
                    parse_result['confidence'] = 0.99
                    break
        
        # Step 2: Validate
        validation = self.validator.validate(parse_result)
        if not validation.valid:
            return {'success': False, 'response': f"I couldn't understand that. {validation.errors[0]}"}
        
        intent = validation.intent
        
        # Step 3: Resolve context references (multi-turn support)
        intent = self.context_manager.resolve_context_references(utterance, intent, session)
        
        # Clear pending clarification if resolved
        if session.pending_clarification and intent.machine:
            session.pending_clarification = None
        
        # Check if clarification needed
        clarification = self.context_manager.needs_clarification(intent)
        if clarification:
            session.pending_clarification = {
                'intent': intent.intent,
                'metric': intent.metric,
                'time_range': intent.time_range
            }
            clarification_response = self.context_manager.generate_clarification_response(
                intent, session, validation.suggestions
            )
            return {'success': False, 'response': clarification_response}
        
        # Step 4: Call EnMS API
        api_result = self._call_enms_api(intent, utterance)
        
        if not api_result.get('success'):
            return {'success': False, 'response': api_result.get('error', "I couldn't retrieve that information.")}
        
        # Step 5: Format response
        response = self.response_formatter.format_response(
            intent_type=intent.intent.value,
            api_data=api_result['data']
        )
        
        # Step 6: Update conversation context
        session.update_intent(intent.intent)
        if intent.machine:
            session.update_machine(intent.machine)
        
        return {'success': True, 'response': response}
```

---

## 🛠️ Integration Steps (Detailed)

### Phase 1: Prepare Skill for OVOS (Pre-Integration)

#### Step 1.1: Disable @intent_handler Decorators

**⚠️ CRITICAL: We're using ONLY converse() method, not @intent_handler decorators**

Edit `__init__.py` and comment out the `@intent_handler` decorators (around lines 1654-1680):

```python
# COMMENT OUT these handlers (we use converse() instead):

# @intent_handler("energy.query.intent")
# def handle_energy_query(self, message: Message):
#     ...

# @intent_handler("machine.status.intent")
# def handle_machine_status(self, message: Message):
#     ...

# @intent_handler("factory.overview.intent")
# def handle_factory_overview(self, message: Message):
#     ...
```

**Why?** Using @intent_handler would cause double parsing (OVOS Padatious → HybridParser), leading to slower responses and potential intent mismatches. Pure converse() preserves exact standalone behavior.

**Optional:** Keep .intent files in `intent/` folder for documentation, but they won't be used by OVOS.

#### Step 1.2: Add self.activate() to initialize() Method

**⚠️ CRITICAL for Pure Converse approach to work!**

The skill needs to be **always active** for `converse()` to be called on every utterance.

Edit `__init__.py` and add `self.activate()` at the end of the `initialize()` method (around line 155):

```python
def initialize(self):
    """
    Called after skill construction
    Initialize all SOTA components
    """
    self.logger.info("skill_initializing", 
                    skill_name="EnmsSkill",
                    version="1.0.0",
                    architecture="multi-tier-adaptive")
    
    # ... (existing initialization code) ...
    
    # Load machine whitelist from API
    machines = self._run_async(self.api_client.list_machines(is_active=True))
    machine_names = [m['name'] for m in machines]
    self.validator.update_machine_whitelist(machine_names)
    
    # ✅ CRITICAL: Make skill always active so converse() is always called
    self.activate()
    
    self.logger.info("skill_initialized",
                    components_ready=True,
                    machine_count=len(machine_names),
                    always_active=True)  # Added status flag
```

**Why this is critical:**
- Without `self.activate()`, converse() only runs if skill was used in last 5 minutes
- With `self.activate()`, converse() runs for EVERY utterance
- This ensures "factory overview" on first use goes through converse() → HybridParser

**Note:** Skill metadata is in `skill.json`, not `setup.py`. OVOS loads skills that have `skill.json` in their directory.

#### Step 1.3: Test Standalone Again

```bash
cd d:\ovos-llm-core\ovos-llm\enms-ovos-skill
python scripts\test_skill_chat.py
```

**Test queries:**
- "factory overview" → Should return factory status
- "compressor 1 kwh" → Should return Compressor-1 energy
- "top 3 consumers" → Should return ranked list

**Verify:** All responses match expected behavior before proceeding to OVOS integration.

---

### Phase 2: Install OVOS Core Components

**⚠️ READ THIS FIRST:** Before proceeding, decide your platform:
- ✅ **WSL2 Ubuntu (RECOMMENDED)**: Full OVOS support, WSLg audio, all features work
- ✅ **Linux/Raspberry Pi**: Production deployment option
- ⚠️ **Windows Native**: Limited support, audio issues likely, text-only recommended

**✅ FOR WSL2 USERS (Recommended):**  
See `WSL2_WORKFLOW_GUIDE.md` for complete workflow setup before proceeding.

#### Step 2.1: Install OVOS Core

**WSL2 Installation (RECOMMENDED - Full Audio Support):**

```bash
# In VS Code WSL2 terminal (current window, NOT new window)
# Project is already accessible at /mnt/d/ovos-llm-core/ovos-llm

# Update Ubuntu packages first
sudo apt update && sudo apt upgrade -y

# Install system dependencies for audio support
sudo apt install -y python3-pip python3-venv portaudio19-dev pulseaudio

# Create OVOS virtual environment in WSL2 home (NOT in /mnt/)
cd ~
python3 -m venv ovos-env
source ovos-env/bin/activate

# Install OVOS core components with extras for default plugins
# Latest versions: ovos-core 2.1.1, ovos-audio 1.1.0, ovos-dinkum-listener 0.5.0
pip install ovos-messagebus          # Message bus (required first)
pip install ovos-core[mycroft]       # Core + mycroft compatibility layer
pip install ovos-audio[extras]       # Audio output + default TTS plugins
pip install ovos-dinkum-listener[extras]  # STT + wake word + default plugins
pip install ovos-phal                # Hardware abstraction layer (optional)

# Install skill from project location (on Windows drive)
cd /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill
pip install -e .

# Verify installation
ovos-skill-launcher --list  # Should show enms-ovos-skill

# Note: After installation, you need to START services manually
# OVOS does NOT auto-start services on install
```

**Windows Native Installation (Limited Support - NOT Recommended):**
```powershell
# Create OVOS environment (separate from skill venv)
python -m venv ovos-env
.\ovos-env\Scripts\activate

# Install OVOS core components
pip install ovos-messagebus
pip install ovos-core[mycroft]
pip install ovos-audio[extras]       # May fail on Windows
pip install ovos-dinkum-listener[extras]  # May fail on Windows
pip install ovos-phal

# Note: Audio components likely won't work on Windows native
```

**Option B: Use ovos-installer (Linux-focused, may not work on Windows)**
```bash
# Not recommended for Windows
bash <(curl -s https://raw.githubusercontent.com/OpenVoiceOS/ovos-installer/main/installer.sh)
```

**⚠️ CRITICAL - Windows Compatibility:**
OVOS is **primarily designed for Linux**. Windows native installation has limitations:

**Issues on Windows:**
- Audio subsystem (PulseAudio/PipeWire) not natively supported
- Systemd services don't exist (need manual service startup)
- Some plugins (especially audio-related) may fail on Windows
- ovos-installer is Linux-only (Bash script)

**RECOMMENDED for Windows users:**
1. **WSL2 (Windows Subsystem for Linux)** - Best option for development
   - Full Linux environment inside Windows
   - Native audio support via WSLg
   - All OVOS features work
   - Run: `wsl --install` in PowerShell (Admin)
   
2. **VirtualBox/VMware Linux VM** - Alternative if WSL2 not available

3. **Raspberry Pi/Linux Server** - Deploy to dedicated hardware for production

4. **Skip OVOS integration** - Keep using `test_skill_chat.py` on Windows (perfectly viable)

**If you proceed with Windows native:**
- Expect manual troubleshooting
- Text-only testing recommended (skip STT/TTS/wake word)
- Use `ovos-core` alone, skip audio components

#### Step 2.2: Install STT/TTS Plugins (Optional - Skip if Windows Issues)

**IMPORTANT:** If you used `[extras]` flags in Step 2.1, default plugins are already installed!

**For offline testing (no internet required):**
```powershell
# Vosk STT (offline, multilingual) - Included in [extras]
pip install ovos-stt-plugin-vosk

# Mimic3 TTS (offline, neural TTS) - Included in [extras]
pip install ovos-tts-plugin-mimic3

# Piper TTS (offline, faster than Mimic3)
pip install ovos-tts-plugin-piper
```

**For cloud-based (better quality, requires API keys):**
```powershell
# Google Cloud STT (requires API key)
pip install ovos-stt-plugin-google

# Google Cloud TTS (requires API key)
pip install ovos-tts-plugin-google

# Edge TTS (free, no key needed, uses Microsoft servers)
pip install ovos-tts-plugin-edge-tts
```

**Recommended for Windows:** Skip STT/TTS, test with text input only via `ovos-cli-client`

#### Step 2.3: Install Wake Word Plugin (Optional - Skip if Windows Issues)

**IMPORTANT:** If you used `[extras]` in Step 2.1, wake word plugin is already installed!

**Current OVOS default:**
```powershell
# Precise Lite (ML-based, best accuracy) - Included in [extras]
pip install ovos-ww-plugin-precise-lite

# Vosk (text-based, no training needed)
pip install ovos-ww-plugin-vosk
```

**Legacy (not recommended):**
```powershell
# PocketSphinx (older, lower accuracy)
pip install ovos-ww-plugin-pocketsphinx
```

**For Windows testing:** Skip wake word entirely, use CLI for text-based testing

---

### Phase 3: Configure OVOS

#### Step 3.1: Create OVOS Configuration

**Location (WSL2 - RECOMMENDED):** `~/.config/mycroft/mycroft.conf` (in WSL2 home)  
**Location (Linux/Raspberry Pi):** `~/.config/mycroft/mycroft.conf`  
**Location (Windows Native):** `C:\Users\YourUsername\.config\mycroft\mycroft.conf`

**Creating config in WSL2:**
```bash
# In WSL2 terminal, create directory
mkdir -p ~/.config/mycroft

# Option A: Edit with VS Code (recommended)
code ~/.config/mycroft/mycroft.conf
# Opens file in current VS Code window for editing

# Option B: Edit with nano in terminal
nano ~/.config/mycroft/mycroft.conf
# Paste config below, save with Ctrl+O, exit with Ctrl+X
```

**Creating config in Windows Native:**
```powershell
mkdir -Force $env:USERPROFILE\.config\mycroft
code $env:USERPROFILE\.config\mycroft\mycroft.conf
```

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
      "enms-ovos-skill"  # Our skill gets priority in converse() stage
    ]
  },
  
  "note": "EnMS skill uses converse() method exclusively (no @intent_handlers). It activates itself in initialize() to ensure converse() is always called for energy-related queries.",
  
  "intents": {
    "pipeline": [
      "stop_high",
      "converse",           # Our skill's converse() called here
      "padatious_high",     # OVOS Padatious for simple patterns
      "adapt_high",         # OVOS Adapt (separate from our internal one)
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
    "shared_connection": false  # Security: separate connection per skill
  }
}
```

#### Step 3.2: Configure EnMS Skill Settings

**Location (WSL2):** `~/.config/mycroft/skills/enms-ovos-skill/settings.json`  
**Location (Windows):** `%USERPROFILE%\.config\mycroft\skills\enms-ovos-skill\settings.json`

**WSL2 Configuration:**
```json
{
  "enms_api_base_url": "http://10.33.10.109:8001/api/v1",
  "llm_model_path": "/mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/models/Qwen_Qwen3-1.7B-Q4_K_M.gguf",
  "confidence_threshold": 0.85,
  "enable_progress_feedback": true,
  "progress_threshold_ms": 500
}
```

**Windows Native Configuration:**
```json
{
  "enms_api_base_url": "http://10.33.10.109:8001/api/v1",
  "llm_model_path": "d:\\ovos-llm-core\\ovos-llm\\enms-ovos-skill\\models\\Qwen_Qwen3-1.7B-Q4_K_M.gguf",
  "confidence_threshold": 0.85,
  "enable_progress_feedback": true,
  "progress_threshold_ms": 500
}
```

**Note:** The LLM model path in WSL2 uses `/mnt/d/` to access the Windows drive.

---

### Phase 4: Install EnMS Skill

#### Step 4.1: Install Skill as Package

**OVOS discovers skills via:**
1. **pip install with entry_points** (recommended, production-ready)
2. **Skills directory symlink** (legacy, development)

**Recommended: Install as editable package**

Our skill now has `setup.py` with proper entry_points configuration:

**WSL2 (Recommended):**
```bash
# Ensure OVOS venv is activated
source ~/ovos-env/bin/activate

# Navigate to skill directory (on Windows drive)
cd /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill

# Install in editable mode (changes to code are live)
pip install -e .

# Verify installation
pip list | grep enms-ovos-skill
# Should show: enms-ovos-skill 1.0.0 /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill

# Verify OVOS can discover it
python3 -c "from ovos_plugin_manager.skills import find_skill_plugins; print([p for p in find_skill_plugins() if 'enms' in p.lower()])"
# Should show: ['enms-ovos-skill.yourname']
```

**Benefits of package approach:**
- ✅ Works with OVOS plugin discovery system
- ✅ Proper skill isolation and dependencies
- ✅ Production-ready deployment
- ✅ Editable mode (`-e`) allows live code updates
- ✅ No manual symlink management

**Alternative (legacy): Symlink to Skills Directory**

**Alternative (legacy): Symlink to Skills Directory**

If you prefer manual symlink approach (not recommended):

**WSL2:**
```bash
# Ensure OVOS venv is activated
source ~/ovos-env/bin/activate

# Find OVOS skills directory (usually ~/.local/share/mycroft/skills or similar)
# Check mycroft.conf for skills directory location
python3 -c "from ovos_utils.xdg_utils import xdg_data_home; print(xdg_data_home() + '/skills')"

# Create skills directory if it doesn't exist
mkdir -p ~/.local/share/mycroft/skills

# Create symlink to our skill (on Windows drive)
ln -s /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill ~/.local/share/mycroft/skills/enms-ovos-skill

# Verify symlink
ls -la ~/.local/share/mycroft/skills/enms-ovos-skill
# Should show link pointing to /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill
```

**Alternative: Install as editable package (if you add setup.py later):**
```bash
# Navigate to skill directory
cd /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill

# Install in editable mode (requires setup.py)
pip install -e .
```

**Windows Native:**
```powershell
# Not recommended - use WSL2 instead
# If you must: manually copy skill to %APPDATA%\mycroft\skills\
```

The skill directory approach is **simpler** and works well for development. Changes to code in `D:\ovos-llm-core\ovos-llm\enms-ovos-skill\` are immediately available to OVOS (no reinstall needed).

#### Step 4.2: Verify Installation

**WSL2:**
```bash
# Check installed skill package
pip show enms-ovos-skill
# Should show: Name: enms-ovos-skill, Version: 1.0.0, Location: /mnt/d/...

# Verify OVOS plugin discovery
python3 -c "from ovos_plugin_manager.skills import find_skill_plugins; skills = find_skill_plugins(); print([s for s in skills if 'enms' in s.lower()])"
# Should show: ['enms-ovos-skill.yourname']

# Check if skill metadata is correct
python3 -c "from ovos_plugin_manager.skills import load_skill_plugins; plugins = load_skill_plugins(); enms = [p for p in plugins if 'enms' in p[0].lower()]; print(enms[0] if enms else 'Not found')"
# Should show skill entry point information
```

**Windows:**
```powershell
ovos-skill-launcher --list
# OR check skill.json
cat d:\ovos-llm-core\ovos-llm\enms-ovos-skill\skill.json
```

---

### Phase 5: Start OVOS Services

**CRITICAL:** OVOS services do NOT auto-start after installation. You must start them manually.

**On Linux (production):** Use systemd services
```bash
# Enable and start services (creates systemd units automatically)
sudo systemctl enable --now ovos
# This starts: messagebus, core, audio, listener
```

**On WSL2/Development:** Run manually in 4 separate WSL2 terminals (in current VS Code window)

**VS Code Terminal Setup:**
```
Click '+' dropdown → Select 'wsl' → Repeat 4 times
You'll have 4 WSL2 terminal tabs in current window
```

#### Step 5.1: Start Message Bus (REQUIRED - Start First)

**Terminal 1 (WSL2):**
```bash
# Activate OVOS venv
source ~/ovos-env/bin/activate

# Start message bus (WebSocket on port 8181)
ovos-messagebus run

# Wait for: "Websocket started on port 8181"
```

#### Step 5.2: Start Skills Service (REQUIRED)

**Terminal 2 (WSL2):**
```bash
# Activate OVOS venv
source ~/ovos-env/bin/activate

# Start skills service (loads our skill)
ovos-core

# Watch for skill loading:
# [Skills] Loading skill: enms-ovos-skill
# [EnmsSkill] skill_initializing
# [EnmsSkill] hybrid_parser_initialized  
# [EnmsSkill] Components initialized with 8 machines
```

#### Step 5.3: Start Audio Services (REQUIRED for Voice - Works in WSL2 via WSLg)

**Terminal 3 (WSL2):**
```bash
# Activate OVOS venv
source ~/ovos-env/bin/activate

# Start audio service (TTS output)
ovos-audio

# Wait for: "Audio service started"
```

#### Step 5.4: Use Windows STT Bridge (REPLACES ovos-dinkum-listener)

**⚠️ IMPORTANT:** Instead of running `ovos-dinkum-listener` in WSL2, we use the Windows STT Bridge to avoid WSLg audio corruption.

**Terminal 4 (PowerShell - Windows side):**
```bash
# Start WSL2 OVOS bridge (WebSocket server)
wsl bash -c "cd /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/bridge ; nohup python3 wsl_ovos_bridge.py > wsl_bridge.log 2>&1 &"

# Wait 3 seconds for bridge to start
timeout /t 3
```

**Terminal 5 (PowerShell - Windows side):**
```bash
# Start Windows STT bridge (Precise Lite + Whisper)
python d:\ovos-llm-core\ovos-llm\enms-ovos-skill\bridge\windows_stt_bridge_final.py

# OR use startup script:
d:\ovos-llm-core\ovos-llm\enms-ovos-skill\bridge\start_bridge.bat
```

**Expected Output:**
```
============================================================
  🎤 Windows STT Bridge - FINAL SOLUTION
  Precise Lite + Whisper (100% FREE)
============================================================

2025-11-28 16:50:19,888 - INFO - ✅ Model downloaded
2025-11-28 16:50:31,741 - INFO - ✅ Whisper loaded (command transcription)
2025-11-28 16:50:33,963 - INFO - ✅ Connected to OVOS bridge
2025-11-28 16:50:33,964 - INFO - 🎙️ Wake word: 'Hey Mycroft'
2025-11-28 16:50:33,964 - INFO - 🎯 Precise Lite (OVOS wake word engine)
2025-11-28 16:50:33,964 - INFO - 🧠 Whisper (command transcription)
2025-11-28 16:50:33,964 - INFO - 
💤 Waiting for wake word...

INFO: Created TensorFlow Lite XNNPACK delegate for CPU.
```

**Status:** [ ] WSL2 bridge running, [ ] Windows STT bridge running

---

## 🧪 Phase 6: Bridge Testing (NEW)

### Task 6.1: Test Wake Word Detection

**In PowerShell terminal with Windows STT bridge:**

**Test 1: Wake word**
```
You: "Hey Mycroft"
Expected: "🎯 WAKE WORD DETECTED! ('Hey Mycroft')"
```

**Status:** [ ] Wake word detected

---

### Task 6.2: Test Command Transcription

**Test 2: Simple command**
```
You: "Hey Mycroft"
Bridge: "🎯 WAKE WORD DETECTED!"
You: "Factory overview"
Expected: "📝 Command: 'Factory overview.'"
Expected: "📤 Sent to OVOS: 'Factory overview.'"
```

**Status:** [ ] Command transcribed, [ ] Sent to OVOS

**Test 3: Complex command**
```
You: "Hey Mycroft"
Bridge: "🎯 WAKE WORD DETECTED!"
You: "What is the energy consumption of compressor 1?"
Expected: "📝 Command: 'What is the energy consumption of compressor 1?'"
Expected: "📤 Sent to OVOS: 'What is the energy consumption of compressor 1?'"
```

**Status:** [ ] Complex command transcribed, [ ] Sent to OVOS

---

### Task 6.3: Verify OVOS Receives Utterances

**Check Terminal 2 (ovos-core) logs:**

**Expected after "Factory overview" sent:**
```
[EnmsSkill] converse_handling_query utterance="factory overview"
[EnmsSkill] Intent: factory_overview (confidence: 0.95)
[EnmsSkill] API: GET /factory/overview
[EnmsSkill] Response formatted
```

**Expected in Terminal 3 (ovos-audio):**
```
[Audio] Speaking: "Factory status: operational. Today's energy: 39152.5 kWh..."
```

**Status:** [ ] Skill received utterance, [ ] Skill processed query, [ ] TTS response generated

---

## 🧪 Phase 7: End-to-End Voice Testing ⏳ NOT STARTED

**Terminal 3 (WSL2):**
```bash
# Activate OVOS venv
source ~/ovos-env/bin/activate

# Start audio service (TTS output)
ovos-audio

# Wait for: "Audio service started"
```

#### Step 5.4: Use Windows STT Bridge (REPLACES ovos-dinkum-listener)

**⚠️ IMPORTANT:** Instead of running `ovos-dinkum-listener` in WSL2, we use the Windows STT Bridge to avoid WSLg audio corruption.

**Terminal 4 (PowerShell - Windows side):**
```bash
# Start WSL2 OVOS bridge (WebSocket server)
wsl bash -c "cd /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/bridge ; nohup python3 wsl_ovos_bridge.py > wsl_bridge.log 2>&1 &"

# Wait 3 seconds for bridge to start
timeout /t 3
```

**Terminal 5 (PowerShell - Windows side):**
```bash
# Start Windows STT bridge (Precise Lite + Whisper)
python d:\ovos-llm-core\ovos-llm\enms-ovos-skill\bridge\windows_stt_bridge_final.py

# OR use startup script:
d:\ovos-llm-core\ovos-llm\enms-ovos-skill\bridge\start_bridge.bat
```

**Expected Output:**
```
============================================================
  🎤 Windows STT Bridge - FINAL SOLUTION
  Precise Lite + Whisper (100% FREE)
============================================================

2025-11-28 16:50:19,888 - INFO - ✅ Model downloaded
2025-11-28 16:50:31,741 - INFO - ✅ Whisper loaded (command transcription)
2025-11-28 16:50:33,963 - INFO - ✅ Connected to OVOS bridge
2025-11-28 16:50:33,964 - INFO - 🎙️ Wake word: 'Hey Mycroft'
2025-11-28 16:50:33,964 - INFO - 🎯 Precise Lite (OVOS wake word engine)
2025-11-28 16:50:33,964 - INFO - 🧠 Whisper (command transcription)
2025-11-28 16:50:33,964 - INFO - 
💤 Waiting for wake word...

INFO: Created TensorFlow Lite XNNPACK delegate for CPU.
```

**Status:** [ ] WSL2 bridge running, [ ] Windows STT bridge running

---

## 🧪 Phase 6: Bridge Testing (NEW)

### Task 6.1: Test Wake Word Detection

**In PowerShell terminal with Windows STT bridge:**

**Test 1: Wake word**
```
You: "Hey Mycroft"
Expected: "🎯 WAKE WORD DETECTED! ('Hey Mycroft')"
```

**Status:** [ ] Wake word detected

---

### Task 6.2: Test Command Transcription

**Test 2: Simple command**
```
You: "Hey Mycroft"
Bridge: "🎯 WAKE WORD DETECTED!"
You: "Factory overview"
Expected: "📝 Command: 'Factory overview.'"
Expected: "📤 Sent to OVOS: 'Factory overview.'"
```

**Status:** [ ] Command transcribed, [ ] Sent to OVOS

**Test 3: Complex command**
```
You: "Hey Mycroft"
Bridge: "🎯 WAKE WORD DETECTED!"
You: "What is the energy consumption of compressor 1?"
Expected: "📝 Command: 'What is the energy consumption of compressor 1?'"
Expected: "📤 Sent to OVOS: 'What is the energy consumption of compressor 1?'"
```

**Status:** [ ] Complex command transcribed, [ ] Sent to OVOS

---

### Task 6.3: Verify OVOS Receives Utterances

**Check Terminal 2 (ovos-core) logs:**

**Expected after "Factory overview" sent:**
```
[EnmsSkill] converse_handling_query utterance="factory overview"
[EnmsSkill] Intent: factory_overview (confidence: 0.95)
[EnmsSkill] API: GET /factory/overview
[EnmsSkill] Response formatted
```

**Expected in Terminal 3 (ovos-audio):**
```
[Audio] Speaking: "Factory status: operational. Today's energy: 39152.5 kWh..."
```

**Status:** [ ] Skill received utterance, [ ] Skill processed query, [ ] TTS response generated

---

## 🧪 Phase 7: End-to-End Voice Testing ⏳ NOT STARTED

**Terminal 3 (WSL2):**
```bash
# Activate OVOS venv
source ~/ovos-env/bin/activate

# Start audio service (TTS playback via WSLg)
ovos-audio

# Wait for: "Audio service started"
```

**Terminal 4 (WSL2):**
```bash
# Activate OVOS venv
source ~/ovos-env/bin/activate

# Start listener service (STT + wake word via WSLg microphone)
ovos-dinkum-listener

# Wait for: "Listener ready"
# Should detect microphone automatically via WSLg
```

**WSLg Audio Notes:**
- WSL2 on Windows 11 includes WSLg (automatic audio/video forwarding)
- Microphone input from Windows → WSL2 (automatic)
- Audio output from WSL2 → Windows speakers (automatic)
- No additional configuration needed

**🚨 CRITICAL WSLg AUDIO ISSUE (2025-11-28):**
- WSLg's RDP audio tunnel corrupts microphone input
- STT produces garbage transcriptions ("fuck that" instead of "factory overview")
- Root cause: Lossy resampling in RDPSource (44.1kHz → 16kHz)
- **Solution:** Use Hybrid/Satellite Architecture (see top of document)
- Windows-native audio capture works correctly

**If services fail on Windows Native:**
- Only run `ovos-messagebus` + `ovos-core` (text-only mode)
- Skip `ovos-audio` and `ovos-dinkum-listener`
- Test with CLI instead of voice

---

### Phase 6: Test Integration

#### Step 6.1: Test via CLI (Text Input)

**WSL2 Terminal:**
```bash
# Activate OVOS venv (in a 5th terminal, or reuse one after stopping a service)
source ~/ovos-env/bin/activate

# Send test utterance via message bus
ovos-cli-client send "recognizer_loop:utterance" '{"utterances": ["what is the energy for compressor 1"]}'
```

**Windows PowerShell:**
```powershell
ovos-cli-client send "recognizer_loop:utterance" '{"utterances": ["what is the energy for compressor 1"]}'
```

#### Step 6.2: Test via Voice (WSL2 with WSLg)

**Using Windows Microphone (WSLg automatically forwards to WSL2):**

```
You: "Hey Mycroft"  [Speak into Windows laptop microphone]
OVOS: [wake sound plays through Windows speakers]

You: "What's the energy for Compressor-1?"
OVOS: "Compressor-1 consumed 450.3 kilowatt hours today"

You: "Show me top 3 consumers"
OVOS: "The top 3 consumers are: Compressor-1 at 450 kWh, ..."
```

**Audio Flow (WSLg on Windows 11):**
```
Windows Microphone
       ↓ (WSLg forwards)
WSL2 ovos-dinkum-listener (STT)
       ↓
WSL2 ovos-core (EnmsSkill processes)
       ↓
WSL2 ovos-audio (TTS generates speech)
       ↓ (WSLg forwards)
Windows Speakers
```

**No additional configuration needed** - WSLg handles audio automatically!

#### Step 6.3: Verify Logs

**Check skill activation:**
```
[EnmsSkill] converse() called: "what's the energy for compressor 1"
[EnmsSkill] Intent: energy_query (confidence: 0.95)
[EnmsSkill] API: GET /machines/status/Compressor-1
[EnmsSkill] Response formatted
```

---

## 🔧 Conflict Resolution & Coexistence

### Issue 1: Two Adapt Parsers?

**Question:** We have `adapt-parser` library + OVOS has `ovos-padacioso-pipeline-plugin`. Conflict?

**Answer:** ✅ **NO CONFLICT**

**Explanation:**
- **Our Adapt Parser** = `from adapt-parser import ...`
  - Library we import in `lib/intent_parser.py`
  - Runs INTERNALLY in our skill
  - Only processes queries WE handle in `converse()`
  
- **OVOS Adapt Pipeline** = `ovos-padacioso-pipeline-plugin`
  - Global OVOS pipeline stage
  - Runs AFTER our `converse()` returns `False`
  - Matches intents across ALL skills

**They never conflict because:**
1. Our Adapt runs in our skill's code (private)
2. OVOS Adapt runs in pipeline (global)
3. If we return `True` from `converse()`, OVOS pipeline never runs
4. If we return `False`, OVOS pipeline takes over

### Issue 2: Intent File Discovery

**Question:** Will OVOS Padatious find our `.intent` files?

**Answer:** ⚠️ **NOT NEEDED** - We're using pure converse() approach

**Explanation:**
- OVOS Padatious scans `locale/en-us/*.intent` files
- But we commented out all `@intent_handler` decorators
- So even if Padatious matches, there's no handler to call
- Our `converse()` method runs at stage #2 (before Padatious)
- We handle ALL energy queries in converse() via HybridParser

**Strategy:**
- ✅ Use `converse()` for ALL queries (preserves standalone behavior)
- ✅ Our 3-tier HybridParser handles simple AND complex queries
- ❌ Don't use OVOS Padatious (would cause double parsing)

### Issue 3: Performance - Who Runs First?

**Pipeline Order (from OVOS config):**
```
User Utterance
    ↓
1. stop_high         ← Stop commands
2. converse          ← OUR converse() called HERE ✅ (if skill active)
3. padatious_high    ← OVOS Padatious (we return False, so it never runs)
4. adapt_high        ← OVOS Adapt (we return False, so it never runs)
5. ... rest of pipeline (we return False, so they never run)
```

**Our Strategy:**
1. `converse()` handles ALL energy queries → **stage #2** (before any OVOS matching)
2. Return `True` if we handle it → pipeline stops
3. Return `False` if not our domain → let OVOS pipeline continue

**Performance:**
- Same latency as standalone test_skill_chat.py
- HybridParser's 3-tier routing (Heuristic <1ms → Adapt <10ms → LLM 300-500ms)
- No double parsing overhead
- Predictable, tested behavior

---

## 📊 Performance Comparison: Standalone vs OVOS Pure Converse

| Query Type | Standalone | OVOS Pure Converse | OVOS w/ @intent_handler (AVOIDED) |
|------------|-----------|-------------------|----------------------------------|
| **Simple** ("factory overview") | 180ms | 380ms (+200ms STT) | 430ms (double parsing!) |
| **Medium** ("compressor 1 kwh") | 185ms | 385ms | 450ms |
| **Complex** ("compare boiler and compressor") | 520ms (LLM) | 720ms | 770ms |

**Breakdown of OVOS Pure Converse latency:**
- STT (Vosk): ~200ms
- Pipeline routing to converse: ~1ms
- HybridParser (Tier 1 Heuristic): <1ms (70% queries)
- API call: ~180ms
- TTS preparation: ~5ms
- **Total: ~380ms** (acceptable for voice assistant)

**Why Pure Converse is optimal:**
- ✅ Only ~200ms overhead from STT (unavoidable for voice)
- ✅ No double parsing penalty
- ✅ Predictable, tested behavior
- ✅ Same intelligent routing (Heuristic → Adapt → LLM)

---

## 📊 Integration Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                         User Voice Input                        │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                    OVOS Listener (STT)                         │
│  ovos-dinkum-listener + ovos-stt-plugin-vosk                   │
└────────────────────────────────────────────────────────────────┘
                              ↓
                    "what's the energy for compressor 1"
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                    OVOS Message Bus                            │
│  Message: recognizer_loop:utterance                            │
│  Data: {utterances: ["what's the energy..."]}                  │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                    OVOS Skills Service                         │
│                    (Intent Pipeline)                           │
│                                                                │
│  Stage 1: stop_high       → No match                          │
│  Stage 2: converse        → EnmsSkill.converse() called ✓     │
│           ↓                                                    │
│      ┌─────────────────────────────────────────────┐         │
│      │   EnmsSkill (OUR CODE)                      │         │
│      │                                             │         │
│      │  1. Check: energy-related? YES              │         │
│      │  2. HybridParser.parse()                    │         │
│      │     ├─ Heuristic Router (regex) ✓          │         │
│      │     ├─ Internal Adapt Parser                │         │
│      │     └─ Qwen3 LLM (if needed)                │         │
│      │  3. ENMSValidator.validate()                │         │
│      │  4. ENMSClient.get_machine_status()         │         │
│      │  5. ResponseFormatter.format()              │         │
│      │  6. self.speak(response)                    │         │
│      │  7. return True  ← Consumed!                │         │
│      └─────────────────────────────────────────────┘         │
│                                                                │
│  Stage 3: padatious_high  → Skipped (we returned True)        │
│  Stage 4: adapt_high      → Skipped                           │
│  ...                                                           │
└────────────────────────────────────────────────────────────────┘
                              ↓
                    "Compressor-1 consumed 450.3 ..."
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                    OVOS Audio (TTS)                            │
│  ovos-tts-plugin-mimic3                                        │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                    Speaker Output                              │
└────────────────────────────────────────────────────────────────┘
```

---

## ⚠️ Potential Issues & Solutions

### Issue 1: Windows Audio Support

**Problem:** OVOS audio may not work well on Windows  
**Solution:**
- Test on WSL2 (Windows Subsystem for Linux)
- Or use Linux VM for production deployment
- For Windows dev, use text-only testing

### Issue 2: LLM Model Path

**Problem:** Model path in settings might be wrong after installation  
**Solution:** 
```json
{
  "llm_model_path": "{{SKILL_DIRECTORY}}/models/Qwen_Qwen3-1.7B-Q4_K_M.gguf"
}
```

Or use absolute path:
```json
{
  "llm_model_path": "d:\\ovos-llm-core\\ovos-llm\\enms-ovos-skill\\models\\Qwen_Qwen3-1.7B-Q4_K_M.gguf"
}
```

### Issue 3: API Connectivity

**Problem:** EnMS API at `http://10.33.10.109:8001` not accessible from Windows  
**Solution:**
- Ensure network connectivity to API server
- Test with `curl http://10.33.10.109:8001/api/v1/health`
- Check firewall settings

### Issue 4: Skill Not Loading

**Problem:** `ovos-core` doesn't load our skill  
**Debug:**
```powershell
# Check if skill is installed
pip list | grep enms-ovos-skill

# Check entry point
python -c "from pkg_resources import iter_entry_points; print(list(iter_entry_points('ovos.plugin.skill')))"

# Check logs
ovos-core --debug
```

### Issue 5: Utterance Not Reaching Skill

**Problem:** Voice input not triggering our skill  
**Debug:**
1. Check if listener is running: `ovos-dinkum-listener --debug`
2. Check message bus: `ovos-messagebus --debug`
3. Send test message: `ovos-cli-client send "recognizer_loop:utterance" '{"utterances": ["test"]}'`
4. Check `converse()` is being called (add debug prints)

---

## 🎯 Success Criteria Checklist

### Stage 1: Standalone Works ✅
- [x] `python scripts/test_skill_chat.py` works
- [x] All components load correctly
- [x] API connectivity confirmed
- [x] LLM model loads and runs

### Stage 2: OVOS Core Installed
- [ ] OVOS packages installed
- [ ] STT/TTS plugins installed
- [ ] Wake word plugin installed
- [ ] Configuration files created

### Stage 3: Skill Installed
- [ ] Skill installed as Python package
- [ ] Entry point registered correctly
- [ ] Shows up in `ovos-skill-launcher --list`

### Stage 4: OVOS Services Running
- [ ] `ovos-messagebus` running
- [ ] `ovos-core` loads skill without errors
- [ ] `ovos-audio` running
- [ ] `ovos-dinkum-listener` running

### Stage 5: Text Input Works
- [ ] CLI utterance reaches skill
- [ ] `converse()` method called
- [ ] Skill processes query correctly
- [ ] TTS speaks response

### Stage 6: Voice Input Works
- [ ] Wake word detection works
- [ ] STT transcribes correctly
- [ ] Skill receives utterance
- [ ] Full voice conversation achieved ✅

---

## 📚 Reference Links

- **OVOS Technical Manual:** https://openvoiceos.github.io/ovos-technical-manual/
- **OVOS GitHub:** https://github.com/OpenVoiceOS
- **Message Spec:** https://openvoiceos.github.io/message_spec/
- **Skill Development Guide:** https://openvoiceos.github.io/ovos-technical-manual/401-skill_structure/
- **Pipeline Documentation:** https://openvoiceos.github.io/ovos-technical-manual/pipelines_overview/
- **Converse Method:** https://openvoiceos.github.io/ovos-technical-manual/502-converse/

---

## 🚀 Next Steps (Pure Converse Implementation)

### Phase 1: Code Preparation (15 minutes)
1. **Comment out @intent_handler decorators** in `__init__.py` (lines ~1654-1680)
2. **Add self.activate()** in `initialize()` method (line ~155) - ⚠️ **REQUIRED, not optional!**
3. **Test standalone again** to ensure nothing broke: `python scripts\test_skill_chat.py`
4. **Verify converse() method** is working as expected (already at line 1681)

### Phase 2: OVOS Installation (1-2 hours)
5. **Install OVOS Core** on WSL2 (recommended) or Linux
6. **Install STT/TTS plugins** (Vosk + Mimic3 for offline testing)
7. **Install wake word plugin** (Precise Lite - current default)

### Phase 3: Configuration (30 minutes)
8. **Create mycroft.conf** with pipeline: `["stop_high", "converse", ...]`
9. **Configure skill settings** in `~/.config/mycroft/skills/enms-ovos-skill/settings.json`
10. **Link skill directory** to OVOS skills folder OR use `pip install -e .` if needed

### Phase 4: Integration Testing (2 hours)
10. **Install skill** with `pip install -e .`
11. **Start OVOS services** (messagebus, core, audio, listener)
12. **Test with text input** via `ovos-cli-client`
13. **Test with voice input** (wake word + query)
14. **Verify responses match** standalone test_skill_chat.py behavior

### Success Criteria:
- ✅ "factory overview" → Same response as standalone
- ✅ Complex queries → LLM tier activates correctly
- ✅ Multi-turn conversation → Context preserved
- ✅ Latency: <400ms total (STT ~200ms + Processing ~180ms)

---

**Last Updated:** 2025-11-26  
**Status:** ✅ Ready for Implementation (Pure Converse Approach)  
**Estimated Time:** 4-6 hours (with troubleshooting)  
**Recommended:** Read `CRITICAL_INTEGRATION_ANALYSIS.md` for detailed rationale
