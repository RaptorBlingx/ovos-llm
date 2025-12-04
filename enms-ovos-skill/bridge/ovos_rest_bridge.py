#!/usr/bin/env python3
"""
OVOS REST Bridge for EnMS Integration (v2.0 - Audio Streaming)
===============================================================
Runs on WSL2 alongside OVOS services (Terminal 6)
Exposes HTTP REST API for EnMS frontend to query OVOS

Features:
- Text query → Text response (original)
- Text query → Text + Audio response (NEW)
- TTS via Mimic3 (consistent OVOS voice)

Usage:
    source ~/ovos-env/bin/activate
    python /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/bridge/ovos_rest_bridge.py

EnMS calls:
    POST http://<windows-ip>:5000/query          # Text only
    POST http://<windows-ip>:5000/query/voice    # Text + Audio
"""
import asyncio
import uuid
import logging
import os
import subprocess
import base64
import shutil
from typing import Optional, Dict
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import uvicorn

# OVOS bus client
from ovos_bus_client import MessageBusClient, Message

# ============================================================================
# Configuration
# ============================================================================

MESSAGEBUS_HOST = os.getenv("OVOS_MESSAGEBUS_HOST", "localhost")
MESSAGEBUS_PORT = int(os.getenv("OVOS_MESSAGEBUS_PORT", "8181"))
BRIDGE_PORT = int(os.getenv("OVOS_BRIDGE_PORT", "5000"))
QUERY_TIMEOUT = float(os.getenv("OVOS_QUERY_TIMEOUT", "90.0"))

# TTS Configuration
# Options: "edge-tts" (fast, cloud), "mimic3" (local, slower), "piper" (local, fast), "espeak" (fallback)
TTS_ENGINE = os.getenv("OVOS_TTS_ENGINE", "edge-tts")  # edge-tts is fastest
TTS_VOICE = os.getenv("OVOS_TTS_VOICE", "en-US-GuyNeural")  # Edge-TTS voice
TTS_ENABLED = os.getenv("OVOS_TTS_ENABLED", "true").lower() == "true"

# ============================================================================
# Logging
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OVOS-REST-Bridge")

# ============================================================================
# Request/Response Models
# ============================================================================

class QueryRequest(BaseModel):
    utterance: str
    session_id: Optional[str] = None
    include_audio: bool = False  # NEW: Request audio in response

class QueryResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    session_id: str
    latency_ms: int
    timestamp: str

class VoiceQueryResponse(BaseModel):
    """Response with audio data and optional PDF for report downloads"""
    success: bool
    response: Optional[str] = None
    audio_base64: Optional[str] = None  # Base64 encoded WAV audio
    audio_format: str = "wav"
    pdf_base64: Optional[str] = None  # Base64 encoded PDF for report downloads
    pdf_filename: Optional[str] = None  # Suggested filename for PDF download
    error: Optional[str] = None
    session_id: str
    latency_ms: int
    tts_latency_ms: int = 0
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    ovos_connected: bool
    tts_available: bool
    tts_engine: str
    messagebus_host: str
    messagebus_port: int
    pending_queries: int

# ============================================================================
# TTS Engine - Text to Speech
# ============================================================================

class TTSEngine:
    """Generate TTS audio using Edge-TTS (fastest), Mimic3, Piper, or espeak"""
    
    def __init__(self):
        self.engine = TTS_ENGINE
        self.voice = TTS_VOICE
        self.available = self._check_availability()
        
        if self.available:
            logger.info(f"✅ TTS engine available: {self.engine} (voice: {self.voice})")
        else:
            logger.warning(f"⚠️ TTS engine not available: {self.engine}")
    
    def _check_availability(self) -> bool:
        """Check if TTS engine is installed"""
        if self.engine == "edge-tts":
            return shutil.which("edge-tts") is not None
        elif self.engine == "mimic3":
            return shutil.which("mimic3") is not None
        elif self.engine == "piper":
            return shutil.which("piper") is not None
        elif self.engine == "espeak":
            return shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None
        return False
    
    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Convert text to WAV audio bytes.
        
        Returns:
            WAV audio bytes or None if TTS fails
        """
        if not self.available:
            logger.error("TTS engine not available")
            return None
        
        if not text or not text.strip():
            logger.warning("Empty text for TTS")
            return None
        
        try:
            if self.engine == "edge-tts":
                return self._synthesize_edge_tts(text)
            elif self.engine == "mimic3":
                return self._synthesize_mimic3(text)
            elif self.engine == "piper":
                return self._synthesize_piper(text)
            elif self.engine == "espeak":
                return self._synthesize_espeak(text)
            else:
                logger.error(f"Unknown TTS engine: {self.engine}")
                return None
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return None
    
    def _synthesize_edge_tts(self, text: str) -> Optional[bytes]:
        """Generate audio using Edge-TTS (Microsoft cloud, fast)"""
        import tempfile
        
        # Edge-TTS outputs MP3, we need to convert to WAV for browser compatibility
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as mp3_file:
            mp3_path = mp3_file.name
        
        try:
            # Generate MP3
            result = subprocess.run(
                ["edge-tts", "--voice", self.voice, "--text", text, "--write-media", mp3_path],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Edge-TTS error: {result.stderr.decode()}")
                return None
            
            # Convert MP3 to WAV using ffmpeg (if available) or return MP3
            if shutil.which("ffmpeg"):
                wav_result = subprocess.run(
                    ["ffmpeg", "-y", "-i", mp3_path, "-ar", "22050", "-ac", "1", "-f", "wav", "-"],
                    capture_output=True,
                    timeout=10
                )
                if wav_result.returncode == 0:
                    return wav_result.stdout
            
            # Fallback: return MP3 (browser can play it)
            with open(mp3_path, 'rb') as f:
                return f.read()
        finally:
            # Cleanup temp file
            try:
                os.unlink(mp3_path)
            except:
                pass
    
    def _synthesize_mimic3(self, text: str) -> Optional[bytes]:
        """Generate audio using Mimic3"""
        # Mimic3 outputs WAV to stdout with --stdout flag
        result = subprocess.run(
            ["mimic3", "--voice", self.voice, "--stdout", text],
            capture_output=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"Mimic3 error: {result.stderr.decode()}")
            return None
        
        return result.stdout
    
    def _synthesize_piper(self, text: str) -> Optional[bytes]:
        """Generate audio using Piper"""
        # Piper reads from stdin and outputs WAV to stdout
        result = subprocess.run(
            ["piper", "--model", self.voice, "--output-raw"],
            input=text.encode(),
            capture_output=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"Piper error: {result.stderr.decode()}")
            return None
        
        return result.stdout
    
    def _synthesize_espeak(self, text: str) -> Optional[bytes]:
        """Generate audio using espeak-ng (fallback)"""
        # espeak-ng outputs WAV with --stdout
        espeak_cmd = "espeak-ng" if shutil.which("espeak-ng") else "espeak"
        result = subprocess.run(
            [espeak_cmd, "--stdout", "-v", "en", text],
            capture_output=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"espeak error: {result.stderr.decode()}")
            return None
        
        return result.stdout

# Global TTS engine instance
tts_engine = None

# ============================================================================
# OVOS Bridge
# ============================================================================

class OVOSBridge:
    """Bridge between HTTP REST and OVOS messagebus"""
    
    def __init__(self, messagebus_host: str = "localhost", messagebus_port: int = 8181):
        self.messagebus_host = messagebus_host
        self.messagebus_port = messagebus_port
        self.bus = None
        self.pending_responses: Dict[str, Dict] = {}
        self.connected = False
        
    def connect(self):
        """Connect to OVOS messagebus"""
        logger.info(f"Connecting to OVOS messagebus at {self.messagebus_host}:{self.messagebus_port}")
        
        try:
            self.bus = MessageBusClient(
                host=self.messagebus_host,
                port=self.messagebus_port
            )
            self.bus.run_in_thread()
            
            # Wait for connection
            import time
            for i in range(10):
                if self.bus.started_running:
                    break
                time.sleep(0.5)
                logger.info(f"Waiting for messagebus connection... ({i+1}/10)")
            
            if not self.bus.started_running:
                raise ConnectionError("Failed to connect to OVOS messagebus after 5 seconds")
            
            # Subscribe to responses
            self.bus.on("speak", self._handle_speak)
            self.bus.on("enms.report.generated", self._handle_report_generated)
            
            self.connected = True
            logger.info("✅ Connected to OVOS messagebus")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to messagebus: {e}")
            raise
    
    def _handle_speak(self, message: Message):
        """Handle speak events from skills"""
        session_id = message.context.get("session_id") if message.context else None
        utterance = message.data.get("utterance", "")
        
        logger.debug(f"Received speak event - session: {session_id}, text: {utterance[:50]}...")
        
        if session_id and session_id in self.pending_responses:
            logger.info(f"📥 Response matched for session {session_id[:8]}...")
            self.pending_responses[session_id]["response"] = utterance
            self.pending_responses[session_id]["event"].set()
    
    def _handle_report_generated(self, message: Message):
        """Handle PDF report generated events from EnMS skill"""
        session_id = message.context.get("session_id") if message.context else None
        pdf_base64 = message.data.get("pdf_base64", "")
        filename = message.data.get("filename", "report.pdf")
        
        logger.info(f"📄 Report PDF received - session: {session_id[:8] if session_id else 'None'}..., filename: {filename}")
        
        if session_id and session_id in self.pending_responses:
            # Store PDF data alongside text response (speak event may already have set response)
            self.pending_responses[session_id]["pdf_base64"] = pdf_base64
            self.pending_responses[session_id]["pdf_filename"] = filename
            logger.info(f"📎 PDF attached to session {session_id[:8]}...")
    
    async def query(self, utterance: str, session_id: Optional[str] = None, timeout: float = 90.0) -> Dict:
        """Send query to OVOS and wait for response"""
        if not self.connected:
            return {"success": False, "error": "Not connected to messagebus"}
        
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        logger.info(f"📤 Query: '{utterance}' (session: {session_id[:8]}...)")
        
        # Create async event to wait for response
        event = asyncio.Event()
        self.pending_responses[session_id] = {
            "response": None,
            "pdf_base64": None,
            "pdf_filename": None,
            "event": event
        }
        
        # Send to OVOS
        try:
            self.bus.emit(Message(
                "recognizer_loop:utterance",
                {"utterances": [utterance], "lang": "en-us"},
                {"session_id": session_id}
            ))
        except Exception as e:
            del self.pending_responses[session_id]
            return {"success": False, "error": f"Failed to send message: {e}"}
        
        # Wait for response
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            response_data = self.pending_responses[session_id]
            response = response_data["response"]
            logger.info(f"✅ Response received: '{response[:50]}...'")
            
            # For report queries, wait briefly for PDF event to arrive
            # (PDF event fires shortly after speak event)
            if 'report' in utterance.lower() or 'pdf' in utterance.lower():
                await asyncio.sleep(0.5)  # Allow PDF event to be processed
            
            result = {"success": True, "response": response}
            
            # Include PDF data if present (for report generation)
            if response_data.get("pdf_base64"):
                result["pdf_base64"] = response_data["pdf_base64"]
                result["pdf_filename"] = response_data.get("pdf_filename", "report.pdf")
                logger.info(f"📎 Including PDF in response: {result['pdf_filename']}")
            
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Timeout after {timeout}s (session: {session_id[:8]}...)")
            return {"success": False, "error": f"Timeout after {timeout} seconds"}
            
        finally:
            # Cleanup
            if session_id in self.pending_responses:
                del self.pending_responses[session_id]
    
    def health_check(self) -> Dict:
        """Check connection health"""
        return {
            "ovos_connected": self.connected and (self.bus.started_running if self.bus else False),
            "messagebus_host": self.messagebus_host,
            "messagebus_port": self.messagebus_port,
            "pending_queries": len(self.pending_responses),
            "tts_available": tts_engine.available if tts_engine else False,
            "tts_engine": TTS_ENGINE
        }

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="OVOS REST Bridge",
    description="HTTP REST API wrapper for OVOS messagebus - EnMS Integration",
    version="1.0.0"
)

# CORS - Allow EnMS server to call this bridge
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to EnMS server IP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global bridge instance
bridge = OVOSBridge(messagebus_host=MESSAGEBUS_HOST, messagebus_port=MESSAGEBUS_PORT)

@app.on_event("startup")
async def startup():
    """Connect to OVOS and initialize TTS on startup"""
    global tts_engine
    
    # Initialize TTS engine
    if TTS_ENABLED:
        tts_engine = TTSEngine()
    else:
        logger.info("TTS disabled via OVOS_TTS_ENABLED=false")
    
    # Connect to OVOS messagebus
    try:
        bridge.connect()
    except Exception as e:
        logger.error(f"Failed to connect to OVOS: {e}")
        logger.error("Make sure OVOS messagebus is running (Terminal 1)")

@app.post("/query", response_model=QueryResponse)
async def query_ovos(request: QueryRequest):
    """
    Send text query to OVOS and return natural language response.
    
    Example:
        POST /query
        {"utterance": "factory overview"}
        
    Response:
        {
            "success": true,
            "response": "The factory consumed 2,500 kilowatt hours today...",
            "session_id": "abc123",
            "latency_ms": 180
        }
    """
    start_time = datetime.now()
    
    result = await bridge.query(
        utterance=request.utterance,
        session_id=request.session_id,
        timeout=QUERY_TIMEOUT
    )
    
    latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    session_id = request.session_id or "auto-generated"
    
    if not result["success"]:
        return QueryResponse(
            success=False,
            response=None,
            error=result.get("error", "Unknown error"),
            session_id=session_id,
            latency_ms=latency_ms,
            timestamp=datetime.now().isoformat()
        )
    
    return QueryResponse(
        success=True,
        response=result["response"],
        error=None,
        session_id=session_id,
        latency_ms=latency_ms,
        timestamp=datetime.now().isoformat()
    )

@app.post("/query/voice", response_model=VoiceQueryResponse)
async def query_ovos_with_voice(request: QueryRequest):
    """
    Send text query to OVOS and return response WITH audio.
    
    Example:
        POST /query/voice
        {"utterance": "factory overview"}
        
    Response:
        {
            "success": true,
            "response": "The factory consumed 2,500 kilowatt hours today...",
            "audio_base64": "UklGRi4AAABXQVZFZm10IBAAAA...",
            "audio_format": "wav",
            "session_id": "abc123",
            "latency_ms": 180,
            "tts_latency_ms": 450
        }
    
    Browser usage:
        const audio = new Audio("data:audio/wav;base64," + response.audio_base64);
        audio.play();
    """
    start_time = datetime.now()
    
    # Get text response from OVOS
    result = await bridge.query(
        utterance=request.utterance,
        session_id=request.session_id,
        timeout=QUERY_TIMEOUT
    )
    
    query_latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    session_id = request.session_id or "auto-generated"
    
    if not result["success"]:
        return VoiceQueryResponse(
            success=False,
            response=None,
            audio_base64=None,
            error=result.get("error", "Unknown error"),
            session_id=session_id,
            latency_ms=query_latency_ms,
            tts_latency_ms=0,
            timestamp=datetime.now().isoformat()
        )
    
    response_text = result["response"]
    
    # Generate TTS audio
    audio_base64 = None
    tts_latency_ms = 0
    audio_format = "wav"  # Default, may change to mp3 for edge-tts
    
    if tts_engine and tts_engine.available:
        tts_start = datetime.now()
        audio_bytes = tts_engine.synthesize(response_text)
        tts_latency_ms = int((datetime.now() - tts_start).total_seconds() * 1000)
        
        if audio_bytes:
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            # Detect format from magic bytes
            if audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb':
                audio_format = "mp3"
            logger.info(f"🔊 TTS generated: {len(audio_bytes)} bytes ({audio_format}) in {tts_latency_ms}ms")
        else:
            logger.warning("TTS synthesis returned no audio")
    else:
        logger.warning("TTS not available, returning text only")
    
    total_latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    
    return VoiceQueryResponse(
        success=True,
        response=response_text,
        audio_base64=audio_base64,
        audio_format=audio_format,
        pdf_base64=result.get("pdf_base64"),
        pdf_filename=result.get("pdf_filename"),
        error=None,
        session_id=session_id,
        latency_ms=total_latency_ms,
        tts_latency_ms=tts_latency_ms,
        timestamp=datetime.now().isoformat()
    )

@app.get("/tts/test")
async def test_tts():
    """
    Test TTS functionality with a sample phrase.
    Returns audio directly for browser playback testing.
    """
    if not tts_engine or not tts_engine.available:
        raise HTTPException(503, "TTS engine not available")
    
    test_text = "Hello, I am your energy management assistant. How can I help you today?"
    audio_bytes = tts_engine.synthesize(test_text)
    
    if not audio_bytes:
        raise HTTPException(500, "TTS synthesis failed")
    
    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"Content-Disposition": "inline; filename=tts_test.wav"}
    )

@app.get("/health", response_model=HealthResponse)
async def health():
    """
    Health check endpoint.
    
    Returns:
        - status: "ok" or "degraded"
        - ovos_connected: messagebus connection status
    """
    health_data = bridge.health_check()
    
    return HealthResponse(
        status="ok" if health_data["ovos_connected"] else "degraded",
        **health_data
    )

@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "service": "OVOS REST Bridge",
        "version": "2.0.0",
        "endpoints": {
            "POST /query": "Send query to OVOS (text response)",
            "POST /query/voice": "Send query to OVOS (text + audio response)",
            "GET /tts/test": "Test TTS (returns WAV audio)",
            "GET /health": "Health check"
        },
        "tts_available": tts_engine.available if tts_engine else False,
        "status": "ok" if bridge.connected else "not connected"
    }

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("OVOS REST Bridge for EnMS Integration")
    logger.info("=" * 60)
    logger.info(f"Messagebus: {MESSAGEBUS_HOST}:{MESSAGEBUS_PORT}")
    logger.info(f"Bridge Port: {BRIDGE_PORT}")
    logger.info(f"Query Timeout: {QUERY_TIMEOUT}s")
    logger.info("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",  # Listen on all interfaces
        port=BRIDGE_PORT,
        log_level="info"
    )
