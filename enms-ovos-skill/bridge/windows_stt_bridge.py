#!/usr/bin/env python3
"""
Windows STT Bridge - Silero VAD + Vosk + Whisper for optimal performance.

Architecture:
- Silero VAD: Voice activity detection (filters silence/noise) - FREE
- Vosk: Wake word detection (only when VAD detects speech) - FREE
- Whisper: Accurate command transcription (only after wake word) - FREE

Usage:
    python windows_stt_bridge.py [--host localhost] [--port 5678]
"""

import asyncio
import json
import logging
import queue
import sys
import time
from enum import Enum
from pathlib import Path

import numpy as np
import sounddevice as sd
import websockets
import torch
import vosk
from vosk import Model, KaldiRecognizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("STTBridge")

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 512  # 32ms chunks for Silero VAD (matches its requirements)
DTYPE = 'float32'  # Silero VAD needs float32

# VAD settings
VAD_THRESHOLD = 0.5  # Speech probability threshold (0.0-1.0)

# Wake word settings
WAKE_WORDS = ["mycroft", "jarvis", "computer"]

# Timing settings
SILENCE_DURATION = 1.5  # Seconds of silence to end command
COMMAND_MAX_SECONDS = 10.0  # Max seconds for command recording

# Vosk model path
VOSK_MODEL_PATH = Path("D:/vosk-model-en-us-0.22")


class ListenerState(Enum):
    WAITING_FOR_WAKE = "waiting_for_wake"
    LISTENING_FOR_COMMAND = "listening_for_command"


class WindowsSTTBridge:
    """Silero VAD + Vosk (wake word) + Whisper (commands) STT bridge."""
    
    def __init__(self, wsl_host: str = "localhost", wsl_port: int = 5678):
        self.wsl_host = wsl_host
        self.wsl_port = wsl_port
        self.running = False
        self.ws = None
        
        # Silero VAD for voice activity detection
        self.vad_model = None
        
        # Vosk for wake word detection
        self.vosk_model = None
        self.vosk_recognizer = None
        self.audio_queue = queue.Queue()
        
        # Whisper for command transcription
        self.whisper_model = None
        
        # State machine
        self.state = ListenerState.WAITING_FOR_WAKE
        self.command_audio = []
        self.silence_counter = 0  # Count silent frames
        
    def _load_vad_model(self):
        """Load Silero VAD model for voice activity detection."""
        logger.info("Loading Silero VAD model...")
        try:
            self.vad_model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False,
                trust_repo=True
            )
            logger.info("✅ Silero VAD loaded (voice activity detection)")
        except Exception as e:
            logger.error(f"Failed to load Silero VAD: {e}")
            raise
        
    def _load_vosk_model(self):
        """Load Vosk model for wake word detection."""
        if not VOSK_MODEL_PATH.exists():
            logger.error(f"Vosk model not found at {VOSK_MODEL_PATH}")
            logger.error("Download: https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip")
            sys.exit(1)
        
        logger.info(f"Loading Vosk model from {VOSK_MODEL_PATH}")
        self.vosk_model = Model(str(VOSK_MODEL_PATH))
        self.vosk_recognizer = KaldiRecognizer(self.vosk_model, SAMPLE_RATE)
        self.vosk_recognizer.SetWords(True)
        logger.info("✅ Vosk model loaded (wake word detection)")
    
    def _load_whisper_model(self):
        """Load Whisper model for command transcription."""
        try:
            import whisper
            logger.info("Loading Whisper 'small' model for commands...")
            self.whisper_model = whisper.load_model("small")
            logger.info("✅ Whisper model loaded (command transcription)")
        except ImportError:
            logger.error("Whisper not installed! Run: pip install openai-whisper")
            sys.exit(1)
    
    def _audio_callback(self, indata, frames, time_info, status):
        """
        Audio callback - processes every chunk with Silero VAD first.
        Only sends to Vosk if VAD detects speech.
        """
        if status:
            logger.warning(f"Audio: {status}")
        
        # Convert to tensor for VAD (already float32)
        audio_tensor = torch.from_numpy(indata[:, 0].copy())
        
        # Get speech probability from VAD
        speech_prob = self.vad_model(audio_tensor, SAMPLE_RATE).item()
        
        # Only process with Vosk if VAD detects speech
        if speech_prob > VAD_THRESHOLD:
            # Convert to int16 for Vosk
            audio_int16 = (indata[:, 0] * 32767).astype(np.int16)
            self.audio_queue.put(bytes(audio_int16))
        # else: silence/noise - ignore it (this fixes "the the the" issue!)
    
    def _check_wake_word(self, text: str) -> bool:
        """Check if text contains wake word."""
        text_lower = text.lower().strip()
        for wake_word in WAKE_WORDS:
            if wake_word in text_lower:
                logger.info(f"🎯 Wake word detected: '{wake_word}'")
                return True
        return False
    
    def _get_rms(self, audio: np.ndarray) -> float:
        """Calculate RMS of audio."""
        return np.sqrt(np.mean(audio.astype(np.float32) ** 2))
    
    def _transcribe_whisper(self, audio: np.ndarray) -> str:
        """Transcribe audio using Whisper."""
        import whisper
        
        # Convert int16 to float32 normalized [-1, 1]
        audio_float = audio.astype(np.float32) / 32768.0
        
        result = self.whisper_model.transcribe(
            audio_float,
            language="en",
            fp16=False
        )
        return result["text"].strip()
    
    async def _send_to_ovos(self, utterance: str):
        """Send utterance to OVOS."""
        if not self.ws:
            logger.warning("WebSocket not connected")
            return
        
        message = {
            "type": "recognizer_loop:utterance",
            "data": {"utterances": [utterance], "lang": "en-us"}
        }
        
        try:
            await self.ws.send(json.dumps(message))
            logger.info(f"📤 Sent to OVOS: {utterance}")
        except Exception as e:
            logger.error(f"Send failed: {e}")
    
    async def _connect_to_ovos(self):
        """Connect to WSL2 OVOS bridge."""
        uri = f"ws://{self.wsl_host}:{self.wsl_port}"
        logger.info(f"Connecting to {uri}...")
        
        while self.running:
            try:
                self.ws = await websockets.connect(uri)
                logger.info("✅ Connected to OVOS bridge")
                return True
            except Exception as e:
                logger.warning(f"Connection failed. Retry in 3s...")
                await asyncio.sleep(3)
        return False
    
    async def _process_vosk_audio(self):
        """Process audio queue with Vosk for wake word detection."""
        
        while self.running:
            try:
                # Get audio from queue
                try:
                    audio_bytes = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    # No audio - check for silence if we're recording command
                    if self.state == ListenerState.LISTENING_FOR_COMMAND:
                        self.silence_counter += 1
                        
                        # If silent for ~1.5 seconds (15 * 0.1s)
                        if self.silence_counter > 15 and self.command_audio:
                            logger.info("🔇 Silence detected, transcribing...")
                            full_audio = np.concatenate(self.command_audio)
                            text = self._transcribe_whisper(full_audio)
                            
                            if text:
                                logger.info(f"📝 Command: \"{text}\"")
                                await self._send_to_ovos(text)
                            else:
                                logger.info("❌ No command heard")
                            
                            self.state = ListenerState.WAITING_FOR_WAKE
                            self.command_audio = []
                            self.silence_counter = 0
                            logger.info("💤 Waiting for wake word...")
                    
                    await asyncio.sleep(0.01)
                    continue
                
                # Got audio - reset silence counter
                self.silence_counter = 0
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                
                # State machine: Wake word detection OR Command recording
                if self.state == ListenerState.WAITING_FOR_WAKE:
                    # Use Vosk for wake word detection (check both partial and final)
                    if self.vosk_recognizer.AcceptWaveform(audio_bytes):
                        result = json.loads(self.vosk_recognizer.Result())
                        text = result.get("text", "").strip()
                    else:
                        # Check partial results too (more responsive)
                        result = json.loads(self.vosk_recognizer.PartialResult())
                        text = result.get("partial", "").strip()
                    
                    if text:
                        logger.info(f"🔍 Vosk heard: \"{text}\"")
                        
                        if self._check_wake_word(text):
                            # Wake word detected! Switch to command listening
                            self.state = ListenerState.LISTENING_FOR_COMMAND
                            self.command_audio = []
                            self.silence_counter = 0
                            # Reset Vosk to clear partial buffer
                            self.vosk_recognizer = vosk.KaldiRecognizer(self.vosk_model, SAMPLE_RATE)
                            logger.info("👂 Say your command...")
                
                elif self.state == ListenerState.LISTENING_FOR_COMMAND:
                    # Record audio for Whisper transcription
                    self.command_audio.append(audio_data)
                    
                    # Check for timeout
                    if self.command_audio:
                        audio_seconds = sum(len(a) for a in self.command_audio) / SAMPLE_RATE
                        if audio_seconds > COMMAND_MAX_SECONDS:
                            logger.info("⏱️ Command timeout, transcribing...")
                            full_audio = np.concatenate(self.command_audio)
                            text = self._transcribe_whisper(full_audio)
                            
                            if text:
                                logger.info(f"📝 Command: \"{text}\"")
                                await self._send_to_ovos(text)
                            
                            self.state = ListenerState.WAITING_FOR_WAKE
                            self.command_audio = []
                            self.silence_counter = 0
                            logger.info("💤 Waiting for wake word...")
                
            except Exception as e:
                logger.error(f"Error: {e}")
                self.state = ListenerState.WAITING_FOR_WAKE
                await asyncio.sleep(0.1)
    
    async def _listen_for_responses(self):
        """Listen for responses from OVOS."""
        while self.running and self.ws:
            try:
                message = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                data = json.loads(message)
                
                if data.get("type") == "speak":
                    utterance = data.get("data", {}).get("utterance", "")
                    logger.info(f"🔊 OVOS: {utterance}")
                
            except asyncio.TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                if self.running:
                    logger.error(f"Recv error: {e}")
                await asyncio.sleep(0.1)
    
    async def run(self):
        """Main run loop."""
        print("\n" + "=" * 60)
        print("  🎤 Windows STT Bridge (Silero VAD + Vosk + Whisper)")
        print("=" * 60 + "\n")
        
        # Load models
        self._load_vad_model()  # Load VAD first
        self._load_vosk_model()
        self._load_whisper_model()
        
        # Show default mic
        default_dev = sd.default.device[0]
        dev_name = sd.query_devices(default_dev)['name'] if default_dev else "Unknown"
        logger.info(f"🎙️ Microphone: {dev_name}")
        logger.info(f"💬 Wake words: {', '.join(WAKE_WORDS)}")
        logger.info(f"🔇 Silero VAD filters silence/noise")
        logger.info(f"⚡ Vosk detects wake words")
        logger.info(f"🎯 Whisper transcribes commands")
        
        self.running = True
        self.state = ListenerState.WAITING_FOR_WAKE
        
        logger.info("\n💤 Waiting for wake word...\n")
        
        # Connect to OVOS
        if not await self._connect_to_ovos():
            return
        
        # Start audio stream (float32 for Silero VAD)
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK_SIZE,
            callback=self._audio_callback
        )
        
        try:
            with stream:
                await asyncio.gather(
                    self._process_vosk_audio(),
                    self._listen_for_responses()
                )
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            if self.ws:
                await self.ws.close()
            logger.info("Stopped")


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5678)
    args = parser.parse_args()
    
    bridge = WindowsSTTBridge(wsl_host=args.host, wsl_port=args.port)
    await bridge.run()


if __name__ == "__main__":
    asyncio.run(main())
