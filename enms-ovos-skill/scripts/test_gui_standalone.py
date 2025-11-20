"""
EnMS OVOS Skill - Standalone Testing GUI
Direct skill invocation without OVOS Core message bus

This properly tests the skill by:
1. Instantiating the actual EnmsSkill class from __init__.py
2. Calling its _process_query() method directly
3. Displaying the actual response from skill.speak()

Run: python scripts/test_gui_standalone.py
Open: http://localhost:7862
"""
import sys
import os
from pathlib import Path
from typing import List

skill_dir = Path(__file__).parent.parent
sys.path.insert(0, str(skill_dir))
os.chdir(str(skill_dir))

import gradio as gr
from ovos_bus_client.message import Message

# Import skill components directly (bypass __init__.py)
from lib.intent_parser import HybridParser
from lib.validator import ENMSValidator
from lib.api_client import ENMSClient
from lib.response_formatter import ResponseFormatter
from lib.conversation_context import ConversationContextManager
from lib.voice_feedback import VoiceFeedbackManager
from lib.models import IntentType, Intent
import asyncio
import structlog

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger(__name__)


class SkillTester:
    """Direct testing of skill components without OVOS framework"""
    
    def __init__(self):
        """Initialize skill components"""
        print("🔧 Initializing EnMS Skill Components...")
        
        # Create event loop for async
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize components
        print("  [1/5] Loading parser...")
        self.parser = HybridParser()
        
        print("  [2/5] Loading validator...")
        self.validator = ENMSValidator(confidence_threshold=0.85)
        
        print("  [3/5] Connecting to API...")
        self.api_client = ENMSClient(base_url="http://10.33.10.109:8001/api/v1")
        
        print("  [4/5] Loading formatter...")
        self.formatter = ResponseFormatter()
        
        print("  [5/5] Loading machine whitelist...")
        machines = self.loop.run_until_complete(self.api_client.list_machines(is_active=True))
        machine_names = [m["name"] for m in machines]
        self.validator.update_machine_whitelist(machine_names)
        print(f"       Loaded {len(machine_names)} machines")
        
        print("✅ Skill components ready!\n")
    
    def query_skill(self, query: str) -> tuple[str, dict]:
        """
        Process query through skill pipeline
        
        Returns:
            (response_text, debug_info)
        """
        debug_info = {'query': query}
        
        try:
            # Tier 1-3: Parse
            print(f"\n[Parsing] {query}")
            result = self.parser.parse(query)
            result['utterance'] = query
            debug_info['parse_result'] = result
            
            # Tier 4: Validate
            print(f"[Validating] Intent: {result.get('intent')}")
            validation = self.validator.validate(result)
            debug_info['validation'] = validation.valid
            
            if not validation.valid:
                return f"❌ {' '.join(validation.errors)}", debug_info
            
            intent = validation.intent
            debug_info['intent'] = intent.intent.value
            debug_info['machine'] = intent.machine
            
            # Tier 5: Call API
            print(f"[API Call] Intent: {intent.intent.value}, Machine: {intent.machine}")
            api_data = self.loop.run_until_complete(self._call_api(intent, query))
            debug_info['api_data'] = api_data
            
            # Tier 6: Format response
            print(f"[Formatting] Using templates...")
            response = self._format_response(intent, api_data)
            debug_info['response'] = response
            
            return f"🤖 {response}", debug_info
            
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            debug_info['error'] = error_msg
            logger.error("query_error", error=str(e))
            return f"❌ {str(e)}", debug_info
    
    async def _call_api(self, intent: Intent, utterance: str):
        """Call API based on intent (matches skill logic)"""
        # Health check detection
        health_keywords = ['online', 'health', 'status of', 'system status', 'running']
        is_health_query = any(kw in utterance.lower() for kw in health_keywords)
        
        if intent.intent == IntentType.FACTORY_OVERVIEW and is_health_query:
            result = await self.api_client.get_health()
            return {
                'status': result.get('status'),
                'active_machines': result.get('active_machines'),
                'baseline_models': result.get('baseline_models'),
                'database': result.get('database')
            }
        elif intent.intent == IntentType.FACTORY_OVERVIEW:
            result = await self.api_client.get_factory_summary()
            return {
                'total_machines': result['machines']['total'],
                'active_machines': result['machines']['active'],
                'total_power_kw': result['energy']['current_power_kw'],
                'total_energy_kwh': result['energy']['total_kwh_today']
            }
        elif intent.machine:
            result = await self.api_client.get_machine_status(intent.machine)
            return result
        
        return {}
    
    def _format_response(self, intent: Intent, api_data: dict) -> str:
        """Format response using templates (matches skill logic)"""
        # Special handling for health checks
        if intent.intent == IntentType.FACTORY_OVERVIEW and 'status' in api_data and 'database' in api_data:
            template = self.formatter.env.get_template('health_check.dialog')
            return template.render(**api_data).strip()
        
        # Use standard formatter
        return self.formatter.format(intent, api_data)


# Global skill instance
skill_tester = None


def chat_interface(message: str, history: List[dict]) -> tuple[str, str]:
    """Gradio chat handler"""
    global skill_tester
    
    if skill_tester is None:
        skill_tester = SkillTester()
    
    if not message.strip():
        return "", "**Enter a query to see debug info**"
    
    response, debug_info = skill_tester.query_skill(message)
    
    # Format debug info
    debug_text = f"""
**Query:** {debug_info.get('query', 'N/A')}

**Skill Processing:**
- Handled: {debug_info.get('handled', False)}
- Response: {debug_info.get('response', 'N/A')}

**Error:** {debug_info.get('error', 'None')}
"""
    
    return response, debug_text


def create_gui():
    """Create Gradio interface"""
    
    with gr.Blocks(title="EnMS Skill Tester", theme=gr.themes.Soft()) as app:
        gr.Markdown("""
        # 🏭 EnMS OVOS Skill - Standalone Tester
        ### Direct Skill Invocation (No Message Bus Required)
        
        **What this tests:**
        - Real EnmsSkill class from `__init__.py`
        - Actual `converse()` method that handles all queries
        - Real `_process_query()` pipeline
        - Real `speak()` responses
        
        **Try these queries:**
        - "Check system health"
        - "What's the power consumption of Compressor-1?"
        - "How much energy did Boiler-1 use today?"
        - "Is HVAC-EU-North running?"
        - "Factory overview"
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                chatbot_ui = gr.Chatbot(
                    label="Skill Chat",
                    height=400,
                    type="messages"
                )
                
                msg = gr.Textbox(
                    label="Your Query",
                    placeholder="Ask about machines, energy, power, or factory status...",
                    lines=2
                )
                
                with gr.Row():
                    submit = gr.Button("Test Query", variant="primary")
                    clear = gr.Button("Clear")
            
            with gr.Column(scale=1):
                debug_output = gr.Markdown(
                    label="Debug Info",
                    value="**Skill processing info will appear here**"
                )
        
        gr.Examples(
            examples=[
                "Check system health",
                "What's the power of Compressor-1?",
                "How much energy did Boiler-1 use today?",
                "Factory overview",
            ],
            inputs=msg
        )
        
        def respond(message, chat_history):
            """Process message and update chat"""
            if not message.strip():
                return "", chat_history, "**Enter a query**"
            
            response, debug_text = chat_interface(message, chat_history)
            
            # Add to chat history
            chat_history.append({"role": "user", "content": message})
            chat_history.append({"role": "assistant", "content": response})
            
            return "", chat_history, debug_text
        
        submit.click(respond, [msg, chatbot_ui], [msg, chatbot_ui, debug_output])
        msg.submit(respond, [msg, chatbot_ui], [msg, chatbot_ui, debug_output])
        clear.click(lambda: ([], "**Ready**"), None, [chatbot_ui, debug_output])
    
    return app


if __name__ == "__main__":
    print("\n" + "="*80)
    print("EnMS OVOS Skill - Standalone Testing GUI")
    print("="*80 + "\n")
    
    app = create_gui()
    
    print("\n🌐 Starting web interface on port 7862...")
    print("📍 Open in browser: http://localhost:7862\n")
    
    app.launch(
        server_name="0.0.0.0",
        server_port=7862,
        share=False,
        show_error=True
    )
