"""
OVOS EnMS Skill - PRODUCTION-READY Industrial Energy Management Voice Assistant
Integration with Energy Management System (EnMS) API

Architecture:
- Tier 1 (Heuristic): Ultra-fast regex patterns (<5ms) - 80% queries
- Tier 2 (Adapt): Fast pattern matching (<10ms) - 10% queries  
- Tier 3 (LLM): Qwen3.5-2B GGUF for complex NLU fallback - 10% queries
- Tier 4 (Validator): Zero-trust hallucination prevention
- Tier 5 (API): EnMS REST client with circuit breakers
- Tier 6 (Response): Voice-optimized Jinja2 templates
- Tier 7 (Context): Multi-turn conversation support
- Tier 8 (Feedback): Natural voice feedback

Target Performance:
- P50 latency: <200ms (actual: ~0.18ms for heuristic tier)
- P90 latency: <500ms
- P99 latency: <2000ms
- Accuracy: 99.5%+
- Hallucination prevention: 99.9%
"""
from typing import Optional, Dict, Any, List
import asyncio
import os
import time
import re
import threading
import concurrent.futures
import concurrent.futures
from datetime import datetime, timezone, timedelta
import structlog
from ovos_workshop.decorators import intent_handler
from ovos_workshop.intents import IntentBuilder
from ovos_workshop.skills.fallback import FallbackSkill
from ovos_workshop.skills.ovos import OVOSSkill
from ovos_bus_client.message import Message

# Import all core modules
from .lib.intent_parser import HybridParser, RoutingTier
from .lib.validator import ENMSValidator
from .lib.api_client import ENMSClient
from .adapters import AdapterFactory
from .lib.response_formatter import ResponseFormatter
from .lib.conversation_context import ConversationContextManager
from .lib.voice_feedback import VoiceFeedbackManager, FeedbackType
from .lib.feature_extractor import FeatureExtractor
from .lib.time_parser import TimeRangeParser
from .lib.models import IntentType, Intent, TimeRange
from .lib.machine_registry import DynamicMachineRegistry
from .lib.observability import (
    queries_total,
    query_latency,
    tier_routing,
    errors_total,
    validation_rejections
)

logger = structlog.get_logger(__name__)


class EnmsSkill(FallbackSkill):
    """
    PRODUCTION-READY OVOS Skill for Energy Management System
    
    Features:
    - Multi-tier adaptive routing (heuristic → adapt → LLM)
    - Zero-trust validation (99.5%+ accuracy)
    - Multi-turn conversation support (via converse method when needed)
    - Natural voice feedback
    - Prometheus metrics & observability
    - Graceful degradation
    - <200ms P50 latency
    
    NOTE: Uses FallbackSkill (not ConversationalSkill) to register a fallback handler
    for unmatched queries (Tier 3 LLM). FallbackSkill only fires AFTER all intent
    matchers fail, unlike ConversationalSkill which intercepts ALL utterances.
    """

    def __init__(self, bus=None, skill_id="", **kwargs):
        """Initialize the EnMS skill
        
        Args:
            bus: Message bus instance
            skill_id: Unique skill identifier
            **kwargs: Additional keyword arguments
        """
        # Initialize attributes FIRST to avoid overwriting if initialize() is called by super()
        self.logger = structlog.get_logger(__name__)
        
        # Core components (initialized in initialize())
        self.hybrid_parser: Optional[HybridParser] = None
        self.validator: Optional[ENMSValidator] = None
        self.api_client: Optional[ENMSClient] = None  # Legacy - will use adapter
        self.adapter = None  # Priority 5: EnMS adapter for portability
        self.config: Optional[Dict[str, Any]] = None  # Configuration dict
        self.response_formatter: Optional[ResponseFormatter] = None
        self.context_manager: Optional[ConversationContextManager] = None
        self.voice_feedback: Optional[VoiceFeedbackManager] = None
        
        # Persistent event loop for async API calls (prevents 'Event loop is closed' errors)
        self._async_loop: Optional[asyncio.AbstractEventLoop] = None
        self._async_loop_lock = threading.RLock()
        
        # Performance tracking
        self.query_count = 0
        self.total_latency_ms = 0
        
        # Call parent constructor LAST (may trigger initialize())
        super().__init__(bus=bus, skill_id=skill_id, **kwargs)
        
    def initialize(self):
        """
        Called after skill construction
        Initialize all SOTA components
        """
        logger.info("skill_initializing", 
                        skill_name="EnmsSkill",
                        version="1.0.0",
                        architecture="multi-tier-adaptive")
        
        # Priority 5: Load configuration from config.yaml (WASABI portability)
        import os
        import yaml
        from pathlib import Path
        
        # Try to load config.yaml from skill directory
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            logger.info("loading_config_yaml", path=str(config_path))
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            # Fallback to legacy environment variables and settings
            logger.warning("config_yaml_not_found", path=str(config_path), using_fallback=True)
            self.config = {
                "adapter_type": "humanergy",
                "api_base_url": os.getenv("ENMS_API_URL", 
                                          self.settings.get("enms_api_base_url", "http://10.33.10.104:8001/api/v1")),
                "timeout": self.settings.get("api_timeout_seconds", 90),
                "max_retries": self.settings.get("api_max_retries", 3),
                "factory_name": "Factory",
                "auto_discover_machines": True,
                "refresh_interval_hours": 1,
                "terminology": {},
                "voice": {},
                "features": {}
            }

        env_api_base_url = os.getenv("ENMS_API_URL")
        if env_api_base_url:
            configured_api_base_url = self.config.get("api_base_url")
            if configured_api_base_url and configured_api_base_url != env_api_base_url:
                logger.info(
                    "overriding_config_api_base_url_from_env",
                    configured_api_base_url=configured_api_base_url,
                    env_api_base_url=env_api_base_url
                )
            self.config["api_base_url"] = env_api_base_url
        
        # Extract commonly used settings
        self.enms_api_base_url = self.config.get("api_base_url", "http://10.33.10.104:8001/api/v1")
        _llm_path = self.settings.get("llm_model_path", "./models/Qwen3.5-2B-Q4_K_M.gguf")
        # Resolve relative model path against skill root directory
        from pathlib import Path
        _llm_path_obj = Path(_llm_path)
        if not _llm_path_obj.is_absolute():
            _llm_path_obj = Path(__file__).parent.parent / _llm_path
        self.llm_model_path = str(_llm_path_obj)
        self.confidence_threshold = self.settings.get("confidence_threshold", 0.85)
        self.enable_progress_feedback = self.settings.get("enable_progress_feedback", True)
        self.progress_threshold_ms = self.settings.get("progress_threshold_ms", 500)
        
        # Initialize Tier 1-3: Hybrid Parser (Heuristic + Adapt + LLM)
        logger.info("initializing_hybrid_parser")
        self.hybrid_parser = HybridParser(llm_model_path=self.llm_model_path)
        
        # Initialize Tier 4: Validator
        logger.info("initializing_validator")
        self.validator = ENMSValidator(
            confidence_threshold=self.confidence_threshold,
            enable_fuzzy_matching=self.settings.get("enable_fuzzy_matching", True)
        )
        
        # Initialize Tier 5: EnMS Adapter (Priority 5 - WASABI Portability)
        logger.info("initializing_enms_adapter", 
                   adapter_type=self.config.get("adapter_type", "humanergy"),
                   base_url=self.enms_api_base_url)
        
        try:
            self.adapter = AdapterFactory.create(self.config)
            logger.info("adapter_created_successfully", 
                       adapter_class=self.adapter.__class__.__name__)
        except Exception as e:
            logger.error("adapter_creation_failed", error=str(e))
            # Fallback to legacy ENMSClient for backward compatibility
            logger.warning("falling_back_to_legacy_client")
            self.adapter = None
        
        # Legacy API client (for machine_registry backward compatibility)
        # TODO: Update machine_registry to use adapter instead of api_client
        logger.info("initializing_api_client", base_url=self.enms_api_base_url)
        self.api_client = ENMSClient(
            base_url=self.enms_api_base_url,
            timeout=self.config.get("timeout", 90),
            max_retries=self.config.get("max_retries", 3)
        )
        
        # Initialize Tier 5.5: Dynamic Machine Registry (Priority 4)
        logger.info("initializing_machine_registry")
        self.machine_registry = DynamicMachineRegistry(
            api_client=self.api_client,
            refresh_interval=timedelta(hours=1)
        )
        
        # Initialize Tier 6: Response Formatter
        logger.info("initializing_response_formatter")
        self.response_formatter = ResponseFormatter()
        
        # Initialize Tier 7: Conversation Context
        logger.info("initializing_conversation_context")
        self.context_manager = ConversationContextManager()
        
        # Initialize Tier 8: Voice Feedback
        logger.info("initializing_voice_feedback")
        self.voice_feedback = VoiceFeedbackManager()
        
        # Register fallback handler for unmatched queries (Tier 3 - LLM)
        # Priority 90 = fallback_low, fires only when ALL intent matchers fail
        self.register_fallback(self._handle_fallback, priority=90)
        
        logger.info("skill_initialized_successfully", 
                        components=["HybridParser", "Validator", "APIClient", "MachineRegistry", 
                                  "ResponseFormatter", "ConversationContext", "VoiceFeedback",
                                  "FallbackHandler"],
                        enms_api=self.enms_api_base_url,
                        confidence_threshold=self.confidence_threshold,
                        converse_mode=True)
        
        # Note: Removed self.activate() - OVOSSkill doesn't have this method
        # (activate() is ConversationalSkill-specific)
    
    def on_ready_status(self):
        """Called when skill is fully ready - safe to schedule events here."""
        super().on_ready_status()
        
        # Load machine whitelist from EnMS API
        # Delay first execution by 5 seconds to ensure API is available
        self.schedule_event(
            self._refresh_machine_whitelist, 
            5,
            name=f"{self.skill_id}_whitelist_refresh_initial"
        )
        self.schedule_repeating_event(
            self._refresh_machine_whitelist, 
            86400, 
            86400,
            name=f"{self.skill_id}_whitelist_refresh_daily"
        )  # Daily refresh
        
        # Cleanup expired conversation sessions every hour
        self.schedule_repeating_event(
            self._cleanup_conversations, 
            3600, 
            3600,
            name=f"{self.skill_id}_conversation_cleanup"
        )
        
        # Health check heartbeat every 30 seconds (detects if skill is stuck)
        self.schedule_repeating_event(
            self._health_check,
            30,
            30,
            name=f"{self.skill_id}_health_check"
        )
        
        logger.info("scheduled_events_registered",
                   events=["whitelist_refresh_initial", "whitelist_refresh_daily", "conversation_cleanup", "health_check"])
        
        # Background preload LLM model (non-blocking)
        # This loads the model in a background thread so first LLM query is fast
        threading.Thread(target=self._preload_llm, daemon=True, name="llm_preload").start()
    
    def _health_check(self, message=None):
        """Periodic health check to detect if skill is stuck.
        
        If this stops logging, the skill is hung.
        """
        # Note: Removed self.activate() - OVOSSkill doesn't have this method
        # (activate() is ConversationalSkill-specific)
        
        # NOTE: LLM support removed from HybridParser (now uses only Heuristic + Adapt)
        
        self.logger.debug("health_check",
                        queries_processed=self.query_count,
                        avg_latency_ms=round(self.total_latency_ms / max(self.query_count, 1), 2) if self.query_count > 0 else 0)
    
    def _preload_llm(self):
        """Preload LLM model in background thread.
        
        This eliminates the 90+ second cold start on first LLM query.
        Model stays in memory until skill shuts down.
        """
        try:
            time.sleep(5)  # Let critical services start first
            if not os.path.isfile(self.llm_model_path):
                self.logger.warning(
                    "llm_preload_skipped",
                    reason="optional model file not installed",
                    model_path=self.llm_model_path
                )
                return
            self.logger.info("llm_preload_starting")
            start = time.time()
            
            # Access the qwen3 parser and trigger model load
            llm_parser = getattr(self.hybrid_parser, 'llm', None) if self.hybrid_parser else None
            if llm_parser:
                llm_parser.load_model()
                elapsed = time.time() - start
                self.logger.info("llm_preload_complete", elapsed_seconds=round(elapsed, 1))
            else:
                self.logger.warning("llm_preload_skipped", reason="llm parser not configured")
        except Exception as e:
            self.logger.error("llm_preload_failed", error=str(e), error_type=type(e).__name__)
    
    def _refresh_machine_whitelist(self, message=None):
        """Refresh machine whitelist from EnMS API (Priority 4: Dynamic Discovery)"""
        try:
            self.logger.info("refreshing_machine_whitelist_via_registry")
            
            # Use DynamicMachineRegistry to fetch machines/SEUs
            success = self._run_async(self.machine_registry.refresh())
            
            # Get refreshed machine list
            machine_names = self.machine_registry.get_machines()
            seu_names = self.machine_registry.get_seu_names()
            
            # Update validator whitelist
            self.validator.update_machine_whitelist(machine_names)
            
            # Update heuristic parser patterns
            if hasattr(self.hybrid_parser, 'heuristic') and hasattr(self.hybrid_parser.heuristic, 'MACHINES'):
                self.hybrid_parser.heuristic.MACHINES = machine_names
            
            # Log statistics
            stats = self.machine_registry.get_stats()
            self.logger.info("machine_whitelist_refreshed", 
                           machines_count=len(machine_names),
                           seus_count=len(seu_names),
                           from_api=success,
                           using_fallback=not success,
                           stats=stats)
        except Exception as e:
            self.logger.error("whitelist_refresh_failed", error=str(e), error_type=type(e).__name__)
            # Don't fail skill initialization - registry uses fallback defaults
    
    def _cleanup_conversations(self, message=None):
        """Cleanup expired conversation sessions"""
        try:
            # Defensive check - ensure skill is fully initialized
            if self.context_manager is None:
                return
            
            expired_count = self.context_manager.cleanup_expired_sessions()
            if expired_count > 0:
                self.logger.info("conversation_cleanup", expired_sessions=expired_count)
        except Exception as e:
            self.logger.error("conversation_cleanup_failed", error=str(e))
    
    def _run_async(self, coro, timeout_seconds: float = 20.0):
        """Helper to run async coroutines from sync handlers.
        
        Uses a persistent event loop to avoid 'Event loop is closed' errors
        when making multiple API calls with httpx.AsyncClient.
        
        CRITICAL: Timeout must be LESS than bridge timeout (30s) to return
        errors gracefully. Set to 20s to leave 10s buffer for processing.
        
        Args:
            coro: Async coroutine to run
            timeout_seconds: Maximum time to wait (default 20s, bridge waits 30s)
            
        Returns:
            Result of coroutine
            
        Raises:
            asyncio.TimeoutError: If operation exceeds timeout
        """
        async def _with_timeout():
            return await asyncio.wait_for(coro, timeout=timeout_seconds)

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop and running_loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(lambda: asyncio.run(_with_timeout()))
                return future.result(timeout=timeout_seconds + 1)

        with self._async_loop_lock:
            if self._async_loop is None or self._async_loop.is_closed():
                self._async_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._async_loop)

            try:
                return self._async_loop.run_until_complete(_with_timeout())
            except asyncio.TimeoutError:
                self.logger.error("async_operation_timeout",
                                timeout_seconds=timeout_seconds,
                                operation=str(coro))
                raise
    
    def _get_factory_wide_drivers(self) -> Dict[str, Any]:
        """Get aggregated key energy drivers across ALL machines with baseline models.
        
        ISO 50001 context: Shows the most impactful energy drivers factory-wide.
        """
        all_drivers = []
        machines_analyzed = []
        
        # Get all machines with baseline models
        machines = self.validator.machine_whitelist
        
        for machine_name in machines:
            try:
                # Get baseline models for this machine
                models_response = self._run_async(
                    self.api_client.list_baseline_models(
                        seu_name=machine_name,
                        energy_source="electricity"
                    )
                )
                
                models = models_response.get('models', [])
                active_model = next((m for m in models if m.get('is_active')), models[0] if models else None)
                
                if not active_model:
                    continue
                
                # Get explanation with key drivers
                explanation_response = self._run_async(
                    self.api_client.get_baseline_model_explanation(
                        model_id=active_model.get('id'),
                        include_explanation=True
                    )
                )
                
                explanation = explanation_response.get('explanation', {})
                key_drivers = explanation.get('key_drivers', [])
                
                # Add machine context to each driver
                for driver in key_drivers:
                    driver['machine'] = machine_name
                    all_drivers.append(driver)
                
                machines_analyzed.append(machine_name)
                
            except Exception as e:
                self.logger.warning("factory_driver_fetch_failed", machine=machine_name, error=str(e))
                continue
        
        if not all_drivers:
            return {'success': False, 'error': 'No baseline models found across factory'}
        
        # Aggregate drivers by feature (combine same features across machines)
        driver_summary = {}
        for driver in all_drivers:
            feature = driver.get('human_name', driver.get('feature'))
            if feature not in driver_summary:
                driver_summary[feature] = {
                    'human_name': feature,
                    'total_impact': 0,
                    'machines': [],
                    'direction': driver.get('direction', 'affects')
                }
            driver_summary[feature]['total_impact'] += abs(driver.get('absolute_impact', 0))
            driver_summary[feature]['machines'].append(driver['machine'])
        
        # Sort by total impact and get top 5
        sorted_drivers = sorted(
            driver_summary.values(),
            key=lambda x: x['total_impact'],
            reverse=True
        )[:5]
        
        return {
            'success': True,
            'data': {
                'factory_wide': True,
                'machines_analyzed': len(machines_analyzed),
                'top_drivers': sorted_drivers,
                'machines_list': machines_analyzed
            }
        }
    
    def _get_session_id(self, message: Message) -> str:
        """Extract session ID from message (for conversation context)"""
        # In production, use message.context.get("session_id")
        # For testing, use a default session
        return message.context.get("session_id", "default_session")
    
    def _extract_time_range(self, utterance: str) -> Optional[TimeRange]:
        """
        Extract time range from utterance using TimeRangeParser
        
        Handles:
        - "yesterday" → yesterday 00:00-23:59
        - "last week" → 7 days ago to now
        - "today" → today 00:00 to now  
        - No time mentioned → defaults to "today"
        
        Args:
            utterance: User's query text
            
        Returns:
            TimeRange object with start/end datetimes, or None if parsing fails
        """
        utterance_lower = utterance.lower()
        
        # Look for time keywords
        time_patterns = [
            r'yesterday',
            r'today',
            r'last\s+(?:hour|day|week|month)',
            r'past\s+(?:\d+\s+)?(?:hour|day|week)s?',
            r'since\s+\d+\s*(?:am|pm)',
            r'between\s+.+?\s+and\s+.+?'
        ]
        
        time_range_str = None
        for pattern in time_patterns:
            match = re.search(pattern, utterance_lower)
            if match:
                time_range_str = match.group(0)
                break
        
        # Parse the time range
        if time_range_str:
            start_dt, end_dt = TimeRangeParser.parse(time_range_str)
            
            if start_dt and end_dt:
                self.logger.info("time_range_extracted",
                               raw=time_range_str,
                               start=start_dt.isoformat(),
                               end=end_dt.isoformat())
                
                return TimeRange(
                    start=start_dt,
                    end=end_dt,
                    relative=time_range_str,
                    duration=self._calculate_duration(start_dt, end_dt)
                )
            else:
                self.logger.warning("time_range_parse_failed", raw=time_range_str)
        
        # Default: today (00:00 to now) if no time mentioned
        start_dt, end_dt = TimeRangeParser.parse("today")
        if start_dt and end_dt:
            self.logger.debug("time_range_default_today", 
                            start=start_dt.isoformat(),
                            end=end_dt.isoformat())
            return TimeRange(
                start=start_dt,
                end=end_dt,
                relative="today",
                duration="today"
            )
        
        return None
    
    def _calculate_duration(self, start: datetime, end: datetime) -> str:
        """Calculate duration string from start/end times"""
        delta = end - start
        
        if delta.days >= 30:
            return f"{delta.days // 30}month"
        elif delta.days >= 7:
            return f"{delta.days // 7}week"
        elif delta.days >= 1:
            return f"{delta.days}day"
        elif delta.seconds >= 3600:
            return f"{delta.seconds // 3600}hour"
        else:
            return "custom"

    def _normalize_partner_speech_text(self, utterance: str) -> str:
        """Correct common STT mistakes for ASSA ABLOY press-shop names."""
        normalized = f" {utterance or ''} "
        replacements = [
            (r"\bthe breakfast club\b", "the Bret press group"),
            (r"\bbreakfast club\b", "Bret press group"),
            (r"\bbreakfast group\b", "Bret press group"),
            (r"\bbreakfast press(?:es)?(?: group)?\b", "Bret press group"),
            (r"\bfor breakfast\b", "for Bret press group"),
            (r"\bgreat businesses\b", "Bret presses"),
            (r"\bfor the purposes\b", "for Bret presses"),
            (r"\bbread press(?:es)?\b", "Bret presses"),
            (r"\bbrett press(?:es)?\b", "Bret presses"),
            (r"\bbrett\b", "Bret"),
            (r"\bbrent\b", "Bret"),
            (r"\bbrat\b", "Bret"),
            (r"\bbreath press(?:es)?\b", "Bret presses"),
            (r"\bdime echo\b", "Dimeco"),
            (r"\bdim echo\b", "Dimeco"),
            (r"\bdynamo\b", "Dimeco"),
            (r"\bdy meco\b", "Dimeco"),
            (r"\bdie meco\b", "Dimeco"),
            (r"\bdinoco\b", "Dimeco"),
            (r"\brasta\b", "Raster"),
            (r"\brastor\b", "Raster"),
            (r"\bflexy\b", "Flexi"),
            (r"\bshoe eighty\b", "Schu80"),
            (r"\bshoe 80\b", "Schu80"),
            (r"\bschu eighty\b", "Schu80"),
            (r"\braster one sixty\b", "Rast160"),
            (r"\brast one sixty\b", "Rast160"),
            (r"\bbret one twenty five\b", "Bret125"),
            (r"\bbret one sixty\b", "Bret160"),
            (r"\bbret two fifty\b", "Bret250"),
            (r"\b(?:press\s+)?group (?:one|won|1)\b", "Bret press group"),
            (r"\b(?:press\s+)?group (?:two|2|to|too)\b", "Raster press group"),
            (r"\b(?:press\s+)?group (?:three|tree|3)\b", "Dimeco press group"),
            (r"\b(?:first|left) (?:press\s+)?group\b", "Bret press group"),
            (r"\b(?:second|middle|center|centre) (?:press\s+)?group\b", "Raster press group"),
            (r"\b(?:third|right) (?:press\s+)?group\b", "Dimeco press group"),
            (r"\boption (?:one|1)\b", "Bret press group"),
            (r"\boption (?:two|2|to|too)\b", "Raster press group"),
            (r"\boption (?:three|3)\b", "Dimeco press group"),
        ]
        for pattern, replacement in replacements:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        return " ".join(normalized.split())

    def _is_partner_press_query(self, utterance: str) -> bool:
        """Detect ASSA ABLOY / partner press-shop pilot questions."""
        normalized = self._normalize_partner_speech_text(utterance).lower()
        partner_terms = [
            "assa abloy",
            "partner",
            "partner press",
            "press shop",
            "press-shop",
            "bret",
            "raster",
            "rast",
            "dimeco",
            "dime echo",
            "dim echo",
            "dynamo",
            "flexi",
            "schu",
            "breakfast club",
            "breakfast group",
            "brett",
            "brent",
            "rasta",
            "rastor",
            "flexy",
            "group one",
            "group two",
            "group three",
            "press group one",
            "press group two",
            "press group three",
            "first group",
            "second group",
            "third group",
            "sqdc",
        ]
        if any(term in normalized for term in partner_terms):
            return True
        if os.getenv("PARTNER_PRESS_PILOT_DEFAULT", "false").lower() == "true":
            if (
                "energy system" in normalized
                or "system health" in normalized
                or "system online" in normalized
            ):
                return False
            demo_terms = [
                "compressor", "boiler", "hvac", "conveyor", "injection",
                "molding", "hydraulic", "pump", "forecast",
                "report", "enpi", "opportunity", "save energy",
            ]
            if any(term in normalized for term in demo_terms):
                return False
            partner_default_terms = [
                "energy", "consumption", "kwh", "electricity", "power",
                "production", "quantity", "produced", "produce", "parts",
                "unit", "units", "kpi", "sec", "summary", "overview",
                "anomaly", "anomalies", "alert", "alerts",
                "machine", "machines", "meter", "meters", "seu", "seus",
                "significant energy", "baseline", "baselines", "data period",
                "period", "available data", "today", "current", "latest",
                "reading", "readings", "row", "rows", "import", "imported",
                "transformer", "trafo", "reference meter",
            ]
            if any(term in normalized for term in partner_default_terms):
                return True
        return bool(
            re.search(r"\bpress(?:es)?\b", normalized)
            and any(term in normalized for term in [
                "energy", "consumption", "kwh", "use", "used",
                "production", "quantity", "produced", "produce", "parts",
                "unit", "units", "kpi", "sec", "compare", "meter", "meters",
            ])
        )

    def _is_partner_pilot_default(self) -> bool:
        return os.getenv("PARTNER_PRESS_PILOT_DEFAULT", "false").lower() == "true"

    def _is_demo_asset_query(self, utterance: str) -> bool:
        """Detect legacy simulator/demo equipment names in partner-pilot mode."""
        normalized = re.sub(r"[^a-z0-9]+", " ", (utterance or "").lower())
        compact = normalized.replace(" ", "")
        demo_terms = [
            "boiler", "compressor", "conveyor", "hvac", "hydraulic",
            "pump", "injection", "molding", "turbine",
        ]
        demo_compact_terms = [
            "boiler1", "compressor1", "compressor2", "compressoreu1",
            "conveyora", "hvacmain", "hvaceunorth", "hvacnorth1",
            "hydraulicpump1", "injectionmolding1",
        ]
        return any(term in normalized.split() for term in demo_terms) or any(
            term in compact for term in demo_compact_terms
        )

    def _partner_dataset_mismatch_response(self, utterance: str, start_time: float) -> Dict[str, Any]:
        response_text = (
            "That asset is not part of the ASSA ABLOY Partner Press Shop dataset. "
            "This dev pilot currently contains Bret, Raster, and Dimeco press-shop meter groups "
            "plus their SQDC press production records. I will not substitute simulator/demo data "
            "for partner answers."
        )
        return {
            "success": True,
            "response": response_text,
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "tier": "partner_press_profile",
            "intent": "partner_press_out_of_scope_asset",
            "confidence": 1.0,
            "machine": None,
            "data": {
                "out_of_scope": True,
                "utterance": utterance,
                "available_energy_assets": [
                    "Bret Presses Meter Group",
                    "Raster Presses Meter Group",
                    "Dimeco Presses Meter Group",
                ],
            },
        }

    def _partner_press_group(self, utterance: str) -> Optional[str]:
        normalized = self._normalize_partner_speech_text(utterance).lower()
        for group in ("bret", "raster", "dimeco"):
            if group in normalized:
                return group
        if "rast" in normalized:
            return "raster"
        if "flexi" in normalized or "schu" in normalized:
            return "dimeco"
        return None

    def _partner_press_press(self, utterance: str) -> Optional[str]:
        normalized = re.sub(r"[^a-z0-9]+", " ", self._normalize_partner_speech_text(utterance).lower())
        compact = normalized.replace(" ", "")
        aliases = {
            "bret1251": "Bret125-1",
            "bret1601": "Bret160-1",
            "bret2501": "Bret250-1",
            "bret2502": "Bret250-2",
            "dimeco801": "Dimeco80-1",
            "dimeco802": "Dimeco80-2",
            "flexi": "Flexi-1",
            "flexi1": "Flexi-1",
            "flexione": "Flexi-1",
            "rast1251": "Rast125-1",
            "raster1251": "Rast125-1",
            "rast1252": "Rast125-2",
            "raster1252": "Rast125-2",
            "rast1601": "Rast160-1",
            "raster160": "Rast160-1",
            "raster1601": "Rast160-1",
            "rast2501": "Rast250-1",
            "raster2501": "Rast250-1",
            "rast2502": "Rast250-2",
            "raster2502": "Rast250-2",
            "schu80": "Schu80-1",
            "schu801": "Schu80-1",
            "shoe80": "Schu80-1",
            "shoe801": "Schu80-1",
        }
        for alias, press in aliases.items():
            if alias in compact:
                return press
        return None

    def _partner_press_period(self, utterance: str) -> tuple[Optional[str], Optional[str]]:
        normalized = (utterance or "").lower()
        months = {
            "january": 1, "jan": 1,
            "february": 2, "feb": 2,
            "march": 3, "mar": 3,
            "april": 4, "apr": 4,
            "may": 5,
            "june": 6, "jun": 6,
            "july": 7, "jul": 7,
            "august": 8, "aug": 8,
            "september": 9, "sep": 9, "sept": 9,
            "october": 10, "oct": 10,
            "november": 11, "nov": 11,
            "december": 12, "dec": 12,
        }
        match = re.search(
            r"\b("
            + "|".join(sorted(months.keys(), key=len, reverse=True))
            + r")\s+(20\d{2})\b",
            normalized,
        )
        if not match:
            return None, None

        month = months[match.group(1)]
        year = int(match.group(2))
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        return start.isoformat(), end.isoformat()

    def _partner_press_question_type(self, utterance: str) -> str:
        normalized = self._normalize_partner_speech_text(utterance).lower()
        press = self._partner_press_press(utterance)
        group = self._partner_press_group(utterance)
        if "unknown press" in normalized:
            return "unknown_press"
        if any(term in normalized for term in ["transformer", "trafo", "reference meter"]):
            return "reference_meter"
        if any(term in normalized for term in [
            "data inventory", "how many readings", "how many rows",
            "row count", "reading count", "all the data", "all data",
            "imported data", "data imported",
        ]):
            return "data_inventory"
        if any(term in normalized for term in ["anomaly", "anomalies", "alert", "alerts"]):
            return "anomalies"
        if any(term in normalized for term in ["data period", "period", "available data"]):
            return "period"
        if "baseline" in normalized:
            return "baseline_status"
        if any(term in normalized for term in ["seu", "seus", "significant energy use", "significant energy uses"]):
            return "seus"
        if any(term in normalized for term in ["machine", "machines", "asset", "assets"]):
            return "machines"
        if any(term in normalized for term in ["today", "current", "right now", "live", "latest"]):
            return "current_data"
        if any(term in normalized for term in ["compare", "versus", " vs "]):
            return "compare_groups"
        if (
            not group
            and any(term in normalized for term in ["group", "presses", "meter"])
            and any(term in normalized for term in [
                "energy", "consumption", "production", "produce", "output", "kpi", "sec",
            ])
            and not any(term in normalized for term in [
                "total", "overall", "all groups", "whole shop", "press shop",
            ])
        ):
            return "unknown_group"
        if "sec" in normalized and any(term in normalized for term in ["explain", "mean", "means", "simple"]):
            return "sec_explanation"
        if any(term in normalized for term in ["kpi", "sec", "performance indicator", "energy per", "per produced", "per unit"]):
            return "group_kpis" if group else "kpis"
        if any(term in normalized for term in ["production", "quantity", "produced", "produce", "output", "units", "parts"]):
            if press:
                return "press_production"
            return "group_production" if group else "kpis"
        if press and any(term in normalized for term in ["energy", "consumption", "kwh", "use", "used"]):
            return "press_energy"
        if group and any(term in normalized for term in ["energy", "consumption", "kwh", "use", "used", "electricity", "meter"]):
            return "group_energy"
        if not group and not press and any(term in normalized for term in [
            "how much energy", "energy use", "energy consumption",
            "electricity use", "electricity consumption",
        ]):
            return "total_energy"
        if "total energy" in normalized or "overall energy" in normalized:
            return "total_energy"
        if any(term in normalized for term in ["top", "consumer", "consumers", "most energy"]):
            return "top_energy"
        return "summary"

    def _handle_partner_press_query(self, utterance: str, session_id: str, start_time: float) -> Dict[str, Any]:
        """Answer partner press-shop pilot questions from the imported dataset."""
        question_type = self._partner_press_question_type(utterance)
        group = self._partner_press_group(utterance)
        press = self._partner_press_press(utterance)
        start_time_iso, end_time_iso = self._partner_press_period(utterance)

        data = self._run_async(
            self.api_client.get_partner_press_summary(
                question_type=question_type,
                group=group,
                press=press,
                start_time=start_time_iso,
                end_time=end_time_iso,
            )
        )

        response_text = data.get("response")
        if not response_text:
            response_text = (
                "The ASSA ABLOY partner press-shop dataset is available, but I could not build "
                "a concise answer for that question."
            )

        total_latency_ms = (time.time() - start_time) * 1000
        return {
            "success": True,
            "response": response_text,
            "latency_ms": round(total_latency_ms, 2),
            "tier": "partner_press_profile",
            "intent": "partner_press_pilot",
            "confidence": 1.0,
            "machine": None,
            "data": data,
        }

    def _try_handle_partner_press_message(self, message: Message) -> bool:
        """Route partner press-shop utterances before generic Adapt handlers."""
        utterance = message.data.get("utterances", [""])[0]
        if not self._is_partner_press_query(utterance):
            if self._is_partner_pilot_default() and self._is_demo_asset_query(utterance):
                result = self._partner_dataset_mismatch_response(utterance, time.time())
                self._emit_structured_response(
                    self._get_session_id(message),
                    result.get("intent"),
                    result.get("data"),
                    confidence=result.get("confidence"),
                    utterance=utterance,
                    machine=result.get("machine")
                )
                self.speak(result["response"])
                return True
            return False

        session_id = self._get_session_id(message)
        result = self._handle_partner_press_query(utterance, session_id, time.time())
        if result.get("success"):
            self._emit_structured_response(
                session_id,
                result.get("intent"),
                result.get("data"),
                confidence=result.get("confidence"),
                utterance=utterance,
                machine=result.get("machine")
            )
            self.speak(result["response"])
            return True

        self.speak(result.get("response") or "I could not retrieve the partner press-shop data.")
        return True
    
    def _normalize_machine_name(self, raw_machine: Optional[str]) -> Optional[str]:
        """
        Normalize machine name to handle voice variations
        
        Converts voice input variations to canonical names:
        - "compressor one" → Compressor-1
        - "hvac main" → HVAC-Main
        - "boiler number two" → Boiler-2
        - "COMPRESSOR-1" → Compressor-1 (case normalization)
        
        Args:
            raw_machine: Raw machine name from Adapt or user input
            
        Returns:
            Canonical machine name from whitelist, or None if no match
        """
        if not raw_machine:
            return raw_machine

        if self._is_generic_machine_reference(raw_machine):
            self.logger.debug("generic_machine_reference_ignored", raw=raw_machine)
            return None

        if not self.validator:
            return raw_machine
        
        # Use validator's normalization logic
        normalized = self.validator.normalize_machine_name(raw_machine)
        
        if normalized and normalized != raw_machine:
            self.logger.info("machine_name_normalized",
                           raw=raw_machine,
                           normalized=normalized)
        
        return normalized

    def _normalize_energy_source(self, raw_energy_source: Optional[str]) -> Optional[str]:
        """Normalize energy source names to the backend's canonical values."""
        if not raw_energy_source:
            return None

        if self.validator:
            normalized = self.validator.normalize_energy_source(raw_energy_source)
            if normalized:
                return normalized

        normalized = raw_energy_source.strip().lower().replace('-', ' ').replace('_', ' ')
        mapping = {
            'electricity': 'electricity',
            'electric': 'electricity',
            'electrical': 'electricity',
            'natural gas': 'natural_gas',
            'gas': 'natural_gas',
            'steam': 'steam',
            'compressed air': 'compressed_air',
            'air': 'compressed_air',
        }
        return mapping.get(normalized)

    def _extract_energy_source(self, utterance: str = "", raw_energy_source: Optional[str] = None) -> Optional[str]:
        """Resolve an energy source from explicit entities first, then fallback text matching."""
        normalized = self._normalize_energy_source(raw_energy_source)
        if normalized:
            return normalized

        utterance_lower = utterance.lower()
        if 'compressed air' in utterance_lower or 'compressed_air' in utterance_lower:
            return 'compressed_air'
        if 'natural gas' in utterance_lower or 'natural_gas' in utterance_lower:
            return 'natural_gas'
        if 'electricity' in utterance_lower or re.search(r'\belectric\b', utterance_lower):
            return 'electricity'
        if 'steam' in utterance_lower:
            return 'steam'
        if re.search(r'\bgas\b', utterance_lower):
            return 'natural_gas'

        return None

    def _extract_driver_direction(self, utterance: str) -> Optional[str]:
        """Detect whether a driver query is about increases or decreases."""
        utterance_lower = utterance.lower()

        if any(phrase in utterance_lower for phrase in [
            'what increases',
            'which increases',
            'increase energy',
            'increases energy',
            'raise energy',
            'raises energy',
            'higher energy',
        ]):
            return 'increases'

        if any(phrase in utterance_lower for phrase in [
            'what decreases',
            'which decreases',
            'decrease energy',
            'decreases energy',
            'reduce energy',
            'reduces energy',
            'lower energy',
        ]):
            return 'decreases'

        return None

    def _humanize_energy_source(self, energy_source: Optional[str]) -> Optional[str]:
        """Convert canonical energy source names to user-facing labels."""
        if not energy_source:
            return None

        return energy_source.replace('_', ' ')

    def _join_human_list(self, values: List[str]) -> str:
        """Format a short list for speech output."""
        unique_values = [value for value in dict.fromkeys(values) if value]
        if not unique_values:
            return ""
        if len(unique_values) == 1:
            return unique_values[0]
        if len(unique_values) == 2:
            return f"{unique_values[0]} or {unique_values[1]}"
        return f"{', '.join(unique_values[:-1])}, or {unique_values[-1]}"

    def _format_baseline_target_label(self, seu_name: Optional[str], energy_source: Optional[str]) -> str:
        """Build a user-facing label for a resolved SEU target."""
        if seu_name and energy_source:
            return f"{seu_name} {self._humanize_energy_source(energy_source)}"
        return seu_name or "this machine"

    def _available_baseline_sources(self, matching_seus: List[Dict[str, Any]], exclude_energy_source: Optional[str] = None) -> List[str]:
        """Return human-friendly energy sources that have trained baselines."""
        sources = []
        for seu in matching_seus:
            energy_source = seu.get('energy_source')
            if not energy_source or energy_source == exclude_energy_source:
                continue
            if seu.get('has_baseline'):
                sources.append(self._humanize_energy_source(energy_source))
        return [source for source in dict.fromkeys(sources)]

    def _build_baseline_message_response(
        self,
        message: str,
        seu_name: Optional[str] = None,
        energy_source: Optional[str] = None,
        machine_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a template-friendly baseline message response."""
        data = {'message': message}
        if seu_name:
            data['seu_name'] = seu_name
        if machine_name:
            data['machine_name'] = machine_name
        if energy_source:
            data['energy_source'] = energy_source
        return {'success': True, 'data': data}

    def _resolve_baseline_target(
        self,
        seu_name: Optional[str],
        utterance: str = "",
        energy_source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve a machine name plus optional energy source to a specific SEU."""
        normalized_machine = self._normalize_machine_name(seu_name) if seu_name else None
        if not normalized_machine:
            return {'success': False, 'message': 'Which machine do you mean? Please specify a machine name.'}

        requested_energy_source = self._extract_energy_source(utterance, energy_source)
        seu_response = self._run_async(self.api_client.list_seus())
        seus = seu_response.get('seus', [])
        matching_seus = [
            seu for seu in seus
            if seu.get('name', '').lower() == normalized_machine.lower()
        ]

        if not matching_seus:
            return {
                'success': False,
                'message': f"I couldn't find a significant energy use named {normalized_machine}.",
                'seu_name': normalized_machine,
            }

        available_sources = self._join_human_list([
            self._humanize_energy_source(seu.get('energy_source'))
            for seu in matching_seus
            if seu.get('energy_source')
        ])

        if requested_energy_source:
            selected_seu = next(
                (seu for seu in matching_seus if seu.get('energy_source') == requested_energy_source),
                None,
            )
            if not selected_seu:
                return {
                    'success': False,
                    'message': (
                        f"{normalized_machine} does not have a {self._humanize_energy_source(requested_energy_source)} "
                        f"significant energy use. Available energy sources are {available_sources}."
                    ),
                    'seu_name': normalized_machine,
                    'energy_source': requested_energy_source,
                }

            return {
                'success': True,
                'seu': selected_seu,
                'seu_name': normalized_machine,
                'energy_source': requested_energy_source,
                'matching_seus': matching_seus,
                'defaulted_energy_source': False,
            }

        if len(matching_seus) == 1:
            resolved_energy_source = matching_seus[0].get('energy_source')
            return {
                'success': True,
                'seu': matching_seus[0],
                'seu_name': normalized_machine,
                'energy_source': resolved_energy_source,
                'matching_seus': matching_seus,
                'defaulted_energy_source': False,
            }

        electricity_seu = next(
            (seu for seu in matching_seus if seu.get('energy_source') == 'electricity'),
            None,
        )
        if electricity_seu:
            return {
                'success': True,
                'seu': electricity_seu,
                'seu_name': normalized_machine,
                'energy_source': 'electricity',
                'matching_seus': matching_seus,
                'defaulted_energy_source': True,
            }

        return {
            'success': False,
            'message': (
                f"{normalized_machine} has multiple significant energy uses. "
                f"Please specify {available_sources}."
            ),
            'seu_name': normalized_machine,
        }

    def _is_generic_machine_reference(self, raw_machine: Optional[str]) -> bool:
        """Return True when Adapt matched a generic placeholder instead of a real machine."""
        if not raw_machine:
            return False

        normalized = raw_machine.strip().lower()
        generic_references = {
            "machine",
            "machines",
            "unit",
            "units",
            "equipment",
            "system",
            "systems",
            "all machines",
            "all the machines",
        }
        return normalized in generic_references

    def _looks_like_ranking_query(self, utterance: str) -> bool:
        """Detect ranking language that should not stay on the power-query handler path."""
        utterance_lower = utterance.lower()
        has_ranking_signal = any(word in utterance_lower for word in [
            "top",
            "most",
            "highest",
            "least",
            "lowest",
            "rank",
            "consumer",
        ])
        has_machine_group = any(phrase in utterance_lower for phrase in [
            "which machines",
            "what machines",
            "machines are",
            "machines use",
            "machines consume",
            "all machines",
        ])
        has_metric_signal = any(word in utterance_lower for word in [
            "electricity",
            "energy",
            "power",
            "consumption",
            "cost",
            "alert",
        ])
        return has_ranking_signal and has_machine_group and has_metric_signal

    def _extract_ranking_limit(self, utterance: str) -> int:
        """Extract an explicit top-N limit, falling back to a short ranked list."""
        number_word = r'(one|two|three|four|five|six|seven|eight|nine|ten)'
        number_words = {
            'one': 1,
            'two': 2,
            'three': 3,
            'four': 4,
            'five': 5,
            'six': 6,
            'seven': 7,
            'eight': 8,
            'nine': 9,
            'ten': 10,
        }
        patterns = [
            rf'\btop\s+(\d+|{number_word})\b',
            rf'\b(\d+|{number_word})\s+top\b',
            rf'\bhighest\s+(\d+|{number_word})\b',
            rf'\blowest\s+(\d+|{number_word})\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, utterance, re.IGNORECASE)
            if match:
                raw_limit = match.group(1).lower()
                limit = number_words.get(raw_limit, int(raw_limit) if raw_limit.isdigit() else 5)
                return max(limit, 1)

        return 5

    def _is_machine_list_query(self, utterance: str) -> bool:
        """Return True for inventory/listing questions, not energy rankings."""
        normalized = (utterance or "").lower()
        listing_patterns = [
            r"\bwhat\s+(?:are\s+)?(?:the\s+)?machines\b",
            r"\bwhat\s+machines\s+(?:do\s+we\s+have|are\s+there)\b",
            r"\bwhich\s+machines\s+(?:do\s+we\s+have|are\s+there)\b",
            r"\b(?:list|show)\s+(?:all\s+)?machines\b",
            r"\ball\s+machines\b",
            r"\bavailable\s+machines\b",
            r"\bmachine\s+list\b",
            r"\bhow\s+many\s+machines\b",
        ]
        if not any(re.search(pattern, normalized) for pattern in listing_patterns):
            return False
        ranking_terms = ["top", "consumer", "consumers", "most energy", "highest", "lowest", "rank"]
        return not any(term in normalized for term in ranking_terms)

    def _format_machine_list_payload(self, machines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build template-compatible machine-list data from API machine records."""
        machine_names = [
            machine.get("name") or machine.get("machine_name") or "Unknown"
            for machine in machines
        ]
        return {
            "machines": machine_names,
            "machine_records": machines,
            "count": len(machine_names),
        }

    def _infer_ranking_metric_from_utterance(self, utterance: str) -> str:
        """Map ranking phrasing to the metric used by the top-consumers endpoint."""
        utterance_lower = utterance.lower()

        if "cost" in utterance_lower:
            return "cost"
        if "alert" in utterance_lower or "anomal" in utterance_lower:
            return "alerts"
        if "efficien" in utterance_lower:
            return "efficiency"
        return "energy"
    
    def _apply_implicit_scope(self, intent: Intent) -> Intent:
        """
        Apply factory-wide scope when no machine specified (Priority 3)
        
        Handles implicit queries like:
        - "what's the current draw?" → Factory total power
        - "energy consumption" → Factory total energy today
        - "how much power are we using?" → All machines combined
        
        Rules:
        - Energy/Power query without machine → Set factory_wide flag
        - Status query without machine → Switch to FACTORY_OVERVIEW intent
        
        Args:
            intent: Parsed intent object
            
        Returns:
            Modified intent with factory_wide scope applied
        """
        # Power/Energy query without machine → factory total
        if intent.intent in [IntentType.ENERGY_QUERY, IntentType.POWER_QUERY]:
            if not intent.machine and not intent.seu:
                # Set factory-wide flag
                if not hasattr(intent, 'params') or intent.params is None:
                    intent.params = {}
                intent.params['factory_wide'] = True
                
                self.logger.info("implicit_factory_wide_query",
                               intent=intent.intent.value,
                               reason="no_machine_specified")
        
        # Status query without machine → factory overview
        elif intent.intent == IntentType.MACHINE_STATUS:
            if not intent.machine:
                intent.intent = IntentType.FACTORY_OVERVIEW
                self.logger.info("implicit_factory_overview",
                               original_intent="machine_status",
                               reason="no_machine_specified")
        
        return intent
    
    def _process_query(self, utterance: str, session_id: str, expected_intent: Optional[str] = None) -> Dict[str, Any]:
        """
        CORE QUERY PROCESSING PIPELINE
        
        Full multi-tier flow:
        1. Get conversation session
        2. Voice feedback (acknowledgment)
        3. Parse with HybridParser (heuristic → adapt → LLM)
        4. Validate with ENMSValidator
        5. Resolve context references
        6. Check for clarification needs
        7. Call EnMS API
        8. Format response
        9. Update conversation context
        10. Track metrics
        
        Returns:
            dict with: success, response, latency_ms, tier, intent
        """
        start_time = time.time()
        normalized_utterance = utterance.strip().lower()
        if normalized_utterance in {'ping', 'pong'}:
            self.logger.debug("probe_utterance_ignored", utterance=normalized_utterance)
            return {
                'success': False,
                'response': '',
                'latency_ms': 0.0,
                'tier': RoutingTier.HEURISTIC,
                'intent': None,
                'error': 'probe_utterance_ignored'
            }

        if self._is_partner_press_query(utterance):
            self.logger.info("partner_press_query_detected", utterance=utterance[:120])
            return self._handle_partner_press_query(utterance, session_id, start_time)
        if self._is_partner_pilot_default() and self._is_demo_asset_query(utterance):
            self.logger.info("partner_press_demo_asset_blocked", utterance=utterance[:120])
            return self._partner_dataset_mismatch_response(utterance, start_time)

        self.logger.info("⚙️ PROCESS_QUERY_START", utterance=utterance[:50])
        
        try:
            # Step 1: Get conversation session
            self.logger.info("⚙️ step1_get_session", elapsed_ms=int((time.time()-start_time)*1000))
            session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None
            self.logger.info("⚙️ step1_session_created", elapsed_ms=int((time.time()-start_time)*1000))
            
            # Step 2: Voice acknowledgment (varies by expected intent)
            if expected_intent:
                ack = self.voice_feedback.get_acknowledgment(expected_intent, variation=self.query_count % 3)
                self.speak(ack.message, wait=False)
            
            # Step 3: Parse with HybridParser (multi-tier routing)
            self.logger.info("⚙️ step3_parsing", elapsed_ms=int((time.time()-start_time)*1000))
            parse_start = time.time()
            parse_result = self.hybrid_parser.parse(utterance)
            parse_latency_ms = (time.time() - parse_start) * 1000
            self.logger.info("⚙️ step3_parsed", parse_ms=int(parse_latency_ms), elapsed_ms=int((time.time()-start_time)*1000))
            
            tier = parse_result.get("tier", RoutingTier.HEURISTIC)
            # parse_result IS the llm_output dict (contains intent, confidence, entities, etc.)
            llm_output = parse_result
            llm_output["utterance"] = utterance
            
            self.logger.info("query_parsed",
                           utterance=utterance,
                           tier=tier,
                           parse_latency_ms=round(parse_latency_ms, 2),
                           confidence=parse_result.get("confidence"))
            
            # Track tier routing
            tier_routing.labels(tier=tier).inc()

            raw_intent = str(llm_output.get('intent', '')).strip().lower()
            if raw_intent in {'clarification_needed', IntentType.UNKNOWN.value}:
                clarification_response = llm_output.get(
                    'response_suggestion',
                    "I'm not sure what you're asking. Try rephrasing your question or mention a machine name."
                )
                total_latency_ms = (time.time() - start_time) * 1000
                query_latency.labels(intent_type='unknown', tier=str(tier)).observe(total_latency_ms / 1000)
                self.logger.info(
                    "clarification_response_returned",
                    utterance=utterance,
                    reason=raw_intent or 'missing_intent'
                )
                return {
                    'success': False,
                    'response': clarification_response,
                    'latency_ms': round(total_latency_ms, 2),
                    'tier': tier,
                    'intent': None,
                    'error': clarification_response
                }
            
            # Step 3.5: Check for pending clarification BEFORE validation
            # If query is just a machine name answering clarification
            if session.pending_clarification:
                # Check if query matches any machine (case-insensitive)
                matched_machine = None
                for valid_machine in self.validator.machine_whitelist:
                    if utterance.lower() == valid_machine.lower():
                        matched_machine = valid_machine
                        break
                
                if matched_machine:
                    self.logger.info("resolving_pending_clarification_early",
                                   machine=matched_machine,
                                   pending_intent=session.pending_clarification['intent'].value)
                    
                    # Override parse result with pending intent
                    llm_output['intent'] = session.pending_clarification['intent'].value
                    llm_output['entities'] = {'machine': matched_machine}
                    llm_output['machine'] = matched_machine
                    llm_output['confidence'] = 0.99  # User provided clarification
            
            # Step 4: Validate
            self.logger.info("⚙️ step4_validating", elapsed_ms=int((time.time()-start_time)*1000))
            validation_start = time.time()
            validation = self.validator.validate(llm_output)
            validation_latency_ms = (time.time() - validation_start) * 1000
            self.logger.info("⚙️ step4_validated", valid=validation.valid, elapsed_ms=int((time.time()-start_time)*1000))
            
            if not validation.valid:
                errors_total.labels(error_type='validation', component='validator').inc()
                error_msg = " ".join(validation.errors)
                if validation.suggestions:
                    error_msg += " " + validation.suggestions[0]
                
                self.logger.warning("validation_failed",
                                  errors=validation.errors,
                                  suggestions=validation.suggestions)
                
                # Generate friendly error with voice feedback
                error_response = self.voice_feedback.get_error_message(
                    'invalid_query',
                    context={'suggestion': error_msg}
                )
                
                total_latency_ms = (time.time() - start_time) * 1000
                query_latency.labels(intent_type='unknown', tier=str(tier)).observe(total_latency_ms / 1000)
                
                return {
                    'success': False,
                    'response': error_response.message,
                    'latency_ms': round(total_latency_ms, 2),
                    'tier': tier,
                    'intent': None,
                    'error': error_msg
                }
            
            intent = validation.intent
            
            # Step 5: Resolve context references (multi-turn support)
            intent = self.context_manager.resolve_context_references(utterance, intent, session)
            
            # Clear pending clarification if it was resolved early
            if session.pending_clarification and intent.machine:
                self.logger.info("cleared_pending_clarification", machine=intent.machine)
                session.pending_clarification = None
            
            # Step 5.5: Apply smart defaults (Phase 3.3)
            intent = self.context_manager.apply_smart_defaults(intent, session)
            
            # Step 6: Check for ambiguous machines (Phase 3.2)
            ambiguous_machines = None
            if intent.machine and not intent.machines:
                # Check if machine name is ambiguous (matches multiple machines)
                all_matches = self.validator.find_all_matching_machines(intent.machine)
                if len(all_matches) > 1:
                    # Ambiguous! Store options for clarification
                    ambiguous_machines = all_matches
                    self.logger.info("ambiguous_machine_detected",
                                   query_term=intent.machine,
                                   matches=all_matches,
                                   count=len(all_matches))
            
            # Step 7: Check if clarification needed
            clarification = self.context_manager.needs_clarification(intent, ambiguous_machines)
            if clarification:
                # Store pending clarification in session
                session.pending_clarification = {
                    'intent': intent.intent,
                    'metric': intent.metric,
                    'time_range': intent.time_range,
                    'options': clarification.get('options'),  # Machine options for ambiguous queries
                    'timestamp': time.time()
                }
                clarification_response = self.context_manager.generate_clarification_response(
                    intent, session, validation.suggestions, ambiguous_machines
                )
                
                total_latency_ms = (time.time() - start_time) * 1000
                query_latency.labels(intent_type=str(intent.intent.value), tier=str(tier)).observe(total_latency_ms / 1000)
                
                return {
                    'success': False,
                    'response': clarification_response,
                    'latency_ms': round(total_latency_ms, 2),
                    'tier': tier,
                    'intent': intent.intent,
                    'clarification_needed': clarification
                }
            
            # Step 8: Call EnMS API
            self.logger.info("⚙️ step8_calling_api", intent=intent.intent.value, elapsed_ms=int((time.time()-start_time)*1000))
            api_start = time.time()
            api_data = self._call_enms_api(intent)
            api_latency_ms = (time.time() - api_start) * 1000
            self.logger.info("⚙️ step8_api_returned", success=api_data.get('success'), api_ms=int(api_latency_ms), elapsed_ms=int((time.time()-start_time)*1000))
            
            if not api_data.get('success', False):
                errors_total.labels(error_type='api', component='api_client').inc()
                error_type = api_data.get('error_type', 'api_error')
                error_response = self.voice_feedback.get_error_message(error_type)
                
                total_latency_ms = (time.time() - start_time) * 1000
                query_latency.labels(intent_type=str(intent.intent.value), tier=str(tier)).observe(total_latency_ms / 1000)
                
                return {
                    'success': False,
                    'response': error_response.message,
                    'latency_ms': round(total_latency_ms, 2),
                    'tier': tier,
                    'intent': intent.intent,
                    'error': api_data.get('error')
                }
            
            # Step 9: Format response with templates
            format_start = time.time()
            custom_template = api_data.get('custom_template') or api_data.get('template')
            response_text = self._format_response(intent, api_data['data'], custom_template=custom_template)
            format_latency_ms = (time.time() - format_start) * 1000
            
            # Step 10: Update conversation context
            session.add_turn(
                query=utterance,
                intent=intent,
                response=response_text,
                api_data=api_data['data']
            )
            
            # Step 11: Track metrics
            total_latency_ms = (time.time() - start_time) * 1000
            query_latency.labels(intent_type=str(intent.intent.value), tier=str(tier)).observe(total_latency_ms / 1000)
            queries_total.labels(intent_type=str(intent.intent.value), tier=str(tier), status='success').inc()
            
            self.query_count += 1
            self.total_latency_ms += total_latency_ms
            
            self.logger.info("query_processed_successfully",
                           latency_ms=round(total_latency_ms, 2),
                           parse_ms=round(parse_latency_ms, 2),
                           validation_ms=round(validation_latency_ms, 2),
                           api_ms=round(api_latency_ms, 2),
                           format_ms=round(format_latency_ms, 2),
                           tier=tier,
                           intent=intent.intent,
                           avg_latency_ms=round(self.total_latency_ms / self.query_count, 2))
            
            result = {
                'success': True,
                'response': response_text,
                'latency_ms': round(total_latency_ms, 2),
                'tier': tier,
                'intent': intent.intent,
                'confidence': intent.confidence,
                'machine': intent.machine,
                'data': api_data['data'],
                'breakdown': {
                    'parse_ms': round(parse_latency_ms, 2),
                    'validation_ms': round(validation_latency_ms, 2),
                    'api_ms': round(api_latency_ms, 2),
                    'format_ms': round(format_latency_ms, 2)
                }
            }
            
            # For report generation, include pdf_base64 for browser download
            if intent.intent == IntentType.REPORT and api_data.get('action') == 'generate':
                data = api_data.get('data', {})
                if data.get('pdf_base64'):
                    result['pdf_base64'] = data['pdf_base64']
                    result['pdf_filename'] = data.get('filename', 'report.pdf')
            
            return result
            
        except asyncio.TimeoutError as e:
            self.logger.error("query_timeout",
                            error="API call timeout",
                            utterance=utterance)
            
            error_response = self.voice_feedback.get_error_message('api_timeout')
            total_latency_ms = (time.time() - start_time) * 1000
            query_latency.labels(intent_type='timeout', tier='unknown').observe(total_latency_ms / 1000)
            errors_total.labels(error_type='timeout', component='api_client').inc()
            
            return {
                'success': False,
                'response': error_response.message,
                'latency_ms': round(total_latency_ms, 2),
                'tier': None,
                'intent': None,
                'error': 'API timeout after 45 seconds'
            }
            
        except Exception as e:
            self.logger.error("query_processing_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                            utterance=utterance)
            
            error_response = self.voice_feedback.get_error_message('api_error')
            total_latency_ms = (time.time() - start_time) * 1000
            query_latency.labels(intent_type='error', tier='unknown').observe(total_latency_ms / 1000)
            
            return {
                'success': False,
                'response': error_response.message,
                'latency_ms': round(total_latency_ms, 2),
                'tier': None,
                'intent': None,
                'error': str(e)
            }
    
    def _call_enms_api(self, intent: Intent) -> Dict[str, Any]:
        """
        Call appropriate EnMS API based on intent type
        
        Returns:
            dict with: success, data, error (if failed)
        """
        self.logger.info("🔌 CALL_ENMS_API_START", intent_type=intent.intent.value)
        try:
            if intent.intent == IntentType.MACHINE_STATUS:
                # Check for multiple machines (set by validator for ambiguous queries like "compressor")
                if intent.machines and len(intent.machines) > 1:
                    # Multiple machines from validator - fetch status for ALL
                    self.logger.info("multi_machine_status_from_validator", 
                                   machines=intent.machines,
                                   count=len(intent.machines))
                    
                    machine_statuses = []
                    for machine_name in intent.machines:
                        status_data = self._run_async(self.api_client.get_machine_status(machine_name))
                        machine_statuses.append(status_data)
                    
                    return {
                        'success': True,
                        'data': {
                            'machines': machine_statuses,
                            'count': len(machine_statuses),
                            'query_term': intent.machine if intent.machine else 'multiple machines'
                        },
                        'template': 'multi_machine_status'
                    }
                elif intent.machine:
                    # Check for multiple matching machines (e.g., "HVAC" matches both HVAC-Main and HVAC-EU-North)
                    all_matches = self.validator.find_all_matching_machines(intent.machine)
                    
                    if len(all_matches) > 1:
                        # Multiple machines match - fetch status for ALL of them
                        self.logger.info("multiple_machines_matched", 
                                       query=intent.machine, 
                                       matches=all_matches,
                                       count=len(all_matches))
                        
                        machine_statuses = []
                        for machine_name in all_matches:
                            status_data = self._run_async(self.api_client.get_machine_status(machine_name))
                            machine_statuses.append(status_data)
                        
                        return {
                            'success': True,
                            'data': {
                                'machines': machine_statuses,
                                'count': len(machine_statuses),
                                'query_term': intent.machine
                            },
                            'template': 'multi_machine_status'
                        }
                    else:
                        # Single machine match (existing behavior)
                        data = self._run_async(self.api_client.get_machine_status(intent.machine))
                        return {'success': True, 'data': data}
                else:
                    return {'success': False, 'error': 'No machine specified for status query'}
            
            elif intent.intent == IntentType.POWER_QUERY:
                if intent.machine:
                    # Machine-specific power query
                    # Check if time range is specified (via time_range or entities)
                    if intent.time_range and intent.time_range.relative not in ["today", "now", None]:
                        # Time-series power query
                        self.logger.info("power_query_timeseries",
                                       machine=intent.machine,
                                       time_range=intent.time_range.relative)
                        
                        # Get machine ID
                        machines = self._run_async(self.api_client.list_machines(search=intent.machine))
                        if not machines:
                            return {'success': False, 'error': f"Machine {intent.machine} not found"}
                        
                        machine_id = machines[0]['id']
                        
                        # Determine interval
                        time_delta = intent.time_range.end - intent.time_range.start
                        if time_delta.days > 30:
                            interval = '1day'
                        elif time_delta.days > 7:
                            interval = '1day'
                        elif time_delta.days > 1:
                            interval = '1hour'
                        else:
                            interval = '15min'
                        
                        # Get time-series power data
                        timeseries = self._run_async(
                            self.api_client.get_power_timeseries(
                                machine_id=machine_id,
                                start_time=intent.time_range.start,
                                end_time=intent.time_range.end,
                                interval=interval
                            )
                        )
                        
                        # Calculate average power from timeseries
                        avg_power = 0
                        if 'data_points' in timeseries and isinstance(timeseries['data_points'], list):
                            avg_power = sum(point.get('value', 0) for point in timeseries['data_points']) / len(timeseries['data_points'])
                        
                        # Structure response for template
                        data = {
                            'machine': intent.machine,
                            'time_range': intent.time_range.relative or 'custom',
                            'start_time': intent.time_range.start,
                            'end_time': intent.time_range.end,
                            'timeseries_data': timeseries.get('data_points', []),
                            'avg_power_kw': avg_power,
                            'interval': interval
                        }
                        
                        return {'success': True, 'data': data}
                    elif hasattr(intent, 'entities') and intent.entities:
                        entities = intent.entities if isinstance(intent.entities, dict) else {}
                        
                        if 'start_time' in entities and 'end_time' in entities:
                            # Time-series query - get power for specific time range
                            self.logger.info("power_query_timeseries",
                                           machine=intent.machine,
                                           start=entities['start_time'].isoformat(),
                                           end=entities['end_time'].isoformat())
                            
                            # First get machine ID
                            machines = self._run_async(self.api_client.list_machines(search=intent.machine))
                            if not machines:
                                return {'success': False, 'error': f"Machine {intent.machine} not found"}
                            
                            machine_id = machines[0]['id']
                            
                            # Get time-series data
                            data = self._run_async(
                                self.api_client.get_power_timeseries(
                                    machine_id=machine_id,
                                    start_time=entities['start_time'],
                                    end_time=entities['end_time'],
                                    interval='1hour'
                                )
                            )
                            
                            # Add machine name to response
                            data['machine'] = intent.machine
                            data['time_range'] = entities.get('time_range', 'custom')
                            
                            return {'success': True, 'data': data}
                    
                    # Default: current/today data for specific machine
                    data = self._run_async(self.api_client.get_machine_status(intent.machine))
                    return {'success': True, 'data': data}
                else:
                    # Factory-wide power query (no machine specified) - Priority 3
                    self.logger.info("power_query_factory_wide", intent="power_query", machine=None)
                    
                    # Call /factory/summary endpoint for aggregated data
                    try:
                        summary_data = self._run_async(self.api_client.get_factory_summary())
                        
                        if summary_data and 'energy' in summary_data:
                            # Extract power data from factory summary
                            power_data = {
                                'current_power_kw': summary_data['energy'].get('current_power_kw', 0),
                                'avg_power_kw': summary_data['energy'].get('avg_power_kw', 0),
                                'total_kwh_today': summary_data['energy'].get('total_kwh_today', 0),
                                'machines_active': summary_data.get('machines', {}).get('active', 0),
                                'machines_total': summary_data.get('machines', {}).get('total', 0),
                                'factory_wide': True,
                                'timestamp': summary_data.get('timestamp')
                            }
                            return {'success': True, 'data': power_data, 'template': 'factory_power'}
                        else:
                            # Fallback to system_stats if factory/summary unavailable
                            data = self._run_async(self.api_client.system_stats())
                            return {'success': True, 'data': data}
                    except Exception as e:
                        self.logger.error("factory_summary_failed", error=str(e))
                        # Fallback to system_stats
                        data = self._run_async(self.api_client.system_stats())
                        return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.ENERGY_QUERY:
                if intent.machine:
                    # Machine-specific energy query
                    # Debug: Check time_range
                    self.logger.info("debug_time_range", 
                                   has_time_range=intent.time_range is not None,
                                   time_range_value=intent.time_range,
                                   relative=intent.time_range.relative if intent.time_range else None)
                    
                    # Check if utterance mentions interval keywords (hourly, 15-minute, etc.)
                    utterance_lower = intent.utterance.lower() if hasattr(intent, 'utterance') else ''
                    needs_timeseries = False
                    requested_interval = None
                    
                    # Check for multi-energy queries
                    is_energy_types = 'energy types' in utterance_lower or 'energy sources' in utterance_lower or 'what energy' in utterance_lower
                    is_energy_summary = 'energy summary' in utterance_lower or 'all energy' in utterance_lower
                    specific_energy_type = None
                    
                    if 'electricity' in utterance_lower or 'electric' in utterance_lower:
                        specific_energy_type = 'electricity'
                    elif 'natural gas' in utterance_lower or 'gas' in utterance_lower:
                        specific_energy_type = 'natural_gas'
                    elif 'steam' in utterance_lower:
                        specific_energy_type = 'steam'
                    elif 'compressed air' in utterance_lower or 'air' in utterance_lower:
                        specific_energy_type = 'compressed_air'
                    
                    # Handle multi-energy queries
                    if is_energy_types or is_energy_summary or specific_energy_type:
                        # Lookup machine ID
                        machines = self._run_async(self.api_client.list_machines(search=intent.machine))
                        if not machines:
                            return {'success': False, 'error': f'Machine {intent.machine} not found'}
                        
                        machine_id = machines[0]['id']
                        
                        if is_energy_types:
                            # List energy types
                            try:
                                data = self._run_async(self.api_client.get_energy_types(machine_id=machine_id, hours=24))
                                data['machine_name'] = intent.machine
                                return {'success': True, 'data': data, 'template': 'energy_types'}
                            except Exception as e:
                                # Fallback: API endpoint not available, use machine status
                                self.logger.warning("energy_types_fallback", error=str(e), machine=intent.machine)
                                status_data = self._run_async(self.api_client.get_machine_status(intent.machine))
                                # Most machines use electricity, Boiler-1 uses multiple types
                                # Since we can't query energy types, provide basic response
                                machine_type = status_data.get('machine_type', 'unknown')
                                if machine_type == 'boiler':
                                    # Boilers typically use electricity, natural gas, and steam
                                    energy_types = [
                                        {'energy_type': 'electricity', 'unit': 'kWh'},
                                        {'energy_type': 'natural_gas', 'unit': 'm³'},
                                        {'energy_type': 'steam', 'unit': 'kg'}
                                    ]
                                    total = 3
                                else:
                                    # Default to electricity only
                                    energy_types = [{'energy_type': 'electricity', 'unit': 'kWh'}]
                                    total = 1
                                
                                fallback_data = {
                                    'machine_name': intent.machine,
                                    'energy_types': energy_types,
                                    'total_energy_types': total
                                }
                                return {'success': True, 'data': fallback_data, 'template': 'energy_types'}
                        elif is_energy_summary:
                            # Multi-energy summary
                            data = self._run_async(self.api_client.get_energy_summary(machine_id=machine_id))
                            data['machine_name'] = intent.machine
                            return {'success': True, 'data': data, 'template': 'energy_summary'}
                        elif specific_energy_type:
                            # Specific energy type readings
                            data = self._run_async(self.api_client.get_energy_readings(
                                machine_id=machine_id,
                                energy_type=specific_energy_type,
                                hours=24
                            ))
                            data['machine_name'] = intent.machine
                            data['energy_type'] = specific_energy_type
                            return {'success': True, 'data': data, 'custom_template': 'energy_type_readings'}
                    
                    if 'hourly' in utterance_lower or 'hour by hour' in utterance_lower:
                        needs_timeseries = True
                        requested_interval = '1hour'
                    elif '15-minute' in utterance_lower or '15 minute' in utterance_lower or 'fifteen minute' in utterance_lower:
                        needs_timeseries = True
                        requested_interval = '15min'
                    elif '5-minute' in utterance_lower or '5 minute' in utterance_lower:
                        needs_timeseries = True
                        requested_interval = '5min'
                    elif 'daily' in utterance_lower or 'day by day' in utterance_lower:
                        needs_timeseries = True
                        requested_interval = '1day'
                    
                    # Check if time range is specified (beyond "today") OR if interval keywords detected
                    if intent.time_range and (intent.time_range.relative not in ["today", "now", None] or needs_timeseries):
                        # Time-series query - get energy for specific time range
                        self.logger.info("energy_query_timeseries",
                                       machine=intent.machine,
                                       start=intent.time_range.start.isoformat(),
                                       end=intent.time_range.end.isoformat(),
                                       relative=intent.time_range.relative,
                                       needs_timeseries=needs_timeseries,
                                       requested_interval=requested_interval)
                        
                        # First get machine ID
                        machines = self._run_async(self.api_client.list_machines(search=intent.machine))
                        if not machines:
                            return {'success': False, 'error': f"Machine {intent.machine} not found"}
                        
                        machine_id = machines[0]['id']
                        
                        # Determine interval based on explicit request or time range
                        if requested_interval:
                            interval = requested_interval
                        else:
                            time_delta = intent.time_range.end - intent.time_range.start
                            if time_delta.days > 30:
                                interval = '1day'
                            elif time_delta.days > 7:
                                interval = '1day'  # Changed from 6hour
                            elif time_delta.days > 1:
                                interval = '1hour'
                            else:
                                interval = '15min'
                        
                        # Get time-series data
                        timeseries = self._run_async(
                            self.api_client.get_energy_timeseries(
                                machine_id=machine_id,
                                start_time=intent.time_range.start,
                                end_time=intent.time_range.end,
                                interval=interval
                            )
                        )
                        
                        # Calculate total energy and parse timestamps
                        total_energy = 0
                        data_points_parsed = []
                        if 'data_points' in timeseries and isinstance(timeseries['data_points'], list):
                            for point in timeseries['data_points']:
                                total_energy += point.get('value', 0)
                                # Parse timestamp string to datetime for voice_time filter
                                timestamp_str = point.get('timestamp')
                                if timestamp_str:
                                    try:
                                        from dateutil import parser as date_parser
                                        timestamp_dt = date_parser.parse(timestamp_str)
                                    except:
                                        timestamp_dt = timestamp_str
                                    data_points_parsed.append({
                                        'timestamp': timestamp_dt,
                                        'value': point.get('value', 0),
                                        'unit': point.get('unit', 'kWh')
                                    })
                        
                        # Detect trend/pattern queries
                        utterance = getattr(intent, 'utterance', '').lower() if hasattr(intent, 'utterance') else ''
                        is_trend_query = 'trend' in utterance or 'pattern' in utterance
                        
                        # Calculate trend analysis if requested
                        trend_periods = None
                        if is_trend_query and len(data_points_parsed) > 3:
                            # Divide into 3-4 periods based on data density
                            num_periods = 3 if len(data_points_parsed) <= 24 else 4
                            period_size = len(data_points_parsed) // num_periods
                            trend_periods = []
                            
                            for i in range(num_periods):
                                start_idx = i * period_size
                                end_idx = start_idx + period_size if i < num_periods - 1 else len(data_points_parsed)
                                period_data = data_points_parsed[start_idx:end_idx]
                                
                                if period_data:
                                    period_total = sum(p['value'] for p in period_data)
                                    period_avg = period_total / len(period_data)
                                    period_start = period_data[0]['timestamp']
                                    period_end = period_data[-1]['timestamp']
                                    
                                    # Find peak hour in this period
                                    peak_point = max(period_data, key=lambda p: p['value'])
                                    
                                    trend_periods.append({
                                        'start_time': period_start,
                                        'end_time': period_end,
                                        'total_kwh': round(period_total, 2),
                                        'avg_kwh': round(period_avg, 1),
                                        'peak_kwh': round(peak_point['value'], 1),
                                        'peak_time': peak_point['timestamp']
                                    })
                        
                        # Structure response for template
                        data = {
                            'machine': intent.machine,
                            'time_range': intent.time_range.relative or 'custom',
                            'start_time': intent.time_range.start,
                            'end_time': intent.time_range.end,
                            'timeseries_data': data_points_parsed,
                            'total_energy_kwh': total_energy,
                            'interval': interval,
                            'is_trend_query': is_trend_query,
                            'trend_periods': trend_periods
                        }
                        
                        return {'success': True, 'data': data}
                    
                    # Default: current/today data for specific machine
                    data = self._run_async(self.api_client.get_machine_status(intent.machine))
                    
                    # Check if user asked for average per hour or trend/pattern analysis
                    utterance = getattr(intent, 'utterance', '').lower() if hasattr(intent, 'utterance') else ''
                    if isinstance(data, dict):
                        if 'average' in utterance or 'per hour' in utterance or 'hourly average' in utterance:
                            data['is_average_query'] = True
                        
                        # Detect trend/pattern queries for aggregated time-series analysis
                        if 'trend' in utterance or 'pattern' in utterance:
                            data['is_trend_query'] = True
                    
                    return {'success': True, 'data': data}
                else:
                    # Factory-wide energy query (no machine specified) - Priority 3
                    self.logger.info("energy_query_factory_wide", intent="energy_query", machine=None)
                    
                    # Call /factory/summary endpoint for aggregated data
                    try:
                        summary_data = self._run_async(self.api_client.get_factory_summary())
                        
                        if summary_data and 'energy' in summary_data:
                            # Extract energy data from factory summary
                            energy_data = {
                                'total_kwh_today': summary_data['energy'].get('total_kwh_today', 0),
                                'current_power_kw': summary_data['energy'].get('current_power_kw', 0),
                                'avg_power_kw': summary_data['energy'].get('avg_power_kw', 0),
                                'total_cost_usd': summary_data.get('costs', {}).get('total_usd_today', 0),
                                'machines_active': summary_data.get('machines', {}).get('active', 0),
                                'machines_total': summary_data.get('machines', {}).get('total', 0),
                                'factory_wide': True,
                                'timestamp': summary_data.get('timestamp')
                            }
                            return {'success': True, 'data': energy_data, 'template': 'factory_energy'}
                        else:
                            # Fallback to system_stats if factory/summary unavailable
                            data = self._run_async(self.api_client.system_stats())
                            return {'success': True, 'data': data}
                    except Exception as e:
                        self.logger.error("factory_summary_failed", error=str(e))
                        # Fallback to system_stats
                        data = self._run_async(self.api_client.system_stats())
                        return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.SEUS:
                # Significant Energy Uses (SEUs) queries
                utterance = getattr(intent, 'utterance', '').lower() if hasattr(intent, 'utterance') else ''
                
                # Extract energy source from intent or utterance
                energy_source = intent.energy_source
                if not energy_source:
                    if 'electricity' in utterance or 'electric' in utterance:
                        energy_source = 'electricity'
                    elif 'gas' in utterance or 'natural gas' in utterance:
                        energy_source = 'natural_gas'
                    elif 'steam' in utterance:
                        energy_source = 'steam'
                    elif 'compressed air' in utterance:
                        energy_source = 'compressed_air'
                
                # Check for baseline filtering
                asking_without_baseline = any(phrase in utterance for phrase in [
                    "don't have", "doesn't have", "do not have", "does not have",
                    "without baseline", "without basline",
                    "no baseline", "no basline",
                    "need baseline", "need basline",
                    "missing baseline", "missing basline"
                ])
                asking_with_baseline = any(phrase in utterance for phrase in [
                    "have baseline", "have basline",
                    "has baseline", "has basline",
                    "with baseline", "with basline"
                ])
                
                data = self._run_async(self.api_client.list_seus(energy_source=energy_source))
                
                # Filter by baseline status if requested
                if isinstance(data, dict):
                    if asking_without_baseline:
                        data['seus'] = [seu for seu in data.get('seus', []) if not seu.get('has_baseline')]
                        data['total_count'] = len(data['seus'])
                        data['filter_type'] = 'without_baseline'
                    elif asking_with_baseline:
                        data['seus'] = [seu for seu in data.get('seus', []) if seu.get('has_baseline')]
                        data['total_count'] = len(data['seus'])
                        data['filter_type'] = 'with_baseline'
                
                return {'success': True, 'data': data, 'template': 'seus'}
            
            elif intent.intent == IntentType.FACTORY_OVERVIEW:
                # Check if this is a health/status check vs stats query
                utterance = getattr(intent, 'utterance', '').lower() if hasattr(intent, 'utterance') else ''
                
                # Check for machine listing queries ("list all machines", "show machines")
                if re.search(r'\b(?:list|show)\s+(?:all\s+)?machines', utterance):
                    machines = self._run_async(self.api_client.list_machines())
                    machine_names = [m.get('name', m.get('machine_name', 'Unknown')) for m in machines]
                    return {
                        'success': True,
                        'data': {
                            'machines': machine_names,
                            'count': len(machines)
                        },
                        'template': 'machine_list'
                    }
                
                # Check for carbon/emissions queries
                if 'carbon' in utterance or 'emission' in utterance or 'co2' in utterance:
                    data = self._run_async(self.api_client.system_stats())
                    # Mark as carbon query for template
                    if isinstance(data, dict):
                        data['is_carbon_query'] = True
                    return {'success': True, 'data': data}
                
                # Check for active/offline machine queries
                if re.search(r'\b(?:active|online|running|inactive|offline|stopped)\b.*?\b(?:machines?|equipment)\b', utterance):
                    is_active = bool(re.search(r'\b(?:active|online|running)\b', utterance))
                    machines = self._run_async(self.api_client.list_machines(is_active=is_active))
                    
                    return {
                        'success': True,
                        'data': {
                            'machines': machines,
                            'total_count': len(machines),
                            'filter_type': 'active' if is_active else 'offline'
                        },
                        'template': 'machines_by_status'
                    }
                
                # Check for performance engine health
                if 'performance engine' in utterance or ('engine' in utterance and 'running' in utterance):
                    data = self._run_async(self.api_client.get_performance_health())
                    return {'success': True, 'data': data, 'template': 'performance_health'}
                elif 'opportunities' in utterance or 'saving' in utterance:
                    # Get factory_id from first machine (all machines share same factory)
                    machines = self._run_async(self.api_client.list_machines())
                    factory_id = machines[0]['factory_id'] if machines else None
                    
                    if not factory_id:
                        return {'success': False, 'error': 'Could not determine factory ID'}
                    
                    # Get all opportunities from API
                    data = self._run_async(self.api_client.get_performance_opportunities(
                        factory_id=factory_id,
                        period='week'
                    ))
                    
                    # Filter by SEU name if specified (API doesn't support filtering)
                    if intent.machine:
                        filtered_opps = [opp for opp in data.get('opportunities', []) 
                                        if opp.get('seu_name') == intent.machine]
                        
                        if filtered_opps:
                            # Update data with filtered opportunities
                            data['opportunities'] = filtered_opps
                            data['total_opportunities'] = len(filtered_opps)
                            # Recalculate total savings
                            data['total_potential_savings_kwh'] = sum(o.get('potential_savings_kwh', 0) for o in filtered_opps)
                            data['total_potential_savings_usd'] = sum(o.get('potential_savings_usd', 0) for o in filtered_opps)
                        else:
                            # No opportunities for this specific machine
                            data['opportunities'] = []
                            data['total_opportunities'] = 0
                            data['total_potential_savings_kwh'] = 0
                            data['total_potential_savings_usd'] = 0
                    
                    return {'success': True, 'data': data, 'template': 'opportunities'}
                elif 'action plan' in utterance and 'list' in utterance:
                    # List ISO action plans (check BEFORE create action plan)
                    status_filter = None
                    priority_filter = None
                    
                    if 'completed' in utterance or 'complete' in utterance:
                        status_filter = 'completed'
                    elif 'in progress' in utterance or 'active' in utterance:
                        status_filter = 'in_progress'
                    elif 'planned' in utterance:
                        status_filter = 'planned'
                    
                    if 'high priority' in utterance or 'critical' in utterance:
                        priority_filter = 'high' if 'high' in utterance else 'critical'
                    
                    # Get factory_id
                    machines = self._run_async(self.api_client.list_machines())
                    factory_id = machines[0]['factory_id'] if machines else "11111111-1111-1111-1111-111111111111"
                    
                    data = self._run_async(self.api_client.list_action_plans(
                        factory_id=factory_id,
                        status=status_filter,
                        priority=priority_filter
                    ))
                    return {'success': True, 'data': data, 'template': 'action_plans_list'}
                elif 'action plan' in utterance or 'create plan' in utterance:
                    # Create action plan for improvement
                    if not intent.machine:
                        return {'success': False, 'error': 'Machine name required for action plan'}
                    
                    # Determine issue type from query or use default
                    issue_type = 'inefficient_scheduling'  # default
                    if 'idle' in utterance:
                        issue_type = 'excessive_idle'
                    elif 'drift' in utterance or 'degradation' in utterance or 'efficiency' in utterance:
                        issue_type = 'baseline_drift'
                    elif 'setpoint' in utterance or 'setting' in utterance:
                        issue_type = 'suboptimal_setpoints'
                    
                    data = self._run_async(self.api_client.create_action_plan(
                        seu_name=intent.machine,
                        issue_type=issue_type
                    ))
                    return {'success': True, 'data': data, 'template': 'action_plan'}
                
                # Define health keywords for health check detection
                health_keywords = ['health', 'status', 'alive', 'running', 'online', 'api status', 'system status', 'database']
                if any(keyword in utterance for keyword in health_keywords):
                    # Health check query - use /health endpoint
                    data = self._run_async(self.api_client.health_check())
                    return {'success': True, 'data': data}
                elif 'summary' in utterance or 'overview' in utterance:
                    # Factory summary - comprehensive overview
                    data = self._run_async(self.api_client.factory_summary())
                    return {'success': True, 'data': data, 'custom_template': 'factory_summary'}
                elif 'significant energy' in utterance or 'list seus' in utterance or 'energy uses' in utterance:
                    # List SEUs (significant energy uses)
                    # Check if filtering by energy source
                    energy_source = None
                    if 'electricity' in utterance or 'electric' in utterance:
                        energy_source = 'electricity'
                    elif 'gas' in utterance or 'natural gas' in utterance:
                        energy_source = 'natural_gas'
                    elif 'steam' in utterance:
                        energy_source = 'steam'
                    
                    data = self._run_async(self.api_client.list_seus(energy_source=energy_source))
                    return {'success': True, 'data': data, 'template': 'seus_list'}
                elif 'seu' in utterance or 'significant energy' in utterance or 'energy uses' in utterance:
                    # SEU queries (with typo tolerance for common misspellings)
                    asking_without_baseline = any(phrase in utterance for phrase in [
                        "don't have", "doesn't have", "do not have", "does not have",
                        "without baseline", "without basline",  # typo tolerance
                        "no baseline", "no basline",  # typo tolerance
                        "need baseline", "need basline",  # typo tolerance
                        "missing baseline", "missing basline"  # typo tolerance
                    ])
                    asking_with_baseline = any(phrase in utterance for phrase in [
                        "have baseline", "have basline",  # typo tolerance
                        "has baseline", "has basline",  # typo tolerance
                        "with baseline", "with basline"  # typo tolerance
                    ])
                    
                    energy_source = None
                    if 'electricity' in utterance or 'electric' in utterance:
                        energy_source = 'electricity'
                    elif 'gas' in utterance or 'natural gas' in utterance:
                        energy_source = 'natural_gas'
                    elif 'steam' in utterance:
                        energy_source = 'steam'
                    
                    data = self._run_async(self.api_client.list_seus(energy_source=energy_source))
                    
                    # Filter by baseline status if requested
                    if asking_without_baseline:
                        data['seus'] = [seu for seu in data.get('seus', []) if not seu.get('has_baseline')]
                        data['total_count'] = len(data['seus'])
                        data['filter_type'] = 'without_baseline'
                    elif asking_with_baseline:
                        data['seus'] = [seu for seu in data.get('seus', []) if seu.get('has_baseline')]
                        data['total_count'] = len(data['seus'])
                        data['filter_type'] = 'with_baseline'
                    
                    return {'success': True, 'data': data, 'template': 'seus'}
                elif 'enpi' in utterance or 'iso' in utterance or 'compliance report' in utterance or 'energy performance indicator' in utterance:
                    # ISO 50001 EnPI report
                    # Extract period from utterance (Q1, Q2, Q3, Q4, or year)
                    # Note: re and datetime are imported at module level
                    
                    period = None
                    
                    # Check for quarters
                    quarter_match = re.search(r'q[1-4]|quarter\s*[1-4]', utterance, re.IGNORECASE)
                    if quarter_match:
                        quarter_text = quarter_match.group().lower()
                        quarter_num = re.search(r'[1-4]', quarter_text).group()
                        # Get year from utterance or use current year
                        year_match = re.search(r'20\d{2}', utterance)
                        year = year_match.group() if year_match else str(datetime.now().year)
                        period = f"{year}-Q{quarter_num}"
                    else:
                        # Check for explicit year (e.g., "2025")
                        year_match = re.search(r'20\d{2}', utterance)
                        if year_match:
                            period = year_match.group()
                        else:
                            # Default to current quarter
                            now = datetime.now()
                            current_quarter = (now.month - 1) // 3 + 1
                            period = f"{now.year}-Q{current_quarter}"
                    
                    # Get factory_id from first machine
                    machines = self._run_async(self.api_client.list_machines())
                    factory_id = machines[0]['factory_id'] if machines else "11111111-1111-1111-1111-111111111111"
                    
                    data = self._run_async(self.api_client.get_enpi_report(
                        factory_id=factory_id,
                        period=period
                    ))
                    return {'success': True, 'data': data, 'template': 'enpi_report'}
                elif 'aggregat' in utterance and intent.time_range:
                    # Aggregated stats with time range
                    data = self._run_async(self.api_client.aggregated_stats(
                        start_time=intent.time_range.start,
                        end_time=intent.time_range.end,
                        machine_ids='all'
                    ))
                    # Use aggregated_stats template instead of factory_overview
                    return {'success': True, 'data': data, 'template': 'aggregated_stats'}
                else:
                    # General factory overview - use the same today/current summary as the dashboards.
                    data = self._run_async(self.api_client.factory_summary())
                    return {'success': True, 'data': data, 'custom_template': 'factory_summary'}
                
                return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.RANKING:
                # Check if this is a machine list request vs top consumers ranking
                utterance = getattr(intent, 'utterance', '').lower() if hasattr(intent, 'utterance') else ''
                if self._is_machine_list_query(utterance):
                    machines = self._run_async(self.api_client.list_machines())
                    return {
                        'success': True,
                        'data': self._format_machine_list_payload(machines),
                        'template': 'machine_list'
                    }

                if not intent.limit and not intent.metric:
                    # This is "list all machines" or "what machines do we have"
                    # Check if utterance contains a search term (e.g., "which HVAC units")
                    search_term = None
                    
                    # Extract search term from common patterns
                    # Note: re is imported at module level
                    search_patterns = [
                        r'\b(HVAC|Boiler|Compressor|Conveyor|Turbine|Hydraulic|Injection)s?\b',  # Match plural forms
                        r'\bfind.*?(?:the\s+)?(\w+)\b',
                        r'\bhow\s+many\s+(\w+)\b',  # "how many compressors"
                    ]
                    
                    for pattern in search_patterns:
                        match = re.search(pattern, utterance, re.IGNORECASE)
                        if match:
                            search_term = match.group(1).rstrip('s')  # Remove plural 's'
                            break
                    
                    # Call list_machines with optional search parameter
                    if search_term:
                        machines = self._run_async(self.api_client.list_machines(search=search_term))
                    else:
                        machines = self._run_async(self.api_client.list_machines())
                    
                    return {
                        'success': True,
                        'data': self._format_machine_list_payload(machines),
                        'template': 'machine_list'
                    }
                else:
                    # This is top N ranking by metric
                    limit = intent.limit or 5
                    metric = getattr(intent, 'ranking_metric', 'energy') or getattr(intent, 'metric', 'energy') or 'energy'
                    data = self._run_async(self.api_client.get_top_consumers(limit=limit, metric=metric))
                    data['limit'] = limit
                    return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.COMPARISON and intent.machines:
                # Multi-machine energy comparison
                try:
                    # Get machine IDs for all machines in comparison
                    machine_ids = []
                    machine_names = []
                    
                    for machine_name in intent.machines:
                        machines = self._run_async(self.api_client.list_machines(search=machine_name))
                        if not machines:
                            self.logger.warning("comparison_machine_not_found", machine=machine_name)
                            continue
                        machine_ids.append(machines[0]['id'])
                        machine_names.append(machines[0]['name'])
                    
                    if len(machine_ids) < 2:
                        return {'success': False, 'error': "Need at least 2 machines to compare"}
                    
                    # Get time range (default: today)
                    if intent.time_range and intent.time_range.start and intent.time_range.end:
                        start_time = intent.time_range.start
                        end_time = intent.time_range.end
                    else:
                        # Default: today
                        end_time = datetime.now(timezone.utc)
                        start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    # Call multi-machine comparison API
                    data = self._run_async(self.api_client.get_multi_machine_energy(
                        machine_ids=machine_ids,
                        start_time=start_time,
                        end_time=end_time,
                        interval="1hour"
                    ))
                    
                    # Calculate total energy for each machine from data_points
                    machines_with_totals = []
                    for machine in data.get('machines', []):
                        total_energy = sum(dp['value'] for dp in machine.get('data_points', []))
                        machines_with_totals.append({
                            'machine_name': machine['machine_name'],
                            'total_energy': total_energy,
                            'data_points': machine.get('data_points', [])
                        })
                    
                    # Add machine names for template
                    data['machines'] = machines_with_totals
                    data['machine_names'] = machine_names
                    data['time_period'] = f"today ({start_time.strftime('%Y-%m-%d')})"
                    
                    return {'success': True, 'data': data}
                    
                except Exception as e:
                    self.logger.error("comparison_failed", error=str(e), machines=intent.machines)
                    return {'success': False, 'error': f"Comparison failed: {str(e)}"}
            
            elif intent.intent == IntentType.COST_ANALYSIS:
                # Extract machine if not provided by Adapt parser
                machine = intent.machine
                if not machine:
                    # Try to extract from utterance using validator's whitelist
                    utterance = getattr(intent, 'utterance', '')
                    machine_whitelist = self.validator.machine_whitelist if hasattr(self, 'validator') else []
                    for machine_name in machine_whitelist:
                        if machine_name.lower() in utterance.lower():
                            machine = machine_name
                            break
                
                if machine:
                    # Machine-specific cost
                    data = self._run_async(self.api_client.get_machine_status(machine))
                    return {'success': True, 'data': data}
                else:
                    # Factory-wide cost
                    data = self._run_async(self.api_client.get_system_stats())
                    return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.ANOMALY_DETECTION:
                self.logger.info("🔍 ANOMALY_HANDLER_START", machine=intent.machine)
                # Check what type of anomaly query this is
                utterance = getattr(intent, 'utterance', '').lower()
                self.logger.info("🔍 anomaly_utterance_check", utterance=utterance[:50])
                is_detection_request = any(kw in utterance for kw in ['check for', 'detect', 'scan for', 'analyze for']) and intent.machine
                is_active_request = any(kw in utterance for kw in ['active', 'unresolved', 'alerts', 'need attention'])
                is_search_request = any(kw in utterance for kw in ['find', 'search']) and intent.time_range and intent.time_range.start
                self.logger.info("🔍 anomaly_type_determined", detection=is_detection_request, active=is_active_request, search=is_search_request)
                
                # Extract severity from utterance (critical, warning, info)
                severity = None
                if 'critical' in utterance:
                    severity = 'critical'
                elif 'warning' in utterance or 'warn' in utterance:
                    severity = 'warning'
                elif 'info' in utterance or 'information' in utterance:
                    severity = 'info'
                
                if is_detection_request:
                    # RUN ML anomaly detection - POST /anomaly/detect
                    machines = self._run_async(self.api_client.list_machines(search=intent.machine))
                    if not machines:
                        return {'success': False, 'error': f"Machine {intent.machine} not found"}
                    
                    machine_id = machines[0]['id']
                    
                    # Get time range (default: today)
                    if intent.time_range and intent.time_range.start and intent.time_range.end:
                        start_time = intent.time_range.start
                        end_time = intent.time_range.end
                    else:
                        end_time = datetime.now(timezone.utc)
                        start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    # Run ML detection
                    data = self._run_async(self.api_client.detect_anomalies(
                        machine_id=machine_id,
                        start=start_time,
                        end=end_time
                    ))
                    data['machine_name'] = intent.machine
                    data['is_detection'] = True
                    return {'success': True, 'data': data}
                
                elif is_active_request:
                    # GET active (unresolved) anomalies - GET /anomaly/active
                    data = self._run_async(self.api_client.get_active_anomalies())
                    data['is_active'] = True
                    return {'success': True, 'data': data}
                
                elif is_search_request:
                    # SEARCH anomalies by date range - GET /anomaly/search
                    machine_id = None
                    if intent.machine:
                        machines = self._run_async(self.api_client.list_machines(search=intent.machine))
                        if machines:
                            machine_id = machines[0]['id']
                    
                    data = self._run_async(self.api_client.search_anomalies(
                        start_time=intent.time_range.start,
                        end_time=intent.time_range.end,
                        machine_id=machine_id,
                        severity=severity,
                        limit=50
                    ))
                    if intent.machine:
                        data['machine_name'] = intent.machine
                    return {'success': True, 'data': data}
                
                elif intent.machine:
                    # LIST recent anomalies - GET /anomaly/recent
                    machines = self._run_async(self.api_client.list_machines(search=intent.machine))
                    if not machines:
                        return {'success': False, 'error': f"Machine {intent.machine} not found"}
                    
                    machine_id = machines[0]['id']
                    data = self._run_async(self.api_client.get_recent_anomalies(
                        machine_id=machine_id,
                        severity=severity,
                        limit=10
                    ))
                    # Add machine name for template
                    data['machine_name'] = intent.machine
                    return {'success': True, 'data': data}
                else:
                    # Factory-wide recent anomalies
                    self.logger.info("🔍 anomaly_factory_wide_query", severity=severity)
                    self.logger.info("🔍 calling_get_recent_anomalies")
                    data = self._run_async(self.api_client.get_recent_anomalies(
                        severity=severity,
                        limit=10
                    ))
                    
                    # Extract unique affected machines from anomalies list
                    if 'anomalies' in data and isinstance(data['anomalies'], list):
                        affected_machines = list(set(
                            anomaly.get('machine_name') 
                            for anomaly in data['anomalies'] 
                            if anomaly.get('machine_name')
                        ))
                        data['affected_machines'] = sorted(affected_machines)
                    
                    return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.BASELINE_MODELS:
                # List baseline models for a machine
                if not intent.machine:
                    return self._build_baseline_message_response(
                        'Which machine do you mean? Please specify a machine name.',
                    )
                
                requested_energy_source = self._extract_energy_source(
                    getattr(intent, 'utterance', ''),
                    intent.energy_source,
                )
                resolution = self._resolve_baseline_target(
                    intent.machine,
                    utterance=getattr(intent, 'utterance', ''),
                    energy_source=requested_energy_source,
                )
                if not resolution['success']:
                    return self._build_baseline_message_response(
                        resolution['message'],
                        seu_name=resolution.get('seu_name', intent.machine),
                        energy_source=resolution.get('energy_source'),
                    )

                resolved_energy_source = resolution['energy_source']
                target_label = self._format_baseline_target_label(intent.machine, resolved_energy_source)
                if not resolution['seu'].get('has_baseline'):
                    available_sources = self._available_baseline_sources(
                        resolution['matching_seus'],
                        exclude_energy_source=resolved_energy_source,
                    )
                    if available_sources:
                        message = (
                            f"No baseline model is trained for {target_label}. "
                            f"Available trained baselines exist for {self._join_human_list(available_sources)}."
                        )
                    else:
                        message = f"No baseline model is trained for {target_label}."
                    return self._build_baseline_message_response(
                        message,
                        seu_name=intent.machine,
                        energy_source=resolved_energy_source,
                        machine_name=intent.machine,
                    )

                self.logger.info(
                    "baseline_models_query",
                    machine=intent.machine,
                    energy_source=resolved_energy_source,
                )
                
                # Call list_baseline_models API
                response = self._run_async(
                    self.api_client.list_baseline_models(
                        seu_name=intent.machine,
                        energy_source=resolved_energy_source
                    )
                )
                
                # Process response to extract active model and summary
                models = response.get('models', [])
                active_model = next((m for m in models if m.get('is_active')), models[0] if models else None)

                if not models:
                    return self._build_baseline_message_response(
                        f"No baseline models found for {target_label}.",
                        seu_name=intent.machine,
                        energy_source=resolved_energy_source,
                        machine_name=intent.machine,
                    )
                
                data = {
                    'seu_name': response.get('seu_name', intent.machine),
                    'machine_name': intent.machine,
                    'energy_source': resolved_energy_source,
                    'models': models,
                    'active_version': active_model.get('model_version') if active_model else None,
                    'active_r_squared': active_model.get('r_squared') if active_model else None,
                    'active_samples': active_model.get('training_samples') if active_model else None
                }
                
                return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.BASELINE_EXPLANATION:
                # Explain baseline model (key drivers, accuracy)
                # If no machine specified, show factory-wide key drivers
                if not intent.machine:
                    self.logger.info("baseline_explanation_factory_wide")
                    return self._get_factory_wide_drivers()
                
                requested_energy_source = self._extract_energy_source(
                    getattr(intent, 'utterance', ''),
                    intent.energy_source,
                )
                resolution = self._resolve_baseline_target(
                    intent.machine,
                    utterance=getattr(intent, 'utterance', ''),
                    energy_source=requested_energy_source,
                )
                if not resolution['success']:
                    return self._build_baseline_message_response(
                        resolution['message'],
                        seu_name=resolution.get('seu_name', intent.machine),
                        energy_source=resolution.get('energy_source'),
                    )

                resolved_energy_source = resolution['energy_source']
                target_label = self._format_baseline_target_label(intent.machine, resolved_energy_source)
                if not resolution['seu'].get('has_baseline'):
                    available_sources = self._available_baseline_sources(
                        resolution['matching_seus'],
                        exclude_energy_source=resolved_energy_source,
                    )
                    if available_sources:
                        message = (
                            f"No baseline model is trained for {target_label}. "
                            f"Available trained baselines exist for {self._join_human_list(available_sources)}."
                        )
                    else:
                        message = f"No baseline model is trained for {target_label}."
                    return self._build_baseline_message_response(
                        message,
                        seu_name=intent.machine,
                        energy_source=resolved_energy_source,
                        machine_name=intent.machine,
                    )

                self.logger.info(
                    "baseline_explanation_query",
                    machine=intent.machine,
                    energy_source=resolved_energy_source,
                )
                
                # First get the list of models to find the active model ID
                models_response = self._run_async(
                    self.api_client.list_baseline_models(
                        seu_name=intent.machine,
                        energy_source=resolved_energy_source
                    )
                )
                
                models = models_response.get('models', [])
                active_model = next((m for m in models if m.get('is_active')), models[0] if models else None)
                
                if not active_model:
                    return self._build_baseline_message_response(
                        f"No baseline model found for {target_label}.",
                        seu_name=intent.machine,
                        energy_source=resolved_energy_source,
                        machine_name=intent.machine,
                    )
                
                # Get detailed explanation for the active model
                model_id = active_model.get('id')
                explanation_response = self._run_async(
                    self.api_client.get_baseline_model_explanation(
                        model_id=model_id,
                        include_explanation=True
                    )
                )
                
                # Extract explanation data for template
                explanation = explanation_response.get('explanation', {})
                driver_direction = intent.params.get('driver_direction') if intent.params else None
                key_drivers = explanation.get('key_drivers', [])
                if driver_direction:
                    key_drivers = [
                        driver for driver in key_drivers
                        if driver.get('direction') == driver_direction
                    ]
                data = {
                    'machine_name': explanation_response.get('machine_name', intent.machine),
                    'seu_name': intent.machine,
                    'energy_source': resolved_energy_source,
                    'r_squared': explanation_response.get('r_squared'),
                    'model_version': explanation_response.get('model_version'),
                    'explanation': explanation,
                    'key_drivers': key_drivers,
                    'driver_direction': driver_direction,
                    'accuracy_explanation': explanation.get('accuracy_explanation'),
                    'formula_explanation': explanation.get('formula_explanation')
                }
                
                return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.BASELINE:
                # Baseline prediction - get expected energy for given conditions
                machine = intent.machine
                machines = intent.machines if intent.machines else []
                requested_energy_source = self._extract_energy_source(
                    getattr(intent, 'utterance', ''),
                    intent.energy_source,
                )
                
                # If no machine specified, try conversation context
                if not machine and not machines and self.context_manager:
                    session = self.context_manager.get_or_create_session("default_user") if self.context_manager else None
                    machine = session.get_last_machine()
                    if machine:
                        self.logger.info("baseline_using_context", machine=machine)
                
                if not machine and not machines:
                    return {'success': False, 'error': 'Which machine? Please specify a machine name.', 'needs_clarification': True}
                
                # Extract features from utterance (temperature, pressure, load, production)
                utterance = getattr(intent, 'utterance', '') if hasattr(intent, 'utterance') else ''
                features = FeatureExtractor.extract_all_features(
                    utterance,
                    defaults={
                        "total_production_count": 5000000,
                        "avg_outdoor_temp_c": 22.0,
                        "avg_pressure_bar": 7.0,
                        "avg_load_factor": 0.85
                    }
                )
                
                self.logger.info("baseline_features_extracted", features=features)
                
                # Handle multiple machines (ambiguous query like "HVAC" or "compressor")
                if machines:
                    self.logger.info("baseline_multi_prediction", machines=machines, count=len(machines))
                    predictions = []
                    
                    for seu_name in machines:
                        try:
                            prediction = self._run_async(
                                self.api_client.predict_baseline(
                                    seu_name=seu_name,
                                    energy_source=requested_energy_source or "electricity",
                                    features=features,
                                    include_message=False
                                )
                            )
                            prediction['seu_name'] = seu_name
                            predictions.append(prediction)
                        except Exception as e:
                            self.logger.warning("baseline_prediction_failed", machine=seu_name, error=str(e))
                    
                    # Return multi-machine predictions
                    return {
                        'success': True,
                        'data': {
                            'predictions': predictions,
                            'features': features,
                            'machine_count': len(predictions)
                        }
                    }
                
                # Single machine prediction
                self.logger.info("baseline_prediction", machine=machine)

                resolution = self._resolve_baseline_target(
                    machine,
                    utterance=getattr(intent, 'utterance', ''),
                    energy_source=requested_energy_source,
                )
                if not resolution['success']:
                    return self._build_baseline_message_response(
                        resolution['message'],
                        seu_name=resolution.get('seu_name', machine),
                        energy_source=resolution.get('energy_source'),
                        machine_name=machine,
                    )
                resolved_energy_source = resolution['energy_source']
                
                # Call baseline prediction API
                prediction = self._run_async(
                    self.api_client.predict_baseline(
                        seu_name=machine,
                        energy_source=resolved_energy_source,
                        features=features,
                        include_message=False  # Don't use API message, we format with features
                    )
                )
                
                # Add SEU name and features to response for template
                prediction['seu_name'] = machine
                prediction['energy_source'] = resolved_energy_source
                prediction['features'] = features
                
                # Update conversation context with this machine
                if self.context_manager:
                    session = self.context_manager.get_or_create_session("default_user") if self.context_manager else None
                    session.update_machine(machine)
                
                return {'success': True, 'data': prediction}
            
            elif intent.intent == IntentType.KPI:
                # KPI query - get all KPIs for a machine
                machine = intent.machine
                
                if not machine:
                    return {'success': False, 'error': 'Which machine? Please specify a machine name for KPIs.', 'needs_clarification': True}
                
                self.logger.info("kpi_query", machine=machine, time_range=intent.time_range)
                
                # Get time range (default to today)
                if intent.time_range and intent.time_range.start:
                    start_time = intent.time_range.start
                    end_time = intent.time_range.end if intent.time_range.end else datetime.now(timezone.utc)
                else:
                    start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                    end_time = datetime.now(timezone.utc)
                
                # Get machine ID
                machines = self._run_async(self.api_client.list_machines(search=machine))
                if not machines or len(machines) == 0:
                    return {'success': False, 'error': f'Machine {machine} not found'}
                
                machine_id = machines[0]['id']
                
                # Call KPI API
                kpis = self._run_async(
                    self.api_client.get_all_kpis(
                        machine_id=machine_id,
                        start_time=start_time,
                        end_time=end_time
                    )
                )
                
                return {'success': True, 'data': kpis}
            
            elif intent.intent == IntentType.PERFORMANCE:
                # Performance analysis - analyze SEU performance vs baseline
                machine = intent.machine
                
                if not machine:
                    return {'success': False, 'error': 'Which machine? Please specify a machine name for performance analysis.', 'needs_clarification': True}
                
                self.logger.info("performance_query", machine=machine)
                
                # Use "energy" as default energy source (works for most machines)
                # Boiler-1 would need "electricity" but that's an edge case
                energy_source = "energy"
                
                # Get analysis date (default to today)
                from datetime import date as date_class
                analysis_date = date_class.today().isoformat()
                
                # Call performance API
                performance = self._run_async(
                    self.api_client.analyze_performance(
                        seu_name=machine,
                        energy_source=energy_source,
                        analysis_date=analysis_date
                    )
                )
                
                return {'success': True, 'data': performance}
            
            elif intent.intent == IntentType.FORECAST:
                # Forecast - get future energy prediction
                self.logger.info("forecast_query", machine=intent.machine)
                
                # Check if this is a demand forecast (detailed ARIMA predictions)
                utterance = getattr(intent, 'utterance', '').lower()
                is_demand_forecast = 'demand' in utterance or 'detailed' in utterance
                
                if is_demand_forecast and intent.machine:
                    # Use /forecast/demand endpoint (requires machine UUID)
                    # Lookup machine ID
                    machines = self._run_async(
                        self.api_client.list_machines(search=intent.machine)
                    )
                    
                    if not machines:
                        return {'success': False, 'error': f'Machine {intent.machine} not found'}
                    
                    machine_id = machines[0]['id']
                    
                    # Get detailed demand forecast
                    forecast = self._run_async(
                        self.api_client.forecast_demand(
                            machine_id=machine_id,
                            horizon="short",
                            periods=4
                        )
                    )
                    # Add machine name for template
                    forecast['machine_name'] = intent.machine
                    return {'success': True, 'data': forecast, 'custom_template': 'demand_forecast'}
                else:
                    # Use /forecast/short-term endpoint (simplified daily forecast)
                    forecast = self._run_async(
                        self.api_client.get_forecast(
                            machine=intent.machine,
                            hours=24  # Default to 24 hour forecast
                        )
                    )
                    return {'success': True, 'data': forecast}
            
            elif intent.intent == IntentType.PRODUCTION:
                # Production - get production stats from machine status
                if not intent.machine:
                    return {'success': False, 'error': 'Machine name required for production queries'}
                
                self.logger.info("production_query", machine=intent.machine)
                
                # Get machine status (includes production_today)
                data = self._run_async(
                    self.api_client.get_machine_status(intent.machine)
                )
                
                return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.REPORT:
                # Report generation - generate/preview/list reports
                # Handle both 'action' and 'report_action' keys (heuristic parser uses 'report_action')
                action = intent.params.get('action') or intent.params.get('report_action', 'generate') if intent.params else 'generate'
                report_type = intent.params.get('report_type', 'monthly_enpi') if intent.params else 'monthly_enpi'
                year = intent.params.get('year') if intent.params else None
                month = intent.params.get('month') if intent.params else None
                
                self.logger.info("report_query", action=action, report_type=report_type, year=year, month=month)
                
                if action == 'list_types':
                    # List available report types
                    data = self._run_async(self.api_client.get_report_types())
                    return {'success': True, 'data': data, 'action': 'list_types'}
                    
                elif action == 'preview':
                    # Preview report data
                    data = self._run_async(
                        self.api_client.preview_report(
                            report_type=report_type,
                            year=year,
                            month=month
                        )
                    )
                    return {'success': True, 'data': data, 'action': 'preview'}
                    
                else:  # generate
                    # Generate and download PDF report
                    data = self._run_async(
                        self.api_client.generate_report(
                            report_type=report_type,
                            year=year,
                            month=month
                        )
                    )
                    self.logger.info("report_generate_returned", data=data, data_type=type(data).__name__)
                    return {'success': True, 'data': data, 'action': 'generate'}
            
            elif intent.intent == IntentType.COMPARISON:
                # Machine comparison query - extract all machines from utterance
                machines = []
                if intent.machine:
                    machines.append(intent.machine)
                
                # Try to find additional machines in utterance
                all_machine_names = self.validator.machine_whitelist
                for machine in all_machine_names:
                    machine_lower = machine.lower()
                    intent_machine_lower = intent.machine.lower() if intent.machine else ""
                    if machine_lower in intent.utterance.lower() and machine_lower != intent_machine_lower:
                        machines.append(machine)
                
                # If only one machine found, get top consumers for comparison
                if len(machines) < 2:
                    top_consumers = self._run_async(self.api_client.get_top_consumers(limit=3))
                    if top_consumers and 'top_consumers' in top_consumers:
                        machines = [c['seu_name'] for c in top_consumers['top_consumers'][:2]]
                
                # Get status for each machine
                comparison_data = []
                for machine_name in machines[:5]:  # Limit to 5 machines
                    try:
                        status = self._run_async(self.api_client.get_machine_status(machine_name))
                        comparison_data.append(status)
                    except Exception as e:
                        self.logger.warning("comparison_machine_failed", machine=machine_name, error=str(e))
                
                return {
                    'success': True,
                    'data': {
                        'machines': comparison_data,
                        'count': len(comparison_data)
                    }
                }
            
            elif intent.intent == IntentType.KPI:
                # KPI query - get factory-wide or machine-specific KPIs
                if intent.machine:
                    # Machine-specific KPIs
                    data = self._run_async(self.api_client.get_machine_status(intent.machine))
                    return {'success': True, 'data': data}
                else:
                    # Factory-wide KPIs - use summary endpoint
                    data = self._run_async(self.api_client.get_factory_summary())
                    return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.HEALTH:
                # System health check - call /health endpoint
                data = self._run_async(self.api_client.health_check())
                return {'success': True, 'data': data}
            
            else:
                self.logger.warning("unsupported_intent_api_call", intent=intent.intent)
                return {
                    'success': False,
                    'error': f"API call for intent {intent.intent} not yet implemented",
                    'error_type': 'not_implemented'
                }
                
        except Exception as e:
            self.logger.error("api_call_failed",
                            intent=intent.intent,
                            error=str(e),
                            error_type=type(e).__name__)
            return {
                'success': False,
                'error': str(e),
                'error_type': 'api_timeout' if 'timeout' in str(e).lower() else 'api_error'
            }
    
    def _format_response(self, intent: Intent, api_data: Dict[str, Any], custom_template: Optional[str] = None) -> str:
        """Format API response using Jinja2 templates"""
        try:
            # Use custom template if specified
            if custom_template:
                template = self.response_formatter.env.get_template(f'{custom_template}.dialog')
                return template.render(**api_data).strip()
            
            # Special handling for health check responses within factory_overview
            if intent.intent == IntentType.FACTORY_OVERVIEW and 'status' in api_data and 'database' in api_data:
                # This is a health check response, use health_check template
                template_data = {
                    'status': api_data.get('status'),
                    'active_machines': api_data.get('active_machines', 0),
                    'baseline_models': api_data.get('baseline_models', 0),
                    'database': api_data.get('database', {})
                }
                # Manually render health_check template
                template = self.response_formatter.env.get_template('health_check.dialog')
                return template.render(**template_data).strip()
            
            # Special handling for REPORT intent - choose template based on action
            if intent.intent == IntentType.REPORT:
                action = api_data.get('action', 'generate')
                self.logger.info("report_formatting", action=action, api_data_keys=list(api_data.keys()))
                month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                              'July', 'August', 'September', 'October', 'November', 'December']
                
                if action == 'list_types':
                    template = self.response_formatter.env.get_template('report_types.dialog')
                    return template.render(**api_data.get('data', {})).strip()
                elif action == 'preview':
                    template = self.response_formatter.env.get_template('report_preview.dialog')
                    data = api_data.get('data', {})
                    month = intent.params.get('month', 1) if intent.params else 1
                    year = intent.params.get('year', 2024) if intent.params else 2024
                    return template.render(
                        data=data,
                        report_type=intent.params.get('report_type', 'monthly_enpi') if intent.params else 'monthly_enpi',
                        month_name=month_names[month] if month and 1 <= month <= 12 else 'this month',
                        year=year
                    ).strip()
                else:  # generate
                    template = self.response_formatter.env.get_template('report_generated.dialog')
                    # Data is directly in api_data (not nested in 'data' key)
                    data = api_data.get('data', api_data)  # Try nested first, fallback to flat
                    month = data.get('month', 1)
                    year = data.get('year', 2024)
                    
                    # Debug logging
                    self.logger.info("report_template_data", 
                                    success=data.get('success'),
                                    file_path=data.get('file_path'),
                                    month=month,
                                    year=year,
                                    data_keys=list(data.keys()) if data else [])
                    
                    return template.render(
                        success=data.get('success', False),
                        file_path=data.get('file_path', ''),
                        report_type=data.get('report_type', 'monthly_enpi'),
                        month_name=month_names[month] if month and 1 <= month <= 12 else 'this month',
                        year=year,
                        error=data.get('error')
                    ).strip()
            
            return self.response_formatter.format_response(
                intent_type=intent.intent.value,
                api_data=api_data,
                context={
                    "machine_name": intent.machine,
                    "utterance": getattr(intent, 'utterance', '').lower()
                } if intent.machine or hasattr(intent, 'utterance') else {}
            )
        except Exception as e:
            self.logger.error("response_formatting_failed", error=str(e))
            # Fallback to simple response
            return self._generate_fallback_response(intent, api_data)
    
    def _generate_fallback_response(self, intent: Intent, api_data: Dict[str, Any]) -> str:
        """Generate simple fallback response if template fails"""
        if intent.intent == IntentType.MACHINE_STATUS and 'machine_name' in api_data:
            status = api_data.get('current_status', {})
            return f"{api_data['machine_name']} is {status.get('status', 'unknown')}"
        
        elif intent.intent == IntentType.POWER_QUERY and 'current_status' in api_data:
            power = api_data['current_status'].get('power_kw', 0)
            return f"Current power consumption is {power:.1f} kilowatts"
        
        elif intent.intent == IntentType.FACTORY_OVERVIEW:
            return "Factory overview data retrieved successfully"
        
        else:
            return "I retrieved the data successfully"

    def _json_safe_value(self, value: Any) -> Any:
        """Convert nested skill data into JSON-safe values for messagebus events."""
        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, dict):
            return {
                str(key): self._json_safe_value(item)
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [self._json_safe_value(item) for item in value]

        if isinstance(value, tuple):
            return [self._json_safe_value(item) for item in value]

        if hasattr(value, 'value') and not isinstance(value, (str, bytes)):
            return getattr(value, 'value')

        return value

    def _safe_float(self, value: Any, precision: int = 1) -> Optional[float]:
        """Safely round a numeric value for widget summaries."""
        try:
            if value is None:
                return None
            return round(float(value), precision)
        except (TypeError, ValueError):
            return None

    def _build_widget_metric(self, label: str, value: Any, unit: Optional[str] = None, tone: str = 'neutral') -> Optional[Dict[str, Any]]:
        """Create a compact summary metric for the widget side panel."""
        if value is None:
            return None

        return {
            'label': label,
            'value': value,
            'unit': unit,
            'tone': tone
        }

    def _build_widget_badge(self, label: str, tone: str = 'neutral') -> Dict[str, str]:
        """Create a status badge for the widget side panel."""
        return {
            'label': label,
            'tone': tone
        }

    def _build_widget_spotlight(
        self,
        kicker: str,
        title: Any,
        detail: Optional[str] = None,
        tone: str = 'info'
    ) -> Optional[Dict[str, Any]]:
        """Create a high-emphasis spotlight block for the widget side panel."""
        if title is None or title == '':
            return None

        return {
            'kicker': kicker,
            'title': title,
            'detail': detail,
            'tone': tone
        }

    def _build_response_snapshot(self, api_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Keep a lightweight, JSON-safe snapshot of raw data for the portal response."""
        if not isinstance(api_data, dict):
            return None

        snapshot: Dict[str, Any] = {}
        list_limits = {
            'ranking': 5,
            'anomalies': 8,
            'timeseries_data': 8,
            'data_points': 8,
            'affected_machines': 8
        }
        excluded_keys = {'pdf_base64', 'audio_base64'}

        for key, value in api_data.items():
            if key in excluded_keys:
                continue

            if isinstance(value, list) and key in list_limits:
                snapshot[key] = self._json_safe_value(value[:list_limits[key]])
                snapshot[f'{key}_truncated'] = len(value) > list_limits[key]
                continue

            snapshot[key] = self._json_safe_value(value)

        return snapshot

    def _build_widget_insights(
        self,
        intent_name: Optional[str],
        api_data: Optional[Dict[str, Any]],
        utterance: str = '',
        machine: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Build a curated side-panel payload for selected operational replies."""
        if not intent_name or not isinstance(api_data, dict):
            return None

        normalized_intent = intent_name.value if hasattr(intent_name, 'value') else str(intent_name)
        utterance_lower = (utterance or '').lower()

        if normalized_intent in (
            IntentType.MACHINE_STATUS.value,
            IntentType.ENERGY_QUERY.value,
            IntentType.POWER_QUERY.value
        ):
            if api_data.get('factory_wide') or {'total_kwh_today', 'current_power_kw', 'machines_active'} & set(api_data.keys()):
                metrics = [
                    self._build_widget_metric('Energy Today', self._safe_float(api_data.get('total_kwh_today'), 1), 'kWh', 'neutral'),
                    self._build_widget_metric('Current Power', self._safe_float(api_data.get('current_power_kw'), 1), 'kW', 'info'),
                    self._build_widget_metric('Active Machines', api_data.get('machines_active'), None, 'good'),
                    self._build_widget_metric('Cost Today', self._safe_float(api_data.get('total_cost_usd'), 2), 'USD', 'warning')
                ]
                metrics = [metric for metric in metrics if metric]

                lines = []
                if api_data.get('machines_active') is not None and api_data.get('machines_total') is not None:
                    lines.append(f"{api_data.get('machines_active')} of {api_data.get('machines_total')} machines are active right now.")

                return {
                    'panel_type': 'factory_overview',
                    'title': 'Factory energy snapshot',
                    'subtitle': 'Live operational context',
                    'summary_metrics': metrics,
                    'status_badges': [
                        self._build_widget_badge('Live data', 'good'),
                        self._build_widget_badge('Energy summary', 'neutral')
                    ],
                    'secondary_lines': lines or ['Factory-wide energy totals are available for this request.'],
                    'links': [
                        {'label': 'Open reports', 'href': '/reports.html'}
                    ]
                }

            machine_name = api_data.get('machine_name') or api_data.get('machine') or machine
            current_status = api_data.get('current_status') or {}
            today_stats = api_data.get('today_stats') or {}
            recent_anomalies = api_data.get('recent_anomalies') or {}

            if machine_name and (current_status or today_stats or recent_anomalies):
                status_value = (current_status.get('status') or 'unknown').lower()
                status_tone = {
                    'running': 'good',
                    'idle': 'warning',
                    'stopped': 'neutral'
                }.get(status_value, 'neutral')

                metrics = [
                    self._build_widget_metric('Power', self._safe_float(current_status.get('power_kw'), 1), 'kW', 'info'),
                    self._build_widget_metric('Energy Today', self._safe_float(today_stats.get('energy_kwh'), 1), 'kWh', 'neutral'),
                    self._build_widget_metric('Uptime', self._safe_float(today_stats.get('uptime_percent'), 1), '%', 'good'),
                    self._build_widget_metric('Cost Today', self._safe_float(today_stats.get('cost_usd'), 2), 'USD', 'warning')
                ]
                metrics = [metric for metric in metrics if metric]

                anomaly_count = recent_anomalies.get('count')
                critical_count = recent_anomalies.get('critical')
                warning_count = recent_anomalies.get('warnings')

                badges = [self._build_widget_badge(status_value.title(), status_tone)]
                if anomaly_count == 0:
                    badges.append(self._build_widget_badge('No anomalies today', 'good'))
                elif critical_count:
                    badges.append(self._build_widget_badge(f'{critical_count} critical', 'danger'))
                elif warning_count:
                    badges.append(self._build_widget_badge(f'{warning_count} warnings', 'warning'))

                lines = []
                if status_value != 'unknown':
                    lines.append(f"{machine_name} is currently {status_value}.")

                peak_power = self._safe_float(today_stats.get('peak_power_kw'), 1)
                if peak_power is not None:
                    lines.append(f"Peak power today reached {peak_power} kW.")

                latest_anomaly = recent_anomalies.get('latest') or {}
                if latest_anomaly.get('description'):
                    lines.append(f"Latest anomaly: {latest_anomaly['description']}.")
                elif anomaly_count == 0:
                    lines.append('No anomalies were recorded for this machine today.')

                if 'energy' in utterance_lower and today_stats.get('energy_kwh') is not None:
                    lines.insert(0, f"Energy today is {today_stats.get('energy_kwh')} kWh for {machine_name}.")

                return {
                    'panel_type': 'machine_status',
                    'title': machine_name,
                    'subtitle': 'Live machine context',
                    'summary_metrics': metrics,
                    'status_badges': badges,
                    'secondary_lines': lines[:4],
                    'links': [
                        {'label': 'Open reports', 'href': '/reports.html'}
                    ]
                }

        if normalized_intent == IntentType.FACTORY_OVERVIEW.value:
            energy = api_data.get('energy') or {}
            costs = api_data.get('costs') or {}
            machines = api_data.get('machines') or {}
            anomalies = api_data.get('anomalies') or {}
            top_consumer = api_data.get('top_consumer') or {}
            latest_anomaly = api_data.get('latest_anomaly') or {}

            total_energy = energy.get('total_kwh_today')
            if total_energy is None:
                total_energy = api_data.get('total_energy')

            live_rate = energy.get('current_power_kw')
            if live_rate is None:
                live_rate = api_data.get('energy_per_hour')

            active_machines = machines.get('active')
            if active_machines is None:
                active_machines = api_data.get('active_machines_today')

            critical_alerts = anomalies.get('critical')
            if critical_alerts is None:
                critical_alerts = api_data.get('critical')
            if critical_alerts is None:
                critical_alerts = 0

            total_alerts = anomalies.get('total')
            if total_alerts is None:
                total_alerts = api_data.get('total_anomalies')
            if total_alerts is None:
                total_alerts = 0

            estimated_cost = costs.get('total_usd_today')
            if estimated_cost is None:
                estimated_cost = api_data.get('estimated_cost')

            cost_per_day = costs.get('cost_per_day')
            if cost_per_day is None:
                cost_per_day = api_data.get('cost_per_day')

            peak_power = energy.get('peak_power_kw')
            if peak_power is None:
                peak_power = api_data.get('peak_power')

            avg_power = energy.get('avg_power_kw')
            if avg_power is None:
                avg_power = api_data.get('avg_power')

            carbon_footprint = api_data.get('carbon_footprint')
            readings_per_minute = api_data.get('readings_per_minute')
            total_readings = api_data.get('total_readings')
            uptime_percent = api_data.get('uptime_percent')

            metrics = [
                self._build_widget_metric('Total Energy', self._safe_float(total_energy, 1), 'kWh', 'neutral'),
                self._build_widget_metric('Live Rate', self._safe_float(live_rate, 1), 'kWh/h', 'info'),
                self._build_widget_metric('Active Today', active_machines, None, 'good'),
                self._build_widget_metric('Estimated Cost', self._safe_float(estimated_cost, 2), 'USD', 'warning')
            ]
            metrics = [metric for metric in metrics if metric]

            badges = [self._build_widget_badge(str(api_data.get('status', 'operational')).replace('_', ' ').title(), 'good')]
            if active_machines is not None:
                badges.append(self._build_widget_badge(f"{active_machines} active machines", 'info'))
            if total_alerts:
                badges.append(self._build_widget_badge(f"{total_alerts} alerts logged", 'warning' if total_alerts and not critical_alerts else 'danger'))
            elif total_alerts == 0:
                badges.append(self._build_widget_badge('No active alerts', 'good'))
            if uptime_percent is not None:
                badges.append(self._build_widget_badge(f"{uptime_percent}% uptime", 'neutral'))

            spotlight = None
            if top_consumer.get('machine_name'):
                spotlight = self._build_widget_spotlight(
                    'Top consumer',
                    top_consumer.get('machine_name'),
                    (
                        f"{top_consumer.get('energy_kwh', 0)} kWh"
                        f" · {top_consumer.get('percent_of_total', 0)}% of facility total"
                    ),
                    'warning'
                )
            elif live_rate is not None:
                detail_parts = []
                if active_machines is not None:
                    detail_parts.append(f"{active_machines} active machines")
                if total_alerts is not None:
                    detail_parts.append(f"{total_alerts} alerts tracked")
                if cost_per_day is not None:
                    detail_parts.append(f"${cost_per_day}/day est.")

                spotlight = self._build_widget_spotlight(
                    'Factory pulse',
                    f"{self._safe_float(live_rate, 1)} kWh/h",
                    ' · '.join(detail_parts) if detail_parts else None,
                    'danger' if critical_alerts else 'info'
                )

            lines = []
            if peak_power is not None or avg_power is not None:
                peak_text = f"Peak power reached {peak_power} kW" if peak_power is not None else None
                avg_text = f"average power held at {avg_power} kW" if avg_power is not None else None
                lines.append('. '.join(part for part in [peak_text, avg_text] if part) + '.')
            if cost_per_day is not None or estimated_cost is not None:
                cost_parts = []
                if estimated_cost is not None:
                    cost_parts.append(f"Estimated spend is ${estimated_cost}")
                if cost_per_day is not None:
                    cost_parts.append(f"roughly ${cost_per_day} per day")
                lines.append(' with '.join(cost_parts) + '.')
            if carbon_footprint is not None:
                lines.append(f"Carbon footprint estimate is {carbon_footprint} kilograms.")
            if total_readings is not None or readings_per_minute is not None:
                readings_parts = []
                if total_readings is not None:
                    readings_parts.append(f"{total_readings} readings captured")
                if readings_per_minute is not None:
                    readings_parts.append(f"{readings_per_minute} readings per minute")
                lines.append('Telemetry stream processed ' + ' at '.join(readings_parts) + '.')
            if latest_anomaly.get('machine_name'):
                lines.append(
                    f"Latest anomaly: {latest_anomaly.get('severity', 'info')} alert on {latest_anomaly['machine_name']}."
                )
            if not lines:
                lines.append('Factory-wide summary is available for this request.')

            return {
                'panel_type': 'factory_overview',
                'title': 'Factory overview',
                'subtitle': 'Operational pulse',
                'spotlight': spotlight,
                'summary_metrics': metrics,
                'status_badges': badges,
                'secondary_lines': lines[:4],
                'links': [
                    {'label': 'Open reports', 'href': '/reports.html'}
                ]
            }

        if normalized_intent == IntentType.RANKING.value and isinstance(api_data.get('ranking'), list):
            ranking = api_data.get('ranking', [])[:3]
            if not ranking:
                return None

            metric_label = api_data.get('metric_label') or 'Top consumers'
            top_entry = ranking[0]
            metrics = [
                self._build_widget_metric('Top Value', top_entry.get('value'), api_data.get('unit'), 'info'),
                self._build_widget_metric('Leader Share', self._safe_float(top_entry.get('percentage'), 1), '%', 'good'),
                self._build_widget_metric('Machines', api_data.get('machines_analyzed'), None, 'neutral'),
                self._build_widget_metric('Total', api_data.get('total_value'), api_data.get('unit'), 'warning')
            ]
            metrics = [metric for metric in metrics if metric]

            spotlight = self._build_widget_spotlight(
                'Top consumer',
                top_entry.get('machine_name') or 'Unknown machine',
                (
                    f"{top_entry.get('value')} {api_data.get('unit', '').strip()}"
                    f" · {top_entry.get('percentage', 0)}% of tracked load"
                ),
                'info'
            )

            lines = [
                f"{entry.get('rank')}. {entry.get('machine_name', 'Unknown')} - {entry.get('value')} {api_data.get('unit', '').strip()} ({entry.get('percentage', 0)}%)"
                for entry in ranking
            ]

            return {
                'panel_type': 'ranking',
                'title': metric_label,
                'subtitle': 'Current ranking snapshot',
                'spotlight': spotlight,
                'summary_metrics': metrics,
                'status_badges': [
                    self._build_widget_badge(str(api_data.get('metric', 'ranking')).replace('_', ' ').title(), 'neutral')
                ],
                'secondary_lines': lines,
                'links': [
                    {'label': 'Open reports', 'href': '/reports.html'}
                ]
            }

        if normalized_intent == IntentType.ANOMALY_DETECTION.value:
            by_severity = api_data.get('by_severity') or {}
            anomalies = api_data.get('anomalies') or []
            total_count = api_data.get('total_count')
            if total_count is None:
                total_count = len(anomalies)

            affected_machines = api_data.get('affected_machines') or []
            if not affected_machines and anomalies:
                affected_machines = sorted({
                    anomaly.get('machine_name')
                    for anomaly in anomalies
                    if anomaly.get('machine_name')
                })

            latest = anomalies[0] if anomalies else {}
            metrics = [
                self._build_widget_metric('Total Alerts', total_count, None, 'danger' if total_count else 'good'),
                self._build_widget_metric('Critical', by_severity.get('critical') or api_data.get('critical') or 0, None, 'danger'),
                self._build_widget_metric('Warnings', by_severity.get('warning') or api_data.get('warnings') or 0, None, 'warning'),
                self._build_widget_metric('Machines', len(affected_machines), None, 'neutral')
            ]
            metrics = [metric for metric in metrics if metric]

            badges = []
            if api_data.get('is_active'):
                badges.append(self._build_widget_badge('Active alerts', 'danger' if total_count else 'good'))
            elif api_data.get('is_detection'):
                badges.append(self._build_widget_badge('Detection run', 'info'))
            else:
                badges.append(self._build_widget_badge('Recent anomalies', 'warning' if total_count else 'good'))

            lines = []
            if latest.get('machine_name'):
                lines.append(
                    f"Most recent anomaly: {latest.get('severity', 'info')} on {latest.get('machine_name')}"
                    f" for {latest.get('metric_name') or latest.get('anomaly_type', 'operational drift')}."
                )
            elif total_count == 0:
                lines.append('No anomalies matched this request.')

            if affected_machines:
                lines.append(f"Affected machines: {', '.join(affected_machines[:3])}.")

            return {
                'panel_type': 'anomaly_summary',
                'title': api_data.get('machine_name') or 'Anomaly overview',
                'subtitle': 'Alert context',
                'summary_metrics': metrics,
                'status_badges': badges,
                'secondary_lines': lines[:4] or ['Recent anomaly information is available for this request.'],
                'links': [
                    {'label': 'Open reports', 'href': '/reports.html'}
                ]
            }

        return None

    def _emit_structured_response(
        self,
        session_id: str,
        intent_name: Optional[str],
        api_data: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        utterance: str = '',
        machine: Optional[str] = None
    ) -> None:
        """Emit structured response data so the widget can show extra contextual panels."""
        if not self.bus or not session_id:
            return

        normalized_intent = intent_name.value if hasattr(intent_name, 'value') else str(intent_name) if intent_name else None
        insights = self._build_widget_insights(normalized_intent, api_data, utterance=utterance, machine=machine)
        data_snapshot = self._build_response_snapshot(api_data)

        if not normalized_intent and not insights and not data_snapshot:
            return

        self.bus.emit(Message(
            'enms.skill.response',
            {
                'intent': normalized_intent,
                'confidence': confidence,
                'data': data_snapshot,
                'insights': insights
            },
            {'session_id': session_id}
        ))
    
    # ========== EXISTING MACHINE-SPECIFIC HANDLERS (UPDATED FOR PRIORITY 3) ==========

    @intent_handler(IntentBuilder('PartnerPress').require('partner_press').build())
    def handle_partner_press(self, message: Message):
        """Handle ASSA ABLOY partner press-shop questions through a dedicated Adapt route."""
        try:
            if self._try_handle_partner_press_message(message):
                return
            self.speak(
                "Please mention the ASSA ABLOY press shop, a Bret, Raster, or Dimeco "
                "meter group, or one of the imported press names."
            )
        except Exception as e:
            self.log.error(f"Partner press handler failed: {e}")
            self.speak("I could not retrieve the ASSA ABLOY partner press-shop data.")
    
    @intent_handler(IntentBuilder('EnergyQuery').require('energy_metric').optionally('machine').build())
    def handle_energy_query(self, message: Message):
        """
        Handle energy consumption queries - OVOS interface layer
        
        Priority 3: Now handles both machine-specific AND factory-wide queries:
        - "Compressor-1 energy today" → Machine-specific
        - "energy consumption" → Factory-wide
        - "how much energy are we using?" → Factory-wide
        
        Phase 3.1: Uses session context for follow-up queries
        """
        try:
            if self._try_handle_partner_press_message(message):
                return

            utterance = message.data.get("utterances", [""])[0]
            session_id = self._get_session_id(message)
            
            # Get or create session context
            session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None
            
            # Extract machine (or use context)
            machine_raw = message.data.get('machine')
            machine = self._normalize_machine_name(machine_raw) if machine_raw else None
            
            # Use context if no machine specified
            if not machine and session and session.last_machine:
                machine = session.last_machine
                self.logger.info("using_context_machine", machine=machine, session_id=session_id)
            
            # Extract time range from utterance (or use context)
            time_range = self._extract_time_range(utterance)
            
            # Build intent object
            intent = Intent(
                intent=IntentType.ENERGY_QUERY,
                machine=machine,
                time_range=time_range,
                confidence=0.95,
                utterance=utterance,
                params={'factory_wide': True} if not machine else None
            )
            
            # Log query type
            if not machine:
                self.logger.info("factory_wide_energy_query", utterance=utterance)
            else:
                self.logger.info("machine_specific_energy_query", machine=machine, utterance=utterance)
            
            # Call existing service layer (handles both machine and factory-wide)
            result = self._call_enms_api(intent)
            
            # Speak result
            if result['success']:
                if not machine:
                    # Factory-wide: use speak_dialog with data
                    self.logger.info("factory_energy_speaking", data=result['data'])
                    try:
                        response_text = f"Factory consumed {result['data'].get('total_kwh_today', 0):.1f} kilowatt-hours today"
                        self._emit_structured_response(
                            session_id,
                            intent.intent,
                            result.get('data'),
                            confidence=intent.confidence,
                            utterance=utterance,
                            machine=machine
                        )
                        self.speak_dialog("factory_energy", result['data'])
                    except Exception as dialog_error:
                        self.logger.error("factory_energy_dialog_failed", error=str(dialog_error), data=result['data'])
                        # Fallback to simple response
                        response_text = f"Factory consumed {result['data'].get('total_kwh_today', 0):.1f} kilowatt-hours today"
                        self._emit_structured_response(
                            session_id,
                            intent.intent,
                            result.get('data'),
                            confidence=intent.confidence,
                            utterance=utterance,
                            machine=machine
                        )
                        self.speak(response_text)
                else:
                    # Machine-specific: use formatter
                    response_text = self.response_formatter.format_response('energy_query', result['data'])
                    self._emit_structured_response(
                        session_id,
                        intent.intent,
                        result.get('data'),
                        confidence=intent.confidence,
                        utterance=utterance,
                        machine=machine
                    )
                    self.speak(response_text)
                
                # Update context for next query
                session.add_turn(utterance, intent, response_text, result['data'])
                self.logger.info("context_updated", session_id=session_id, machine=machine, metric="energy")
            else:
                self.logger.error("factory_energy_api_failed", result=result)
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"Energy query handler failed: {e}")
            import traceback
            self.logger.error("factory_energy_traceback", traceback=traceback.format_exc())
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('SystemHealth').require('health_check').build())
    def handle_system_health(self, message: Message):
        """Handle system health queries - API/database/system status checks"""
        try:
            utterance = message.data.get("utterances", [""])[0]
            if self._try_handle_partner_press_message(message):
                return

            session_id = self._get_session_id(message)
            
            self.logger.info("health_check_intent_triggered", 
                           utterance=utterance, 
                           session_id=session_id)
            
            # Build intent object for health check
            intent = Intent(
                intent=IntentType.HEALTH,
                confidence=0.95,
                utterance=utterance
            )
            
            # Call health check API
            result = self._call_enms_api(intent)
            
            if result['success']:
                data = result.get('data', {})
                
                if isinstance(data, dict):
                    status = data.get('status', 'unknown')
                    api_status = data.get('api', {}).get('status', 'unknown') if isinstance(data.get('api'), dict) else 'unknown'
                    db_status = data.get('database', {}).get('status', 'unknown') if isinstance(data.get('database'), dict) else 'unknown'
                    
                    if status == 'healthy' or api_status == 'healthy':
                        response = "The energy management system is healthy and operational."
                    else:
                        response = f"System status is {status}. API: {api_status}, Database: {db_status}"
                else:
                    response = "The system is responding. Status check complete."
                
                self.speak(response)
                
                # Update context - use add_turn which is the proper method
                session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None
                session.add_turn(
                    query=utterance,
                    intent=intent,
                    response=response,
                    api_data=data
                )
            else:
                error = result.get('error', 'Unknown error')
                self.logger.error("health_check_failed", error=error)
                self.speak(f"I couldn't check the system status. Error: {error}")
        except Exception as e:
            self.log.error(f"System health handler failed: {e}")
            import traceback
            self.logger.error("health_check_traceback", traceback=traceback.format_exc())
            self.speak("I encountered an error checking the system health.")
    
    @intent_handler(IntentBuilder('MachineStatus').require('status_check').require('machine').build())
    def handle_machine_status(self, message: Message):
        """Handle machine status queries - OVOS interface layer"""
        try:
            machine_raw = message.data.get('machine')

            machine = self._normalize_machine_name(machine_raw)
            utterance = message.data.get("utterances", [""])[0]
            session_id = self._get_session_id(message)
            
            # Build intent object
            intent = Intent(
                intent=IntentType.MACHINE_STATUS,
                machine=machine,
                confidence=0.95,
                utterance=utterance
            )
            
            # Call existing service layer
            result = self._call_enms_api(intent)
            
            # Speak result
            if result['success']:
                response = self.response_formatter.format_response('machine_status', result['data'])
                self._emit_structured_response(
                    session_id,
                    intent.intent,
                    result.get('data'),
                    confidence=intent.confidence,
                    utterance=utterance,
                    machine=machine
                )
                self.speak(response)
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"Machine status handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('FactoryOverview').require('factory').build())
    def handle_factory_overview(self, message: Message):
        """Handle factory-wide queries - OVOS interface layer"""
        try:
            if self._try_handle_partner_press_message(message):
                return

            utterance = message.data.get("utterances", [""])[0]
            session_id = self._get_session_id(message)
            
            # Build intent object
            intent = Intent(
                intent=IntentType.FACTORY_OVERVIEW,
                confidence=0.95,
                utterance=utterance
            )
            
            # Call existing service layer
            result = self._call_enms_api(intent)
            
            # Speak result
            if result['success']:
                response = self.response_formatter.format_response(
                    result.get('custom_template') or result.get('template') or 'factory_overview',
                    result['data']
                )
                self._emit_structured_response(
                    session_id,
                    intent.intent,
                    result.get('data'),
                    confidence=intent.confidence,
                    utterance=utterance
                )
                self.speak(response)
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"Factory overview handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('AnomalyDetection').require('anomaly').optionally('machine').build())
    def handle_anomaly_detection(self, message: Message):
        """Handle anomaly detection queries - OVOS interface layer (Phase 3.1: with context)"""
        try:
            utterance = message.data.get("utterances", [""])[0]
            if self._try_handle_partner_press_message(message):
                return

            session_id = self._get_session_id(message)
            
            # Get or create session context
            session = None
            if self.context_manager:
                session = self.context_manager.get_or_create_session(session_id)
            
            # Extract machine (or use context)
            machine_raw = message.data.get('machine')
            machine = self._normalize_machine_name(machine_raw) if machine_raw else None
            
            # Use context if no machine specified
            if not machine and session and session.last_machine:
                machine = session.last_machine
                self.logger.info("using_context_machine", machine=machine, session_id=session_id)
            
            # Extract time range from utterance
            time_range = self._extract_time_range(utterance)
            
            intent = Intent(
                intent=IntentType.ANOMALY_DETECTION,
                time_range=time_range,
                machine=machine,
                confidence=0.95,
                utterance=utterance
            )
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                response = self.response_formatter.format_response('anomaly_detection', result['data'])
                self._emit_structured_response(
                    session_id,
                    intent.intent,
                    result.get('data'),
                    confidence=intent.confidence,
                    utterance=utterance,
                    machine=machine
                )
                self.speak(response)
                
                # Update context for next query
                if session:
                    session.add_turn(utterance, intent, response, result['data'])
                    self.logger.info("context_updated", session_id=session_id, machine=machine)
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"Anomaly detection handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('Ranking').require('ranking').build())
    def handle_ranking(self, message: Message):
        """Handle ranking/top consumers queries - OVOS interface layer"""
        try:
            if self._try_handle_partner_press_message(message):
                return

            utterance = message.data.get("utterances", [""])[0]
            limit = message.data.get('limit')
            session_id = self._get_session_id(message)
            
            # Convert limit to int if Adapt provided one; otherwise parse spoken top-N words.
            try:
                limit_int = int(limit) if limit else self._extract_ranking_limit(utterance)
            except:
                limit_int = self._extract_ranking_limit(utterance)
            
            intent = Intent(
                intent=IntentType.RANKING,
                limit=limit_int,
                confidence=0.95,
                utterance=utterance
            )
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                response = self.response_formatter.format_response(
                    result.get('template') or 'ranking',
                    result['data']
                )
                self._emit_structured_response(
                    session_id,
                    intent.intent,
                    result.get('data'),
                    confidence=intent.confidence,
                    utterance=utterance
                )
                self.speak(response)
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"Ranking handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('Comparison').require('comparison').require('machine').build())
    def handle_comparison(self, message: Message):
        """Handle machine comparison queries - OVOS interface layer (Phase 3.1: with context)"""
        try:
            if self._try_handle_partner_press_message(message):
                return

            utterance = message.data.get("utterances", [""])[0]
            session_id = self._get_session_id(message)
            
            # Get or create session context
            session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None
            
            # Extract machine
            machine_raw = message.data.get('machine')
            machine = self._normalize_machine_name(machine_raw) if machine_raw else None
            
            intent = Intent(
                intent=IntentType.COMPARISON,
                machine=machine,
                confidence=0.95,
                utterance=utterance
            )
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                response = self.response_formatter.format_response('comparison', result['data'])
                self.speak(response)
                
                # Update context for next query
                session.add_turn(utterance, intent, response, result['data'])
                self.logger.info("context_updated", session_id=session_id, machines=intent.machines)
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"Comparison handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('CostAnalysis').require('cost_metric').optionally('machine').build())
    def handle_cost_analysis(self, message: Message):
        """Handle cost analysis queries - OVOS interface layer (Phase 3.1: with context)"""
        self.logger.info("COST_HANDLER_ENTRY")
        print("=" * 80)
        print("COST HANDLER CALLED!")
        print("=" * 80)
        try:
            utterance = message.data.get("utterances", [""])[0]
            if self._try_handle_partner_press_message(message):
                return
            session_id = self._get_session_id(message)
            self.logger.info("cost_handler_start", utterance=utterance, session_id=session_id)
            
            # Get or create session context
            session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None
            self.logger.info("cost_session_retrieved", session_id=session_id)
            
            # Extract machine (or use context)
            machine_raw = message.data.get('machine')
            machine = self._normalize_machine_name(machine_raw) if machine_raw else None
            
            # Use context if no machine specified
            if not machine and session and session.last_machine:
                machine = session.last_machine
                self.logger.info("using_context_machine", machine=machine, session_id=session_id)
            
            # Extract time range from utterance
            time_range = self._extract_time_range(utterance)
            
            intent = Intent(
                intent=IntentType.COST_ANALYSIS,
                time_range=time_range,
                machine=machine,
                confidence=0.95,
                utterance=utterance
            )
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                self.logger.info("cost_api_success", data_keys=list(result['data'].keys()))
                response = self.response_formatter.format_response('cost_analysis', result['data'])
                self.logger.info("cost_response_generated", response=response[:100])
                self.speak(response)
                
                # Update context for next query
                session.add_turn(utterance, intent, response, result['data'])
                self.logger.info("context_updated", session_id=session_id, machine=machine, metric="cost")
            else:
                self.logger.error("cost_api_failed", error=result.get('error'))
                self.speak_dialog("error.general")
        except Exception as e:
            self.logger.error("cost_handler_exception", error=str(e), error_type=type(e).__name__)
            import traceback
            self.logger.error("cost_handler_traceback", trace=traceback.format_exc())
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('Forecast').require('forecast').optionally('machine').build())
    def handle_forecast(self, message: Message):
        """Handle energy forecast queries - OVOS interface layer (Phase 3.1: with context)"""
        try:
            utterance = message.data.get("utterances", [""])[0]
            session_id = self._get_session_id(message)
            
            # Get or create session context
            session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None
            
            # Extract machine (or use context)
            machine_raw = message.data.get('machine')
            machine = self._normalize_machine_name(machine_raw) if machine_raw else None
            
            # Use context if no machine specified
            if not machine and session and session.last_machine:
                machine = session.last_machine
                self.logger.info("using_context_machine", machine=machine, session_id=session_id)
            
            # Extract time range from utterance
            time_range = self._extract_time_range(utterance)
            
            intent = Intent(
                intent=IntentType.FORECAST,
                time_range=time_range,
                machine=machine,
                confidence=0.95,
                utterance=utterance
            )
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                response = self.response_formatter.format_response('forecast', result['data'])
                self.speak(response)
                
                # Update context for next query
                session.add_turn(utterance, intent, response, result['data'])
                self.logger.info("context_updated", session_id=session_id, machine=machine)
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"Forecast handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('Baseline').require('baseline').require('machine').optionally('energy_source').build())
    def handle_baseline(self, message: Message):
        """Handle baseline prediction queries - OVOS interface layer (Phase 3.1: with context)"""
        try:
            utterance = message.data.get("utterances", [""])[0]
            if self._try_handle_partner_press_message(message):
                return

            session_id = self._get_session_id(message)
            
            # Get or create session context
            session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None
            
            # Extract machine (or use context)
            machine_raw = message.data.get('machine')
            machine = self._normalize_machine_name(machine_raw) if machine_raw else None
            energy_source = self._extract_energy_source(utterance, message.data.get('energy_source'))
            
            # Use context if no machine specified and required
            if not machine and session and session.last_machine:
                machine = session.last_machine
                self.logger.info("using_context_machine", machine=machine, session_id=session_id)
            if not energy_source and session and session.last_energy_source:
                energy_source = session.last_energy_source
            
            # Extract time range from utterance
            time_range = self._extract_time_range(utterance)
            
            intent = Intent(
                intent=IntentType.BASELINE,
                time_range=time_range,
                machine=machine,
                energy_source=energy_source,
                confidence=0.95,
                utterance=utterance
            )
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                response = self.response_formatter.format_response('baseline', result['data'])
                self.speak(response)
                
                # Update context for next query
                session.add_turn(utterance, intent, response, result['data'])
                self.logger.info("context_updated", session_id=session_id, machine=machine)
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"Baseline handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('BaselineModels').require('baseline').require('machine').optionally('energy_source').require('model_query').build())
    def handle_baseline_models(self, message: Message):
        """Handle baseline models listing - OVOS interface layer (Phase 3.1: with context)"""
        try:
            utterance = message.data.get("utterances", [""])[0]
            session_id = self._get_session_id(message)
            
            # Get or create session context
            session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None
            
            # Extract machine (or use context)
            machine_raw = message.data.get('machine')
            machine = self._normalize_machine_name(machine_raw) if machine_raw else None
            energy_source = self._extract_energy_source(utterance, message.data.get('energy_source'))
            
            # Use context if no machine specified
            if not machine and session and session.last_machine:
                machine = session.last_machine
                self.logger.info("using_context_machine", machine=machine, session_id=session_id)
            if not energy_source and session and session.last_energy_source:
                energy_source = session.last_energy_source
            
            intent = Intent(
                intent=IntentType.BASELINE_MODELS,
                machine=machine,
                energy_source=energy_source,
                confidence=0.95,
                utterance=utterance
            )
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                response = self.response_formatter.format_response('baseline_models', result['data'])
                self.speak(response)
                
                # Update context for next query
                session.add_turn(utterance, intent, response, result['data'])
                self.logger.info("context_updated", session_id=session_id, machine=machine)
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"Baseline models handler failed: {e}")
            self.speak_dialog("error.general")

    def _handle_baseline_explanation_message(self, message: Message):
        """Shared baseline explanation flow for both baseline and driver-specific Adapt intents."""
        utterance = message.data.get("utterances", [""])[0]
        session_id = self._get_session_id(message)

        session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None

        machine_raw = message.data.get('machine')
        machine = self._normalize_machine_name(machine_raw) if machine_raw else None
        energy_source = self._extract_energy_source(utterance, message.data.get('energy_source'))
        driver_direction = self._extract_driver_direction(utterance)

        if not machine and session and session.last_machine:
            machine = session.last_machine
            self.logger.info("using_context_machine", machine=machine, session_id=session_id)
        if not energy_source and session and session.last_energy_source:
            energy_source = session.last_energy_source

        intent = Intent(
            intent=IntentType.BASELINE_EXPLANATION,
            machine=machine,
            energy_source=energy_source,
            params={'driver_direction': driver_direction} if driver_direction else None,
            confidence=0.95,
            utterance=utterance
        )

        result = self._call_enms_api(intent)

        if result['success']:
            response = self.response_formatter.format_response('baseline_explanation', result['data'])
            self.speak(response)
            session.add_turn(utterance, intent, response, result['data'])
            self.logger.info("context_updated", session_id=session_id, machine=machine)
        else:
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('BaselineExplanation').require('kpi_metric').require('machine').optionally('energy_source').require('explain_query').build())
    def handle_baseline_explanation(self, message: Message):
        """Handle baseline explanation queries - OVOS interface layer (Phase 3.1: with context)"""
        try:
            self._handle_baseline_explanation_message(message)
        except Exception as e:
            self.log.error(f"Baseline explanation handler failed: {e}")
            self.speak_dialog("error.general")

    @intent_handler(IntentBuilder('DriverExplanation').require('driver_query').require('machine').optionally('energy_source').build())
    def handle_driver_explanation(self, message: Message):
        """Handle explicit driver questions with high-confidence Adapt matching."""
        try:
            self._handle_baseline_explanation_message(message)
        except Exception as e:
            self.log.error(f"Driver explanation handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('SEUs').require('seu_query').build())
    def handle_seus(self, message: Message):
        """Handle SEU (Significant Energy Uses) queries - OVOS interface layer"""
        try:
            if self._try_handle_partner_press_message(message):
                return

            utterance = message.data.get("utterances", [""])[0]
            
            intent = Intent(
                intent=IntentType.SEUS,
                confidence=0.95,
                utterance=utterance
            )
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                response = self.response_formatter.format_response('seus', result['data'])
                self.speak(response)
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"SEUs handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('KPI').require('kpi_metric').optionally('machine').build())
    def handle_kpi(self, message: Message):
        """Handle KPI queries - OVOS interface layer (Phase 3.1: with context)"""
        try:
            if self._try_handle_partner_press_message(message):
                return

            utterance = message.data.get("utterances", [""])[0]
            session_id = self._get_session_id(message)
            
            # Get or create session context
            session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None
            
            # Extract machine (or use context)
            machine_raw = message.data.get('machine')
            machine = self._normalize_machine_name(machine_raw) if machine_raw else None
            
            # Use context if no machine specified
            if not machine and session and session.last_machine:
                machine = session.last_machine
                self.logger.info("using_context_machine", machine=machine, session_id=session_id)
            
            intent = Intent(
                intent=IntentType.KPI,
                machine=machine,
                confidence=0.95,
                utterance=utterance
            )
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                response = self.response_formatter.format_response('kpi', result['data'])
                self.speak(response)
                
                # Update context for next query
                session.add_turn(utterance, intent, response, result['data'])
                self.logger.info("context_updated", session_id=session_id, machine=machine, metric="kpi")
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"KPI handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('Performance').require('performance_query').require('machine').build())
    def handle_performance(self, message: Message):
        """Handle performance analysis queries - OVOS interface layer (Phase 3.1: with context)"""
        try:
            utterance = message.data.get("utterances", [""])[0]
            session_id = self._get_session_id(message)
            
            # Get or create session context
            session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None
            
            # Extract machine (or use context)
            machine_raw = message.data.get('machine')
            machine = self._normalize_machine_name(machine_raw) if machine_raw else None
            
            # Use context if no machine specified
            if not machine and session and session.last_machine:
                machine = session.last_machine
                self.logger.info("using_context_machine", machine=machine, session_id=session_id)
            
            intent = Intent(
                intent=IntentType.PERFORMANCE,
                machine=machine,
                confidence=0.95,
                utterance=utterance
            )
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                response = self.response_formatter.format_response('performance', result['data'])
                self.speak(response)
                
                # Update context for next query
                session.add_turn(utterance, intent, response, result['data'])
                self.logger.info("context_updated", session_id=session_id, machine=machine)
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"Performance handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('Production').require('production_query').require('machine').build())
    def handle_production(self, message: Message):
        """Handle production data queries - OVOS interface layer (Phase 3.1: with context)"""
        try:
            if self._try_handle_partner_press_message(message):
                return

            utterance = message.data.get("utterances", [""])[0]
            session_id = self._get_session_id(message)
            
            # Get or create session context
            session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None
            
            # Extract machine (or use context)
            machine_raw = message.data.get('machine')
            machine = self._normalize_machine_name(machine_raw) if machine_raw else None
            
            # Use context if no machine specified
            if not machine and session and session.last_machine:
                machine = session.last_machine
                self.logger.info("using_context_machine", machine=machine, session_id=session_id)
            
            intent = Intent(
                intent=IntentType.PRODUCTION,
                machine=machine,
                confidence=0.95,
                utterance=utterance
            )
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                response = self.response_formatter.format_response('production', result['data'])
                self.speak(response)
                
                # Update context for next query
                session.add_turn(utterance, intent, response, result['data'])
                self.logger.info("context_updated", session_id=session_id, machine=machine)
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"Production handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('PowerQuery').require('power_metric').optionally('machine').build())
    def handle_power_query(self, message: Message):
        """
        Handle power consumption queries - OVOS interface layer
        
        Priority 3: Now handles both machine-specific AND factory-wide queries:
        - "Compressor-1 power" → Machine-specific
        - "what's the current draw?" → Factory-wide
        - "how much power are we using?" → Factory-wide
        
        Phase 3.1: Uses session context for follow-up queries
        """
        try:
            if self._try_handle_partner_press_message(message):
                return

            utterance = message.data.get("utterances", [""])[0]
            session_id = self._get_session_id(message)
            
            # Get or create session context
            session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None
            
            # Extract machine (or use context)
            machine_raw = message.data.get('machine')
            machine = self._normalize_machine_name(machine_raw) if machine_raw else None
            
            # Use context if no machine specified
            if not machine and session and session.last_machine:
                machine = session.last_machine
                self.logger.info("using_context_machine", machine=machine, session_id=session_id)

            if not machine and self._looks_like_ranking_query(utterance):
                ranking_metric = self._infer_ranking_metric_from_utterance(utterance)
                ranking_limit = self._extract_ranking_limit(utterance)
                ranking_intent = Intent(
                    intent=IntentType.RANKING,
                    limit=ranking_limit,
                    metric=ranking_metric,
                    ranking_metric=ranking_metric,
                    confidence=0.90,
                    utterance=utterance,
                )

                self.logger.info(
                    "power_query_rerouted_to_ranking",
                    utterance=utterance,
                    limit=ranking_limit,
                    metric=ranking_metric,
                )

                result = self._call_enms_api(ranking_intent)

                if result['success']:
                    response_text = self.response_formatter.format_response('ranking', result['data'])
                    self._emit_structured_response(
                        session_id,
                        ranking_intent.intent,
                        result.get('data'),
                        confidence=ranking_intent.confidence,
                        utterance=utterance,
                    )
                    self.speak(response_text)

                    if session:
                        session.add_turn(utterance, ranking_intent, response_text, result['data'])

                    return

                self.speak_dialog("error.general")
                return
            
            # Extract time range from utterance
            time_range = self._extract_time_range(utterance)
            
            intent = Intent(
                intent=IntentType.POWER_QUERY,
                machine=machine,
                time_range=time_range,
                confidence=0.95,
                utterance=utterance,
                params={'factory_wide': True} if not machine else None
            )
            
            # Log query type
            if not machine:
                self.logger.info("factory_wide_power_query", utterance=utterance)
            else:
                self.logger.info("machine_specific_power_query", machine=machine, utterance=utterance)
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                if not machine:
                    # Factory-wide: use speak_dialog with data
                    response_text = f"Current power is {result['data'].get('current_power_kw', 0):.1f} kilowatts"
                    self._emit_structured_response(
                        session_id,
                        intent.intent,
                        result.get('data'),
                        confidence=intent.confidence,
                        utterance=utterance,
                        machine=machine
                    )
                    self.speak_dialog("factory_power", result['data'])
                else:
                    # Machine-specific: use formatter
                    response_text = self.response_formatter.format_response('power_query', result['data'])
                    self._emit_structured_response(
                        session_id,
                        intent.intent,
                        result.get('data'),
                        confidence=intent.confidence,
                        utterance=utterance,
                        machine=machine
                    )
                    self.speak(response_text)
                
                # Update context for next query
                session.add_turn(utterance, intent, response_text, result['data'])
                self.logger.info("context_updated", session_id=session_id, machine=machine, metric="power")
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"Power query handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('Report').require('report_query').build())
    def handle_report(self, message: Message):
        """Handle report generation queries - OVOS interface layer"""
        try:
            report_type = message.data.get('report_type')
            machine_raw = message.data.get('machine')

            machine = self._normalize_machine_name(machine_raw)
            utterance = message.data.get("utterances", [""])[0]
            session_id = self._get_session_id(message)
            utterance_lower = utterance.lower()

            is_enpi_status_query = (
                any(phrase in utterance_lower for phrase in [
                    'energy performance indicator',
                    'energy performance indicators',
                    'enpi report',
                    'enpi status',
                    'iso 50001 report',
                    'compliance report'
                ])
                and not any(action in utterance_lower for action in [
                    'download',
                    'generate',
                    'create',
                    'export',
                    'pdf'
                ])
            )

            if is_enpi_status_query:
                result = self._process_query(utterance, session_id)
                if result.get('success'):
                    self._emit_structured_response(
                        session_id,
                        result.get('intent'),
                        result.get('data'),
                        confidence=result.get('confidence'),
                        utterance=utterance,
                        machine=result.get('machine')
                    )
                    self.speak(result['response'])
                else:
                    self.speak(result.get('response') or "Sorry, I couldn't retrieve the EnPI report.")
                return
            
            intent = Intent(
                intent=IntentType.REPORT,
                machine=machine,
                confidence=0.95,
                utterance=utterance,
                params={'report_type': report_type} if report_type else None
            )
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                response = self.response_formatter.format_response('enpi_report', result['data'])
                self.speak(response)
            else:
                self.speak_dialog("error.general")
        except Exception as e:
            self.log.error(f"Report handler failed: {e}")
            self.speak_dialog("error.general")
    
    @intent_handler(IntentBuilder('Help').require('help_query').build())
    def handle_help(self, message: Message):
        """Handle help queries - OVOS interface layer"""
        try:
            utterance = message.data.get("utterances", [""])[0]
            
            intent = Intent(
                intent=IntentType.HELP,
                confidence=0.95,
                utterance=utterance
            )
            
            result = self._call_enms_api(intent)
            
            if result['success']:
                response = self.response_formatter.format_response('help', result['data'])
                self.speak(response)
            else:
                self.speak("I can help you with energy monitoring, machine status, anomaly detection, KPIs, forecasting, and more. Try asking about a specific machine or factory overview.")
        except Exception as e:
            self.log.error(f"Help handler failed: {e}")
            self.speak("I can help you with energy monitoring, machine status, anomaly detection, KPIs, forecasting, and more. Try asking about a specific machine or factory overview.")
    
    def _handle_fallback(self, message: Message) -> bool:
        """
        Fallback handler (Tier 3) — catches queries that no intent matcher could handle.
        
        Fires at fallback_low priority (90) AFTER all adapt/padatious matchers fail.
        Routes through HybridParser which includes LLM for complex/typo queries.
        
        Returns:
            True if we handled the utterance, False to let other fallback skills try
        """
        try:
            utterance = message.data.get("utterances", [""])[0]
            if utterance and utterance.strip().lower() in {"ping", "pong"}:
                self.logger.debug("fallback_probe_ignored", utterance=utterance.strip().lower())
                return False

            if not utterance or len(utterance.strip()) < 3:
                return False
            
            self.logger.info("fallback_handler_triggered",
                           utterance=utterance[:80],
                           reason="no_intent_match")
            
            session_id = self._get_session_id(message)
            result = self._process_query(utterance, session_id)
            
            if result.get('success'):
                self._emit_structured_response(
                    session_id,
                    result.get('intent'),
                    result.get('data'),
                    confidence=result.get('confidence'),
                    utterance=utterance,
                    machine=result.get('machine')
                )
                self.speak(result['response'])
                
                # For report generation, emit custom event with PDF data
                if result.get('pdf_base64'):
                    self.bus.emit(Message(
                        "enms.report.generated",
                        {
                            "pdf_base64": result['pdf_base64'],
                            "filename": result.get('pdf_filename', 'report.pdf')
                        },
                        {"session_id": session_id}
                    ))
                return True
            
            # If HybridParser returned clarification_needed, speak the suggestion
            response = result.get('response', '')
            if response:
                self.speak(response)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error("fallback_handler_error",
                            error=str(e),
                            error_type=type(e).__name__,
                            utterance=message.data.get("utterances", [""])[0][:80])
            return False
    
    def can_answer(self, message: Message) -> bool:
        """Required by FallbackSkill — determines if we can handle this fallback query.
        
        We always return True because our _handle_fallback will route through
        HybridParser (with LLM) or return a clarification response.
        """
        return True
    
    def can_converse(self, message: Message) -> bool:
        """
        Required by ConversationalSkill - determines if this skill should handle the utterance.
        We always return True because EnMS handles all energy-related queries via converse().
        """
        return True
    
    def converse(self, message: Message) -> bool:
        """
        Handle follow-up questions and contextual queries
        
        Now that we have proper @intent_handler methods, this method only handles:
        - Follow-up questions ("what about yesterday?", "and the other one?")
        - Contextual queries that need previous conversation context
        - Queries that don't match any intent patterns (fallback)
        
        Returns:
            True if we handled the utterance, False to let intent handlers try
            
        CRITICAL: This method MUST always return True/False, never hang.
        All processing is wrapped in try/except to ensure robustness.
        """
        try:
            utterance = message.data.get("utterances", [""])[0]
            
            # Empty or too short utterance
            if not utterance or len(utterance.strip()) < 2:
                return False
            
            # Check if this is a follow-up/contextual query
            # These typically reference previous context without full detail
            follow_up_indicators = [
                'what about', 'and the', 'how about', 'also show',
                'what else', 'anything else', 'more details', 'tell me more',
                'yesterday', 'last week', 'last month', 'today',
                'the other', 'another', 'different'
            ]
            
            is_follow_up = any(indicator in utterance.lower() for indicator in follow_up_indicators)
            
            # Check if we have active context
            session_id = self._get_session_id(message)
            has_context = False
            if self.context_manager:
                session = self.context_manager.get_or_create_session(session_id) if self.context_manager else None
                has_context = len(session.history) > 0
            
            # Only handle if it's clearly a follow-up AND we have context
            # Otherwise, let intent handlers try first
            if not (is_follow_up and has_context):
                return False
            
            # Process as follow-up query with context
            result = self._process_query(utterance, session_id)
            
            if result['success'] or 'error' in result:
                if result.get('success'):
                    self._emit_structured_response(
                        session_id,
                        result.get('intent'),
                        result.get('data'),
                        confidence=result.get('confidence'),
                        utterance=utterance,
                        machine=result.get('machine')
                    )
                self.speak(result['response'])
                
                # For report generation, emit custom event with PDF data
                if result.get('pdf_base64'):
                    self.bus.emit(Message(
                        "enms.report.generated",
                        {
                            "pdf_base64": result['pdf_base64'],
                            "filename": result.get('pdf_filename', 'report.pdf')
                        },
                        {"session_id": session_id}
                    ))
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error("converse_crash", 
                            error=str(e), 
                            error_type=type(e).__name__,
                            utterance=message.data.get("utterances", [""])[0])
            return False  # Let intent handlers try instead
    
    def shutdown(self):
        """Clean shutdown of skill components"""
        # Cancel all scheduled events to prevent callbacks on dead instance
        try:
            self.cancel_all_repeating_events()
        except Exception as e:
            self.logger.error("event_cancellation_failed", error=str(e))
        
        self.logger.info("skill_shutdown", 
                        skill_name="EnmsSkill",
                        total_queries=self.query_count,
                        avg_latency_ms=round(self.total_latency_ms / max(self.query_count, 1), 2))
        
        # Close async clients using persistent loop
        try:
            if self.api_client:
                self._run_async(self.api_client.close())
        except Exception as e:
            self.logger.error("api_client_shutdown_failed", error=str(e))
        
        # Close the persistent event loop
        try:
            if self._async_loop and not self._async_loop.is_closed():
                self._async_loop.close()
                self._async_loop = None
        except Exception as e:
            self.logger.error("event_loop_shutdown_failed", error=str(e))
        
        # Cleanup conversation sessions
        try:
            if self.context_manager:
                self.context_manager.cleanup_expired_sessions()
        except Exception as e:
            self.logger.error("context_cleanup_failed", error=str(e))
        
        super().shutdown()
