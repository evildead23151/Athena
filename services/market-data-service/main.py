"""
ATHENA Market Data Service
Port: 7002
Handles live market feeds, price snapshots, and latency monitoring
Includes WebSocket channel: market_ticks
"""
import os
import sys
import asyncio
import random
from datetime import datetime
from typing import List, Dict, Set
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from common.database import Database, get_db, init_db, close_db
from common.redis_client import RedisClient, get_redis, init_redis, close_redis
from common.auth import verify_token, get_current_user, UserContext
from common.logging import get_logger
from common.models import MarketTick, MarketStatusResponse, LatencyResponse, MarketStatus

app = FastAPI(
    title="ATHENA Market Data Service",
    description="Real-time market data feeds and monitoring",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = get_logger("market-data-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "7002"))

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.add(connection)
        for conn in disconnected:
            self.active_connections.discard(conn)

manager = ConnectionManager()

# Simulated market data
SYMBOLS = ["AAPL", "GOOGL", "MSFT", "TSLA", "SPY", "VIX", "BTC-USD", "ETH-USD"]
BASE_PRICES = {
    "AAPL": 185.50,
    "GOOGL": 141.80,
    "MSFT": 402.30,
    "TSLA": 248.90,
    "SPY": 495.20,
    "VIX": 14.50,
    "BTC-USD": 62500.00,
    "ETH-USD": 3450.00
}

# Feed status
FEEDS = {
    "BLOOMBERG_L1": {"status": "CONNECTED", "latency_ms": 12, "message_count": 0},
    "REFINITIV": {"status": "CONNECTED", "latency_ms": 8, "message_count": 0},
    "BINANCE_WS": {"status": "CONNECTED", "latency_ms": 45, "message_count": 0}
}

market_task = None

async def generate_market_ticks():
    """Generate simulated market ticks"""
    redis = await get_redis()
    db = await get_db()
    
    while True:
        try:
            for symbol in SYMBOLS:
                base = BASE_PRICES[symbol]
                # Random price movement
                change = random.uniform(-0.002, 0.002) * base
                new_price = base + change
                spread = new_price * 0.0002  # 0.02% spread
                
                tick = {
                    "symbol": symbol,
                    "timestamp": datetime.utcnow().isoformat(),
                    "bid": round(new_price - spread/2, 4),
                    "ask": round(new_price + spread/2, 4),
                    "last_price": round(new_price, 4),
                    "volume": random.randint(1000, 100000)
                }
                
                # Store latest price in Redis
                await redis.set_json(f"price:{symbol}", tick, ex=60)
                
                # Broadcast to WebSocket clients
                await manager.broadcast({
                    "channel": "market_ticks",
                    "data": tick
                })
                
                # Update feed stats
                for feed in FEEDS.values():
                    feed["message_count"] += 1
                    feed["latency_ms"] = random.randint(5, 50)
            
            # Store aggregate market status
            await redis.set_json("market:status", {
                "feeds": FEEDS,
                "last_update": datetime.utcnow().isoformat(),
                "symbols_active": len(SYMBOLS)
            }, ex=60)
            
            await asyncio.sleep(0.5)  # 500ms tick rate
            
        except Exception as e:
            logger.error(f"Error generating market ticks: {e}")
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup():
    global market_task
    logger.info("Market Data Service starting up...")
    await init_db()
    await init_redis()
    
    # Start market data generator
    market_task = asyncio.create_task(generate_market_ticks())
    logger.info(f"Market Data Service running on port {SERVICE_PORT}")

@app.on_event("shutdown")
async def shutdown():
    global market_task
    logger.info("Market Data Service shutting down...")
    if market_task:
        market_task.cancel()
    await close_db()
    await close_redis()

# ========================================
# REST ENDPOINTS
# ========================================

@app.get("/status")
async def get_status():
    """
    Get current market feed status
    """
    redis = await get_redis()
    
    status = await redis.get_json("market:status")
    if not status:
        status = {
            "feeds": FEEDS,
            "last_update": datetime.utcnow().isoformat(),
            "symbols_active": len(SYMBOLS)
        }
    
    return {
        "status": "OPERATIONAL",
        "feeds": [
            {
                "feed_name": name,
                "status": data["status"],
                "latency_ms": data["latency_ms"],
                "message_count": data["message_count"]
            }
            for name, data in status.get("feeds", FEEDS).items()
        ],
        "symbols_active": status.get("symbols_active", len(SYMBOLS)),
        "last_update": status.get("last_update"),
        "websocket_connections": len(manager.active_connections)
    }

@app.get("/latency", response_model=LatencyResponse)
async def get_latency():
    """
    Get latency metrics for all feeds
    """
    feeds = []
    latencies = []
    
    for name, data in FEEDS.items():
        latency = data["latency_ms"]
        latencies.append(latency)
        feeds.append(MarketStatusResponse(
            feed_name=name,
            status=MarketStatus(data["status"]),
            latency_ms=latency,
            last_heartbeat=datetime.utcnow(),
            message_count=data["message_count"]
        ))
    
    return LatencyResponse(
        feeds=feeds,
        average_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
        max_latency_ms=max(latencies) if latencies else 0
    )

@app.get("/prices")
async def get_all_prices():
    """
    Get latest prices for all symbols
    """
    redis = await get_redis()
    prices = {}
    
    for symbol in SYMBOLS:
        price = await redis.get_json(f"price:{symbol}")
        if price:
            prices[symbol] = price
    
    return {
        "prices": prices,
        "timestamp": datetime.utcnow().isoformat(),
        "count": len(prices)
    }

@app.get("/prices/{symbol}")
async def get_price(symbol: str):
    """
    Get latest price for specific symbol
    """
    redis = await get_redis()
    price = await redis.get_json(f"price:{symbol.upper()}")
    
    if not price:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    return price

@app.get("/symbols")
async def get_symbols():
    """
    Get list of available symbols
    """
    db = await get_db()
    
    instruments = await db.fetch(
        """
        SELECT symbol, name, asset_class, exchange, currency, is_active
        FROM market_instruments
        WHERE is_active = true
        ORDER BY symbol
        """
    )
    
    return {
        "symbols": [
            {
                "symbol": i["symbol"],
                "name": i["name"],
                "asset_class": i["asset_class"],
                "exchange": i["exchange"],
                "currency": i["currency"]
            }
            for i in instruments
        ],
        "count": len(instruments)
    }

# ========================================
# WEBSOCKET ENDPOINT
# ========================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time market data
    Channel: market_ticks
    """
    await manager.connect(websocket)
    
    try:
        # Send initial snapshot
        redis = await get_redis()
        prices = {}
        for symbol in SYMBOLS:
            price = await redis.get_json(f"price:{symbol}")
            if price:
                prices[symbol] = price
        
        await websocket.send_json({
            "type": "snapshot",
            "channel": "market_ticks",
            "data": prices
        })
        
        # Keep connection alive and handle messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # Handle subscription messages if needed
                logger.debug(f"Received WebSocket message: {data}")
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "market-data-service", "port": SERVICE_PORT}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
