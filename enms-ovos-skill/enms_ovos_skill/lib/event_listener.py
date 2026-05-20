"""
EnMS Event Listener - Minimal Working Version
Subscribes to Redis pub/sub for proactive warnings.
"""
import asyncio
import json
import logging
import os
from typing import Callable, Optional
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class EnMSEventListener:
    """Listens to EnMS Redis events and triggers OVOS notifications."""
    
    def __init__(self, callback: Callable):
        """
        Initialize listener.
        
        Args:
            callback: Function to call when event received (event_type, data)
        """
        self.callback = callback
        self.redis_host = os.getenv("REDIS_HOST", "redis")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_password = os.getenv("REDIS_PASSWORD")
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        self.redis: Optional[Redis] = None
        self.pubsub = None
        self.running = False
        
        # Channels to subscribe
        self.channels = [
            "anomaly.detected",
            "system.alert",
            "training.completed",
            "metric.updated"
        ]
    
    async def start_and_listen(self):
        """Connect, subscribe, and listen (blocking)."""
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                # Connect
                self.redis = Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    password=self.redis_password,
                    db=self.redis_db,
                    decode_responses=True,
                    socket_connect_timeout=30,
                    socket_timeout=30
                )
                
                await self.redis.ping()
                logger.info(f"EnMS Event Listener: Connected to Redis at {self.redis_host}:{self.redis_port}")
                break
            
            except Exception as e:
                retry_count += 1
                logger.warning(f"Redis connection attempt {retry_count}/{max_retries} failed: {e}")
                if retry_count >= max_retries:
                    raise
                await asyncio.sleep(5)
        
        try:
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(*self.channels)
            logger.info(f"EnMS Event Listener: Subscribed to {len(self.channels)} channels")
            
            self.running = True
            
            # Listen loop (blocking)
            async for message in self.pubsub.listen():
                if not self.running:
                    break
                
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        event_type = data.get('event_type', message['channel'])
                        logger.info(f"EnMS Event Listener: Received {event_type}")
                        
                        # Call callback (non-blocking)
                        if self.callback:
                            try:
                                self.callback(event_type, data)
                            except Exception as e:
                                logger.error(f"Callback error: {e}")
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse event: {e}")
                    except Exception as e:
                        logger.error(f"Error processing event: {e}")
        
        except Exception as e:
            logger.error(f"EnMS Event Listener failed: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """Stop listening."""
        self.running = False
        if self.pubsub:
            await self.pubsub.unsubscribe(*self.channels)
            await self.pubsub.close()
        if self.redis:
            await self.redis.aclose()
        logger.info("EnMS Event Listener stopped")
    
    async def start_and_listen_background(self):
        """Start listening in background (non-blocking)."""
        # Connect with retries
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                self.redis = Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    password=self.redis_password,
                    db=self.redis_db,
                    decode_responses=True,
                    socket_connect_timeout=10,
                    socket_timeout=10
                )
                
                await self.redis.ping()
                logger.info(f"EnMS Event Listener: Connected to Redis")
                break
            
            except Exception as e:
                retry_count += 1
                logger.warning(f"Redis connection attempt {retry_count}/{max_retries} failed: {e}")
                if retry_count >= max_retries:
                    logger.error("Failed to connect to Redis after retries")
                    return
                await asyncio.sleep(5)
        
        try:
            # Create pubsub and subscribe
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(*self.channels)
            logger.info(f"EnMS Event Listener: Subscribed to {len(self.channels)} channels")
            
            self.running = True
            
            # Create background task
            asyncio.create_task(self._listen_loop())
            logger.info("EnMS Event Listener: Background task created")
        
        except Exception as e:
            logger.error(f"Failed to start listener: {e}")
    
    async def _listen_loop(self):
        """Background listening loop."""
        try:
            async for message in self.pubsub.listen():
                if not self.running:
                    break
                
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        event_type = data.get('event_type', message['channel'])
                        logger.info(f"EnMS Event: {event_type}")
                        
                        if self.callback:
                            try:
                                self.callback(event_type, data)
                            except Exception as e:
                                logger.error(f"Callback error: {e}")
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse event: {e}")
                    except Exception as e:
                        logger.error(f"Error processing event: {e}")
        
        except Exception as e:
            logger.error(f"Listen loop failed: {e}")
            self.running = False
