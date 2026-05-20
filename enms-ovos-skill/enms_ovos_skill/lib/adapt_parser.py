"""
Adapt Intent Parser for ENMS OVOS Skill
========================================

Tier 2: Fast pattern-based intent matching with Adapt
Target: <10ms latency for common patterns
"""

import re
from typing import Dict, Optional, List
from pathlib import Path

import structlog
from adapt.intent import IntentBuilder
from adapt.engine import IntentDeterminationEngine

from .models import IntentType
from .observability import query_latency, tier_routing, queries_total

logger = structlog.get_logger()


class AdaptParser:
    """
    Tier 2: Adapt-based intent parser
    
    Uses Adapt intent engine for fast pattern matching
    Complements heuristic router with example-based learning
    """
    
    def __init__(self, skill_dir: Optional[Path] = None):
        """
        Initialize Adapt parser
        
        Args:
            skill_dir: Path to skill directory (for loading .intent files)
        """
        self.logger = logger.bind(component="adapt_parser")
        self.engine = IntentDeterminationEngine()
        self.machines: List[str] = []
        
        # Determine skill directory
        if skill_dir is None:
            skill_dir = Path(__file__).parent.parent
        self.skill_dir = Path(skill_dir)
        
        # Register vocabulary and intents
        self._register_vocabulary()
        self._register_intents()
        
        self.logger.info("adapt_parser_initialized")
    
    def _register_vocabulary(self):
        """Register entity vocabulary (machines, metrics, time ranges)"""
        
        # Machine names (8 machines)
        machines = [
            "Boiler-1", "Compressor-1", "Compressor-EU-1", "Conveyor-A",
            "HVAC-EU-North", "HVAC-Main", "Hydraulic-Pump-1", "Injection-Molding-1"
        ]
        self.machines = machines
        
        # Number word mappings for spoken forms
        digit_to_word = {'1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five'}
        
        for machine in machines:
            self.engine.register_entity(machine, "machine")
            # Also register spoken forms (e.g., "compressor 1" → "Compressor-1")
            spoken_form = machine.replace("-", " ")
            if spoken_form != machine:
                self.engine.register_entity(spoken_form, "machine")
            # Also register number word variants (e.g., "compressor one")
            for digit, word in digit_to_word.items():
                if digit in machine:
                    word_form = machine.replace("-", " ").replace(digit, word)
                    self.engine.register_entity(word_form, "machine")
        
        # Energy keywords - EXPANDED with domain synonyms
        energy_keywords = [
            "energy", "kwh", "kilowatt", "kilowatt hour", "kilowatt-hour",
            "consumption", "used", "consumed", "usage", "draw", "load",
            "demand", "requirement", "utilization", "electricity"
        ]
        for keyword in energy_keywords:
            self.engine.register_entity(keyword, "energy_metric")
        
        # Power keywords - EXPANDED with electrical terms
        power_keywords = [
            "power", "watts", "watt", "kw", "kilowatts", "kilowatt",
            "wattage", "electrical load", "current draw", "instantaneous power",
            "real power", "active power"
        ]
        for keyword in power_keywords:
            self.engine.register_entity(keyword, "power_metric")
        
        # Status keywords - EXPANDED with operational states
        status_keywords = [
            "status", "running", "online", "offline", "availability",
            "state", "condition", "operation mode", "running status",
            "idle", "standby", "waiting", "not running", "stopped",
            "full load", "maximum capacity", "peak load", "full power",
            "partial load", "reduced capacity", "part load", "ramping"
        ]
        for keyword in status_keywords:
            self.engine.register_entity(keyword, "status_check")
        
        # Cost keywords
        cost_keywords = ["cost", "price", "expense", "spend", "spent"]
        for keyword in cost_keywords:
            self.engine.register_entity(keyword, "cost_metric")
        
        # KPI keywords - EXPANDED with ISO 50001 terms
        kpi_keywords = [
            "kpi", "kpis", "efficiency", "sec", "specific energy consumption",
            "load factor", "peak demand", "performance",
            "efficiency ratio", "energy intensity",
            # ISO 50001 terms
            "seu", "significant energy use", "significant energy user",
            "enpi", "energy performance indicator", "performance metric",
            "baseline", "energy baseline", "baseline model", "reference consumption"
        ]
        for keyword in kpi_keywords:
            self.engine.register_entity(keyword, "kpi_metric")
        
        # Ranking keywords
        ranking_keywords = ["top", "highest", "biggest", "consumers", "machines"]
        for keyword in ranking_keywords:
            self.engine.register_entity(keyword, "ranking")
        
        # Factory keywords - EXPANDED with industrial terms
        factory_keywords = [
            "factory", "facility", "plant", "site", "total", "overview", "summary",
            "all machines", "all equipment", "entire facility", "whole plant",
            # Equipment synonyms
            "equipment", "machine", "machines", "asset", "assets", "unit", "units", "device", "devices"
        ]
        for keyword in factory_keywords:
            self.engine.register_entity(keyword, "factory")
        
        # Comparison keywords
        comparison_keywords = ["compare", "versus", "vs", "difference", "between"]
        for keyword in comparison_keywords:
            self.engine.register_entity(keyword, "comparison")
        
        # Time range keywords - EXPANDED with natural expressions
        time_keywords = [
            # Absolute
            "today", "yesterday", "week", "month", "hour", "day", "year",
            # Relative/Natural
            "right now", "at the moment", "currently", "as of now",
            "in the past hour", "during last shift", "overnight",
            "last week", "past month", "previous quarter",
            # Industrial terms
            "shift", "batch", "cycle", "production run", "operation period"
        ]
        for keyword in time_keywords:
            self.engine.register_entity(keyword, "time_range")
    
        
        # Forecast/Prediction keywords - NEW
        forecast_keywords = [
            "forecast", "forecasting", "predict", "prediction", "predicted",
            "expected", "estimate", "projection", "future",
            "will use", "will consume", "going to", "next hour", "next day",
            "tomorrow", "next week", "upcoming", "anticipated"
        ]
        for keyword in forecast_keywords:
            self.engine.register_entity(keyword, "forecast")
        
        # Anomaly keywords - NEW
        anomaly_keywords = [
            "anomaly", "anomalies", "alert", "alerts", "warning", "warnings",
            "issue", "issues", "problem", "problems", "unusual", "abnormal",
            "outlier", "outliers", "deviation", "deviations", "spike", "spikes",
            "drop", "irregular", "unexpected"
        ]
        for keyword in anomaly_keywords:
            self.engine.register_entity(keyword, "anomaly")
        
        # Help keywords - NEW
        help_keywords = [
            "help", "assist", "assistance", "guide", "how to", "tutorial",
            "show me", "tell me", "explain", "what can you do", "capabilities"
        ]
        for keyword in help_keywords:
            self.engine.register_entity(keyword, "help_query")

    def _extract_machine_fuzzy(self, utterance: str) -> Optional[str]:
        """Recover a canonical machine name from a natural utterance when Adapt omits the entity."""
        utterance_lower = utterance.lower()
        number_words = {
            'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
            'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'
        }

        utterance_normalized = utterance_lower
        for word, digit in number_words.items():
            utterance_normalized = re.sub(rf'\b{word}\b', digit, utterance_normalized)

        for machine in self.machines:
            machine_lower = machine.lower()
            machine_spaced = machine_lower.replace('-', ' ')
            if machine_lower in utterance_lower or machine_spaced in utterance_normalized:
                return machine

        return None
        
        # Report keywords - NEW
        report_keywords = [
            "report", "reports", "pdf", "document", "generate", "create",
            "summary", "export", "download", "monthly report", "energy report"
        ]
        for keyword in report_keywords:
            self.engine.register_entity(keyword, "report_query")
        
        # Production keywords - NEW
        production_keywords = [
            "production", "units", "output", "manufactured", "produced",
            "oee", "overall equipment effectiveness", "quality", "yield",
            "throughput", "batch", "produced units"
        ]
        for keyword in production_keywords:
            self.engine.register_entity(keyword, "production_query")
        
        # SEU keywords - NEW
        seu_keywords = [
            "seu", "seus", "significant energy use", "significant energy user",
            "significant energy uses", "energy consumer", "major consumer"
        ]
        for keyword in seu_keywords:
            self.engine.register_entity(keyword, "seu_query")
        
        # Performance keywords - NEW
        performance_keywords = [
            "performance", "efficiency score", "operating efficiency",
            "performance rating", "performance index"
        ]
        for keyword in performance_keywords:
            self.engine.register_entity(keyword, "performance_query")
        
        # Model keywords - NEW
        model_keywords = [
            "model", "models", "available", "list", "show models",
            "baseline model", "trained model"
        ]
        for keyword in model_keywords:
            self.engine.register_entity(keyword, "model_query")
        
        # Explain keywords - NEW
        explain_keywords = [
            "explain", "why", "reason", "explanation", "because",
            "how does it work", "tell me why"
        ]
        for keyword in explain_keywords:
            self.engine.register_entity(keyword, "explain_query")

        driver_analysis_keywords = [
            "energy drivers",
            "main energy drivers",
            "main drivers",
            "top energy drivers",
            "top drivers",
            "key energy drivers",
            "key drivers",
            "driver analysis",
            "what drives energy",
            "what affects energy",
            "what affects consumption",
            "affect energy use",
            "influence energy use",
            "most influential driver",
        ]
        for keyword in driver_analysis_keywords:
            self.engine.register_entity(keyword, "driver_analysis")

        driver_keywords = [
            "temperature",
            "outdoor temperature",
            "ambient temperature",
            "indoor temperature",
            "machine temperature",
            "pressure",
            "operating pressure",
            "steam pressure",
            "air pressure",
            "production",
            "production count",
            "throughput",
            "output",
            "humidity",
            "load factor",
            "load",
            "runtime",
            "operating hours",
            "weather",
            "heating degree days",
            "cooling degree days",
            "dew point",
            "dewpoint",
        ]
        for keyword in driver_keywords:
            self.engine.register_entity(keyword, "driver")

        energy_source_keywords = [
            "electricity",
            "electric",
            "natural gas",
            "gas",
            "steam",
            "compressed air",
            "air",
        ]
        for keyword in energy_source_keywords:
            self.engine.register_entity(keyword, "energy_source")

    def _register_intents(self):
        """Register Adapt intent patterns"""
        
        # Power query intent
        power_intent = IntentBuilder("power_query") \
            .require("machine") \
            .require("power_metric") \
            .build()
        self.engine.register_intent_parser(power_intent)
        
        # Energy query intent
        energy_intent = IntentBuilder("energy_query") \
            .require("machine") \
            .require("energy_metric") \
            .build()
        self.engine.register_intent_parser(energy_intent)
        
        # Machine status intent
        status_intent = IntentBuilder("machine_status") \
            .require("machine") \
            .require("status_check") \
            .build()
        self.engine.register_intent_parser(status_intent)
        
        # Cost query intent
        cost_intent = IntentBuilder("cost_analysis") \
            .require("cost_metric") \
            .build()
        self.engine.register_intent_parser(cost_intent)
        
        # KPI query intent (efficiency, SEC, load factor, peak demand)
        kpi_intent = IntentBuilder("kpi") \
            .require("kpi_metric") \
            .build()
        self.engine.register_intent_parser(kpi_intent)
        
        # Ranking intent
        ranking_intent = IntentBuilder("ranking") \
            .require("ranking") \
            .build()
        self.engine.register_intent_parser(ranking_intent)
        
        # Factory overview intent
        factory_intent = IntentBuilder("factory_overview") \
            .require("factory") \
            .build()
        self.engine.register_intent_parser(factory_intent)
        
        # Comparison intent
        comparison_intent = IntentBuilder("comparison") \
            .require("comparison") \
            .require("machine") \
            .build()
        
        # Forecast intent - NEW
        forecast_intent = IntentBuilder("baseline_prediction") \
            .require("forecast") \
            .build()
        self.engine.register_intent_parser(forecast_intent)
        
        # Anomaly detection intent - NEW
        anomaly_intent = IntentBuilder("anomaly_detection") \
            .require("anomaly") \
            .build()
        self.engine.register_intent_parser(anomaly_intent)
        self.engine.register_intent_parser(comparison_intent)
        
        # Baseline intent (not forecast, actual baseline query)
        baseline_intent = IntentBuilder("baseline") \
            .require("kpi_metric") \
            .require("machine") \
            .build()
        self.engine.register_intent_parser(baseline_intent)
        
        # Baseline models intent
        baseline_models_intent = IntentBuilder("baseline_models") \
            .require("kpi_metric") \
            .require("machine") \
            .require("model_query") \
            .build()
        self.engine.register_intent_parser(baseline_models_intent)
        
        # Baseline explanation intent
        baseline_explanation_intent = IntentBuilder("baseline_explanation") \
            .require("kpi_metric") \
            .require("machine") \
            .require("explain_query") \
            .build()
        self.engine.register_intent_parser(baseline_explanation_intent)

        driver_analysis_intent = IntentBuilder("driver_analysis") \
            .require("driver_analysis") \
            .optionally("machine") \
            .optionally("driver") \
            .optionally("energy_source") \
            .build()
        self.engine.register_intent_parser(driver_analysis_intent)

        factory_driver_analysis_intent = IntentBuilder("factory_driver_analysis") \
            .require("driver_analysis") \
            .require("factory") \
            .optionally("driver") \
            .optionally("energy_source") \
            .build()
        self.engine.register_intent_parser(factory_driver_analysis_intent)
        
        # SEUs intent
        seus_intent = IntentBuilder("seus") \
            .require("seu_query") \
            .build()
        self.engine.register_intent_parser(seus_intent)
        
        # Performance intent
        performance_intent = IntentBuilder("performance") \
            .require("performance_query") \
            .require("machine") \
            .build()
        self.engine.register_intent_parser(performance_intent)
        
        # Production intent
        production_intent = IntentBuilder("production") \
            .require("production_query") \
            .require("machine") \
            .build()
        self.engine.register_intent_parser(production_intent)
        
        # Report intent
        report_intent = IntentBuilder("report") \
            .require("report_query") \
            .build()
        self.engine.register_intent_parser(report_intent)
        
        # Help intent
        help_intent = IntentBuilder("help") \
            .require("help_query") \
            .build()
        self.engine.register_intent_parser(help_intent)

    def _parse_driver_analysis_direct(self, utterance: str) -> Optional[Dict]:
        """Route driver-analysis phrasing before generic energy/ranking matches."""
        text = utterance.lower()
        driver_patterns = (
            "driver analysis",
            "energy drivers",
            "top energy drivers",
            "key energy drivers",
            "what drives energy",
            "what affects energy",
            "what affects consumption",
            "affect energy use",
            "influence energy use",
        )
        driver_terms = (
            "temperature", "pressure", "humidity", "production", "throughput",
            "output", "load factor", "runtime", "weather", "dew point", "dewpoint"
        )

        if not any(pattern in text for pattern in driver_patterns) and not (
            "affect" in text and "energy" in text
        ):
            return None

        entities = {}
        machine = self._extract_machine_fuzzy(utterance)
        if machine:
            entities["machine"] = machine

        for driver in driver_terms:
            if driver in text:
                entities["driver_name"] = driver
                break

        return {
            "intent": IntentType.DRIVER_ANALYSIS.value,
            "confidence": 0.95,
            "entities": entities
        }
    
    def parse(self, utterance: str) -> Optional[Dict]:
        """
        Parse utterance using Adapt
        
        Args:
            utterance: User query string
            
        Returns:
            Intent dict or None if no match
        """
        import time
        start_time = time.time()

        direct_driver_result = self._parse_driver_analysis_direct(utterance)
        if direct_driver_result:
            return direct_driver_result
        
        # Run Adapt parser
        intents = list(self.engine.determine_intent(utterance))
        
        if not intents:
            self.logger.debug("adapt_no_match", utterance=utterance)
            return None
        
        # Get best intent
        best_intent = intents[0]
        intent_name = best_intent.get('intent_type', '').replace('_', '')
        confidence = best_intent.get('confidence', 0.0)
        
        # Extract entities
        entities = {}
        
        # Extract machine name
        if 'machine' in best_intent:
            entities['machine'] = best_intent['machine']
        else:
            recovered_machine = self._extract_machine_fuzzy(utterance)
            if recovered_machine:
                entities['machine'] = recovered_machine
        
        # Extract metric type
        if 'power_metric' in best_intent:
            entities['metric'] = 'power'
        elif 'energy_metric' in best_intent:
            entities['metric'] = 'energy'
        elif 'cost_metric' in best_intent:
            entities['metric'] = 'cost'
        elif 'kpi_metric' in best_intent:
            entities['metric'] = 'kpi'
        
        # Extract time range
        if 'time_range' in best_intent:
            entities['time_range'] = best_intent['time_range']

        if 'driver' in best_intent:
            entities['driver_name'] = best_intent['driver']

        if 'energy_source' in best_intent:
            entities['energy_source'] = best_intent['energy_source'].replace(' ', '_')
        
        # Extract limit for ranking queries (e.g., "highest 3", "top 5")
        if intent_name.lower() == 'ranking':
            # Try to extract number from utterance
            import re
            limit_match = re.search(r'\b(\d+)\b', utterance)
            if limit_match:
                entities['limit'] = int(limit_match.group(1))
        
        # Map Adapt intent name to IntentType
        intent_mapping = {
            'powerquery': IntentType.POWER_QUERY,
            'energyquery': IntentType.ENERGY_QUERY,
            'machinestatus': IntentType.MACHINE_STATUS,
            'costanalysis': IntentType.COST_ANALYSIS,
            'kpi': IntentType.KPI,
            'ranking': IntentType.RANKING,
            'factoryoverview': IntentType.FACTORY_OVERVIEW,
            'comparison': IntentType.COMPARISON,
            'baselineprediction': IntentType.FORECAST,
            'anomalydetection': IntentType.ANOMALY_DETECTION,
            'baseline': IntentType.BASELINE,
            'baselinemodels': IntentType.BASELINE_MODELS,
            'baselineexplanation': IntentType.BASELINE_EXPLANATION,
            'driveranalysis': IntentType.DRIVER_ANALYSIS,
            'factorydriveranalysis': IntentType.DRIVER_ANALYSIS,
            'seus': IntentType.SEUS,
            'performance': IntentType.PERFORMANCE,
            'production': IntentType.PRODUCTION,
            'report': IntentType.REPORT,
            'help': IntentType.HELP,
        }
        
        mapped_intent = intent_mapping.get(intent_name.lower())
        if not mapped_intent:
            self.logger.warning("adapt_unknown_intent", 
                              intent=intent_name,
                              utterance=utterance)
            return None
        
        # Build result (convert enum to string for validator compatibility)
        # Boost confidence to meet validator threshold (Adapt's calculation is conservative)
        boosted_confidence = max(confidence, 0.85)
        
        result = {
            'intent': mapped_intent.value if hasattr(mapped_intent, 'value') else str(mapped_intent),
            'confidence': boosted_confidence,
            'entities': entities
        }
        
        latency_ms = (time.time() - start_time) * 1000
        
        self.logger.info("adapt_match",
                        intent=mapped_intent,
                        confidence=confidence,
                        latency_ms=latency_ms)
        
        # Update metrics
        query_latency.labels(intent_type=mapped_intent, tier="adapt").observe(latency_ms / 1000)
        
        return result
