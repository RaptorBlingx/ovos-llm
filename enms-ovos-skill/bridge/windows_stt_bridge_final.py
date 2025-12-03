#!/usr/bin/env python3
"""
Windows STT Bridge - FINAL SOLUTION

Architecture (FREE, no hallucinations):
- Precise Lite: Wake word detection (trained for "Hey Mycroft") - FREE
- Whisper: Accurate command transcription - FREE
- WebSocket: Send to WSL2 OVOS bridge

This uses the SAME wake word engine as OVOS itself!
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from enum import Enum

import numpy as np
import sounddevice as sd
import websockets
from precise_lite_runner import PreciseLiteListener

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("STTBridge")

# Wake word model
MODEL_URL = "https://github.com/OpenVoiceOS/precise-lite-models/raw/master/wakewords/en/hey_mycroft.tflite"
MODEL_PATH = Path("d:/ovos-llm-core/ovos-llm/enms-ovos-skill/bridge/hey_mycroft.tflite")

# Audio config
SAMPLE_RATE = 16000
CHUNK_SIZE = 2048
COMMAND_MAX_SECONDS = 10.0
SILENCE_THRESHOLD = 0.01  # RMS threshold for silence detection
SILENCE_DURATION = 1.2    # Seconds of silence to trigger end of command
MIN_SPEECH_DURATION = 0.3 # Minimum speech before silence detection kicks in


class ListenerState(Enum):
    WAITING_FOR_WAKE = 1
    LISTENING_FOR_COMMAND = 2


class WindowsSTTBridge:
    """Precise Lite (wake word) + Whisper (commands) STT bridge."""
    
    def __init__(self, wsl_host: str = "localhost", wsl_port: int = 5678):
        self.wsl_host = wsl_host
        self.wsl_port = wsl_port
        self.ws = None
        self.state = ListenerState.WAITING_FOR_WAKE
        self.command_audio = []
        self.command_start_time = None
        self.whisper_model = None
        self.precise_listener = None
        self.recording_stream = None
        
        # VAD (Voice Activity Detection) state
        self.speech_detected = False
        self.silence_start_time = None
        
    def _load_whisper_model(self):
        """Load Whisper model for command transcription."""
        try:
            import whisper
            logger.info("⏳ Loading Whisper 'small' model...")
            self.whisper_model = whisper.load_model("small")
            logger.info("✅ Whisper loaded (command transcription)")
        except ImportError:
            logger.error("Whisper not installed! Run: pip install openai-whisper")
            raise
    
    def _on_wake_word(self):
        """Called when Precise Lite detects wake word."""
        logger.info("🎯 WAKE WORD DETECTED! ('Hey Mycroft')")
        self.state = ListenerState.LISTENING_FOR_COMMAND
        self.command_audio = []
        self.command_start_time = time.time()
        
        # Reset VAD state
        self.speech_detected = False
        self.silence_start_time = None
        
        # Start recording command audio
        self._start_command_recording()
        
        logger.info("👂 Say your command...")
    
    def _start_command_recording(self):
        """Start recording audio for command transcription."""
        if self.recording_stream:
            return  # Already recording
        
        def callback(indata, frames, time_info, status):
            if self.state == ListenerState.LISTENING_FOR_COMMAND:
                audio_chunk = indata[:, 0].copy()
                
                # Store audio for Whisper (float32)
                self.command_audio.append(audio_chunk)
                
                # VAD: Calculate RMS (volume level)
                rms = np.sqrt(np.mean(audio_chunk ** 2))
                
                if rms > SILENCE_THRESHOLD:
                    # Speech detected
                    self.speech_detected = True
                    self.silence_start_time = None
                else:
                    # Silence detected
                    if self.speech_detected and self.silence_start_time is None:
                        self.silence_start_time = time.time()
        
        self.recording_stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            blocksize=CHUNK_SIZE,
            callback=callback
        )
        self.recording_stream.start()
    
    def _stop_command_recording(self):
        """Stop recording command audio."""
        if self.recording_stream:
            self.recording_stream.stop()
            self.recording_stream.close()
            self.recording_stream = None
    
    def _on_prediction(self, prob):
        """Called for each audio chunk with wake word probability."""
        # We don't need to do anything here, Precise handles detection
        pass
    
    def _transcribe_whisper(self, audio: np.ndarray) -> str:
        """Transcribe audio using Whisper."""
        import whisper
        
        # Whisper expects float32 normalized [-1, 1]
        # Audio from sounddevice is already in correct format
        result = self.whisper_model.transcribe(audio, language="en", fp16=False)
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
            logger.info(f"📤 Sent to OVOS: '{utterance}'")
        except Exception as e:
            logger.error(f"Send error: {e}")
    
    async def _connect_to_ovos(self):
        """Connect to WSL2 OVOS bridge."""
        uri = f"ws://{self.wsl_host}:{self.wsl_port}"
        logger.info(f"Connecting to {uri}...")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ws = await websockets.connect(uri)
                logger.info("✅ Connected to OVOS bridge")
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection failed, retry {attempt+1}/{max_retries}...")
                    await asyncio.sleep(3)
                else:
                    logger.error(f"Could not connect: {e}")
                    return False
    
    async def _monitor_command_recording(self):
        """Monitor command recording and trigger transcription via VAD or timeout."""
        while True:
            await asyncio.sleep(0.1)  # Check every 100ms for faster response
            
            if self.state == ListenerState.LISTENING_FOR_COMMAND and self.command_start_time:
                elapsed = time.time() - self.command_start_time
                
                # VAD: Check if user finished speaking (speech detected, then silence)
                if self.speech_detected and self.silence_start_time:
                    silence_duration = time.time() - self.silence_start_time
                    if silence_duration >= SILENCE_DURATION and elapsed >= MIN_SPEECH_DURATION:
                        logger.info(f"🔇 Silence detected ({silence_duration:.1f}s), transcribing...")
                        await self._finish_command()
                        continue
                
                # Timeout fallback (max recording time)
                if elapsed > COMMAND_MAX_SECONDS:
                    logger.info("⏱️ Command timeout, transcribing...")
                    await self._finish_command()
    
    async def _finish_command(self):
        """Transcribe and send command."""
        # Stop recording
        self._stop_command_recording()
        
        if not self.command_audio:
            logger.info("❌ No command audio recorded")
            self.state = ListenerState.WAITING_FOR_WAKE
            self.command_start_time = None
            return
        
        # Concatenate all audio chunks
        full_audio = np.concatenate(self.command_audio)
        
        # Skip if too short (< 0.5s)
        if len(full_audio) < 8000:  # 0.5s at 16kHz
            logger.info("❌ Audio too short, ignoring")
        else:
            try:
                logger.info("🧠 Transcribing...")
                text = self._transcribe_whisper(full_audio)
                
                if text:
                    logger.info(f"📝 Command: '{text}'")
                    await self._send_to_ovos(text)
                else:
                    logger.info("❌ No command heard")
            except Exception as e:
                logger.error(f"Whisper error: {e}")
        
        # Reset to wake word listening
        self.state = ListenerState.WAITING_FOR_WAKE
        self.command_audio = []
        self.command_start_time = None
        self.speech_detected = False
        self.silence_start_time = None
        logger.info("💤 Waiting for wake word...")
    
    async def _listen_for_responses(self):
        """Listen for responses from OVOS."""
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
                logger.error(f"Error receiving: {e}")
                await asyncio.sleep(0.1)
    
    async def run(self):
        """Main run loop."""
        print("\n" + "=" * 60)
        print("  🎤 Windows STT Bridge - FINAL SOLUTION")
        print("  Precise Lite + Whisper (100% FREE)")
        print("=" * 60 + "\n")
        
        # Download model if needed
        if not MODEL_PATH.exists():
            logger.info(f"Downloading wake word model...")
            import urllib.request
            MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            logger.info("✅ Model downloaded")
        
        # Load Whisper
        self._load_whisper_model()
        
        # Connect to OVOS
        if not await self._connect_to_ovos():
            logger.error("Exiting - cannot connect to OVOS bridge")
            return
        
        logger.info("🎙️ Wake word: 'Hey Mycroft'")
        logger.info("🎯 Precise Lite (OVOS wake word engine)")
        logger.info("🧠 Whisper (command transcription)")
        logger.info("\n💤 Waiting for wake word...\n")
        
        # Create Precise Lite listener
        self.precise_listener = PreciseLiteListener(
            str(MODEL_PATH),
            on_activation=self._on_wake_word,
            on_prediction=self._on_prediction,
            chunk_size=2048,
            trigger_level=3,
            sensitivity=0.5
        )
        
        # Start Precise Lite
        self.precise_listener.start()
        
        try:
            # Run monitoring tasks
            await asyncio.gather(
                self._monitor_command_recording(),
                self._listen_for_responses()
            )
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
        finally:
            self.precise_listener.stop()
            if self.ws:
                await self.ws.close()


async def main():
    bridge = WindowsSTTBridge()
    await bridge.run()


if __name__ == "__main__":
    asyncio.run(main())
