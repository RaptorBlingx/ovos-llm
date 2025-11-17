"""
EnMS LLM Chat GUI - Manual Testing Interface
Week 2: Test end-to-end LLM → Validator → API → Response pipeline

Run: python scripts/chat_gui.py
Open: http://localhost:7860
"""
import sys
import asyncio
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import gradio as gr
import structlog

from lib.qwen3_parser import Qwen3Parser
from lib.validator import ENMSValidator
from lib.api_client import ENMSClient
from lib.response_formatter import ResponseFormatter
from lib.models import IntentType

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger(__name__)


class EnMSChatbot:
    """EnMS Chatbot with full LLM pipeline"""
    
    def __init__(self):
        """Initialize all components"""
        print("🔧 Initializing EnMS Chatbot...")
        
        # Tier 1: LLM Parser
        print("  [1/4] Loading Qwen3 LLM (this may take a moment)...")
        self.parser = Qwen3Parser()
        
        # Tier 2: Validator
        print("  [2/4] Initializing validator...")
        self.validator = ENMSValidator(confidence_threshold=0.85)
        
        # Tier 3: API Client
        print("  [3/4] Connecting to EnMS API...")
        self.api_client = ENMSClient(base_url="http://10.33.10.109:8001/api/v1")
        
        # Tier 4: Response Formatter
        print("  [4/4] Loading response templates...")
        self.formatter = ResponseFormatter()
        
        # Load machine whitelist
        print("  📋 Loading machine whitelist from API...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            machines = loop.run_until_complete(self.api_client.list_machines(is_active=True))
            machine_names = [m["name"] for m in machines]
            self.validator.update_machine_whitelist(machine_names)
            print(f"  ✅ Loaded {len(machine_names)} machines: {', '.join(machine_names[:3])}...")
        finally:
            loop.close()
        
        print("✅ EnMS Chatbot ready!\n")
    
    def process_query(self, query: str) -> Tuple[str, dict]:
        """
        Process user query through full pipeline
        
        Returns:
            (response_text, debug_info)
        """
        debug_info = {}
        
        try:
            # Tier 1: LLM Parse
            debug_info['stage'] = 'LLM Parsing'
            llm_output = self.parser.parse(query)
            llm_output['utterance'] = query
            
            debug_info['llm_output'] = llm_output
            debug_info['intent'] = llm_output.get('intent')
            debug_info['confidence'] = llm_output.get('confidence')
            debug_info['entities'] = llm_output.get('entities', {})
            
            # Tier 2: Validate
            debug_info['stage'] = 'Validation'
            validation = self.validator.validate(llm_output)
            
            debug_info['validation'] = {
                'valid': validation.valid,
                'errors': validation.errors,
                'warnings': validation.warnings,
                'suggestions': validation.suggestions
            }
            
            if not validation.valid:
                error_msg = " ".join(validation.errors)
                if validation.suggestions:
                    error_msg += "\n\n" + "\n".join(validation.suggestions)
                return f"❌ {error_msg}", debug_info
            
            intent = validation.intent
            
            # Tier 3: Call EnMS API
            debug_info['stage'] = 'API Call'
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                api_data = None
                
                if intent.intent in [IntentType.ENERGY_QUERY, IntentType.POWER_QUERY, IntentType.MACHINE_STATUS]:
                    if intent.machine:
                        # Get machine status
                        result = loop.run_until_complete(
                            self.api_client.get_machine_status(intent.machine)
                        )
                        
                        api_data = {
                            'machine': intent.machine,
                            'is_running': result['current_status']['is_running'],
                            'status': result['current_status']['status'],
                            'power_kw': result['current_status']['power_kw'],
                            'energy_kwh': result['today_stats']['energy_kwh'],
                            'cost_eur': result['today_stats']['cost_usd'],
                            'time_range': 'today'
                        }
                        
                        debug_info['api_data'] = api_data
                
                elif intent.intent == IntentType.FACTORY_OVERVIEW:
                    # Get factory summary
                    result = loop.run_until_complete(
                        self.api_client.get_factory_summary()
                    )
                    
                    api_data = {
                        'total_machines': result['total_machines'],
                        'active_machines': result['active_machines'],
                        'total_power_kw': result['current_power_kw'],
                        'total_energy_kwh': result['today_energy_kwh']
                    }
                    
                    debug_info['api_data'] = api_data
                
                elif intent.intent == IntentType.RANKING:
                    # Get top consumers
                    limit = intent.entities.get('limit', 5)
                    result = loop.run_until_complete(
                        self.api_client.get_top_consumers(limit=limit, metric='energy')
                    )
                    
                    api_data = {
                        'limit': limit,
                        'top_consumers': result
                    }
                    
                    debug_info['api_data'] = api_data
                
                # Tier 4: Format Response
                debug_info['stage'] = 'Response Formatting'
                
                if api_data:
                    # Use templates
                    intent_map = {
                        IntentType.POWER_QUERY: 'power_query',
                        IntentType.ENERGY_QUERY: 'energy_query',
                        IntentType.MACHINE_STATUS: 'machine_status',
                        IntentType.FACTORY_OVERVIEW: 'factory_overview',
                        IntentType.RANKING: 'ranking'
                    }
                    
                    template_name = intent_map.get(intent.intent, 'energy_query')
                    response = self.formatter.format_response(template_name, api_data)
                    
                    return f"✅ {response}", debug_info
                else:
                    return f"⚠️ Intent '{intent.intent}' recognized but not yet implemented in API caller", debug_info
                
            finally:
                loop.close()
            
        except Exception as e:
            logger.error("query_processing_error", error=str(e))
            debug_info['error'] = str(e)
            return f"❌ Error: {str(e)}", debug_info


# Global chatbot instance
chatbot = None


def chat_interface(message: str, history: List[List[str]]) -> Tuple[str, str]:
    """
    Gradio chat interface handler
    
    Args:
        message: User input
        history: Chat history
        
    Returns:
        (response, debug_info_formatted)
    """
    global chatbot
    
    if chatbot is None:
        chatbot = EnMSChatbot()
    
    response, debug_info = chatbot.process_query(message)
    
    # Format debug info
    debug_text = f"""
**Stage:** {debug_info.get('stage', 'Unknown')}

**LLM Output:**
- Intent: {debug_info.get('intent', 'N/A')}
- Confidence: {debug_info.get('confidence', 0):.2f}
- Entities: {debug_info.get('entities', {})}

**Validation:**
{debug_info.get('validation', {})}

**API Data:**
{debug_info.get('api_data', 'N/A')}

**Error:** {debug_info.get('error', 'None')}
"""
    
    return response, debug_text


def create_gui():
    """Create Gradio chat interface"""
    
    with gr.Blocks(title="EnMS Energy Assistant", theme=gr.themes.Soft()) as app:
        gr.Markdown("""
        # 🏭 EnMS Energy Management Assistant
        ### LLM-Powered Industrial Energy Queries
        
        **Status:** Phase 1 Complete - Full LLM Pipeline ✅
        
        **Try these queries:**
        - "What's the power consumption of Compressor-1?"
        - "How much energy did Boiler-1 use?"
        - "Is HVAC-EU-North running?"
        - "Factory overview"
        - "Show me top 5 energy consumers"
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                chatbot_ui = gr.Chatbot(
                    label="Chat",
                    height=400,
                    type="messages"
                )
                
                msg = gr.Textbox(
                    label="Your Query",
                    placeholder="Ask about machines, energy, power, or factory status...",
                    lines=2
                )
                
                with gr.Row():
                    submit = gr.Button("Send", variant="primary")
                    clear = gr.Button("Clear")
            
            with gr.Column(scale=1):
                debug_output = gr.Markdown(
                    label="Debug Info",
                    value="**Debug information will appear here**"
                )
        
        gr.Examples(
            examples=[
                "What's the power of Compressor-1?",
                "How much energy did Boiler-1 use today?",
                "Is HVAC-EU-North running?",
                "Factory overview",
                "Show me top 5 energy consumers",
                "Compare Compressor-1 and Boiler-1"
            ],
            inputs=msg
        )
        
        def respond(message, chat_history):
            """Process message and update chat"""
            if not message.strip():
                return "", chat_history, "**Enter a query to see debug info**"
            
            response, debug_text = chat_interface(message, chat_history)
            
            # Add to chat history
            chat_history.append({"role": "user", "content": message})
            chat_history.append({"role": "assistant", "content": response})
            
            return "", chat_history, debug_text
        
        submit.click(respond, [msg, chatbot_ui], [msg, chatbot_ui, debug_output])
        msg.submit(respond, [msg, chatbot_ui], [msg, chatbot_ui, debug_output])
        clear.click(lambda: ([], "**Debug information will appear here**"), None, [chatbot_ui, debug_output])
    
    return app


if __name__ == "__main__":
    import os
    
    print("\n" + "="*80)
    print("EnMS Energy Assistant - Manual Testing GUI")
    print("="*80 + "\n")
    
    app = create_gui()
    
    port = int(os.getenv("GRADIO_SERVER_PORT", "7862"))
    print(f"\n🌐 Starting web interface on port {port}...")
    print(f"📍 Open in browser: http://localhost:{port}\n")
    
    app.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True
    )
