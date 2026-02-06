"""
ATHENA Redis Client
Redis connection for caching and real-time pub/sub
"""
import os
import json
import asyncio
from typing import Optional, Any, List, Callable
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


class RedisClient:
    """Async Redis client for caching and pub/sub"""
    
    def __init__(self, url: str = None):
        self.url = url or REDIS_URL
        self.client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self._listeners: dict = {}
    
    async def connect(self):
        """Initialize Redis connection"""
        if self.client is None:
            self.client = redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.pubsub:
            await self.pubsub.close()
        if self.client:
            await self.client.close()
            self.client = None
    
    # ========================================
    # CACHING OPERATIONS
    # ========================================
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        return await self.client.get(key)
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from cache"""
        value = await self.get(key)
        return json.loads(value) if value else None
    
    async def set(self, key: str, value: str, ex: int = None):
        """Set value in cache with optional expiry"""
        await self.client.set(key, value, ex=ex)
    
    async def set_json(self, key: str, value: Any, ex: int = None):
        """Set JSON value in cache"""
        await self.set(key, json.dumps(value), ex=ex)
    
    async def delete(self, key: str):
        """Delete key from cache"""
        await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return await self.client.exists(key) > 0
    
    async def incr(self, key: str) -> int:
        """Increment counter"""
        return await self.client.incr(key)
    
    async def expire(self, key: str, seconds: int):
        """Set key expiry"""
        await self.client.expire(key, seconds)
    
    # ========================================
    # REDIS STREAMS (Event Bus)
    # ========================================
    
    async def stream_add(self, stream: str, data: dict, maxlen: int = 10000) -> str:
        """Add event to stream"""
        return await self.client.xadd(stream, data, maxlen=maxlen)
    
    async def stream_read(self, stream: str, last_id: str = "0", count: int = 100) -> List:
        """Read events from stream"""
        return await self.client.xread({stream: last_id}, count=count, block=1000)
    
    async def stream_range(self, stream: str, start: str = "-", end: str = "+", count: int = 100) -> List:
        """Get range of events from stream"""
        return await self.client.xrange(stream, start, end, count=count)
    
    # ========================================
    # PUB/SUB OPERATIONS
    # ========================================
    
    async def publish(self, channel: str, message: Any):
        """Publish message to channel"""
        if isinstance(message, dict):
            message = json.dumps(message)
        await self.client.publish(channel, message)
    
    async def subscribe(self, channel: str, callback: Callable):
        """Subscribe to channel with callback"""
        if self.pubsub is None:
            self.pubsub = self.client.pubsub()
        
        await self.pubsub.subscribe(channel)
        self._listeners[channel] = callback
    
    async def unsubscribe(self, channel: str):
        """Unsubscribe from channel"""
        if self.pubsub:
            await self.pubsub.unsubscribe(channel)
            self._listeners.pop(channel, None)
    
    async def listen(self):
        """Start listening for pub/sub messages"""
        if self.pubsub:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    if channel in self._listeners:
                        data = message["data"]
                        try:
                            data = json.loads(data)
                        except (json.JSONDecodeError, TypeError):
                            pass
                        await self._listeners[channel](data)
    
    # ========================================
    # REAL-TIME STATE
    # ========================================
    
    async def set_state(self, key: str, state: dict):
        """Set real-time state (JSON)"""
        await self.set_json(f"state:{key}", state)
        await self.publish(f"state_update:{key}", state)
    
    async def get_state(self, key: str) -> Optional[dict]:
        """Get real-time state"""
        return await self.get_json(f"state:{key}")


# Global Redis instance
_redis: Optional[RedisClient] = None


async def get_redis() -> RedisClient:
    """Get or create Redis instance"""
    global _redis
    if _redis is None:
        _redis = RedisClient()
        await _redis.connect()
    return _redis


async def init_redis():
    """Initialize Redis on startup"""
    return await get_redis()


async def close_redis():
    """Close Redis on shutdown"""
    global _redis
    if _redis:
        await _redis.disconnect()
        _redis = None
