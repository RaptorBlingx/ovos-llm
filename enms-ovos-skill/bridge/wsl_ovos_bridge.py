#!/usr/bin/env python3
"""
WSL2 OVOS Bridge - Receives text from Windows STT Bridge and sends to OVOS messagebus.

This runs in WSL2 and:
1. Listens for WebSocket connections from Windows
2. Receives recognized utterances
3. Forwards them to OVOS messagebus
4. Sends OVOS responses back to Windows for TTS

Usage (in WSL2):
    source ~/ovos-env/bin/activate
    python wsl_ovos_bridge.py [--port 5678]
"""

import asyncio
import json
import logging
from typing import Set

import websockets
from ovos_bus_client import MessageBusClient, Message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WSL2OVOSBridge")


class WSL2OVOSBridge:
    """Bridge between Windows STT and OVOS messagebus."""
    
    def __init__(self, port: int = 5678):
        self.port = port
        self.bus = None
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.running = False
        self._loop = None  # Main event loop reference for thread-safe async calls
        
    def _connect_to_messagebus(self):
        """Connect to OVOS messagebus."""
        logger.info("Connecting to OVOS messagebus...")
        self.bus = MessageBusClient()
        self.bus.run_in_thread()
        
        # Wait for connection
        import time
        for _ in range(10):
            if self.bus.started_running:
                break
            time.sleep(0.5)
        
        if not self.bus.started_running:
            raise ConnectionError("Failed to connect to OVOS messagebus")
        
        logger.info("Connected to OVOS messagebus")
        
        # Subscribe to speak events to forward to Windows
        self.bus.on("speak", self._handle_speak)
        self.bus.on("recognizer_loop:audio_output_start", self._handle_audio_start)
        self.bus.on("recognizer_loop:audio_output_end", self._handle_audio_end)
        
    def _handle_speak(self, message: Message):
        """Handle speak events from OVOS - forward to Windows for TTS."""
        utterance = message.data.get("utterance", "")
        logger.info(f"OVOS speak: {utterance}")
        
        # Forward to all connected Windows clients (thread-safe)
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast({
                "type": "speak",
                "data": {"utterance": utterance}
            }), self._loop)
    
    def _handle_audio_start(self, message: Message):
        """Handle audio output start."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast({
                "type": "audio_output_start",
                "data": {}
            }), self._loop)
    
    def _handle_audio_end(self, message: Message):
        """Handle audio output end."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast({
                "type": "audio_output_end", 
                "data": {}
            }), self._loop)
    
    async def _broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if not self.connected_clients:
            return
        
        msg_str = json.dumps(message)
        disconnected = set()
        
        for client in self.connected_clients:
            try:
                await client.send(msg_str)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        self.connected_clients -= disconnected
    
    async def _handle_client(self, websocket: websockets.WebSocketServerProtocol):
        """Handle a connected Windows client."""
        self.connected_clients.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"Windows client connected: {client_addr}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "")
                    
                    if msg_type == "recognizer_loop:utterance":
                        utterances = data.get("data", {}).get("utterances", [])
                        lang = data.get("data", {}).get("lang", "en-us")
                        
                        if utterances:
                            utterance = utterances[0]
                            logger.info(f"📥 Received from Windows: {utterance}")
                            
                            # Forward to OVOS messagebus
                            self.bus.emit(Message(
                                "recognizer_loop:utterance",
                                {"utterances": utterances, "lang": lang}
                            ))
                    
                    elif msg_type == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                    
                    else:
                        logger.debug(f"Unknown message type: {msg_type}")
                
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message[:100]}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Windows client disconnected: {client_addr}")
        finally:
            self.connected_clients.discard(websocket)
    
    async def run(self):
        """Main run loop."""
        # Store reference to main event loop for thread-safe callbacks
        self._loop = asyncio.get_running_loop()
        
        logger.info("=" * 50)
        logger.info("WSL2 OVOS Bridge Starting")
        logger.info("=" * 50)
        
        # Connect to OVOS messagebus
        self._connect_to_messagebus()
        
        # Start WebSocket server
        self.running = True
        
        # Bind to all interfaces so Windows can connect
        async with websockets.serve(
            self._handle_client,
            "0.0.0.0",
            self.port
        ):
            logger.info(f"🌐 WebSocket server listening on ws://0.0.0.0:{self.port}")
            logger.info("   Windows clients can connect to this bridge")
            logger.info("   Waiting for connections...")
            
            # Keep running
            while self.running:
                await asyncio.sleep(1)
    
    def stop(self):
        """Stop the bridge."""
        self.running = False
        if self.bus:
            self.bus.close()


async def main():
    """Entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="WSL2 OVOS Bridge")
    parser.add_argument("--port", type=int, default=5678, help="WebSocket port")
    args = parser.parse_args()
    
    bridge = WSL2OVOSBridge(port=args.port)
    
    try:
        await bridge.run()
    except KeyboardInterrupt:
        logger.info("Stopping...")
        bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
