#!/usr/bin/env python3
"""
OVOS REST Bridge - Messagebus Gateway
======================================
Provides REST API interface that forwards queries to OVOS messagebus.
This is the CORRECT architecture - Portal → REST API → Messagebus → EnmsSkill

Unlike the old bridge, this does NOT implement skill logic.
It's a thin proxy that lets the portal communicate with OVOS.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message
from ovos_utils.log import LOG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic models
class QueryRequest(BaseModel):
    text: str = Field(..., description="User query text")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    user_id: Optional[str] = Field(None, description="User ID")
    
class QueryResponse(BaseModel):
    success: bool
    response: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    data: Optional[Dict[str, Any]] = None
    pdf_download: Optional[Dict[str, Any]] = None  # NEW: PDF download info
    timestamp: str
    session_id: str

class HealthResponse(BaseModel):
    status: str
    messagebus_connected: bool
    timestamp: str


class OVOSRestBridge:
    """REST API bridge to OVOS messagebus"""
    
    def __init__(self):
        self.bus: Optional[MessageBusClient] = None
        self.responses: Dict[str, Dict[str, Any]] = {}
        self.pdf_downloads: Dict[str, Dict[str, Any]] = {}  # NEW: Track PDF downloads
        self.response_timeout = 90  # seconds (increased for ML baseline operations)
        
    def connect_to_messagebus(self):
        """Connect to OVOS messagebus"""
        try:
            self.bus = MessageBusClient()
            
            # Register handlers for responses from skills
            self.bus.on('speak', self._handle_speak)
            self.bus.on('enms.skill.response', self._handle_skill_response)
            self.bus.on('enms.pdf.download', self._handle_pdf_download)  # NEW: PDF downloads
            
            # Start messagebus client in background thread
            self.bus.run_in_thread()
            logger.info("✅ Connected to OVOS messagebus")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to messagebus: {e}")
            raise
    
    def _handle_speak(self, message: Message):
        """Handle speak messages from skills"""
        session_id = message.context.get('session_id', 'default')
        utterance = message.data.get('utterance', '')
        
        if session_id in self.responses:
            # Append responses (skill speaks twice for reports: initial + confirmation)
            if self.responses[session_id]['response']:
                self.responses[session_id]['response'] += f" {utterance}"
            else:
                self.responses[session_id]['response'] = utterance
            self.responses[session_id]['received'] = True
            logger.debug(f"Received speak for session {session_id}: {utterance[:50]}...")
    
    def _handle_skill_response(self, message: Message):
        """Handle structured responses from EnmsSkill"""
        session_id = message.context.get('session_id', 'default')
        
        if session_id in self.responses:
            self.responses[session_id].update({
                'intent': message.data.get('intent'),
                'confidence': message.data.get('confidence'),
                'data': message.data.get('data'),
                'received': True
            })
            logger.debug(f"Received skill response for session {session_id}")
    
    def _handle_pdf_download(self, message: Message):
        """
        Handle PDF download events from EnmsSkill
        
        Captures report_id, download_url, filename for browser download
        """
        session_id = message.context.get('session_id', 'default')
        
        pdf_data = {
            'report_id': message.data.get('report_id'),
            'download_url': message.data.get('download_url'),
            'filename': message.data.get('filename'),
            'file_size_kb': message.data.get('file_size_kb'),
            'ready': True
        }
        
        self.pdf_downloads[session_id] = pdf_data
        logger.info(f"📄 PDF download ready for session {session_id}: {pdf_data.get('filename')} ({pdf_data.get('file_size_kb')} KB)")
    
    async def process_query(self, text: str, session_id: str, user_id: Optional[str] = None) -> QueryResponse:
        """
        Send query to OVOS messagebus and wait for response
        """
        if not self.bus or not self.bus.connected_event.is_set():
            raise HTTPException(status_code=503, detail="Messagebus not connected")
        
        # Clean text: strip trailing punctuation that breaks Adapt matching
        # Question marks, periods, exclamation marks can prevent intent matching
        cleaned_text = text.rstrip('?!.,;:')
        if cleaned_text != text:
            logger.info(f"🧹 Stripped punctuation: '{text}' → '{cleaned_text}'")
        
        # Initialize response tracker
        self.responses[session_id] = {
            'response': '',
            'intent': None,
            'confidence': None,
            'data': None,
            'received': False
        }
        self.pdf_downloads[session_id] = {'ready': False}  # NEW: Initialize PDF tracker
        
        try:
            # Send utterance to OVOS messagebus
            context = {
                'session_id': session_id,
                'user_id': user_id or 'anonymous',
                'source': 'rest_bridge'
            }
            
            message = Message(
                'recognizer_loop:utterance',
                data={'utterances': [cleaned_text]},
                context=context
            )
            
            self.bus.emit(message)
            logger.info(f"📤 Sent query to messagebus: '{cleaned_text}' (session: {session_id})")
            
            # Detect if this is a report generation query (needs longer wait for PDF)
            is_report_query = any(kw in cleaned_text.lower() for kw in ['report', 'generate', 'create'])
            min_wait_time = 15.0 if is_report_query else 5.0  # Reports need at least 15s
            logger.info(f"⏱️ Query type: {'REPORT' if is_report_query else 'NORMAL'}, min_wait={min_wait_time}s")
            print(f"🐛 DEBUG: is_report_query={is_report_query}, min_wait={min_wait_time}s", flush=True)
            
            # Wait for response with timeout
            start_time = asyncio.get_event_loop().time()
            last_check_time = start_time
            
            while asyncio.get_event_loop().time() - start_time < self.response_timeout:
                current_time = asyncio.get_event_loop().time()
                
                # Check every second if we have response AND if we should continue waiting
                if current_time - last_check_time > 1.0:
                    if self.responses[session_id]['received']:
                        # Got at least one speak message
                        response_text = self.responses[session_id]['response'].lower()
                        
                        # Check for completion conditions:
                        # 1. PDF download event arrived
                        if self.pdf_downloads.get(session_id, {}).get('ready'):
                            logger.info(f"✅ PDF event received for session {session_id}")
                            break
                        
                        # 2. Response contains final confirmation keywords
                        if any(keyword in response_text for keyword in ['downloaded', 'check your downloads', 'ready and']):
                            logger.info(f"✅ Final confirmation detected in response")
                            await asyncio.sleep(0.5)  # Small delay to ensure PDF event arrives
                            break
                        
                        # 3. Wait minimum time before giving up (longer for reports)
                        elapsed = current_time - start_time
                        if elapsed > min_wait_time:
                            logger.info(f"⏱️ Timeout after {elapsed:.1f}s (min_wait={min_wait_time}s), returning response")
                            break
                    
                    last_check_time = current_time
                        
                await asyncio.sleep(0.1)
            
            # Check if we got a response
            response_data = self.responses[session_id]
            if not response_data['received']:
                logger.warning(f"⏱️ Timeout waiting for response (session: {session_id})")
                return QueryResponse(
                    success=False,
                    response="Sorry, I didn't receive a response in time. Please try again.",
                    timestamp=datetime.utcnow().isoformat(),
                    session_id=session_id
                )
            
            # Check for PDF download (NEW)
            pdf_data = None
            if self.pdf_downloads.get(session_id, {}).get('ready'):
                pdf_data = self.pdf_downloads[session_id]
                logger.info(f"📄 Including PDF download data in response: {pdf_data.get('filename')}")
            
            # Clean up
            del self.responses[session_id]
            if session_id in self.pdf_downloads:
                del self.pdf_downloads[session_id]
            
            return QueryResponse(
                success=True,
                response=response_data['response'] or "I received your request but have no response.",
                intent=response_data.get('intent'),
                confidence=response_data.get('confidence'),
                data=response_data.get('data'),
                pdf_download=pdf_data,  # NEW: Include PDF download info
                timestamp=datetime.utcnow().isoformat(),
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing query: {e}")
            if session_id in self.responses:
                del self.responses[session_id]
            raise HTTPException(status_code=500, detail=str(e))
    
    def is_connected(self) -> bool:
        """Check if messagebus is connected"""
        return self.bus is not None and self.bus.connected_event.is_set()


# Global bridge instance
bridge = OVOSRestBridge()


# FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting OVOS REST Bridge...")
    bridge.connect_to_messagebus()
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down OVOS REST Bridge...")
    if bridge.bus:
        bridge.bus.close()


app = FastAPI(
    title="OVOS EnMS REST Bridge",
    description="REST API gateway to OVOS messagebus for Energy Management System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if bridge.is_connected() else "unhealthy",
        messagebus_connected=bridge.is_connected(),
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/query", response_model=QueryResponse)
@app.post("/query/voice", response_model=QueryResponse)  # Alias for audio requests
async def process_query(request: QueryRequest):
    """
    Process a natural language query through OVOS
    
    The query is sent to the OVOS messagebus, where the EnmsSkill
    will handle it and respond with energy management data.
    
    NOTE: /query/voice is an alias for /query (analytics expects this for audio)
    """
    # Generate session ID if not provided
    session_id = request.session_id or f"session_{datetime.utcnow().timestamp()}"
    
    logger.info(f"📥 Received query: '{request.text}' (session: {session_id})")
    
    try:
        response = await bridge.process_query(
            text=request.text,
            session_id=session_id,
            user_id=request.user_id
        )
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "OVOS EnMS REST Bridge",
        "version": "1.0.0",
        "description": "REST API gateway to OVOS messagebus",
        "messagebus_connected": bridge.is_connected(),
        "endpoints": {
            "health": "/health",
            "query": "/query (POST)",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import os
    
    port = int(os.getenv("OVOS_BRIDGE_PORT", "5000"))
    log_level = os.getenv("LOG_LEVEL", "INFO").lower()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level=log_level
    )
