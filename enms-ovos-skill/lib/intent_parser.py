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
    PATTERNS = {
        # Top N ranking queries (CRITICAL: handle "top 3", "top 5 machines", etc.)
        'ranking': [
            re.compile(r'\btop\s+(\d+)\s*(?:machines?|consumers?)?\b', re.IGNORECASE),
            re.compile(r'\bshow\s+(?:me\s+)?(?:the\s+)?top\s+(\d+)', re.IGNORECASE),
            re.compile(r'\b(\d+)\s+top\s+(?:machines?|consumers?)', re.IGNORECASE),
        ],
        
        # Factory-wide queries
        'factory_overview': [
            re.compile(r'\bfactory\s+(?:overview|status|summary)\b', re.IGNORECASE),
            re.compile(r'\btotal\s+(?:factory\s+)?(?:kwh|consumption|energy|power)\b', re.IGNORECASE),
            re.compile(r'\b(?:complete|full)\s+factory\b', re.IGNORECASE),
            re.compile(r'\bfacility\s+(?:overview|status)\b', re.IGNORECASE),
        ],
        
        # Machine status queries
        'machine_status': [
            re.compile(r'\b({})\s+(?:status|online|offline|running|availability)\b'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\b(?:is|check)\s+({})\s*(?:running|online|offline)?\b'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\b({})\s+availability\b'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
        ],
        
        # Power queries
        'power_query': [
            re.compile(r'\b({})\s+(?:power|watts?|kw)\b'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\bpower\s+(?:of\s+)?({})'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            # Handle short forms like "HVAC watts" (extract HVAC from HVAC-EU-North)
            re.compile(r'\b(HVAC|Boiler|Compressor|Conveyor|Turbine|Injection)[^\s]*\s+(?:power|watts?|kw)\b', re.IGNORECASE),
        ],
        
        # Energy queries
        'energy_query': [
            re.compile(r'\b({})\s+(?:energy|kwh|consumption)\b'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\benergy\s+(?:of\s+)?({})'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
            re.compile(r'\b({})\s+(?:used|consumed)'.format('|'.join(re.escape(m) for m in MACHINES)), re.IGNORECASE),
        ],
        
        # Comparison queries
        'comparison': [
            re.compile(r'\bcompare\s+({})\s+(?:and|vs|versus)\s+({})'.format(
                '|'.join(re.escape(m) for m in MACHINES),
                '|'.join(re.escape(m) for m in MACHINES)
            ), re.IGNORECASE),
            re.compile(r'\b({})\s+vs\s+({})'.format(
                '|'.join(re.escape(m) for m in MACHINES),
                '|'.join(re.escape(m) for m in MACHINES)
            ), re.IGNORECASE),
        ],
    }
    
    def __init__(self):
        """Initialize heuristic router"""
        self.logger = logger.bind(component="heuristic_router")
    
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
        
        # Try each pattern category
        for intent_type, patterns in self.PATTERNS.items():
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
        """Build intent dictionary from regex match"""
        try:
            if intent_type == 'ranking':
                # Extract N from "top N"
                limit = int(match.group(1))
                return {
                    'intent': IntentType.RANKING,
                    'confidence': 0.95,  # High confidence for exact pattern match
                    'entities': {
                        'limit': limit,
                        'metric': 'energy'  # Default to energy ranking
                    }
                }
            
            elif intent_type == 'factory_overview':
                return {
                    'intent': IntentType.FACTORY_OVERVIEW,
                    'confidence': 0.95,
                    'entities': {}
                }
            
            elif intent_type == 'machine_status':
                # Extract machine name from match
                machine = match.group(1)
                return {
                    'intent': IntentType.MACHINE_STATUS,
                    'confidence': 0.95,
                    'entities': {
                        'machine': self._normalize_machine_name(machine)
                    }
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
                    'intent': IntentType.POWER_QUERY,
                    'confidence': 0.95,
                    'entities': {
                        'machine': normalized_machine,
                        'metric': 'power'
                    }
                }
            
            elif intent_type == 'energy_query':
                machine = match.group(1)
                return {
                    'intent': IntentType.ENERGY_QUERY,
                    'confidence': 0.95,
                    'entities': {
                        'machine': self._normalize_machine_name(machine),
                        'metric': 'energy'
                    }
                }
            
            elif intent_type == 'comparison':
                machine1 = match.group(1)
                machine2 = match.group(2)
                return {
                    'intent': IntentType.COMPARISON,
                    'confidence': 0.95,
                    'entities': {
                        'machine': f"{self._normalize_machine_name(machine1)},{self._normalize_machine_name(machine2)}"
                    }
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
