# 🎯 OVOS EnMS Skill Sophistication Roadmap

**Date:** December 17, 2025 (Updated: December 19, 2025)
**Current Status:** 17/18 intents working (94%), ~75-80 use cases covered  
**Goal:** Super sophisticated skill covering 90%+ of documented use cases

---

## 📊 Progress Summary (Updated: Dec 19, 2025)

### Completed (✅):
1. ✅ **Template Name Fixes** - 4 intents (energy_query, power_query, anomaly_detection, cost_analysis)
2. ✅ **Baseline Vocabulary Fix** - Created baseline.voc, fixed 3 intent timeouts
3. ✅ **Timeout Increases** - 30s → 90s for ML operations
4. ✅ **Comparison & KPI API** - Multi-machine extraction, factory-wide KPI support
5. ✅ **Phase 1 Vocabulary (Partial)** - 5 files enhanced (+45 synonyms), 2 new files created
6. ✅ **Priority 1: Time Range Parsing** - "yesterday", "today", "last week" all working with smart defaults
7. ✅ **Priority 2: Machine Name Normalization** - Voice variations working ("compressor one" → Compressor-1)
8. ✅ **Priority 3: Implicit Factory-Wide Queries** - "energy consumption" → Factory-wide totals (19456.8 kWh)

### In Progress (⏳):
- ⏳ **Phase 1 Vocabulary (Complete)** - 12 more .voc files to enhance

### Pending (⏸️):
- ⏸️ **Priority 3:** Implicit factory-wide queries
- ⏸️ **Priority 4:** Dynamic machine/SEU discovery
- ⏸️ **Priority 5:** Portability layer (WASABI alignment)
- ⏸️ **Phase 3:** Contextual intelligence
- ⏸️ **Phase 4:** Dynamic response generation  

---

## 📊 Current Architecture Analysis

### What We Have:
```
Tier 1: HybridParser (LLM-based intent classification)
├─ Tier 2: AdaptParser (Keyword matching with .voc files)
│  └─ 18 IntentBuilder patterns
├─ Tier 3: PadaciosoParser (Disabled - migrated to Adapt)
└─ Intent Handlers: 18 @intent_handler methods
    └─ ResponseFormatter: Template-based responses
```

### Vocabulary Coverage:
- **23 .voc files** in `locale/en-us/vocab/`
- **17 recently created** for Adapt migration
- **Machine names:** 6 machines (Compressor-1, Boiler-1, HVAC-Main, etc.)
- **Keywords per file:** 3-8 variations average

### Current Limitations:
1. ❌ Limited synonym coverage (e.g., "power" vs "wattage" vs "electricity")
2. ❌ No multi-entity extraction (comparing 2+ machines)
3. ❌ Basic time range parsing (no "since 9am", "between 2-5pm")
4. ❌ No contextual memory (can't say "how about yesterday?" after first query)
5. ❌ Static responses (no dynamic adaptation to data)
6. ❌ No ambiguity resolution ("which compressor?" when multiple exist)
7. ❌ **Hardcoded machine names** - not dynamic discovery from EnMS API
8. ❌ **No implicit factory-wide queries** - "what's the current draw?" fails without machine
9. ❌ **No default time frames** - queries fail if API needs time but user doesn't specify
10. ❌ **Case-sensitive matching** - "Compressor-1" vs "compressor one" treated differently
11. ❌ **Humanergy-specific** - not portable to other EnMS installations

---

## 🧠 Critical Sophistication Requirements (User-Driven Analysis)

### Requirement 1: Implicit Factory-Wide Queries
**Problem:** User asks "what's the current draw?" without mentioning a machine → Skill fails

**Analysis:**
- ✅ **AGREE**: This should default to factory-wide total consumption
- **Logic:** If no machine mentioned → aggregate all machines
- **Voice UX:** Natural to ask "how much power?" meaning "entire facility"
- **Implementation:** Smart defaults in HybridParser + API aggregation

**Solution (Phase 2.4 - NEW):**
```python
def apply_implicit_scope(self, intent: Intent) -> Intent:
    """Apply factory-wide scope when no entity specified"""
    
    # Power/Energy query without machine → factory total
    if intent.intent in [IntentType.ENERGY_QUERY, IntentType.POWER_QUERY]:
        if not intent.machine and not intent.seu:
            intent.scope = "factory_wide"
            self.logger.info("No machine specified, defaulting to factory-wide")
    
    # Status query without machine → factory overview
    elif intent.intent == IntentType.MACHINE_STATUS:
        if not intent.machine:
            intent.intent = IntentType.FACTORY_OVERVIEW
            self.logger.info("No machine for status, switching to factory overview")
    
    return intent
```

**API Pattern:**
```python
# Factory-wide power query
GET /machines/factory-overview  # Returns aggregated metrics
# OR aggregate individual machines
machines = api_client.get_all_machines()
total_power = sum([m['current_power_kw'] for m in machines])
```

**Expected Queries:**
- "what's the current draw?" → Factory total: 247 kW
- "energy consumption?" → Factory total today: 5,932 kWh
- "how much power are we using?" → All machines combined

---

### Requirement 2: Time Range Parsing & Defaults
**Problem:** "energy consumption yesterday" fails due to time parsing

**Analysis:**
- ✅ **NOT DIFFICULT**: Already created `time_range.voc` with 26 expressions
- **Missing:** Parsing logic to convert "yesterday" → `start_time`, `end_time`
- **Default Strategy:** If API requires time but none specified → default to "today"

**Solution (Phase 2.2 - ENHANCED):**
```python
def extract_time_range(self, utterance: str) -> Optional[Dict]:
    """Parse natural language time expressions"""
    
    # Yesterday (00:00 to 23:59)
    if "yesterday" in utterance.lower():
        return {
            'start': (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0),
            'end': (datetime.now() - timedelta(days=1)).replace(hour=23, minute=59)
        }
    
    # Today (00:00 to now) - DEFAULT
    if "today" in utterance.lower() or not any(time_word in utterance for time_word in ['yesterday', 'last', 'since']):
        return {
            'start': datetime.now().replace(hour=0, minute=0),
            'end': datetime.now()
        }
    
    # Last hour
    if "last hour" in utterance.lower():
        return {
            'start': datetime.now() - timedelta(hours=1),
            'end': datetime.now()
        }
    
    # Last week
    if "last week" in utterance.lower():
        return {
            'start': datetime.now() - timedelta(days=7),
            'end': datetime.now()
        }
    
    # Default if nothing matches
    return {
        'start': datetime.now().replace(hour=0, minute=0),
        'end': datetime.now()
    }
```

**Default Time Frame Strategy:**
| Intent Type | Default Time Frame | Rationale |
|-------------|-------------------|-----------|
| Energy Query | Today (00:00 - now) | Cumulative consumption |
| Power Query | Now (real-time) | Instantaneous value |
| Anomaly Detection | Last 24 hours | Recent anomalies |
| Baseline Prediction | Next period (forecast) | Future prediction |
| Cost Analysis | Current month | Billing period |
| Production Metrics | Today | Daily production |

---

### Requirement 3: Case-Insensitive & Variation Handling
**Problem:** "Compressor-1" vs "compressor one" vs "compressor 1" should resolve to same machine

**Analysis:**
- ✅ **CRITICAL FOR VOICE**: Speech-to-text produces variations
- **Wake word:** "Jarvis, what is the energy consumption of compressor one?"
- **STT Output:** "compressor one" (not "Compressor-1")
- **Current State:** Hardcoded whitelist with exact case matching

**Solution (Phase 2.5 - NEW - Machine Name Normalization):**
```python
def normalize_machine_name(self, raw_name: str, machine_list: List[str]) -> Optional[str]:
    """Normalize voice/text variations to canonical machine name"""
    
    # Normalize input
    normalized = raw_name.lower().strip()
    
    # Remove common STT artifacts
    normalized = normalized.replace(" ", "-")  # "compressor 1" → "compressor-1"
    normalized = re.sub(r'\bone\b', '1', normalized)  # "one" → "1"
    normalized = re.sub(r'\btwo\b', '2', normalized)  # "two" → "2"
    
    # Fuzzy match against whitelist
    for machine in machine_list:
        machine_normalized = machine.lower()
        
        # Exact match (case-insensitive)
        if normalized == machine_normalized:
            return machine
        
        # Hyphen vs space
        if normalized.replace("-", " ") == machine_normalized.replace("-", " "):
            return machine
        
        # Partial match (e.g., "compressor" matches "Compressor-1")
        if normalized in machine_normalized or machine_normalized in normalized:
            return machine
    
    return None
```

**Variations Table:**
| User Says (Voice) | STT Output | Normalized | Matches API Name |
|-------------------|------------|------------|------------------|
| "Compressor one" | compressor one | compressor-1 | Compressor-1 ✅ |
| "compressor 1" | compressor 1 | compressor-1 | Compressor-1 ✅ |
| "Compressor dash one" | compressor-1 | compressor-1 | Compressor-1 ✅ |
| "HVAC main" | hvac main | hvac-main | HVAC-Main ✅ |
| "boiler number two" | boiler number 2 | boiler-2 | Boiler-2 ✅ |

**Implementation Status:** ✅ COMPLETE (Dec 19, 2025)

**Test Results:**
```bash
# Test 1: "status of compressor one"
Result: ✅ Compressor-1 is currently running, using 47.3 kW...

# Test 2: "hvac main status"
Result: ✅ HVAC-Main is currently running, using 8.5 kW...

# Test 3: "boiler one status"
Result: ✅ Boiler-1 is currently running, using 28.0 kW...

# Test 4: "COMPRESSOR-1 status" (uppercase)
Result: ✅ Compressor-1 data returned
```

**Implementation Notes:**
- ✅ Used `thefuzz==0.22.1` library for fuzzy matching
- ✅ Confidence threshold: 80% similarity
- ✅ Enhanced validator.py with normalize_machine_name() method
- ✅ Added voice variations to machine.voc for Adapt matching
- ✅ Fixed duplicate method definition bug (line 491)
- ✅ All 18 intent handlers updated to normalize machine names

---

### Requirement 4: Dynamic Machine/SEU Discovery
**Problem:** Currently hardcoded machine whitelist in validators.py

**Analysis:**
- ❌ **CURRENT:** `machine_whitelist = ["Compressor-1", "Boiler-1", ...]` (hardcoded)
- ✅ **NEEDED:** Dynamic fetch from EnMS API on skill startup
- **API Endpoint:** `GET /machines` → Returns all machines
- **API Endpoint:** `GET /seus` → Returns all SEUs
- **Frequency:** Refresh every 1 hour or on skill restart

**Solution (Phase 0 - Prerequisite - NEW):**
```python
class DynamicMachineRegistry:
    """Fetch and cache machines/SEUs from EnMS API"""
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.machines = []
        self.seus = []
        self.last_refresh = None
        self.refresh_interval = timedelta(hours=1)
    
    async def refresh(self):
        """Fetch machines and SEUs from EnMS API"""
        try:
            # Get all machines
            response = await self.api_client.get("/machines")
            if response['success']:
                self.machines = [m['machine_id'] for m in response['data']]
                self.logger.info(f"Loaded {len(self.machines)} machines: {self.machines}")
            
            # Get all SEUs
            response = await self.api_client.get("/seus")
            if response['success']:
                self.seus = [s['seu_name'] for s in response['data']]
                self.logger.info(f"Loaded {len(self.seus)} SEUs: {self.seus}")
            
            self.last_refresh = datetime.now()
        except Exception as e:
            self.logger.error(f"Failed to refresh machines/SEUs: {e}")
            # Fallback to hardcoded if API fails
            self.machines = ["Compressor-1", "Boiler-1", "HVAC-Main"]
    
    def get_machines(self) -> List[str]:
        """Get cached machine list (auto-refresh if stale)"""
        if not self.last_refresh or (datetime.now() - self.last_refresh) > self.refresh_interval:
            asyncio.create_task(self.refresh())
        return self.machines
```

**Integration in Skill:**
```python
class EnmsSkill(OVOSSkill):
    def initialize(self):
        # Initialize dynamic registry
        self.machine_registry = DynamicMachineRegistry(self.api_client)
        
        # Fetch machines on startup
        asyncio.run(self.machine_registry.refresh())
        
        # Update validators with dynamic list
        self.validator.machine_whitelist = self.machine_registry.get_machines()
```

**API Discovery Commands:**
```bash
# Get all machines
curl -X GET http://enms-analytics:8001/api/v1/machines

# Get all SEUs
curl -X GET http://enms-analytics:8001/api/v1/seus

# Get factory metadata
curl -X GET http://enms-analytics:8001/api/v1/factory/metadata
```

---

### Requirement 5: Generalization & Portability (WASABI Alignment)
**Problem:** Skill currently Humanergy-specific - not portable to other EnMS installations

**Analysis:**
**WASABI Proposal Commitments:**
- Deliverable: "Open-source OVOS voice assistant integration for ISO 50001 compliance"
- Target Users: Industrial facilities implementing ISO 50001
- **Implication:** Skill must work with ANY EnMS installation, not just Humanergy

**Current Blockers:**
1. Hardcoded machine names (Humanergy-specific)
2. Hardcoded API endpoints (assumes specific EnMS structure)
3. Humanergy-specific terminology in responses
4. No configuration for different energy monitoring systems

**Solution Strategy - Configuration-Driven Architecture:**

#### 5.1 Configuration File (config.yaml)
```yaml
# OVOS EnMS Skill Configuration
# Allows adaptation to any EnMS installation

enms:
  # API Connection
  api_base_url: "http://enms-analytics:8001/api/v1"
  api_timeout: 90
  
  # Entity Discovery
  auto_discover_machines: true
  auto_discover_seus: true
  refresh_interval_hours: 1
  
  # Fallback (if API discovery fails)
  fallback_machines:
    - "Machine-1"
    - "Machine-2"
  
  # Factory Metadata
  factory_name: "Humanergy Factory"  # Used in responses
  factory_id: "humanergy_001"
  timezone: "Europe/Berlin"
  
  # Terminology (customize for different industries)
  terminology:
    energy_unit: "kWh"  # or MWh, GJ, etc.
    power_unit: "kW"    # or MW, HP, etc.
    machine_term: "machine"  # or "equipment", "asset", "unit"
    seu_term: "significant energy use"  # or "energy consumer"

voice:
  # Response customization
  use_factory_name: true  # "Humanergy Factory consumed..." vs "The factory consumed..."
  verbosity: "medium"  # low, medium, high
  round_numbers: true  # 97.743 → 97.7
  
  # Defaults
  default_time_range: "today"
  default_scope: "factory_wide"  # When no machine specified
```

#### 5.2 Generic API Adapter Pattern
```python
class EnMSAPIAdapter:
    """Abstract adapter for any EnMS API"""
    
    def __init__(self, config: dict):
        self.base_url = config['enms']['api_base_url']
        self.terminology = config['enms']['terminology']
    
    async def get_machines(self) -> List[str]:
        """Generic machine discovery - works with any EnMS"""
        # Try standard endpoint
        try:
            response = await self.client.get(f"{self.base_url}/machines")
            return self._extract_machine_ids(response)
        except:
            # Fallback to configured machines
            return self.config['enms']['fallback_machines']
    
    async def get_energy(self, machine: str, time_range: dict) -> dict:
        """Generic energy query - adapts to API structure"""
        endpoint = f"{self.base_url}/machines/{machine}/energy"
        params = self._format_time_params(time_range)
        return await self.client.get(endpoint, params=params)
    
    def _extract_machine_ids(self, response: dict) -> List[str]:
        """Extract machine IDs from various API response formats"""
        # Try common patterns
        if 'data' in response:
            if isinstance(response['data'], list):
                return [m.get('machine_id') or m.get('id') or m.get('name') 
                        for m in response['data']]
        return []
```

#### 5.3 Installation Script for Portability
```bash
#!/bin/bash
# setup_ovos_skill.sh - Configure OVOS skill for YOUR EnMS

echo "🔧 OVOS EnMS Skill Setup"
echo "========================"

# Prompt for EnMS details
read -p "Enter your EnMS API URL (e.g., http://localhost:8001/api/v1): " API_URL
read -p "Enter your factory name: " FACTORY_NAME
read -p "Auto-discover machines from API? (y/n): " AUTO_DISCOVER

# Generate config.yaml
cat > config.yaml <<EOF
enms:
  api_base_url: "$API_URL"
  auto_discover_machines: $([ "$AUTO_DISCOVER" = "y" ] && echo "true" || echo "false")
  factory_name: "$FACTORY_NAME"
EOF

echo "✅ Configuration saved to config.yaml"

# Test connection
echo "🧪 Testing API connection..."
curl -s "$API_URL/machines" > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ API connection successful"
else
    echo "⚠️  API connection failed - check URL"
fi

# Discover machines
if [ "$AUTO_DISCOVER" = "y" ]; then
    echo "🔍 Discovering machines..."
    MACHINES=$(curl -s "$API_URL/machines" | jq -r '.data[].machine_id')
    echo "Found machines: $MACHINES"
fi

echo "🎉 Setup complete! Start OVOS skill with: docker compose up"
```

#### 5.4 Documentation for Generic Use
**File:** `INSTALLATION_GUIDE.md`
```markdown
# Installing OVOS EnMS Skill for YOUR EnMS

This skill works with **any** EnMS system that exposes a REST API.

## Requirements:
- EnMS with REST API (GET /machines, GET /energy, etc.)
- OVOS installation (via Docker or native)
- Network connectivity between OVOS and EnMS

## Quick Start:
1. Clone repository: `git clone https://github.com/your-org/enms-ovos-skill`
2. Run setup: `./setup_ovos_skill.sh`
3. Start skill: `docker compose up`
4. Test: "Hey Jarvis, what's the energy consumption?"

## API Compatibility:
The skill adapts to various API structures. Minimum required endpoints:
- `GET /machines` - List all machines
- `GET /machines/{id}/energy` - Get energy consumption
- `GET /machines/{id}/status` - Get machine status

See [API_REQUIREMENTS.md](API_REQUIREMENTS.md) for details.
```

#### 5.5 Benefits of Generalization

**For Humanergy:**
- Skill continues to work perfectly (config.yaml = Humanergy defaults)
- Easy updates when adding new machines (auto-discovery)

**For WASABI Partners:**
- Drop-in installation at any facility
- Works with their existing EnMS
- No code changes needed

**For Open Source Community:**
- Wider adoption (not limited to one company)
- More contributors (more use cases)
- Fulfills WASABI open-source commitment

---

## 📋 Updated Implementation Phases

### **Phase 0: Portability Foundation** (NEW - 3-4 hours)
**Priority: HIGH** (enables WASABI alignment)

- [ ] Create `config.yaml` template with all configurable parameters
- [ ] Implement `DynamicMachineRegistry` for API discovery
- [ ] Implement `EnMSAPIAdapter` abstraction layer
- [ ] Create `setup_ovos_skill.sh` installation script
- [ ] Write `INSTALLATION_GUIDE.md` for generic deployments
- [ ] Write `API_REQUIREMENTS.md` documenting minimum EnMS API needs
- [ ] Test with Humanergy EnMS (existing)
- [ ] Test with mock EnMS (different structure) to validate portability

**Deliverable:** Skill works with any EnMS installation via configuration

---

## 🚀 Sophistication Strategy: 4-Phase Approach

### **Phase 1: Vocabulary Expansion** (2-3 hours) ✅ PARTIALLY DONE (60% Complete)
**Goal:** Cover 90% of documented query variations
**Status:** 
- ✅ 5 .voc files enhanced (+45 synonyms): energy_metric, power_metric, status_check
- ✅ 2 new files created: time_range.voc (26 expressions), comparison_words.voc (9 keywords)
- ✅ Test results: 3/5 new queries working (60% success rate)
- ⏳ Remaining: 12 .voc files to enhance, 25 queries to test

#### 1.1 Enhance Existing .voc Files
Add synonyms and natural language variations:

**energy_metric.voc** (current: 1 word)
```
# Current
energy

# Enhanced (15+ variations)
energy
power consumption  
electricity usage
kwh
kilowatt hours
wattage
energy draw
energy usage
power draw
electrical consumption
electricity consumption
how much energy
how much power
energy consumption
power usage
```

**time_range.voc** (NEW - critical for sophistication)
```
# Relative times
today
yesterday
last hour
last 24 hours
past day
past week
this week
last week
this month
past month

# Specific times
since 9am
between 2pm and 5pm
from morning to afternoon
during business hours
overnight
weekend

# Comparative
compared to yesterday
vs last week
versus previous month
```

**machine_groups.voc** (NEW - for multi-machine queries)
```
all compressors
both compressors
all HVAC units
cooling equipment
heating equipment
production machines
all machines
factory wide
plant wide
entire facility
```

**action_verbs.voc** (NEW - better intent detection)
```
show
show me
display
tell me
what is
what's
how much
give me
list
find
search
check
analyze
compare
calculate
```

#### 1.2 Create Missing Vocabulary Files

**aggregation.voc** (NEW)
```
total
average
peak
maximum
minimum
sum
mean
```

**comparison_words.voc** (NEW)
```
compare
versus
vs
against
compared to
difference between
```

**threshold_words.voc** (NEW)
```
above
below
over
under
more than
less than
exceeds
```

**Estimated Impact:** +40 use cases covered

---

### **Phase 2: Entity Extraction Enhancement** (6-8 hours) ⚠️ IN PROGRESS (60% Complete)
**Goal:** Extract complex parameters from natural language + implicit queries + defaults
**Status:**
- ✅ Phase 2.2 Time Parsing: COMPLETE (Priority 1)
- ✅ Phase 2.5 Name Normalization: COMPLETE (Priority 2)
- ✅ Phase 2.4 Factory-Wide Scope: COMPLETE (Priority 3)
- ⏳ Phase 2.1 Multi-Machine: PENDING
- ⏳ Phase 2.3 Metric Intelligence: PENDING

#### 2.1 Multi-Machine Extraction
**Current:** Only extracts ONE machine per query  
**Target:** Extract ALL machines mentioned

**Implementation in HybridParser:**
```python
def extract_machines(self, utterance: str) -> List[str]:
    """Extract ALL machines mentioned in utterance"""
    machines = []
    
    # Check against whitelist
    for machine in self.validator.machine_whitelist:
        if machine.lower() in utterance.lower():
            machines.append(machine)
    
    # Check for groups (e.g., "all compressors")
    if "all compressor" in utterance.lower():
        machines = [m for m in self.validator.machine_whitelist 
                   if "compressor" in m.lower()]
    
    return machines
```

**Benefits:**
- "Compare Compressor-1 and Boiler-1" → extracts BOTH
- "Show me all HVAC units" → extracts HVAC-Main, HVAC-EU-North
- "Which compressor uses more?" → extracts all compressors

#### 2.2 Advanced Time Range Extraction ⚡ PRIORITY: HIGH
**Current:** Basic relative times (today, yesterday)  
**Target:** Complex time expressions with defaults

**Implementation (lib/hybrid_parser.py):**
```python
def extract_time_range(self, utterance: str) -> Dict[str, datetime]:
    """Extract time range from natural language with smart defaults"""
    
    # Yesterday (00:00 to 23:59)
    if "yesterday" in utterance.lower():
        yesterday = datetime.now() - timedelta(days=1)
        return {
            'start': yesterday.replace(hour=0, minute=0, second=0),
            'end': yesterday.replace(hour=23, minute=59, second=59),
            'duration': '1d'
        }
    
    # Last hour
    if "last hour" in utterance.lower() or "past hour" in utterance.lower():
        return {
            'start': datetime.now() - timedelta(hours=1),
            'end': datetime.now(),
            'duration': '1h'
        }
    
    # Last week
    if "last week" in utterance.lower():
        return {
            'start': datetime.now() - timedelta(days=7),
            'end': datetime.now(),
            'duration': '7d'
        }
    
    # Specific times
    if match := re.search(r'since (\d+)(am|pm)', utterance.lower()):
        hour = int(match.group(1))
        if match.group(2) == 'pm' and hour != 12:
            hour += 12
        return {
            'start': datetime.now().replace(hour=hour, minute=0, second=0),
            'end': datetime.now(),
            'duration': 'custom'
        }
    
    # Between times
    if match := re.search(r'between (\d+)(am|pm) and (\d+)(am|pm)', utterance.lower()):
        start_hour = int(match.group(1))
        end_hour = int(match.group(3))
        if match.group(2) == 'pm' and start_hour != 12:
            start_hour += 12
        if match.group(4) == 'pm' and end_hour != 12:
            end_hour += 12
        return {
            'start': datetime.now().replace(hour=start_hour, minute=0),
            'end': datetime.now().replace(hour=end_hour, minute=0),
            'duration': 'custom'
        }
    
    # DEFAULT: No time mentioned → today (00:00 to now)
    return {
        'start': datetime.now().replace(hour=0, minute=0, second=0),
        'end': datetime.now(),
        'duration': 'today',
        'is_default': True  # Flag for logging
    }
```

**Benefits:**
- ✅ "energy consumption yesterday" → WORKS (extracts yesterday 00:00-23:59)
- ✅ "Energy since 9am" → extracts 9am to now
- ✅ "Power between 2pm and 5pm" → extracts specific range
- ✅ **DEFAULT:** "what's the consumption?" → defaults to today (implicit)
- ✅ Logs when default applied for debugging

**Testing Commands:**
```bash
# Test yesterday parsing
curl -X POST http://localhost:5000/query -d '{"text": "energy consumption yesterday"}'
# Expected: Parses yesterday 00:00-23:59, calls API with correct time range

# Test default time
curl -X POST http://localhost:5000/query -d '{"text": "what is the consumption?"}'
# Expected: Defaults to today, logs "Using default time range: today"
```

#### 2.3 Metric Intelligence
**Current:** Relies on exact keyword matches  
**Target:** Infer metric from context

**Implementation:**
```python
def infer_metric(self, utterance: str, intent_type: IntentType) -> str:
    """Intelligently infer what metric user wants"""
    
    # Cost indicators
    if any(word in utterance.lower() for word in 
           ['cost', 'price', 'expense', 'dollar', 'spend']):
        return 'cost'
    
    # Power indicators (instantaneous)
    if any(word in utterance.lower() for word in 
           ['power', 'watt', 'kw', 'current', 'now', 'right now']):
        return 'power'
    
    # Energy indicators (cumulative)
    if any(word in utterance.lower() for word in 
           ['energy', 'kwh', 'consumption', 'used', 'total']):
        return 'energy'
    
    # Default by intent type
    return intent_type.default_metric()
```

**Benefits:**
- "How much did Compressor-1 cost today?" → auto-detects cost_metric
- "What's the current draw?" → auto-detects power_metric
- "Total consumption this week" → auto-detects energy_metric

#### 2.4 Implicit Factory-Wide Scope (NEW) ⚡ PRIORITY: HIGH
**Current:** Queries without machine fail  
**Target:** Default to factory-wide aggregation

**Implementation (lib/hybrid_parser.py):**
```python
def apply_implicit_scope(self, intent: Intent) -> Intent:
    """Apply factory-wide scope when no entity specified"""
    
    # Power/Energy query without machine → factory total
    if intent.intent in [IntentType.ENERGY_QUERY, IntentType.POWER_QUERY]:
        if not intent.machine and not intent.seu:
            intent.scope = "factory_wide"
            intent.use_factory_total = True
            self.logger.info(f"No machine specified, defaulting to factory-wide for {intent.intent}")
    
    # Status query without machine → factory overview
    elif intent.intent == IntentType.MACHINE_STATUS:
        if not intent.machine:
            intent.intent = IntentType.FACTORY_OVERVIEW
            self.logger.info("No machine for status, switching to factory overview")
    
    # Ranking without machine → show top 5
    elif intent.intent == IntentType.RANKING:
        if not intent.machine:
            intent.show_top_n = 5
    
    return intent
```

**API Integration (enms_ovos_skill/__init__.py):**
```python
def handle_energy_query(self, message: Message):
    intent = self.parser.parse(message.data.get('utterance'))
    
    # Check for factory-wide scope
    if intent.use_factory_total:
        # Option 1: Use factory overview endpoint
        result = self._run_async(self.api_client.get_factory_overview())
        total_energy = result.get('total_energy_kwh', 0)
        
        # Option 2: Aggregate all machines
        # machines = self.machine_registry.get_machines()
        # total_energy = sum([self._get_machine_energy(m) for m in machines])
        
        return self.format_response(
            'factory_energy',
            total_energy_kwh=total_energy,
            time_period="today"
        )
```

**New Dialog Template (locale/en-us/dialog/factory_energy.dialog):**
```jinja2
The factory consumed {{ total_energy_kwh|round(1) }} kilowatt hours {{ time_period }}.
```

**Benefits:**
- ✅ "what's the current draw?" → Factory total: 247.3 kW
- ✅ "energy consumption?" → Factory total today: 5,932 kWh
- ✅ "how much power are we using?" → All machines combined
- ✅ Natural voice UX (no need to say "factory" every time)

#### 2.5 Machine Name Normalization (NEW) ⚡ PRIORITY: CRITICAL
**Current:** Case-sensitive, exact matching  
**Target:** Voice-friendly variations

**Implementation (lib/validators.py):**
```python
def normalize_machine_name(self, raw_name: str) -> Optional[str]:
    """Normalize voice/text variations to canonical machine name"""
    
    # Get current machine list
    machine_list = self.machine_registry.get_machines()
    
    # Normalize input
    normalized = raw_name.lower().strip()
    
    # Remove common STT artifacts
    normalized = normalized.replace(" ", "-")  # "compressor 1" → "compressor-1"
    normalized = re.sub(r'\bone\b', '1', normalized)  # "one" → "1"
    normalized = re.sub(r'\btwo\b', '2', normalized)  # "two" → "2"
    normalized = re.sub(r'\bthree\b', '3', normalized)
    normalized = re.sub(r'\bmain\b', 'Main', normalized)  # "hvac main" → "hvac-Main"
    
    # Try exact match (case-insensitive)
    for machine in machine_list:
        if normalized == machine.lower():
            return machine
    
    # Try hyphen vs space variants
    for machine in machine_list:
        machine_variants = [
            machine.lower(),
            machine.lower().replace("-", " "),
            machine.lower().replace("-", ""),
        ]
        if normalized in machine_variants or \
           normalized.replace("-", " ") in machine_variants or \
           normalized.replace("-", "") in machine_variants:
            return machine
    
    # Fuzzy match (80% similarity)
    from thefuzz import fuzz
    best_match = None
    best_score = 0
    for machine in machine_list:
        score = fuzz.ratio(normalized, machine.lower())
        if score > best_score and score >= 80:
            best_score = score
            best_match = machine
    
    if best_match:
        self.logger.info(f"Fuzzy matched '{raw_name}' → '{best_match}' (score: {best_score})")
        return best_match
    
    return None
```

**Testing Matrix:**
| User Says (Voice) | STT Output | Normalized | API Match | Result |
|-------------------|------------|------------|-----------|---------|
| "Compressor one" | compressor one | compressor-1 | Compressor-1 | ✅ MATCH |
| "compressor 1" | compressor 1 | compressor-1 | Compressor-1 | ✅ MATCH |
| "COMPRESSOR-1" | compressor-1 | compressor-1 | Compressor-1 | ✅ MATCH |
| "HVAC main" | hvac main | hvac-main | HVAC-Main | ✅ MATCH |
| "boiler number two" | boiler number 2 | boiler-2 | Boiler-2 | ✅ MATCH |
| "kompressor one" | kompressor one | kompressor-1 | Compressor-1 | ✅ FUZZY (82%) |

**Dependencies:**
```bash
# Add to requirements.txt
thefuzz==0.20.0  # Fuzzy string matching
python-Levenshtein==0.21.0  # Faster fuzzy matching
```

**Estimated Impact:** +35 use cases covered (all voice variations work)

---

---

### **Phase 3: Contextual Intelligence** (6-8 hours)
**Goal:** Remember context across queries, handle follow-ups

#### 3.1 Session Context Management
**Already exists** in `lib/conversation_context.py`, need to USE it:

**Enhancement in handlers:**
```python
def handle_energy_query(self, message: Message):
    # Get context
    session_id = message.context.get('session_id', 'default_user')
    context = self.context_manager.get_context(session_id)
    
    # Extract machine (or use last mentioned)
    machine = message.data.get('machine') or context.last_machine
    
    # Store for next query
    if machine:
        self.context_manager.update_machine(session_id, machine)
    
    # ... rest of handler
```

**Benefits:**
- User: "Status of Compressor-1"
- OVOS: "Compressor-1 is running..."
- User: "How about yesterday?" ← Uses context: Compressor-1, yesterday
- OVOS: "Yesterday, Compressor-1 consumed..."

#### 3.2 Clarification Prompts
**Current:** Fails silently on ambiguity  
**Target:** Ask user for clarification

**Implementation:**
```python
def handle_ambiguous_machine(self, matches: List[str]) -> str:
    """Generate clarification prompt"""
    if len(matches) == 2:
        return f"Did you mean {matches[0]} or {matches[1]}?"
    else:
        options = ", ".join(matches[:-1]) + f", or {matches[-1]}"
        return f"Which machine? {options}"
```

**Benefits:**
- User: "Status of compressor"
- OVOS: "Did you mean Compressor-1 or Compressor-EU-1?"
- User: "The first one"
- OVOS: *Returns Compressor-1 status*

#### 3.3 Smart Defaults
**Implementation:**
```python
def apply_smart_defaults(self, intent: Intent) -> Intent:
    """Apply intelligent defaults based on context"""
    
    # No time range? Default to 'today'
    if not intent.time_range:
        intent.time_range = TimeRange.today()
    
    # No machine but handler requires one? Use factory summary
    if not intent.machine and intent.intent in [IntentType.ENERGY_QUERY]:
        intent.use_factory_wide = True
    
    # Ambiguous metric? Infer from intent type
    if not intent.metric:
        intent.metric = self.infer_metric(intent.utterance, intent.intent)
    
    return intent
```

**Estimated Impact:** +20 use cases covered, much better UX

---

### **Phase 4: Dynamic Response Generation** (4-5 hours)
**Goal:** Responses adapt to data, not static templates

#### 4.1 Template Enhancements
**Current:** Static Jinja2 templates  
**Target:** Dynamic, data-driven responses

**Example - energy_query.dialog:**
```jinja2
{# Current (static) #}
{{ machine }} consumed {{ energy_kwh }} kilowatt hours today.

{# Enhanced (dynamic) #}
{% if energy_kwh > threshold %}
⚠️ {{ machine }} consumed {{ energy_kwh }} kilowatt hours today - that's {{ percent_above }}% above normal!
{% elif energy_kwh < threshold %}
✅ {{ machine }} consumed {{ energy_kwh }} kilowatt hours today - {{ percent_below }}% below normal. Great efficiency!
{% else %}
{{ machine }} consumed {{ energy_kwh }} kilowatt hours today.
{% endif %}

{% if trend == "increasing" %}
Consumption has been trending upward over the past {{ trend_days }} days.
{% elif trend == "decreasing" %}
Consumption has been decreasing - keep it up!
{% endif %}

{% if cost_usd %}
This cost {{ cost_usd }} dollars{% if cost_change %}, which is {{ cost_change }} compared to {{ comparison_period }}{% endif %}.
{% endif %}
```

**Benefits:**
- Alerts user to anomalies automatically
- Provides trends without asking
- Richer, more informative responses

#### 4.2 Voice Optimization
**Already implemented** in `ResponseFormatter._voice_number()`, enhance it:

```python
def voice_optimize(self, response: str) -> str:
    """Make response more natural for voice"""
    
    # Round numbers for voice
    response = re.sub(r'(\d+\.\d{3,})', lambda m: f"{float(m.group(1)):.1f}", response)
    
    # Replace technical terms
    replacements = {
        'kWh': 'kilowatt hours',
        'kW': 'kilowatts',
        'SEU': 'energy use',
        'EnPI': 'energy performance indicator',
        '%': 'percent'
    }
    
    for old, new in replacements.items():
        response = response.replace(old, new)
    
    # Add natural pauses
    response = response.replace('. ', '. ... ')
    
    return response
```

#### 4.3 List Handling
**Current:** Returns all items  
**Target:** Voice-friendly summaries

```python
def format_list_response(self, items: List[Dict], max_items: int = 3) -> str:
    """Format list for voice with top N + summary"""
    
    response_parts = []
    
    # Top N items
    for i, item in enumerate(items[:max_items], 1):
        response_parts.append(f"{i}. {item['name']}: {item['value']}")
    
    # Summary of remaining
    remaining = len(items) - max_items
    if remaining > 0:
        response_parts.append(f"... and {remaining} more")
    
    return "\n".join(response_parts)
```

**Estimated Impact:** Better UX, more natural interactions

---

## 📈 Implementation Priority & Timeline

### **Week 0: Portability Foundation (3-4 hours)** ⚡ NEW PRIORITY - NOT STARTED
**Day 0:** Phase 0 - WASABI Alignment
- [ ] Create `config.yaml` template for generic EnMS installations
- [ ] Implement `DynamicMachineRegistry` (API discovery)
- [ ] Implement `EnMSAPIAdapter` abstraction layer
- [ ] Test with Humanergy EnMS (existing setup)
- [ ] Write `INSTALLATION_GUIDE.md` for portable deployments
- **Deliverable:** Skill works with ANY EnMS via configuration

### **Week 1: Foundation (18-22 hours)** ⚠️ IN PROGRESS
**Days 1-2:** Phase 1 - Vocabulary Expansion ✅ PARTIALLY DONE
- [x] ✅ Enhance energy_metric.voc (+16 synonyms) - DONE
- [x] ✅ Enhance power_metric.voc (+13 synonyms) - DONE
- [x] ✅ Enhance status_check.voc (+16 action verbs) - DONE
- [x] ✅ Create time_range.voc (26 time expressions) - DONE
- [x] ✅ Create comparison_words.voc (9 keywords) - DONE
- [ ] Enhance 12 remaining .voc files with synonyms
- [ ] Test with 30+ new query variations
- **Deliverable:** 90% vocabulary coverage (Partial: 5/25 files done, 60% coverage estimated)

**Days 3-4:** Phase 2.2 & 2.5 - Time Parsing & Normalization ⚡ IN PROGRESS
- [x] ✅ Implement time range extraction with defaults (__init__.py) - DONE (Priority 1)
- [x] ✅ Test "energy consumption yesterday" → ✅ WORKS (1115.75 kWh Dec 18)
- [x] ✅ Test "Compressor-1 energy today" → ✅ WORKS
- [ ] ⏳ Implement machine name normalization (lib/validators.py) - NEXT (Priority 2)
- [ ] Add fuzzy matching dependency (thefuzz)
- [ ] Test "compressor one" variations → MUST WORK
- **Deliverable:** Voice-friendly queries work (Time parsing: ✅ DONE, Normalization: ⏳ NEXT)

**Day 5:** Phase 2.1 & 2.4 - Multi-Machine & Implicit Scope - NOT STARTED
- [ ] Implement multi-machine extraction in HybridParser
- [ ] Implement implicit factory-wide logic (Priority 3)
- [ ] Test "what's the current draw?" → Factory total
- [ ] Test "compare X and Y since 9am"
- **Deliverable:** Complex queries work, factory-wide defaults

### **Week 2: Intelligence (12-15 hours)**
**Days 6-7:** Phase 2.3 & 3.1 - Metric Intelligence & Context
- [ ] Implement metric inference logic
- [ ] Integrate context_manager in all handlers
- [ ] Test follow-up queries
- **Deliverable:** Context-aware conversations

**Days 8-9:** Phase 3.2 & 3.3 - Clarification & Defaults
- [ ] Implement clarification prompts
- [ ] Add smart defaults logic
- [ ] Test ambiguous queries
- **Deliverable:** Graceful handling of edge cases

**Day 10:** Integration Testing
- [ ] Test 150 documented use cases
- [ ] Benchmark response quality
- [ ] Fix issues
- **Deliverable:** 95%+ use case coverage

### **Week 3: Polish (8-10 hours)**
**Days 11-12:** Phase 4 - Dynamic Responses
- [ ] Enhance all 18 dialog templates
- [ ] Implement voice optimization
- [ ] Add list handling
- **Deliverable:** Natural, informative responses

**Day 13:** Production Readiness
- [ ] Performance testing (latency, throughput)
- [ ] Error handling audit
- [ ] Documentation update
- **Deliverable:** Production-ready skill

**Day 14:** Deployment & Monitoring
- [ ] Deploy to production
- [ ] Enable query logging
- [ ] Monitor for unhandled queries
- **Deliverable:** Live sophisticated skill

---

## 🎯 Success Metrics

### Coverage Metrics:
- [ ] **90%+ of 128 documented use cases** handled successfully
- [ ] **<5% unhandled queries** in production logs
- [ ] **Zero timeout errors** for all intents
- [ ] **Factory-wide queries work** without explicit machine mention

### Quality Metrics:
- [ ] **Average response time** < 2 seconds
- [ ] **User satisfaction** > 4.5/5 (via feedback)
- [ ] **Response accuracy** > 95% (matches API data)
- [ ] **Voice recognition success** > 90% (case/variation handling)

### Sophistication Metrics:
- [ ] **Context retention** across 3+ query turns
- [ ] **Synonym coverage** > 10 variations per concept
- [ ] **Multi-entity queries** work for 2-5 entities
- [ ] **Clarification rate** < 10% (most queries unambiguous)
- [ ] **Default application** logged and successful (time, scope)

### Portability Metrics (WASABI):
- [ ] **Generic installation** works in <10 minutes
- [ ] **API discovery** auto-configures machines/SEUs
- [ ] **Non-Humanergy EnMS** successfully integrated (test case)
- [ ] **Configuration-driven** - no code changes for new installations

---

## 🔧 Technical Implementation Details

### Architecture Changes:

**Before (Current):**
```
User Query → REST Bridge → OVOS Skill → IntentBuilder Match → Handler → API Call → Template Response
```

**After (Sophisticated):**
```
User Query → REST Bridge → OVOS Skill
    ↓
HybridParser (Enhanced)
    ├─ Multi-entity extraction
    ├─ Time range parsing
    ├─ Metric inference
    └─ Context integration
    ↓
Intent Handler (Enhanced)
    ├─ Smart defaults
    ├─ Clarification logic
    └─ Context updates
    ↓
API Call (with extracted params)
    ↓
ResponseFormatter (Enhanced)
    ├─ Dynamic templates
    ├─ Voice optimization
    └─ Data-driven content
    ↓
Natural Voice Response
```

### Key Files to Modify:

**Phase 1:** Vocabulary Files
- `locale/en-us/vocab/*.voc` (23 existing + 6 new)

**Phase 2:** Entity Extraction
- `lib/hybrid_parser.py` - Multi-machine extraction
- `lib/hybrid_parser.py` - Time range parsing
- `lib/validators.py` - Enhanced validation

**Phase 3:** Context & Intelligence
- `__init__.py` - Handler enhancements (all 18)
- `lib/conversation_context.py` - Context usage
- `lib/hybrid_parser.py` - Metric inference

**Phase 4:** Response Generation
- `lib/response_formatter.py` - Dynamic templates
- `locale/en-us/dialog/*.dialog` - Template enhancements (39 files)

---

## 🧪 Testing Strategy

### Phase 1 Tests:
```bash
# Vocabulary coverage test
./test_vocabulary_coverage.sh
# Expected: 90%+ of documented queries match at least one .voc keyword
```

### Phase 2 Tests:
```bash
# Multi-entity extraction test
./test_multi_entity.sh
# Input: "Compare Compressor-1 and Boiler-1"
# Expected: extracts ["Compressor-1", "Boiler-1"]

# Time range parsing test
./test_time_parsing.sh
# Input: "Energy since 9am"
# Expected: extracts TimeRange(start=09:00, end=now)
```

### Phase 3 Tests:
```bash
# Context retention test
./test_context.sh
# Query 1: "Status of Compressor-1"
# Query 2: "How about yesterday?"
# Expected: Query 2 uses Compressor-1 from context
```

### Phase 4 Tests:
```bash
# Response quality test
./test_response_quality.sh
# Measures: naturalness, accuracy, informativeness
# Expected: Score > 4.5/5
```

---

## 📚 Documentation Updates Needed

1. **USER_GUIDE.md** - How to interact with sophisticated skill
2. **TESTING_GUIDE.md** - Comprehensive test procedures
3. **VOCABULARY_REFERENCE.md** - All .voc files documented
4. **CONTEXT_MANAGEMENT.md** - How context works
5. **TEMPLATE_GUIDE.md** - Dialog template best practices

---

## 🚨 Risk Mitigation

### Potential Issues:

**1. Over-matching:** Too many synonyms cause false positives
- **Solution:** Use confidence thresholds, prefer specific matches

**2. Context confusion:** Wrong context retained
- **Solution:** 30-minute context timeout, explicit context clearing

**3. Performance degradation:** Too much processing
- **Solution:** Cache frequent queries, optimize regex patterns

**4. Maintenance complexity:** Too many variations to test
- **Solution:** Automated test generation from use case list

---

## 🎉 Expected Final State

**After Full Implementation:**

### Query Examples That Will Work:
✅ "Compare all compressors"  
✅ "Energy since 9am compared to yesterday"  
✅ "Which machine costs more to run?"  
✅ "How much power during business hours?"  
✅ "Show me yesterday's consumption"  
✅ "Is anything using too much energy?"  
✅ "What's the trend this week?"  
✅ "How efficient is the factory?"  
✅ "Which HVAC unit uses less?"  
✅ "Total consumption between 2pm and 5pm"

### Conversations That Will Work:
```
User: "Status of Compressor-1"
OVOS: "Compressor-1 is running, using 47 kilowatts..."

User: "How about yesterday?"
OVOS: "Yesterday, Compressor-1 consumed 628 kilowatt hours..."

User: "And last week?"
OVOS: "Last week, it consumed 4,396 kilowatt hours total..."

User: "Compare it to the boiler"
OVOS: "Compressor-1 used 628 kWh, Boiler-1 used 1,250 kWh..."
```

---

## 🎯 Immediate Next Steps (Prioritized by User Requirements)

### **Priority 1: Time Range Parsing** ✅ COMPLETE (Actual: 2 hours)
**User Requirement:** "energy consumption yesterday" must work
**Status:** ✅ IMPLEMENTED AND TESTED

**Completed Tasks:**
1. ✅ Implemented `_extract_time_range()` helper method in __init__.py
2. ✅ Added default time logic (today if not specified)
3. ✅ Integrated with 5 time-aware intents: EnergyQuery, PowerQuery, CostAnalysis, AnomalyDetection, Baseline
4. ✅ Test results:
   - "Compressor-1 energy yesterday" → ✅ WORKS (returns Dec 18 data: 1115.75 kWh)
   - "energy consumption Compressor-1 yesterday" → ✅ WORKS
   - "status of Compressor-1" → ✅ WORKS (defaults to today)
   - "Compressor-1 energy today" → ✅ WORKS
5. ✅ Documentation updated in roadmap

**Implementation Details:**
- Created `_extract_time_range()` method using TimeRangeParser
- Supports: yesterday, today, last week, last hour, last N days
- Smart defaults: No time → "today" (00:00 to now)
- Fast parsing with regex (<5ms)
- Logs extraction for debugging
- Graceful fallback on parse failures

**Result:** ✅ "energy consumption yesterday" queries work end-to-end with accurate historical data

---

### **Priority 2: Machine Name Normalization** ⚡ CRITICAL (2-3 hours)
**User Requirement:** Voice variations (compressor one, Compressor-1, etc.) must work
**Blocker:** Case-sensitive, exact matching only

**Tasks:**
1. [ ] Add thefuzz dependency to requirements.txt
2. [ ] Implement `normalize_machine_name()` in lib/validators.py
3. [ ] Integrate with HybridParser machine extraction
4. [ ] Test cases:
   - "compressor one" → matches Compressor-1
   - "hvac main" → matches HVAC-Main
   - "boiler number two" → matches Boiler-2
5. [ ] Document normalization rules

**Expected Result:** All voice variations resolve to correct machine

---

### **Priority 3: Implicit Factory-Wide Queries** ⚡ HIGH (1-2 hours)
**User Requirement:** "what's the current draw?" should return factory total
**Blocker:** No implicit scope logic

**Tasks:**
1. [ ] Implement `apply_implicit_scope()` in lib/hybrid_parser.py
2. [ ] Create factory_energy.dialog and factory_power.dialog templates
3. [ ] Update handlers to check for `use_factory_total` flag
4. [ ] Test cases:
   - "what's the current draw?" → Factory total (not error)
   - "energy consumption?" → Factory total today
   - "how much power are we using?" → All machines combined
5. [ ] Log when defaults applied

**Expected Result:** Queries without machine return meaningful factory-wide data

---

### **Priority 4: Dynamic Machine Discovery** ⚡ HIGH (2-3 hours)
**User Requirement:** Auto-discover machines/SEUs from API, not hardcoded
**WASABI Requirement:** Must work with any EnMS installation

**Tasks:**
1. [ ] Implement `DynamicMachineRegistry` class
2. [ ] Fetch machines from `GET /machines` endpoint
3. [ ] Fetch SEUs from `GET /seus` endpoint
4. [ ] Integrate with skill initialization
5. [ ] Test with Humanergy EnMS
6. [ ] Document API endpoints used

**Expected Result:** Skill knows about all machines/SEUs without hardcoding

---

### **Priority 5: Portability Configuration** ⚡ MEDIUM (3-4 hours)
**WASABI Requirement:** Skill must work with any EnMS, not just Humanergy
**Blocker:** Hardcoded Humanergy-specific details

**Tasks:**
1. [ ] Create config.yaml template
2. [ ] Implement EnMSAPIAdapter abstraction
3. [ ] Create setup_ovos_skill.sh installer
4. [ ] Write INSTALLATION_GUIDE.md
5. [ ] Write API_REQUIREMENTS.md (minimum EnMS API)
6. [ ] Test with mock EnMS (different structure)

**Expected Result:** Open-source community can install on their EnMS

---

### **Completed (Previous Session):**
1. ✅ Fix Baseline Timeout → baseline.voc created, 3 intents working
2. ✅ Comprehensive Test → 17/18 working (94%)
3. ✅ Phase 1 Vocabulary Expansion (partial):
   - ✅ Enhanced energy_metric.voc: +16 synonyms
   - ✅ Enhanced power_metric.voc: +13 synonyms
   - ✅ Enhanced status_check.voc: +16 action verbs
   - ✅ Created time_range.voc: 26 time expressions
   - ✅ Created comparison_words.voc: 9 comparison keywords
   - ✅ Tested 5 new queries: 3 working (60%), 2 need time parsing
   - [ ] Enhance remaining .voc files (machine.voc, ranking.voc, etc.)

**Current Status:** 17/18 intents working, vocabulary coverage improved ~40%, time range parsing needed (Phase 2)

---

**Ready to execute Phase 1? Start with vocabulary expansion to cover 90% of documented queries with existing 18 handlers.**
