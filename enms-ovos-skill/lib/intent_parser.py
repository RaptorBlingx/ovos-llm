"""
Hybrid Intent Parser for ENMS OVOS Skill
========================================

Multi-tier adaptive routing:
- Tier 1 (Heuristic): Ultra-fast regex patterns (<5ms)
- Tier 2 (Adapt): Fast pattern matching (<10ms) [future]
- Tier 3 (LLM): Complex NLU with Qwen3 (300-500ms)

Goal: Route 80% of queries via Tier 1+2 (<10ms) for <200ms P50 latency
"""

import re
import time
from typing import Dict, Optional, List, Tuple
from enum import Enum

import structlog

from lib.models import Intent, IntentType
from lib.qwen3_parser import Qwen3Parser
from lib.adapt_parser import AdaptParser
from lib.time_parser import TimeRangeParser
from lib.observability import (
    tier_routing,
    query_latency,
    queries_total,
    active_queries
)

logger = structlog.get_logger()


class RoutingTier(str, Enum):
    """Which parser tier handled the query"""
    HEURISTIC = "heuristic"
    ADAPT = "adapt"
    LLM = "llm"


class HeuristicRouter:
    """
    Tier 1: Ultra-fast regex-based intent detection
    
    Handles:
    - "top N" queries → ranking
    - "top N machines" → ranking
    - "factory overview" → factory_overview
    - "factory status" → factory_overview
    - "total kwh" → factory_overview
    - "{machine} status" → machine_status
    - "{machine} power" → power_query
    - "{machine} kwh" → energy_query
    - "{machine} energy" → energy_query
    - "compare {machine1} and {machine2}" → comparison
    """
    
    # Known machine names (loaded from validator)
    MACHINES = [
        "Boiler-1", "Compressor-1", "Compressor-EU-1", "Conveyor-A",
        "HVAC-EU-North", "HVAC-Main", "Injection-Molding-1", "Turbine-1"
    ]
    
    # Regex patterns (compiled for speed)
    # CRITICAL: Order matters! More specific patterns first
    PATTERNS = {
        # NEW: Production queries (units, quality, OEE)
        'production': [
            re.compile(r'\bhow\s+many\s+units', re.IGNORECASE),
            re.compile(r'\bunits?\s+(?:produced|made|manufactured)', re.IGNORECASE),
            re.compile(r'\bproduction\s+(?:count|total|volume)', re.IGNORECASE),
            re.compile(r'\bquality\s+(?:rate|percent|percentage)', re.IGNORECASE),
            re.compile(r'\bOEE\b', re.IGNORECASE),
            re.compile(r'\boverall\s+equipment\s+effectiveness', re.IGNORECASE),
        ],
        
        # Anomaly detection
        'anomaly_detection': [
            re.compile(r'\b(?:show|list|get|display).*?anomal(?:y|ies)', re.IGNORECASE),
            re.compile(r'\banomal(?:y|ies).*?(?:show|list|get)', re.IGNORECASE),
            re.compile(r'\bactive\s+(?:anomal(?:y|ies)|alerts?)', re.IGNORECASE),
            re.compile(r'\b(?:critical|warning|info)\s+anomal(?:y|ies)', re.IGNORECASE),
            re.compile(r'\bcheck\s+for\s+anomal(?:y|ies)', re.IGNORECASE),
            re.compile(r'\bdetect\s+anomal(?:y|ies)', re.IGNORECASE),
            re.compile(r'\b(?:any|are there)\s+anomal(?:y|ies)', re.IGNORECASE),
            # NEW: Which machines have anomalies
            re.compile(r'\b(?:which|what).*?machines?.*?(?:anomal|alert|issue|problem)', re.IGNORECASE),
            re.compile(r'\bmachines?.*?(?:have|with|has).*?(?:anomal|alert)', re.IGNORECASE),
        ],
        
        # NEW: Baseline prediction (expected/predicted energy)
        'baseline_models': [
            re.compile(r'\b(?:list|show|get).*?baseline\s+models?', re.IGNORECASE),
            re.compile(r'\bbaseline\s+models?\s+(?:for|exist|available)', re.IGNORECASE),
            re.compile(r'\bwhat\s+baseline\s+models?', re.IGNORECASE),
            re.compile(r'\bhistory\s+of.*?baseline\s+models?', re.IGNORECASE),
        ],
        
        'kpi': [
            re.compile(r'\bKPIs?\b', re.IGNORECASE),
            re.compile(r'\bkey\s+performance\s+indicators?', re.IGNORECASE),
            re.compile(r'\b(?:show|get|what).*?KPIs?\b', re.IGNORECASE),
            re.compile(r'\b(?:energy\s+efficiency|load\s+factor|peak\s+demand|carbon\s+intensity)', re.IGNORECASE),
            re.compile(r'\bspecific\s+energy\s+consumption', re.IGNORECASE),
        ],
        
        'performance': [
            re.compile(r'\banalyze\s+performance', re.IGNORECASE),
            re.compile(r'\banalyze\s+\w+.*?performance', re.IGNORECASE),
            re.compile(r'\bperformance\s+(?:analysis|of|for)', re.IGNORECASE),
            re.compile(r'\b(?:efficiency|performance)\s+(?:score|rating|status)', re.IGNORECASE),
            re.compile(r'\bhow.*?performing', re.IGNORECASE),
            re.compile(r'\broot\s+cause', re.IGNORECASE),
        ],
        
        'baseline': [
            re.compile(r'\b(?:expected|predicted)\s+(?:energy|power|consumption)', re.IGNORECASE),
            re.compile(r'\bpredict.*?(?:energy|power|consumption)', re.IGNORECASE),
            re.compile(r'\bbaseline\s+prediction', re.IGNORECASE),
            re.compile(r'\bbaseline\s+for\s+({})'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\b(?:what|get|give|show).*?baseline\s+(?:for|of)', re.IGNORECASE),
            re.compile(r'\benergy\s+(?:with|at)\s+(?:temp|temperature|pressure|load)', re.IGNORECASE),
        ],
        
        # Baseline models (list models for a machine)
        'baseline_models': [
            re.compile(r'\blist.*?baseline.*?models?', re.IGNORECASE),
            re.compile(r'\bbaseline.*?models?.*?(?:for|of)', re.IGNORECASE),
            re.compile(r'\b(?:does|do|has|have).*?baseline.*?model', re.IGNORECASE),
            re.compile(r'\bhow\s+many.*?baseline.*?models?', re.IGNORECASE),
            re.compile(r'\bshow.*?baseline.*?models?', re.IGNORECASE),
        ],
        
        # Baseline explanation (key drivers, model accuracy)
        'baseline_explanation': [
            re.compile(r'\bkey\s+energy\s+drivers?', re.IGNORECASE),
            re.compile(r'\bexplain.*?(?:baseline|model)', re.IGNORECASE),
            re.compile(r'\bhow\s+accurate.*?(?:model|baseline)', re.IGNORECASE),
            re.compile(r'\btell\s+me\s+about.*?(?:baseline|model)', re.IGNORECASE),
            re.compile(r'\bwhat\s+(?:drives?|affects?|impacts?).*?energy', re.IGNORECASE),
            re.compile(r'\bmodel\s+(?:details?|info|explanation)', re.IGNORECASE),
        ],
        
        # NEW: Forecast (future prediction)
        'forecast': [
            re.compile(r'\b(?:forecast|tomorrow|next\s+(?:day|week|month))', re.IGNORECASE),
            re.compile(r'\bwhat.*?(?:will|going\s+to)\s+(?:consume|use)', re.IGNORECASE),
            re.compile(r'\bpeak\s+demand.*?(?:tomorrow|next)', re.IGNORECASE),
        ],
        
        # Top N ranking queries (CRITICAL: handle "top 3", "top 5 machines", etc.)
        'ranking': [
            re.compile(r'\btop\s+(\d+)\s*(?:machines?|consumers?)?\b', re.IGNORECASE),
            re.compile(r'\bshow\s+(?:me\s+)?(?:the\s+)?top\s+(\d+)', re.IGNORECASE),
            re.compile(r'\b(\d+)\s+top\s+(?:machines?|consumers?)', re.IGNORECASE),
            # NEW: Efficiency/cost ranking (which machine = ranking, not machine extraction)
            re.compile(r'\brank.*?by\s+(?:efficiency|cost)', re.IGNORECASE),
            re.compile(r'\bwhich\s+machine.*?most\s+(?:efficient|cost-effective)', re.IGNORECASE),
            re.compile(r'\bwhich\s+machine.*?(?:uses?|consumes?)\s+(?:the\s+)?most', re.IGNORECASE),
            re.compile(r'\bwhich\s+machine.*?(?:has|have)\s+(?:the\s+)?most\s+alerts', re.IGNORECASE),
            # NEW: Least/lowest ranking
            re.compile(r'\bwhich\s+machine.*?(?:uses?|consumes?)\s+(?:the\s+)?least', re.IGNORECASE),
            re.compile(r'\bwhich\s+machine.*?(?:lowest|minimum)', re.IGNORECASE),
            # NEW: Which/what {type} units/machines
            re.compile(r'\b(?:which|what)\s+(HVAC|Boiler|Compressor|Conveyor|Turbine|Hydraulic|Injection)\s+(?:units?|machines?)', re.IGNORECASE),
            re.compile(r'\bfind.*?(HVAC|Boiler|Compressor|Conveyor|Turbine|Hydraulic|Injection)', re.IGNORECASE),
            # NEW: List machines (moved from factory_overview)
            re.compile(r'\blist\s+(?:all\s+)?machines', re.IGNORECASE),
            re.compile(r'\bshow\s+(?:me\s+)?(?:all\s+)?machines', re.IGNORECASE),
            re.compile(r'\bwhat\s+machines\s+(?:do\s+we\s+have|are\s+there)', re.IGNORECASE),
            # NEW: How many {type} machines
            re.compile(r'\bhow\s+many\s+(HVAC|Boiler|Compressor|Conveyor|Turbine|Hydraulic|Injection)', re.IGNORECASE),
        ],
        
        # Factory-wide queries
        'factory_overview': [
            re.compile(r'\bfactory\s+(?:overview|status|summary)\b', re.IGNORECASE),
            re.compile(r'\btotal\s+(?:factory\s+)?(?:kwh|consumption|energy|power)\b', re.IGNORECASE),
            re.compile(r'\b(?:complete|full)\s+factory\b', re.IGNORECASE),
            re.compile(r'\bfacility\s+(?:overview|status)\b', re.IGNORECASE),
            # NEW: Carbon/emissions queries
            re.compile(r'\bcarbon\s+(?:footprint|emissions?)\b', re.IGNORECASE),
            re.compile(r'\b(?:what|how\s+much).*?carbon\b', re.IGNORECASE),
            re.compile(r'\bCO2\s+emissions?\b', re.IGNORECASE),
            re.compile(r'\bemissions?\s+(?:total|today)\b', re.IGNORECASE),
            # NEW: Significant Energy Uses (SEUs)
            re.compile(r'\bsignificant\s+energy\s+uses?\b', re.IGNORECASE),
            re.compile(r'\blist\s+(?:all\s+)?seus?\b', re.IGNORECASE),
            re.compile(r'\benergy\s+uses\b', re.IGNORECASE),
            # NEW: SEU baseline queries (with typo tolerance)
            re.compile(r'\bwhich\s+seu.*?(?:have|has|with|without).*?baselines?', re.IGNORECASE),
            re.compile(r'\bwhich\s+seu.*?(?:have|has|with|without).*?baslines?', re.IGNORECASE),  # typo: missing 'e'
            re.compile(r'\bseu.*?(?:don\'t|do not|doesn\'t|does not|no|without).*?baselines?', re.IGNORECASE),
            re.compile(r'\bseu.*?(?:don\'t|do not|doesn\'t|does not|no|without).*?baslines?', re.IGNORECASE),  # typo
            re.compile(r'\bseu.*?(?:need|require|missing).*?baselines?', re.IGNORECASE),
            re.compile(r'\bseu.*?(?:need|require|missing).*?baslines?', re.IGNORECASE),  # typo
            # NEW: Active/offline machine queries
            re.compile(r'\b(?:show|list|what).*?(?:active|online|running).*?(?:machines?|equipment)', re.IGNORECASE),
            re.compile(r'\b(?:show|list|what).*?(?:inactive|offline|stopped).*?(?:machines?|equipment)', re.IGNORECASE),
            # NEW: Aggregated stats
            re.compile(r'\baggregated?\s+(?:stats?|statistics?)', re.IGNORECASE),
            # NEW: Multi-factory comparison
            re.compile(r'\bcompare.*?(?:across|all)\s+factories', re.IGNORECASE),
            re.compile(r'\bwhich\s+factory', re.IGNORECASE),
            # NEW: Performance engine health
            re.compile(r'\bperformance\s+engine', re.IGNORECASE),
            re.compile(r'\bengine\s+(?:health|status|running)', re.IGNORECASE),
            # NEW: Energy saving opportunities
            re.compile(r'\bsaving\s+opportunities', re.IGNORECASE),
            re.compile(r'\benergy\s+saving', re.IGNORECASE),
            re.compile(r'\bimprovement\s+opportunities', re.IGNORECASE),
            re.compile(r'\bopportunities', re.IGNORECASE),
            # NEW: ISO 50001 EnPI reports
            re.compile(r'\benpi\s+report', re.IGNORECASE),
            re.compile(r'\benergy\s+performance\s+indicators?', re.IGNORECASE),
            re.compile(r'\biso\s*50001', re.IGNORECASE),
            re.compile(r'\bcompliance\s+report', re.IGNORECASE),
            # NEW: ISO action plans
            re.compile(r'\blist.*?action\s+plans?', re.IGNORECASE),
            re.compile(r'\baction\s+plans?.*?list', re.IGNORECASE),
            re.compile(r'\biso\s+action\s+plans?', re.IGNORECASE),
        ],
        
        # Machine status queries
        'machine_status': [
            re.compile(r'\b({})\s+(?:status|online|offline|running|availability)\b'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\b(?:is|check)\s+({})\s*(?:running|online|offline)?\b'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\b({})\s+availability\b'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            # NEW: Show/get info/details for machine
            re.compile(r'\b(?:show|get|display)\s+(?:info|details|information)\s+(?:for|about)\s+({})'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\b({})(?:\s+info|\s+details|\s+information)\b'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
        ],
        
        # Power queries
        'power_query': [
            re.compile(r'\b({})\s+(?:power|watts?|kw)\b'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\bpower\s+(?:of\s+)?({})'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            # Handle short forms like "HVAC watts" (extract HVAC from HVAC-EU-North)
            re.compile(r'\b(HVAC|Boiler|Compressor|Conveyor|Turbine|Injection)[^\s]*\s+(?:power|watts?|kw)\b', re.IGNORECASE),
            # NEW: Steam flow rate (technically power query for steam)
            re.compile(r'\bsteam\s+flow\s+rate', re.IGNORECASE),
        ],
        
        # Energy queries
        'energy_query': [
            re.compile(r'\b({})\s+(?:energy|kwh|consumption)\b'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\benergy\s+(?:of\s+)?({})'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\b({})\s+(?:used|consumed)'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            # NEW: Multi-energy support (moved from machine_status)
            re.compile(r'\benergy\s+(?:types?|sources?)\s+(?:does|for)\s+({})'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\blist.*?energy\s+sources?\s+for\s+({})'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\bwhat\s+energy.*?({})'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\b(?:what|which)\s+energy\s+(?:types?|sources?)', re.IGNORECASE),
            re.compile(r'\benergy\s+types?\s+(?:does|for)', re.IGNORECASE),
            re.compile(r'\benergy\s+summary', re.IGNORECASE),
            re.compile(r'\b(?:natural\s+gas|electricity|steam|compressed\s+air)\s+(?:consumption|usage|readings?)', re.IGNORECASE),
            re.compile(r'\bshow.*?(?:natural\s+gas|steam|electricity|compressed\s+air)', re.IGNORECASE),
            # NEW: Energy breakdown
            re.compile(r'\benergy\s+breakdown', re.IGNORECASE),
            re.compile(r'\bsummarize.*?energy.*?consumption', re.IGNORECASE),
            re.compile(r'\btotal\s+energy\s+usage', re.IGNORECASE),
        ],
        
        # Comparison queries
        'comparison': [
            re.compile(r'\bcompare\s+.*?(?:between\s+)?({}).*?(?:and|vs|versus)\s+({})'.format(
                '|'.join(re.escape(m) for m in MACHINES),
                '|'.join(re.escape(m) for m in MACHINES)
            ), re.IGNORECASE),
            re.compile(r'\b({})\s+vs\s+({})'.format(
                '|'.join(re.escape(m) for m in MACHINES),
                '|'.join(re.escape(m) for m in MACHINES)
            ), re.IGNORECASE),
            # NEW: Performance comparison
            re.compile(r'\bcompare.*?performance', re.IGNORECASE),
        ],
    }
    
    def __init__(self):
        """Initialize heuristic router"""
        self.logger = logger.bind(component="heuristic_router")
    
    def _extract_machine_fuzzy(self, utterance: str) -> Optional[str]:
        """
        Extract machine name with fuzzy matching
        
        Handles partial matches like "hvac" → "hvac-main" or "hvac-eu-north"
        Returns first match OR None if ambiguous (validator will clarify)
        
        Args:
            utterance: User query
            
        Returns:
            Matched machine name or first match from ambiguous set
        """
        utterance_lower = utterance.lower()
        
        # Try exact match first (full machine name in query)
        for m in self.MACHINES:
            if m.lower() in utterance_lower:
                return m
        
        # Try partial match (machine type without suffix)
        # E.g., "hvac" should match "HVAC-Main", "HVAC-EU-North"
        machine_types = {
            'hvac': ['HVAC-Main', 'HVAC-EU-North'],
            'compressor': ['Compressor-1', 'Compressor-EU-1'],
            'boiler': ['Boiler-1'],
            'conveyor': ['Conveyor-A'],
            'pump': ['Hydraulic-Pump-1'],
            'injection': ['Injection-Molding-1'],
        }
        
        for machine_type, machines in machine_types.items():
            if machine_type in utterance_lower:
                # Find all matches in whitelist
                matches = [m for m in machines if m in self.MACHINES]
                if matches:
                    # Return special marker for validator to detect ambiguity
                    # Use machine type as placeholder (e.g., "hvac")
                    if len(matches) > 1:
                        return machine_type  # Validator will detect this is ambiguous
                    return matches[0]
        
        return None
    
    def route(self, utterance: str) -> Optional[Dict]:
        """
        Attempt to parse utterance using fast heuristics
        
        Args:
            utterance: User query string
            
        Returns:
            Parsed intent dict or None if no pattern matched
        """
        start_time = time.time()
        
        # Normalize utterance
        normalized = utterance.strip()
        utterance_lower = normalized.lower()
        
        # Special case: ISO queries should use factory_overview, not performance
        # This prevents "ISO performance" from matching performance intent
        iso_query = 'iso' in utterance_lower or 'enpi' in utterance_lower or 'compliance report' in utterance_lower
        
        # Try each pattern category
        for intent_type, patterns in self.PATTERNS.items():
            # Skip performance if this is an ISO query
            if intent_type == 'performance' and iso_query:
                continue
                
            for pattern in patterns:
                match = pattern.search(normalized)
                if match:
                    result = self._build_intent(intent_type, match, normalized)
                    if result:
                        latency_ms = (time.time() - start_time) * 1000
                        self.logger.info(
                            "heuristic_match",
                            intent=intent_type,
                            pattern=pattern.pattern[:50],
                            latency_ms=latency_ms
                        )
                        query_latency.labels(intent_type=intent_type, tier="heuristic").observe(latency_ms / 1000)
                        return result
        
        # No pattern matched
        latency_ms = (time.time() - start_time) * 1000
        self.logger.debug("heuristic_no_match", utterance=normalized, latency_ms=latency_ms)
        return None
    
    def _build_intent(self, intent_type: str, match: re.Match, utterance: str) -> Optional[Dict]:
        """
        Build intent dictionary from regex match
        
        CRITICAL: Returns LLM-compatible format (string intent, flat structure)
        This ensures validator compatibility across all tiers
        """
        try:
            if intent_type == 'ranking':
                # Extract N from "top N" if present
                limit = None
                try:
                    limit = int(match.group(1))
                except (IndexError, ValueError):
                    # Check if this is a machine listing query vs top-N ranking
                    utterance_lower = utterance.lower()
                    
                    # Machine listing patterns: "which HVAC units", "find compressors", "how many", "list machines"
                    is_listing = any([
                        re.search(r'\b(?:which|what)\s+(HVAC|Boiler|Compressor|Conveyor|Turbine|Hydraulic|Injection)', utterance_lower),
                        'find' in utterance_lower and any(t in utterance_lower for t in ['hvac', 'boiler', 'compressor', 'conveyor']),
                        'how many' in utterance_lower,
                        'list' in utterance_lower and 'machine' in utterance_lower,
                    ])
                    
                    # Top-N ranking patterns: "which machine uses most", "which machine has most alerts"
                    is_ranking = any([
                        'most' in utterance_lower,
                        'least' in utterance_lower,
                        'highest' in utterance_lower,
                        'lowest' in utterance_lower,
                    ])
                    
                    if is_listing and not is_ranking:
                        limit = None  # Machine listing query
                    else:
                        limit = 1 if is_ranking else 5  # Top-N ranking (1 for "which uses most", 5 for others)
                
                # Determine ranking metric from query
                metric = 'energy'  # default
                utterance_lower = utterance.lower()
                if 'efficiency' in utterance_lower or 'efficient' in utterance_lower:
                    metric = 'efficiency'
                elif 'cost' in utterance_lower:
                    metric = 'cost'
                elif 'alert' in utterance_lower:
                    metric = 'alerts'
                
                # For machine listing queries, set metric to None
                is_listing_final = limit is None or (limit == 1 and not any(word in utterance_lower for word in ['most', 'least', 'highest', 'lowest']))
                if is_listing_final and any(word in utterance_lower for word in ['which', 'what', 'find', 'list', 'how many']):
                    metric = None
                
                return {
                    'intent': 'ranking',
                    'confidence': 0.95,
                    'limit': limit,
                    'metric': metric,
                    'ranking_metric': metric  # NEW: explicit ranking metric
                }
            
            elif intent_type == 'baseline_models':
                # List baseline models - requires machine name
                machine = self._extract_machine_fuzzy(utterance)
                
                return {
                    'intent': 'baseline_models',
                    'confidence': 0.95,
                    'machine': machine
                }
            
            elif intent_type == 'baseline_explanation':
                # Explain baseline model (key drivers, accuracy) - requires machine name
                machine = self._extract_machine_fuzzy(utterance)
                
                return {
                    'intent': 'baseline_explanation',
                    'confidence': 0.95,
                    'machine': machine
                }
            
            elif intent_type == 'kpi':
                # KPI queries - extract machine name
                machine = None
                utterance_lower = utterance.lower()
                for m in self.MACHINES:
                    if m.lower() in utterance_lower:
                        machine = m
                        break
                
                return {
                    'intent': 'kpi',
                    'confidence': 0.95,
                    'machine': machine
                }
            
            elif intent_type == 'performance':
                # Performance analysis - extract machine name
                machine = None
                utterance_lower = utterance.lower()
                for m in self.MACHINES:
                    if m.lower() in utterance_lower:
                        machine = m
                        break
                
                return {
                    'intent': 'performance',
                    'confidence': 0.95,
                    'machine': machine
                }
            
            elif intent_type == 'baseline':
                # Baseline queries - may or may not have machine name
                machine = self._extract_machine_fuzzy(utterance)
                
                return {
                    'intent': 'baseline',
                    'confidence': 0.95,
                    'machine': machine
                }
            
            elif intent_type == 'production':
                # Production queries - extract machine name
                machine = None
                utterance_lower = utterance.lower()
                for m in self.MACHINES:
                    if m.lower() in utterance_lower:
                        machine = m
                        break
                
                return {
                    'intent': 'production',
                    'confidence': 0.95,
                    'machine': machine
                }
            
            elif intent_type == 'forecast':
                # Forecast queries - may or may not have machine name
                machine = None
                utterance_lower = utterance.lower()
                for m in self.MACHINES:
                    if m.lower() in utterance_lower:
                        machine = m
                        break
                
                return {
                    'intent': 'forecast',
                    'confidence': 0.95,
                    'machine': machine
                }
            
            elif intent_type == 'factory_overview':
                # Factory overview - may include machine name for filtering (e.g., opportunities for Compressor-1)
                machine = None
                utterance_lower = utterance.lower()
                for m in self.MACHINES:
                    if m.lower() in utterance_lower:
                        machine = m
                        break
                
                return {
                    'intent': 'factory_overview',
                    'confidence': 0.95,
                    'machine': machine
                }
            
            elif intent_type == 'machine_status':
                # Extract machine name from match
                machine = match.group(1)
                return {
                    'intent': 'machine_status',
                    'confidence': 0.95,
                    'machine': self._normalize_machine_name(machine)
                }
            
            elif intent_type == 'power_query':
                machine = match.group(1)
                # Handle partial machine names (e.g., "HVAC" → "HVAC-EU-North" or "HVAC-Main")
                normalized_machine = self._normalize_machine_name(machine)
                # If exact match failed, try fuzzy matching
                if normalized_machine == machine:
                    # Try prefix matching (HVAC → HVAC-EU-North or HVAC-Main)
                    matches = [m for m in self.MACHINES if m.startswith(machine)]
                    if len(matches) == 1:
                        normalized_machine = matches[0]
                    elif len(matches) > 1:
                        # Ambiguous - will be caught by validator
                        normalized_machine = machine
                
                return {
                    'intent': 'power_query',
                    'confidence': 0.95,
                    'machine': normalized_machine,
                    'metric': 'power'
                }
            
            elif intent_type == 'energy_query':
                machine = match.group(1)
                return {
                    'intent': 'energy_query',
                    'confidence': 0.95,
                    'machine': self._normalize_machine_name(machine),
                    'metric': 'energy'
                }
            
            elif intent_type == 'comparison':
                machine1 = match.group(1)
                machine2 = match.group(2)
                # Return comma-separated machines (will be split by validator)
                return {
                    'intent': 'comparison',
                    'confidence': 0.95,
                    'machines': f"{self._normalize_machine_name(machine1)},{self._normalize_machine_name(machine2)}"
                }
            
            elif intent_type == 'anomaly_detection':
                # Anomaly detection - may or may not have machine name
                machine = None
                utterance_lower = utterance.lower()
                for m in self.MACHINES:
                    if m.lower() in utterance_lower:
                        machine = m
                        break
                
                return {
                    'intent': 'anomaly_detection',
                    'confidence': 0.95,
                    'machine': machine
                }
            
            return None
            
        except (IndexError, ValueError) as e:
            self.logger.warning("pattern_extraction_error", error=str(e), pattern=intent_type)
            return None
    
    def _normalize_machine_name(self, name: str) -> str:
        """Normalize machine name to match whitelist format"""
        # Case-insensitive match against known machines
        name_lower = name.lower().replace(' ', '-').replace('_', '-')
        
        for machine in self.MACHINES:
            if machine.lower().replace(' ', '-').replace('_', '-') == name_lower:
                return machine
        
        # If no exact match, return original (validator will handle fuzzy matching)
        return name


class HybridParser:
    """
    Orchestrates multi-tier intent parsing
    
    Routing Strategy:
    1. Try Heuristic (Tier 1) - <5ms, 70-80% coverage
    2. Try Adapt (Tier 2) - <10ms, 10-15% coverage [FUTURE]
    3. Fallback to LLM (Tier 3) - 300-500ms, 10-15% coverage
    
    Performance Target: P50 < 200ms (weighted average)
    """
    
    def __init__(self):
        """Initialize hybrid parser with all tiers"""
        self.logger = logger.bind(component="hybrid_parser")
        
        # Initialize parsers
        self.heuristic = HeuristicRouter()
        self.adapt = AdaptParser()
        self.llm = Qwen3Parser()
        
        # Routing stats
        self.stats = {
            'heuristic': 0,
            'adapt': 0,
            'llm': 0,
            'total': 0
        }
        
        self.logger.info("hybrid_parser_initialized", tiers=["heuristic", "adapt", "llm"])
    
    def parse(self, utterance: str) -> Dict:
        """
        Parse utterance using adaptive routing
        
        Args:
            utterance: User query string
            
        Returns:
            Intent dictionary with routing tier metadata
        """
        start_time = time.time()
        tier_used = None
        result = None
        
        try:
            # Tier 1: Heuristic Router (Ultra-Fast)
            result = self.heuristic.route(utterance)
            if result:
                tier_used = RoutingTier.HEURISTIC
                self.stats['heuristic'] += 1
            
            # Tier 2: Adapt (Fast pattern matching)
            if not result:
                result = self.adapt.parse(utterance)
                # Only use Adapt result if confidence is reasonable
                if result and result.get('confidence', 0) < 0.6:
                    self.logger.debug("adapt_low_confidence",
                                     confidence=result['confidence'],
                                     utterance=utterance)
                    result = None  # Fallback to LLM for low-confidence matches
                
                if result:
                    tier_used = RoutingTier.ADAPT
                    self.stats['adapt'] += 1
            
            # Tier 3: LLM (Fallback for complex queries)
            if not result:
                result = self.llm.parse(utterance)
                tier_used = RoutingTier.LLM
                self.stats['llm'] += 1
            
            # Parse time_range if present (from ANY tier, especially LLM)
            # Check both result['entities'] dict and result['time_range'] string
            time_range_str = None
            
            if result and 'entities' in result:
                entities = result.get('entities', {})
                if isinstance(entities, dict):
                    time_range_str = entities.get('time_range')
            
            # Try to extract time range from utterance if not in entities
            if not time_range_str:
                # Look for common time patterns in utterance
                import re
                
                # "from X to Y" - greedy match
                match = re.search(r'from\s+(.+?)\s+to\s+(.+?)(?:\s+(?:am|pm|for|in|at|$))', utterance.lower())
                if match:
                    # Reconstruct full range
                    time_range_str = f"{match.group(1)} to {match.group(2)}"
                else:
                    # Try other patterns
                    for pattern in [
                        r'in\s+the\s+last\s+(\d+\s+)?(\w+)',  # "in the last hour", "in the last 2 days"
                        r'this\s+(week|month|year)',
                        r'last\s+(week|month|year|\d+\s+(?:hour|day|week)s?)',
                        r'between\s+(.+?)\s+and\s+(.+?)(?:\s|$)',
                        r'(yesterday|today)',
                    ]:
                        match = re.search(pattern, utterance.lower())
                        if match:
                            time_range_str = match.group(0)
                            break
            
            # Parse the time range if found
            if time_range_str:
                start_dt, end_dt = TimeRangeParser.parse(time_range_str)
                
                if start_dt and end_dt:
                    # Ensure entities dict exists
                    if 'entities' not in result:
                        result['entities'] = {}
                    
                    result['entities']['time_range'] = time_range_str
                    result['entities']['start_time'] = start_dt
                    result['entities']['end_time'] = end_dt
                    
                    self.logger.info("time_range_parsed",
                                   raw=time_range_str,
                                   start=start_dt.isoformat(),
                                   end=end_dt.isoformat(),
                                   tier=tier_used)
                else:
                    self.logger.warning("time_range_parse_failed", 
                                      raw=time_range_str,
                                      tier=tier_used)
            
            # Add routing metadata
            result['tier'] = tier_used
            result['routing_latency_ms'] = (time.time() - start_time) * 1000
            
            # Update stats
            self.stats['total'] += 1
            
            # Log routing decision
            self.logger.info(
                "query_routed",
                utterance=utterance[:50],
                tier=tier_used,
                intent=result.get('intent'),
                confidence=result.get('confidence'),
                latency_ms=result['routing_latency_ms']
            )
            
            # Update metrics
            tier_routing.labels(tier=tier_used).inc()
            query_latency.labels(intent_type=result.get('intent'), tier=tier_used).observe(result['routing_latency_ms'] / 1000)
            queries_total.labels(intent_type=result.get('intent'), tier=tier_used, status='success').inc()
            
            return result
            
        except Exception as e:
            self.logger.error("parsing_error", error=str(e), utterance=utterance)
            raise
    
    def get_stats(self) -> Dict:
        """Get routing statistics"""
        total = self.stats['total']
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            'distribution': {
                'heuristic': f"{(self.stats['heuristic'] / total) * 100:.1f}%",
                'adapt': f"{(self.stats['adapt'] / total) * 100:.1f}%",
                'llm': f"{(self.stats['llm'] / total) * 100:.1f}%",
            }
        }
