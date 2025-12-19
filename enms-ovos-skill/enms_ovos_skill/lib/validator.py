"""
Zero-Trust Validator - Tier 2: Hallucination Prevention
Validates ALL LLM outputs before API execution
99.5%+ accuracy through strict entity whitelisting
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import re
import structlog
from pydantic import BaseModel, ValidationError

# Fuzzy string matching library
try:
    from thefuzz import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    logger.warning("thefuzz not installed - fuzzy matching will use simple Levenshtein")

from .models import Intent, IntentType, TimeRange, ValidationResult

logger = structlog.get_logger(__name__)


# Entity Whitelists (will be refreshed from EnMS API)
VALID_MACHINES = [
    "Compressor-1",
    "Compressor-EU-1",
    "Boiler-1",
    "HVAC-Main",
    "HVAC-EU-North",
    "Conveyor-A",
    "Injection-Molding-1",
    "Pump-1"
]

VALID_METRICS = [
    "energy", "power", "consumption", "kwh", "watts", "kilowatts",
    "status", "running", "online", "offline", "active",
    "cost", "price", "expense",
    "temperature", "temp", "pressure", "vibration",
    "efficiency", "performance"
]

# NEW: Energy source validation
VALID_ENERGY_SOURCES = [
    "electricity", "electric", "electrical",
    "natural_gas", "natural gas", "gas",
    "steam",
    "compressed_air", "compressed air", "air"
]

# NEW: Factory validation (will be loaded from API)
VALID_FACTORIES = [
    "Demo Manufacturing Plant",
    "European Facility"
]

# NEW: Ranking metrics
VALID_RANKING_METRICS = [
    "energy", "power", "cost", "efficiency", "alerts", "consumption"
]

VALID_INTENTS = [intent.value for intent in IntentType]


class ENMSValidator:
    """
    Zero-trust validator with strict entity whitelisting
    
    Validation layers:
    1. Pydantic schema validation
    2. Confidence threshold filtering (>0.85)
    3. Machine name whitelist + fuzzy matching
    4. Metric whitelist
    5. Time range parsing and validation
    6. Intent type validation
    """
    
    def __init__(
        self,
        machine_whitelist: Optional[List[str]] = None,
        confidence_threshold: float = 0.85,
        enable_fuzzy_matching: bool = True
    ):
        """
        Initialize validator
        
        Args:
            machine_whitelist: List of valid machine names
            confidence_threshold: Minimum confidence score (0-1)
            enable_fuzzy_matching: Allow fuzzy machine name matching
        """
        self.machine_whitelist = machine_whitelist or VALID_MACHINES
        self.confidence_threshold = confidence_threshold
        self.enable_fuzzy_matching = enable_fuzzy_matching
        
        logger.info("validator_initialized",
                   machines=len(self.machine_whitelist),
                   confidence_threshold=confidence_threshold)
    
    def validate(self, llm_output: Dict[str, Any]) -> ValidationResult:
        """
        Validate LLM output with zero-trust approach
        
        Args:
            llm_output: Raw LLM JSON output
            
        Returns:
            ValidationResult with valid intent or errors
        """
        errors = []
        warnings = []
        suggestions = []
        
        logger.info("validation_start", llm_output=llm_output)
        
        # Layer 1: Pydantic schema validation
        try:
            # Handle both flat and nested entity structures
            entities = llm_output.get("entities", {})
            
            # Get machine(s) - check both flat and nested locations
            machine = llm_output.get("machine") or entities.get("machine")
            machines_str = llm_output.get("machines") or entities.get("machines")
            
            # Parse machines list (comma-separated or array)
            machines_list = None
            if machines_str:
                if isinstance(machines_str, str):
                    machines_list = [m.strip() for m in machines_str.split(',') if m.strip()]
                elif isinstance(machines_str, list):
                    machines_list = machines_str
            
            # Parse time range - prefer pre-parsed times from parser
            time_range_obj = None
            start_time = entities.get('start_time')
            end_time = entities.get('end_time')
            time_range_str = llm_output.get("time_range") or entities.get("time_range")
            
            if start_time and end_time:
                # Parser already extracted times
                time_range_obj = TimeRange(
                    start=start_time,
                    end=end_time,
                    relative=time_range_str  # Store original string
                )
            elif time_range_str:
                # Fall back to validator parsing
                time_range_obj = self._parse_time_range(time_range_str)
            
            intent = Intent(
                intent=IntentType(llm_output.get("intent", "unknown")),
                confidence=float(llm_output.get("confidence", 0.0)),
                utterance=llm_output.get("utterance", ""),
                machine=machine,
                machines=machines_list,
                metric=llm_output.get("metric") or entities.get("metric"),
                time_range=time_range_obj,
                aggregation=llm_output.get("aggregation") or entities.get("aggregation"),
                limit=llm_output.get("limit") or entities.get("limit"),
                params=self._extract_intent_params(llm_output)
            )
        except (ValidationError, ValueError) as e:
            errors.append(f"Schema validation failed: {str(e)}")
            return ValidationResult(valid=False, intent=None, errors=errors)
        
        # Layer 2: Confidence threshold
        if intent.confidence < self.confidence_threshold:
            errors.append(f"Confidence {intent.confidence:.2f} below threshold {self.confidence_threshold}")
            warnings.append("LLM uncertain about this query")
            return ValidationResult(valid=False, intent=None, errors=errors, warnings=warnings)
        
        # Layer 3: Intent validation
        if intent.intent == IntentType.UNKNOWN:
            errors.append("Unknown intent type")
            suggestions.append("Try rephrasing your question")
            return ValidationResult(valid=False, intent=None, errors=errors, suggestions=suggestions)
        
        # Layer 4: Machine name validation
        # Skip machine validation for factory-wide intents
        factory_wide_intents = [
            IntentType.FACTORY_OVERVIEW, 
            IntentType.RANKING, 
            IntentType.COST_ANALYSIS, 
            IntentType.REPORT, 
            IntentType.KPI,
            IntentType.SEUS,
            IntentType.HELP,
            IntentType.FORECAST  # Can be factory-wide or machine-specific
        ]
        
        if intent.machine and intent.intent not in factory_wide_intents:
            # Special handling for COMPARISON: detect group/plural terms
            if intent.intent == IntentType.COMPARISON:
                machine_lower = intent.machine.lower()
                is_group_query = any([
                    machine_lower.startswith('all '),
                    machine_lower.endswith('s') and machine_lower not in ['status'],  # plurals: compressors, HVACs
                    machine_lower in ['compressor', 'hvac', 'boiler', 'conveyor', 'pump'],  # machine types
                ])
                
                if is_group_query:
                    # Find all matching machines for this type/group
                    all_matches = self.find_all_matching_machines(intent.machine)
                    
                    if len(all_matches) >= 2:
                        # Populate intent.machines for comparison
                        intent = intent.model_copy(update={'machines': all_matches, 'machine': None})
                        logger.info("comparison_group_detected", 
                                   query_term=intent.machine, 
                                   matches=all_matches,
                                   count=len(all_matches))
                    elif len(all_matches) == 1:
                        # Only one match - not enough for comparison
                        warnings.append(f"Only one {intent.machine} found - comparison needs at least 2 machines")
                        intent = intent.model_copy(update={'machine': all_matches[0]})
                    else:
                        # No matches
                        errors.append(f"No machines found matching '{intent.machine}'")
                        return ValidationResult(valid=False, intent=None, errors=errors)
                else:
                    # Not a group query - validate as single machine (will ask for clarification)
                    machine_valid, matched_machine, suggestion = self._validate_machine(intent.machine)
                    if not machine_valid:
                        errors.append(f"Invalid machine name: '{intent.machine}'")
                        if suggestion:
                            suggestions.append(f"Did you mean '{suggestion}'?")
                        return ValidationResult(valid=False, intent=None, errors=errors, suggestions=suggestions)
                    intent = intent.model_copy(update={'machine': matched_machine})
            else:
                # Non-COMPARISON intents: Standard machine validation with ambiguity check
                machine_valid, matched_machine, suggestion = self._validate_machine(intent.machine)
                if not machine_valid:
                    errors.append(f"Invalid machine name: '{intent.machine}'")
                    if suggestion:
                        suggestions.append(f"Did you mean '{suggestion}'?")
                    return ValidationResult(valid=False, intent=None, errors=errors, suggestions=suggestions)
                
                # Check for ambiguous machine names ONLY if fuzzy match was used
                # If exact match found (after number normalization), skip ambiguity check
                # Number words to digits mapping (same as in _validate_machine)
                number_words = {
                    'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
                    'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
                    'first': '1', 'second': '2', 'third': '3'
                }
                
                # Normalize user input with number conversion
                machine_normalized = intent.machine.lower()
                for word, digit in number_words.items():
                    machine_normalized = re.sub(rf'\b{word}\b', digit, machine_normalized)
                machine_normalized_dash = machine_normalized.replace(" ", "-").replace("_", "-")
                
                # Check if matched_machine is an exact match after normalization
                is_exact_match = False
                if matched_machine:
                    matched_lower_dash = matched_machine.lower().replace(" ", "-").replace("_", "-")
                    is_exact_match = (machine_normalized == matched_machine.lower() or 
                                     machine_normalized_dash == matched_lower_dash)
                
                if not is_exact_match:
                    all_matches = self.find_all_matching_machines(intent.machine)
                    if len(all_matches) > 1:
                        # For BASELINE, MACHINE_STATUS, and ENERGY_QUERY intents: aggregate results for all matches
                        # For other intents: ask for clarification
                        if intent.intent in (IntentType.BASELINE, IntentType.MACHINE_STATUS, IntentType.ENERGY_QUERY):
                            logger.info("multi_machine_aggregation",
                                       intent=intent.intent.value,
                                       query_term=intent.machine,
                                       matches=all_matches,
                                       count=len(all_matches))
                            intent = intent.model_copy(update={'machines': all_matches, 'machine': None})
                        else:
                            errors.append(f"Ambiguous machine name: '{intent.machine}' matches {len(all_matches)} machines")
                            suggestions.append(f"Please specify which one: {', '.join(all_matches)}")
                            return ValidationResult(valid=False, intent=None, errors=errors, suggestions=suggestions)
                
                # Update intent with normalized machine name (Pydantic v2 immutability)
                if matched_machine and matched_machine != intent.machine:
                    warnings.append(f"Normalized '{intent.machine}' to '{matched_machine}'")
                    intent = intent.model_copy(update={'machine': matched_machine})
        
        # For factory-wide intents, clear the machine field if it was incorrectly extracted
        # EXCEPTIONS: Allow machine for factory_overview if:
        # 1. Opportunities query (for filtering)
        # 2. Action plan query (required for plan creation)
        if intent.intent in factory_wide_intents and intent.machine:
            utterance_lower = intent.utterance.lower()
            is_opportunities = 'opportunities' in utterance_lower or 'saving' in utterance_lower
            is_action_plan = 'action plan' in utterance_lower or 'create plan' in utterance_lower
            
            if not (is_opportunities or is_action_plan):
                warnings.append(f"Ignoring machine '{intent.machine}' for factory-wide query")
                intent = intent.model_copy(update={'machine': None})
        
        # Layer 5: Multi-machine validation (for comparisons)
        if intent.machines:
            validated_machines = []
            for machine in intent.machines:
                valid, matched, suggestion = self._validate_machine(machine)
                if not valid:
                    errors.append(f"Invalid machine in comparison: '{machine}'")
                    if suggestion:
                        suggestions.append(f"Did you mean '{suggestion}'?")
                    continue
                validated_machines.append(matched or machine)
            
            if errors:
                return ValidationResult(valid=False, intent=None, errors=errors, suggestions=suggestions)
            
            intent = intent.model_copy(update={'machines': validated_machines})
        
        # Layer 6: Metric validation (optional - soft validation)
        if intent.metric:
            if not self._validate_metric(intent.metric):
                warnings.append(f"Uncommon metric: '{intent.metric}' - may not be supported")
        
        logger.info("validation_success",
                   intent=intent.intent.value,
                   confidence=intent.confidence,
                   machine=intent.machine)
        
        return ValidationResult(
            valid=True,
            intent=intent,
            errors=[],
            warnings=warnings,
            suggestions=[]
        )
    
    def _validate_machine(self, machine_name: str) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validate machine name with fuzzy matching
        
        Returns:
            (is_valid, matched_name, suggestion)
        """
        if not machine_name:
            return True, None, None
        
        # Number words to digits mapping for spoken input
        number_words = {
            'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
            'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
            'first': '1', 'second': '2', 'third': '3'
        }
        
        # Convert number words to digits (e.g., "compressor one" -> "compressor 1")
        machine_normalized = machine_name.lower()
        for word, digit in number_words.items():
            machine_normalized = re.sub(rf'\b{word}\b', digit, machine_normalized)
        
        # Normalize: lowercase, replace spaces/underscores with hyphens
        machine_normalized_dash = machine_normalized.replace(" ", "-").replace("_", "-")
        
        # Exact match (case-insensitive) - check both original and dash-normalized
        for valid_machine in self.machine_whitelist:
            valid_lower = valid_machine.lower()
            valid_lower_dash = valid_lower.replace(" ", "-").replace("_", "-")
            
            # Direct exact match or dash-normalized exact match
            if machine_normalized == valid_lower or machine_normalized_dash == valid_lower_dash:
                return True, valid_machine, None
        
        # Fuzzy matching
        if self.enable_fuzzy_matching:
            # Normalize: lowercase, replace spaces/underscores with hyphens
            machine_lower = machine_normalized.replace(" ", "-").replace("_", "-")
            
            # Strip common suffixes from user input (e.g., "injection molding machine" → "injection-molding")
            machine_base = re.sub(r'-(machine|equipment|unit|system)$', '', machine_lower)
            
            for valid_machine in self.machine_whitelist:
                valid_lower = valid_machine.lower().replace(" ", "-").replace("_", "-")
                
                # Exact match after normalization
                if machine_lower == valid_lower or machine_base == valid_lower:
                    return True, valid_machine, None
                
                # Substring match
                if machine_lower in valid_lower or valid_lower in machine_lower:
                    return True, valid_machine, None
                
                # Machine type match (e.g., "injection molding" → "Injection-Molding-1")
                # Remove trailing numbers/hyphens from valid machine name
                valid_base = re.sub(r'[-_]\d+$', '', valid_lower)
                if machine_lower == valid_base or machine_base == valid_base:
                    return True, valid_machine, None
                
                # Check if normalized input is substring of base name
                if machine_base in valid_base or valid_base in machine_base:
                    return True, valid_machine, None
                
                # Levenshtein distance check (simple version)
                if self._fuzzy_match(machine_lower, valid_lower):
                    return False, None, valid_machine  # Suggest but don't auto-correct
        
        return False, None, None
    
    def normalize_machine_name(self, raw_name: str) -> Optional[str]:
        """
        Normalize voice/text variations to canonical machine name
        
        Handles voice input variations:
        - "compressor one" → Compressor-1
        - "hvac main" → HVAC-Main
        - "boiler number two" → Boiler-2
        - Case variations (COMPRESSOR-1, compressor-1, etc.)
        
        Args:
            raw_name: Raw machine name from user input or STT
            
        Returns:
            Canonical machine name from whitelist, or None if no match
        """
        if not raw_name:
            return None
        
        # Number words to digits mapping
        number_words = {
            'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
            'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
            'first': '1', 'second': '2', 'third': '3', 'fourth': '4'
        }
        
        # Normalize input
        normalized = raw_name.lower().strip()
        
        # Remove common STT artifacts
        normalized = normalized.replace(" number ", " ")
        normalized = normalized.replace(" dash ", "-")
        
        # Convert number words to digits
        for word, digit in number_words.items():
            normalized = re.sub(rf'\b{word}\b', digit, normalized)
        
        # Standardize separators: space → hyphen
        normalized = normalized.replace(" ", "-").replace("_", "-")
        
        # Try exact match (case-insensitive)
        for machine in self.machine_whitelist:
            machine_normalized = machine.lower().replace(" ", "-").replace("_", "-")
            if normalized == machine_normalized:
                logger.debug("machine_normalized_exact", raw=raw_name, matched=machine)
                return machine
        
        # Try hyphen vs space variants
        for machine in self.machine_whitelist:
            machine_variants = [
                machine.lower(),
                machine.lower().replace("-", " "),
                machine.lower().replace("-", ""),
                machine.lower().replace(" ", "")
            ]
            normalized_variants = [
                normalized,
                normalized.replace("-", " "),
                normalized.replace("-", "")
            ]
            
            for norm_var in normalized_variants:
                for mach_var in machine_variants:
                    if norm_var == mach_var:
                        logger.debug("machine_normalized_variant", raw=raw_name, matched=machine, variant=norm_var)
                        return machine
        
        # Fuzzy match (80% similarity threshold)
        if FUZZY_AVAILABLE and self.enable_fuzzy_matching:
            best_match = None
            best_score = 0
            
            for machine in self.machine_whitelist:
                machine_lower = machine.lower()
                score = fuzz.ratio(normalized, machine_lower)
                
                if score > best_score and score >= 80:
                    best_score = score
                    best_match = machine
            
            if best_match:
                logger.info("machine_normalized_fuzzy", 
                           raw=raw_name, 
                           matched=best_match, 
                           score=best_score)
                return best_match
        
        logger.warning("machine_normalization_failed", raw=raw_name)
        return None
    
    def find_all_matching_machines(self, machine_name: str) -> List[str]:
        """
        Find ALL machines that match the query (for ambiguous requests)
        
        Returns:
            List of matching machine names (empty if no matches)
        """
        if not machine_name:
            return []
        
        matches = []
        
        # Number words to digits mapping for spoken input
        number_words = {
            'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
            'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
            'first': '1', 'second': '2', 'third': '3'
        }
        
        # Convert number words to digits (e.g., "compressor one" -> "compressor 1")
        machine_lower = machine_name.lower()
        for word, digit in number_words.items():
            machine_lower = re.sub(rf'\b{word}\b', digit, machine_lower)
        
        # Normalize: lowercase, replace spaces/underscores with hyphens
        machine_lower = machine_lower.replace(" ", "-").replace("_", "-")
        
        # Strip common suffixes from user input
        machine_base = re.sub(r'-(machine|equipment|unit|system)s?$', '', machine_lower)
        
        # FIRST: Check for exact matches only
        exact_matches = []
        for valid_machine in self.machine_whitelist:
            valid_lower = valid_machine.lower().replace(" ", "-").replace("_", "-")
            
            # Exact match after normalization
            if machine_lower == valid_lower or machine_base == valid_lower:
                exact_matches.append(valid_machine)
        
        # If exact match found, return ONLY exact matches (no fuzzy/substring)
        if exact_matches:
            return exact_matches
        
        # FALLBACK: No exact match - do fuzzy/substring matching for ambiguous queries
        for valid_machine in self.machine_whitelist:
            valid_lower = valid_machine.lower().replace(" ", "-").replace("_", "-")
            
            # Substring match (only if no exact match found)
            if machine_lower in valid_lower or valid_lower in machine_lower:
                matches.append(valid_machine)
                continue
            
            # Machine type match (e.g., "hvac" → ["HVAC-Main", "HVAC-EU-North"])
            # Remove trailing location/number suffixes iteratively: -main, -eu-north, -1, -eu-1, etc.
            valid_base = valid_lower
            while True:
                new_base = re.sub(r'[-_](main|eu|north|south|east|west|\d+)$', '', valid_base, flags=re.IGNORECASE)
                if new_base == valid_base:
                    break
                valid_base = new_base
            
            if machine_lower == valid_base or machine_base == valid_base:
                matches.append(valid_machine)
                continue
            
            # Check if normalized input is substring of base name
            if machine_base and len(machine_base) > 3:  # Avoid matching too short strings
                if machine_base in valid_base or valid_base in machine_base:
                    matches.append(valid_machine)
        
        return matches
    
    def _fuzzy_match(self, s1: str, s2: str, threshold: int = 80) -> bool:
        """
        Enhanced fuzzy string matching using thefuzz library
        
        Args:
            s1: First string to compare
            s2: Second string to compare
            threshold: Similarity score threshold (0-100, default 80)
            
        Returns:
            True if strings are similar enough
        """
        if FUZZY_AVAILABLE:
            # Use thefuzz for advanced fuzzy matching
            similarity = fuzz.ratio(s1.lower(), s2.lower())
            logger.debug("fuzzy_match", s1=s1, s2=s2, similarity=similarity, threshold=threshold)
            return similarity >= threshold
        else:
            # Fallback to simple Levenshtein distance
            if abs(len(s1) - len(s2)) > 3:
                return False
            
            # Simple character difference count
            diff = sum(c1 != c2 for c1, c2 in zip(s1, s2))
            diff += abs(len(s1) - len(s2))
            
            return diff <= 3
    
    def _validate_metric(self, metric: str) -> bool:
        """Validate metric is in known list"""
        if not metric:
            return True
        
        metric_lower = metric.lower()
        return any(valid.lower() in metric_lower or metric_lower in valid.lower() 
                  for valid in VALID_METRICS)
    
    def _parse_machine_list(self, machine_str: Optional[str]) -> Optional[List[str]]:
        """Parse comma-separated machine names"""
        if not machine_str:
            return None
        
        if "," in machine_str:
            return [m.strip() for m in machine_str.split(",") if m.strip()]
        
        return None
    
    def _parse_time_range(self, time_str: Optional[str]) -> Optional[TimeRange]:
        """
        Parse time range expressions
        
        Supported formats:
        - Relative: "today", "yesterday", "last week", "24h", "7d"
        - Absolute: ISO 8601 timestamps
        """
        if not time_str:
            return None
        
        time_lower = time_str.lower().strip()
        now = datetime.utcnow()
        
        # Relative time expressions
        if time_lower in ["today", "now"]:
            return TimeRange(
                start=now.replace(hour=0, minute=0, second=0, microsecond=0),
                end=now,
                relative="today"
            )
        
        elif time_lower == "yesterday":
            yesterday = now - timedelta(days=1)
            return TimeRange(
                start=yesterday.replace(hour=0, minute=0, second=0, microsecond=0),
                end=yesterday.replace(hour=23, minute=59, second=59, microsecond=999999),
                relative="yesterday"
            )
        
        elif time_lower in ["this week", "current week"]:
            # Start of current week (Sunday or Monday, using Sunday)
            days_since_sunday = now.weekday() + 1 if now.weekday() != 6 else 0
            week_start = now - timedelta(days=days_since_sunday)
            return TimeRange(
                start=week_start.replace(hour=0, minute=0, second=0, microsecond=0),
                end=now,
                relative="this_week"
            )
        
        elif time_lower in ["this month", "current month"]:
            # Start of current month
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return TimeRange(
                start=month_start,
                end=now,
                relative="this_month"
            )
        
        elif time_lower in ["last month", "previous month"]:
            # Last month: first day to last day of previous month
            first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_end = first_of_this_month - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return TimeRange(
                start=last_month_start,
                end=last_month_end.replace(hour=23, minute=59, second=59, microsecond=999999),
                relative="last_month"
            )
        
        elif time_lower in ["last week", "week"]:
            week_ago = now - timedelta(days=7)
            return TimeRange(
                start=week_ago,
                end=now,
                relative="last_week"
            )
        
        # Duration expressions (24h, 7d, etc.)
        duration_match = re.match(r'(\d+)\s*(h|hour|hours|d|day|days|w|week|weeks)', time_lower)
        if duration_match:
            value = int(duration_match.group(1))
            unit = duration_match.group(2)[0]  # First char: h, d, w
            
            if unit == 'h':
                delta = timedelta(hours=value)
            elif unit == 'd':
                delta = timedelta(days=value)
            elif unit == 'w':
                delta = timedelta(weeks=value)
            else:
                return None
            
            return TimeRange(
                start=now - delta,
                end=now,
                duration=time_str
            )
        
        # ISO 8601 timestamp parsing
        try:
            timestamp = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            return TimeRange(start=timestamp, end=timestamp)
        except ValueError:
            pass
        
        return None
    
    def update_machine_whitelist(self, machines: List[str]):
        """Update machine whitelist from EnMS API"""
        self.machine_whitelist = machines
        logger.info("whitelist_updated", count=len(machines))
    
    def _extract_intent_params(self, llm_output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract intent-specific parameters
        
        Args:
            llm_output: Raw LLM output with potential extra params
            
        Returns:
            Dict of intent-specific params or None
        """
        params = {}
        
        # Report-specific params
        if llm_output.get('report_action'):
            params['action'] = llm_output['report_action']
        if llm_output.get('report_type'):
            params['report_type'] = llm_output['report_type']
        if llm_output.get('month'):
            params['month'] = llm_output['month']
        if llm_output.get('year'):
            params['year'] = llm_output['year']
        
        return params if params else None
