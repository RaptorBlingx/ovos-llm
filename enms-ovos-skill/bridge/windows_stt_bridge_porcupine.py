#!/usr/bin/env python3
"""
Windows STT Bridge - Porcupine (wake word) + Whisper (commands)

CRITICAL: Porcupine is purpose-built for wake word detection.
Unlike Vosk, it ignores all audio EXCEPT the specific wake word signatures.

Setup:
1. Get free AccessKey: https://console.picovoice.ai/
2. pip install pvporcupine
3. Paste your key below
"""

import pvporcupine
import whisper
import sounddevice as sd
import numpy as np
import asyncio
import websockets
import json
import logging
from enum import Enum

# -------------------------------------------------------------------------
# 🔑 GET YOUR FREE KEY: https://console.picovoice.ai/
ACCESS_KEY = "PASTE_YOUR_ACCESS_KEY_HERE" 
# -------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(message)s', 
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class ListenerState(Enum):
    WAITING_FOR_WAKE = 1
    LISTENING_FOR_COMMAND = 2


class WindowsSTTBridge:
    def __init__(self, wsl_host: str = "localhost", wsl_port: int = 5678):
        self.wsl_host = wsl_host
        self.wsl_port = wsl_port
        self.ws = None
        self.state = ListenerState.WAITING_FOR_WAKE
        self.command_audio = []
        self.silence_counter = 0
        
        # Load Porcupine (wake word detection)
        try:
            # Built-in keywords: 'alexa', 'american express', 'blueberry', 'bumblebee', 
            # 'computer', 'grapefruit', 'grasshopper', 'hey google', 'hey siri', 
            # 'jarvis', 'ok google', 'picovoice', 'porcupine', 'terminator'
            self.porcupine = pvporcupine.create(
                access_key=ACCESS_KEY, 
                keywords=['jarvis', 'computer']
            )
            logger.info(f"✅ Porcupine loaded - Wake words: Jarvis, Computer")
        except Exception as e:
            logger.error(f"❌ Porcupine Error: {e}")
            logger.error("Did you paste your AccessKey from https://console.picovoice.ai/ ?")
            raise

        # Load Whisper (command transcription)
        logger.info("⏳ Loading Whisper model (small)...")
        self.whisper = whisper.load_model("small")
        logger.info("✅ Whisper loaded")
        
    async def connect_ovos(self):
        """Connect to WSL OVOS bridge."""
        try:
            url = f"ws://{self.wsl_host}:{self.wsl_port}"
            logger.info(f"Connecting to {url}...")
            self.ws = await websockets.connect(url)
            logger.info("✅ Connected to OVOS bridge")
            return True
        except Exception as e:
            logger.error(f"❌ Could not connect to WSL bridge: {e}")
            logger.error("Is wsl_ovos_bridge.py running?")
            return False

    async def send_to_ovos(self, text: str):
        """Send transcribed utterance to OVOS."""
        if self.ws:
            try:
                message = json.dumps({
                    "type": "recognizer_loop:utterance",
                    "data": {"utterances": [text]}
                })
                await self.ws.send(message)
                logger.info(f"📤 Sent to OVOS: '{text}'")
            except Exception as e:
                logger.error(f"Error sending to OVOS: {e}")

    async def listen_for_responses(self):
        """Listen for OVOS responses."""
        while self.ws:
            try:
                message = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                data = json.loads(message)
                
                if data.get("type") == "speak":
                    utterance = data.get("data", {}).get("utterance", "")
                    logger.info(f"🔊 OVOS: {utterance}")
                    
            except asyncio.TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed:
                logger.warning("OVOS bridge connection closed")
                break
            except Exception as e:
                logger.error(f"Error receiving from OVOS: {e}")
                await asyncio.sleep(0.1)

    def audio_callback(self, indata, frames, time_info, status):
        """Audio stream callback - processes every audio chunk."""
        if status:
            logger.warning(f"Audio status: {status}")
            
        # Convert float32 to int16 for Porcupine
        pcm = (indata[:, 0] * 32767).astype(np.int16)
        
        if self.state == ListenerState.WAITING_FOR_WAKE:
            # Porcupine wake word detection
            try:
                keyword_index = self.porcupine.process(pcm)
                if keyword_index >= 0:
                    wake_word = 'Jarvis' if keyword_index == 0 else 'Computer'
                    logger.info(f"🎤 WAKE WORD DETECTED! ({wake_word})")
                    logger.info("👂 Say your command...")
                    
                    self.state = ListenerState.LISTENING_FOR_COMMAND
                    self.command_audio = []
                    self.silence_counter = 0
            except Exception as e:
                logger.debug(f"Porcupine processing error: {e}")
                
        elif self.state == ListenerState.LISTENING_FOR_COMMAND:
            # Record audio for Whisper transcription
            self.command_audio.append(indata[:, 0].copy())
            
            # Simple silence detection (RMS)
            rms = np.sqrt(np.mean(indata[:, 0]**2))
            if rms < 0.01:  # Silence threshold
                self.silence_counter += 1
            else:
                self.silence_counter = 0

    async def run(self):
        """Main run loop."""
        print("\n" + "=" * 60)
        print("  🎤 Windows STT Bridge (Porcupine + Whisper)")
        print("=" * 60 + "\n")
        
        # Connect to OVOS
        if not await self.connect_ovos():
            logger.error("Exiting - cannot connect to OVOS bridge")
            return
            
        # Show audio device info
        default_dev = sd.default.device[0]
        dev_name = sd.query_devices(default_dev)['name'] if default_dev else "Unknown"
        logger.info(f"🎙️ Microphone: {dev_name}")
        logger.info(f"⚡ Silent wake word detection (no false positives)")
        logger.info(f"🎯 Accurate commands with Whisper")
        logger.info("")
        logger.info("💤 Waiting for wake word...\n")
        
        # Start audio stream
        # Porcupine requires 512 samples per frame at 16kHz
        stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype='float32',
            blocksize=self.porcupine.frame_length,
            callback=self.audio_callback
        )
        
        try:
            with stream:
                # Create task for OVOS responses
                response_task = asyncio.create_task(self.listen_for_responses())
                
                while True:
                    await asyncio.sleep(0.1)
                    
                    # Check if silence timeout reached (1.5 seconds)
                    # 16000Hz / 512 samples = 31.25 blocks/sec
                    # 1.5s = ~47 blocks
                    if self.state == ListenerState.LISTENING_FOR_COMMAND and self.silence_counter > 45:
                        if len(self.command_audio) > 0:
                            logger.info("🔇 Silence detected, transcribing...")
                            audio_data = np.concatenate(self.command_audio).astype(np.float32)
                            
                            # Skip if audio is too short (< 0.5s)
                            if len(audio_data) < 8000:
                                logger.info("❌ Audio too short, ignoring")
                            else:
                                try:
                                    result = self.whisper.transcribe(audio_data)
                                    text = result["text"].strip()
                                    
                                    if text:
                                        logger.info(f"📝 Command: '{text}'")
                                        await self.send_to_ovos(text)
                                    else:
                                        logger.info("❌ No command heard")
                                except Exception as e:
                                    logger.error(f"Whisper error: {e}")

                        # Return to wake word listening
                        self.state = ListenerState.WAITING_FOR_WAKE
                        self.command_audio = []
                        self.silence_counter = 0
                        logger.info("💤 Waiting for wake word...")
                        
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
        finally:
            response_task.cancel()
            if self.ws:
                await self.ws.close()
            self.porcupine.delete()


if __name__ == "__main__":
    import sys
    
    # Parse arguments
    host = "localhost"
    port = 5678
    
    if "--host" in sys.argv:
        host = sys.argv[sys.argv.index("--host") + 1]
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    
    bridge = WindowsSTTBridge(wsl_host=host, wsl_port=port)
    asyncio.run(bridge.run())
