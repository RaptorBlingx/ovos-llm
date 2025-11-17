"""
OVOS EnMS Skill - Industrial Energy Management Voice Assistant
Integration with Energy Management System (EnMS) API
"""
from typing import Optional, Dict, Any
import asyncio
import structlog
from ovos_workshop.decorators import intent_handler
from ovos_workshop.skills import OVOSSkill
from ovos_bus_client.message import Message

# Import our core modules
from .lib.qwen3_parser import Qwen3Parser
from .lib.validator import ENMSValidator
from .lib.api_client import ENMSClient
from .lib.models import IntentType
# from .lib.response_formatter import TemplateEngine  # Week 2

logger = structlog.get_logger(__name__)


class EnmsSkill(OVOSSkill):
    """
    OVOS Skill for Energy Management System Integration
    
    Architecture:
    - Tier 1: Qwen3-1.7B LLM for natural language understanding
    - Tier 2: Zero-trust validator (Pydantic schemas, entity whitelists)
    - Tier 3: EnMS API client (httpx, circuit breaker, retries)
    - Tier 4: Response formatter (Jinja2 templates, voice-optimized)
    - Tier 5: Fast-path NLU (Adapt/Padatious/Heuristics) - Week 3
    """

    def __init__(self, *args, **kwargs):
        """Initialize the EnMS skill"""
        super().__init__(*args, **kwargs)
        self.logger = structlog.get_logger(__name__)
        
        # Core components (initialized in initialize())
        self.parser = None
        self.validator = None
        self.api_client = None
        self.response_formatter = None
        
    def initialize(self):
        """
        Called after skill construction
        Initialize all core components here
        """
        self.logger.info("skill_initializing", skill_name="EnmsSkill")
        
        # Get settings from settingsmeta.yaml
        self.enms_api_base_url = self.settings.get("enms_api_base_url", "http://10.33.10.109:8001/api/v1")
        self.llm_model_path = self.settings.get("llm_model_path", "./models/qwen3-1.7b-instruct-q4_k_m.gguf")
        self.confidence_threshold = self.settings.get("confidence_threshold", 0.85)
        
        # Initialize Tier 1: LLM Parser
        self.parser = Qwen3Parser(
            model_path=self.llm_model_path,
            temperature=self.settings.get("llm_temperature", 0.1),
            max_tokens=self.settings.get("llm_max_tokens", 256)
        )
        
        # Initialize Tier 2: Validator
        self.validator = ENMSValidator(
            confidence_threshold=self.confidence_threshold,
            enable_fuzzy_matching=self.settings.get("enable_fuzzy_matching", True)
        )
        
        # Initialize Tier 3: API Client
        self.api_client = ENMSClient(
            base_url=self.enms_api_base_url,
            timeout=self.settings.get("api_timeout_seconds", 30)
        )
        
        # Tier 4: Response formatter (Week 2)
        # self.response_formatter = TemplateEngine(locale_dir=self.root_dir / "locale")
        
        # Load machine whitelist from EnMS API
        self.schedule_event(self._refresh_machine_whitelist, 0)  # Run immediately
        
        self.logger.info("skill_initialized", 
                        enms_api=self.enms_api_base_url,
                        llm_model=self.llm_model_path,
                        confidence_threshold=self.confidence_threshold)
    
    async def _refresh_machine_whitelist(self):
        """Refresh machine whitelist from EnMS API"""
        try:
            machines = await self.api_client.list_machines(is_active=True)
            machine_names = [m["name"] for m in machines]
            self.validator.update_machine_whitelist(machine_names)
            self.logger.info("machine_whitelist_refreshed", count=len(machine_names))
        except Exception as e:
            self.logger.error("whitelist_refresh_failed", error=str(e))
    
    def _run_async(self, coro):
        """Helper to run async coroutines from sync handlers"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    @intent_handler("energy.query.intent")
    def handle_energy_query(self, message: Message):
        """
        Handle energy consumption queries
        Examples:
        - "What's the power consumption of Compressor-1?"
        - "How much energy did Boiler-1 use yesterday?"
        - "Show me hourly energy for HVAC-Main"
        """
        utterance = message.data.get("utterance", "")
        self.logger.info("intent_received", intent="energy_query", utterance=utterance)
        
        self.speak_dialog("checking")
        
        # Tier 1: Parse with LLM
        llm_output = self.parser.parse(utterance)
        llm_output["utterance"] = utterance
        
        # Tier 2: Validate
        validation = self.validator.validate(llm_output)
        
        if not validation.valid:
            error_msg = " ".join(validation.errors)
            if validation.suggestions:
                error_msg += " " + " ".join(validation.suggestions)
            self.speak(f"Sorry, {error_msg}")
            return
        
        intent = validation.intent
        
        # Tier 3: Call EnMS API
        try:
            if intent.intent == IntentType.ENERGY_QUERY and intent.machine:
                # Get machine status (includes energy data)
                result = self._run_async(
                    self.api_client.get_machine_status(intent.machine)
                )
                
                # Tier 4: Simple response (template in Week 2)
                energy = result["today_stats"]["energy_kwh"]
                power = result["current_status"]["power_kw"]
                cost = result["today_stats"]["cost_usd"]
                
                response = (
                    f"{intent.machine} is currently using {power:.1f} kilowatts. "
                    f"Today it has consumed {energy:.1f} kilowatt hours, "
                    f"costing ${cost:.2f}"
                )
                self.speak(response)
                
            else:
                self.speak("I understood your query but this intent type is not yet implemented")
                
        except Exception as e:
            self.logger.error("api_call_failed", error=str(e))
            self.speak("Sorry, I couldn't retrieve that information from the energy system")
    
    @intent_handler("machine.status.intent")
    def handle_machine_status(self, message: Message):
        """
        Handle machine status queries
        Examples:
        - "Is Boiler-1 running?"
        - "What's the status of Compressor-1?"
        - "Check HVAC-Main"
        """
        utterance = message.data.get("utterance", "")
        self.logger.info("intent_received", intent="machine_status", utterance=utterance)
        
        self.speak_dialog("checking")
        self.speak("Status query handler not yet implemented")
    
    @intent_handler("factory.overview.intent")
    def handle_factory_overview(self, message: Message):
        """
        Handle factory-wide queries
        Examples:
        - "Factory overview"
        - "Show me factory status"
        - "Total factory consumption"
        """
        utterance = message.data.get("utterance", "")
        self.logger.info("intent_received", intent="factory_overview", utterance=utterance)
        
        self.speak_dialog("checking")
        self.speak("Factory overview handler not yet implemented")
    
    def shutdown(self):
        """Clean shutdown of skill components"""
        self.logger.info("skill_shutdown", skill_name="EnmsSkill")
        
        # TODO: Close async clients, cleanup resources
        # if self.api_client:
        #     await self.api_client.close()
        
        super().shutdown()


def create_skill():
    """Skill factory function required by OVOS"""
    return EnmsSkill()
