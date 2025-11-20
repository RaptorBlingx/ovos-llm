"""
EnMS OVOS GUI - Message Bus Client
Connects to OVOS Core via WebSocket message bus

This is the PROPER architecture:
- GUI is just a frontend
- Sends messages to OVOS Core via message bus
- OVOS Core routes to the skill
- Skill processes and responds
- GUI displays the response

Run: python scripts/gui_messagebus.py
Open: http://localhost:7862
"""
import sys
import asyncio
import json
from pathlib import Path
from typing import List, Optional
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

import gradio as gr
from ovos_bus_client import MessageBusClient, Message
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


class OVOSMessageBusGUI:
    """GUI that connects to OVOS via message bus"""
    
    def __init__(self):
        """Initialize OVOS message bus connection"""
        print("🔧 Initializing OVOS Message Bus GUI...")
        
        # Connect to OVOS message bus
        print("  [1/2] Connecting to OVOS message bus...")
        self.bus = MessageBusClient()
        self.bus.run_in_thread()
        
        # Wait for connection
        for i in range(10):
            if self.bus.started_running:
                break
            time.sleep(0.5)
        
        if not self.bus.started_running:
            raise RuntimeError("Failed to connect to OVOS message bus")
        
        print("  [2/2] Message bus connected!")
        
        # Response storage
        self.last_response = None
        self.response_event = asyncio.Event()
        
        # Register handlers for skill responses
        self.bus.on('speak', self._handle_speak)
        self.bus.on('enms.response', self._handle_enms_response)
        
        print("✅ OVOS Message Bus GUI ready!\n")
    
    def _handle_speak(self, message):
        """Handle TTS speak events from OVOS"""
        utterance = message.data.get('utterance', '')
        logger.info("ovos_speak", utterance=utterance)
        self.last_response = utterance
        self.response_event.set()
    
    def _handle_enms_response(self, message):
        """Handle custom EnMS skill responses"""
        response = message.data.get('response', '')
        logger.info("enms_response", response=response)
        self.last_response = response
        self.response_event.set()
    
    async def query_ovos(self, query: str, timeout: float = 30.0) -> tuple[str, dict]:
        """
        Send query to OVOS and wait for response
        
        Args:
            query: User query
            timeout: Max wait time in seconds
            
        Returns:
            (response_text, debug_info)
        """
        debug_info = {
            'query': query,
            'timestamp': time.time(),
            'bus_connected': self.bus.started_running
        }
        
        try:
            # Reset response
            self.last_response = None
            self.response_event.clear()
            
            # Send utterance to OVOS
            # This mimics a user speaking to OVOS
            message = Message(
                'recognizer_loop:utterance',
                {
                    'utterances': [query],
                    'lang': 'en-us',
                    'session': {'session_id': f'gui-{int(time.time())}'}
                }
            )
            
            logger.info("sending_to_ovos", query=query)
            debug_info['message_sent'] = True
            
            self.bus.emit(message)
            
            # Wait for response with timeout
            try:
                await asyncio.wait_for(
                    self.response_event.wait(),
                    timeout=timeout
                )
                
                response = self.last_response or "No response received"
                debug_info['response_received'] = True
                debug_info['response'] = response
                
                return f"🤖 {response}", debug_info
                
            except asyncio.TimeoutError:
                debug_info['timeout'] = True
                return f"⏱️ Timeout waiting for OVOS response ({timeout}s)", debug_info
            
        except Exception as e:
            logger.error("query_error", error=str(e))
            debug_info['error'] = str(e)
            return f"❌ Error: {str(e)}", debug_info
    
    def query_sync(self, query: str) -> tuple[str, dict]:
        """Synchronous wrapper for gradio"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.query_ovos(query))
        finally:
            loop.close()
    
    def close(self):
        """Close message bus connection"""
        if self.bus:
            self.bus.close()
        logger.info("ovos_gui_closed")


# Global GUI instance
gui_client = None


def chat_interface(message: str, history: List[dict]) -> tuple[str, str]:
    """
    Gradio chat interface handler
    
    Args:
        message: User input
        history: Chat history
        
    Returns:
        (response, debug_info_formatted)
    """
    global gui_client
    
    if gui_client is None:
        gui_client = OVOSMessageBusGUI()
    
    if not message.strip():
        return "", "**Enter a query to see debug info**"
    
    response, debug_info = gui_client.query_sync(message)
    
    # Format debug info
    debug_text = f"""
**Query Sent:** {debug_info.get('query', 'N/A')}

**Message Bus:**
- Connected: {debug_info.get('bus_connected', False)}
- Message Sent: {debug_info.get('message_sent', False)}
- Response Received: {debug_info.get('response_received', False)}

**Timing:**
- Timestamp: {debug_info.get('timestamp', 0)}
- Timeout: {debug_info.get('timeout', False)}

**Response:**
```
{debug_info.get('response', 'N/A')}
```

**Error:** {debug_info.get('error', 'None')}
"""
    
    return response, debug_text


def create_gui():
    """Create Gradio chat interface"""
    
    with gr.Blocks(title="OVOS EnMS Assistant", theme=gr.themes.Soft()) as app:
        gr.Markdown("""
        # 🏭 OVOS EnMS Energy Assistant
        ### Message Bus Integration - Connected to Real OVOS Skill
        
        **Architecture:**
        - Frontend: This Gradio GUI
        - Message Bus: WebSocket connection to OVOS Core
        - Backend: EnMS Skill running in OVOS
        
        **Try these queries:**
        - "Check system health"
        - "What's the power consumption of Compressor-1?"
        - "How much energy did Boiler-1 use today?"
        - "Is HVAC-EU-North running?"
        - "Factory overview"
        - "Show me top 5 energy consumers"
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                chatbot_ui = gr.Chatbot(
                    label="OVOS Chat",
                    height=400,
                    type="messages"
                )
                
                msg = gr.Textbox(
                    label="Your Query",
                    placeholder="Ask OVOS about machines, energy, power, or factory status...",
                    lines=2
                )
                
                with gr.Row():
                    submit = gr.Button("Send to OVOS", variant="primary")
                    clear = gr.Button("Clear")
            
            with gr.Column(scale=1):
                debug_output = gr.Markdown(
                    label="Message Bus Debug",
                    value="**Message bus info will appear here**"
                )
        
        gr.Examples(
            examples=[
                "Check system health",
                "What's the power of Compressor-1?",
                "How much energy did Boiler-1 use today?",
                "Is HVAC-EU-North running?",
                "Factory overview",
                "Show me top 5 energy consumers",
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
        clear.click(lambda: ([], "**Message bus info will appear here**"), None, [chatbot_ui, debug_output])
    
    return app


if __name__ == "__main__":
    import os
    
    print("\n" + "="*80)
    print("OVOS EnMS Assistant - Message Bus GUI")
    print("="*80 + "\n")
    
    # Check if OVOS is running
    print("⚠️  PREREQUISITES:")
    print("   1. OVOS Core must be running: systemctl status ovos-core")
    print("   2. EnMS skill must be loaded and active")
    print("   3. Message bus must be accessible (default: ws://localhost:8181/core)\n")
    
    try:
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
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  - Check OVOS is running: systemctl status ovos-core")
        print("  - Check message bus: netstat -an | grep 8181")
        print("  - Install ovos-bus-client: pip install ovos-bus-client")
        sys.exit(1)
