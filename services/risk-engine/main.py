"""
ATHENA Risk Engine Service
Port: 7004
Handles risk monitoring, mandate tracking, kill switch, and real-time risk alerts
WebSocket channel: risk_alerts
"""
import os
import sys
import asyncio
import random
import json
from datetime import datetime
from typing import Optional, List, Set
from uuid import UUID, uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from common.database import Database, get_db, init_db, close_db
from common.redis_client import RedisClient, get_redis, init_redis, close_redis
from common.auth import verify_token, get_current_user, require_role, require_permission, UserContext
from common.logging import get_logger
from common.models import (
    RiskSnapshot, RiskMandate, RiskAlert, KillSwitchRequest, KillSwitchResponse,
    MandateStatus, AlertSeverity
)

app = FastAPI(
    title="ATHENA Risk Engine Service",
    description="Real-time risk monitoring and control",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = get_logger("risk-engine")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "7004"))


# WebSocket manager for risk alerts
class RiskAlertManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Risk WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"Risk WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast_alert(self, alert: dict):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(alert)
            except:
                disconnected.add(connection)
        for conn in disconnected:
            self.active_connections.discard(conn)

alert_manager = RiskAlertManager()
risk_monitor_task = None


# Simulated risk state
RISK_STATE = {
    "net_exposure": 3100000,
    "gross_exposure": 4200000000,
    "gross_leverage": 4.2,
    "net_leverage": 0.02,
    "var_95": 12500000,
    "var_99": 18700000,
    "max_drawdown": -0.042,
    "daily_pnl": 124002,
    "concentration_risk": 0.18,
    "sector_exposures": {
        "Technology": 0.145,
        "Healthcare": 0.08,
        "Financials": 0.12,
        "Consumer": 0.05
    }
}


async def log_audit(db: Database, user_id: str, action: str, resource_type: str = None,
                    resource_id: str = None, before: dict = None, after: dict = None):
    await db.execute(
        """
        INSERT INTO audit_events (user_id, service, action, resource_type, resource_id, before_state, after_state)
        VALUES ($1, 'risk-engine', $2, $3, $4, $5, $6)
        """,
        UUID(user_id) if user_id else None, action, resource_type, resource_id,
        json.dumps(before) if before else None,
        json.dumps(after) if after else None
    )


async def check_mandate_breaches(db: Database, redis: RedisClient):
    """Check all mandates and generate alerts for breaches"""
    mandates = await db.fetch("SELECT * FROM risk_mandates WHERE is_active = true")
    
    for mandate in mandates:
        current = float(mandate["current_value"]) if mandate["current_value"] else 0
        hard_limit = float(mandate["hard_limit"]) if mandate["hard_limit"] else None
        soft_limit = float(mandate["soft_limit"]) if mandate["soft_limit"] else None
        
        new_status = "OK"
        alert_severity = None
        
        if hard_limit and abs(current) >= abs(hard_limit):
            new_status = "BREACH"
            alert_severity = "CRITICAL"
        elif soft_limit and abs(current) >= abs(soft_limit):
            new_status = "WARNING"
            alert_severity = "WARNING"
        
        if mandate["status"] != new_status:
            # Update mandate status
            await db.execute(
                "UPDATE risk_mandates SET status = $1, updated_at = $2 WHERE id = $3",
                new_status, datetime.utcnow(), mandate["id"]
            )
            
            if alert_severity:
                # Create alert
                alert = {
                    "id": str(uuid4()),
                    "mandate_id": str(mandate["id"]),
                    "mandate_code": mandate["mandate_id"],
                    "severity": alert_severity,
                    "message": f"Mandate {mandate['mandate_id']}: {mandate['description']} - {new_status}",
                    "current_value": current,
                    "limit": hard_limit if new_status == "BREACH" else soft_limit,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Broadcast via WebSocket
                await alert_manager.broadcast_alert({
                    "channel": "risk_alerts",
                    "type": "MANDATE_ALERT",
                    "data": alert
                })
                
                # Store in database
                await db.execute(
                    """
                    INSERT INTO risk_alerts (mandate_id, severity, message, details)
                    VALUES ($1, $2, $3, $4)
                    """,
                    mandate["id"], alert_severity, alert["message"], json.dumps(alert)
                )


async def risk_monitoring_loop():
    """Background task for continuous risk monitoring"""
    db = await get_db()
    redis = await get_redis()
    
    while True:
        try:
            # Simulate risk state changes
            RISK_STATE["net_exposure"] += random.randint(-100000, 100000)
            RISK_STATE["daily_pnl"] += random.randint(-5000, 5000)
            RISK_STATE["max_drawdown"] = min(RISK_STATE["max_drawdown"] + random.uniform(-0.001, 0.0005), 0)
            
            # Randomly update mandate values
            mandates = await db.fetch("SELECT * FROM risk_mandates WHERE is_active = true")
            for mandate in mandates:
                if random.random() < 0.1:  # 10% chance to update
                    current = float(mandate["current_value"]) if mandate["current_value"] else 0
                    variation = current * random.uniform(-0.02, 0.02)
                    new_value = current + variation
                    await db.execute(
                        "UPDATE risk_mandates SET current_value = $1 WHERE id = $2",
                        new_value, mandate["id"]
                    )
            
            # Check for breaches
            await check_mandate_breaches(db, redis)
            
            # Store risk snapshot in Redis
            await redis.set_json("risk:snapshot", {
                **RISK_STATE,
                "timestamp": datetime.utcnow().isoformat()
            }, ex=60)
            
            # Store in database every 5 seconds
            if random.random() < 0.2:
                await db.execute(
                    """
                    INSERT INTO risk_snapshots 
                    (net_exposure, gross_exposure, gross_leverage, net_leverage, 
                     var_95, var_99, max_drawdown, daily_pnl, sector_exposures, concentration_risk)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    RISK_STATE["net_exposure"], RISK_STATE["gross_exposure"],
                    RISK_STATE["gross_leverage"], RISK_STATE["net_leverage"],
                    RISK_STATE["var_95"], RISK_STATE["var_99"],
                    RISK_STATE["max_drawdown"], RISK_STATE["daily_pnl"],
                    json.dumps(RISK_STATE["sector_exposures"]), RISK_STATE["concentration_risk"]
                )
            
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Risk monitoring error: {e}")
            await asyncio.sleep(5)


@app.on_event("startup")
async def startup():
    global risk_monitor_task
    logger.info("Risk Engine Service starting up...")
    await init_db()
    await init_redis()
    risk_monitor_task = asyncio.create_task(risk_monitoring_loop())
    logger.info(f"Risk Engine Service running on port {SERVICE_PORT}")


@app.on_event("shutdown")
async def shutdown():
    global risk_monitor_task
    logger.info("Risk Engine Service shutting down...")
    if risk_monitor_task:
        risk_monitor_task.cancel()
    await close_db()
    await close_redis()


# ========================================
# REST ENDPOINTS
# ========================================

@app.get("/risk/snapshot")
async def get_risk_snapshot(current_user: UserContext = Depends(get_current_user)):
    """
    Get current risk snapshot
    """
    redis = await get_redis()
    db = await get_db()
    
    # Get latest snapshot from Redis
    snapshot = await redis.get_json("risk:snapshot")
    if not snapshot:
        snapshot = RISK_STATE.copy()
        snapshot["timestamp"] = datetime.utcnow().isoformat()
    
    # Get mandate statuses
    mandates = await db.fetch(
        "SELECT * FROM risk_mandates WHERE is_active = true ORDER BY mandate_id"
    )
    
    # Get active alerts
    alerts = await db.fetch(
        """
        SELECT ra.*, rm.mandate_id as mandate_code
        FROM risk_alerts ra
        LEFT JOIN risk_mandates rm ON ra.mandate_id = rm.id
        WHERE ra.is_acknowledged = false
        ORDER BY ra.created_at DESC
        LIMIT 10
        """
    )
    
    return {
        "snapshot": snapshot,
        "mandates": [
            {
                "id": str(m["id"]),
                "mandate_id": m["mandate_id"],
                "description": m["description"],
                "constraint_type": m["constraint_type"],
                "soft_limit": float(m["soft_limit"]) if m["soft_limit"] else None,
                "hard_limit": float(m["hard_limit"]) if m["hard_limit"] else None,
                "current_value": float(m["current_value"]) if m["current_value"] else None,
                "status": m["status"],
                "delta": float(m["current_value"]) - float(m["soft_limit"]) 
                        if m["current_value"] and m["soft_limit"] else 0
            }
            for m in mandates
        ],
        "active_alerts": [
            {
                "id": str(a["id"]),
                "mandate_code": a["mandate_code"],
                "severity": a["severity"],
                "message": a["message"],
                "created_at": a["created_at"].isoformat()
            }
            for a in alerts
        ],
        "alerts_count": len(alerts)
    }


@app.post("/risk/kill-switch", response_model=KillSwitchResponse)
async def execute_kill_switch(
    request: KillSwitchRequest,
    current_user: UserContext = Depends(require_permission("kill_switch"))
):
    """
    Execute emergency kill switch
    - Cancels all open orders
    - Flattens all positions
    - Halts all strategies
    - Emits system-wide alerts
    
    Requires: ADMIN role
    """
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="Kill switch must be explicitly confirmed"
        )
    
    db = await get_db()
    redis = await get_redis()
    
    logger.critical(f"KILL SWITCH ACTIVATED by {current_user.username}", 
                    user_id=current_user.id, action="KILL_SWITCH")
    
    # Get current state before kill
    open_orders = await db.fetchval("SELECT COUNT(*) FROM orders WHERE status IN ('PENDING', 'OPEN')")
    active_strategies = await db.fetchval("SELECT COUNT(*) FROM strategies WHERE status = 'ACTIVE'")
    
    before_state = {
        "open_orders": open_orders,
        "active_strategies": active_strategies,
        "kill_switch_active": False
    }
    
    try:
        # Cancel all open orders
        await db.execute(
            """
            UPDATE orders SET status = 'CANCELLED', updated_at = $1 
            WHERE status IN ('PENDING', 'OPEN')
            """,
            datetime.utcnow()
        )
        
        # Close all positions (mark as closed)
        positions_closed = await db.fetchval(
            "SELECT COUNT(*) FROM positions WHERE quantity != 0"
        )
        await db.execute(
            "UPDATE positions SET quantity = 0, updated_at = $1",
            datetime.utcnow()
        )
        
        # Halt all strategies
        await db.execute(
            """
            UPDATE strategies SET status = 'HALTED', updated_at = $1 
            WHERE status = 'ACTIVE'
            """,
            datetime.utcnow()
        )
        
        # Set kill switch state
        await db.execute(
            """
            UPDATE system_state SET value = 'true', updated_at = $1 
            WHERE key = 'kill_switch_active'
            """,
            datetime.utcnow()
        )
        
        await db.execute(
            """
            UPDATE system_state SET value = '"EMERGENCY"', updated_at = $1 
            WHERE key = 'system_status'
            """,
            datetime.utcnow()
        )
        
        after_state = {
            "open_orders": 0,
            "active_strategies": 0,
            "kill_switch_active": True,
            "positions_closed": positions_closed
        }
        
        # Log audit
        await log_audit(
            db, current_user.id, "KILL_SWITCH_EXECUTE", "system", "global",
            before=before_state, after=after_state
        )
        
        # Broadcast critical alert
        await alert_manager.broadcast_alert({
            "channel": "risk_alerts",
            "type": "KILL_SWITCH",
            "severity": "CRITICAL",
            "data": {
                "message": f"KILL SWITCH ACTIVATED by {current_user.username}",
                "reason": request.reason,
                "orders_cancelled": open_orders,
                "positions_closed": positions_closed,
                "strategies_halted": active_strategies,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        # Also broadcast via Redis for other services
        await redis.publish("system_alerts", {
            "type": "KILL_SWITCH",
            "executed_by": current_user.username,
            "reason": request.reason,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return KillSwitchResponse(
            success=True,
            orders_cancelled=open_orders,
            positions_closed=positions_closed,
            message=f"Kill switch executed. Reason: {request.reason}",
            executed_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Kill switch execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Kill switch failed: {str(e)}")


@app.post("/risk/update")
async def update_risk_settings(
    settings: dict,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Update risk settings/gates
    """
    if current_user.role not in ["ADMIN", "QUANT"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    db = await get_db()
    redis = await get_redis()
    
    # Log the update
    await log_audit(
        db, current_user.id, "RISK_SETTINGS_UPDATE", "risk", "settings",
        after=settings
    )
    
    # Store in Redis
    await redis.set_json("risk:settings", settings)
    
    return {"success": True, "settings": settings}


@app.get("/risk/mandates")
async def get_mandates(current_user: UserContext = Depends(get_current_user)):
    """
    Get all risk mandates
    """
    db = await get_db()
    
    mandates = await db.fetch(
        "SELECT * FROM risk_mandates ORDER BY mandate_id"
    )
    
    return {
        "mandates": [
            {
                "id": str(m["id"]),
                "mandate_id": m["mandate_id"],
                "description": m["description"],
                "constraint_type": m["constraint_type"],
                "soft_limit": float(m["soft_limit"]) if m["soft_limit"] else None,
                "hard_limit": float(m["hard_limit"]) if m["hard_limit"] else None,
                "current_value": float(m["current_value"]) if m["current_value"] else None,
                "status": m["status"],
                "is_active": m["is_active"]
            }
            for m in mandates
        ],
        "breaches": sum(1 for m in mandates if m["status"] == "BREACH"),
        "warnings": sum(1 for m in mandates if m["status"] == "WARNING")
    }


@app.post("/risk/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Acknowledge a risk alert
    """
    db = await get_db()
    
    await db.execute(
        """
        UPDATE risk_alerts 
        SET is_acknowledged = true, acknowledged_by = $1, acknowledged_at = $2
        WHERE id = $3
        """,
        UUID(current_user.id), datetime.utcnow(), UUID(alert_id)
    )
    
    return {"success": True, "alert_id": alert_id}


# ========================================
# WEBSOCKET ENDPOINT
# ========================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket for real-time risk alerts
    Channel: risk_alerts
    """
    await alert_manager.connect(websocket)
    
    try:
        # Send initial snapshot
        redis = await get_redis()
        snapshot = await redis.get_json("risk:snapshot")
        
        await websocket.send_json({
            "type": "snapshot",
            "channel": "risk_alerts",
            "data": snapshot or RISK_STATE
        })
        
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                logger.debug(f"Received WebSocket message: {data}")
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
    except WebSocketDisconnect:
        alert_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        alert_manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "risk-engine", "port": SERVICE_PORT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
