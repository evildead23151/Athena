"""
ATHENA Strategy Registry Service
Port: 7003
Handles strategy registration, activation/deactivation, and metadata
"""
import os
import sys
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from common.database import Database, get_db, init_db, close_db
from common.redis_client import RedisClient, get_redis, init_redis, close_redis
from common.auth import verify_token, get_current_user, require_role, require_permission, UserContext
from common.logging import get_logger
from common.models import (
    StrategyStatus, StrategyCreate, StrategyResponse, StrategyPerformance
)

app = FastAPI(
    title="ATHENA Strategy Registry Service",
    description="Strategy registration and lifecycle management",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = get_logger("strategy-registry")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "7003"))


async def log_audit(db: Database, user_id: str, action: str, resource_type: str, 
                    resource_id: str, before: dict = None, after: dict = None):
    """Log audit event"""
    await db.execute(
        """
        INSERT INTO audit_events (user_id, service, action, resource_type, resource_id, before_state, after_state)
        VALUES ($1, 'strategy-registry', $2, $3, $4, $5, $6)
        """,
        UUID(user_id) if user_id else None, action, resource_type, resource_id,
        json.dumps(before) if before else None,
        json.dumps(after) if after else None
    )


async def broadcast_state_change(redis: RedisClient, event_type: str, data: dict):
    """Broadcast state change via Redis pub/sub"""
    await redis.publish("state_updates", {
        "type": event_type,
        "service": "strategy-registry",
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.on_event("startup")
async def startup():
    logger.info("Strategy Registry Service starting up...")
    await init_db()
    await init_redis()
    logger.info(f"Strategy Registry Service running on port {SERVICE_PORT}")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Strategy Registry Service shutting down...")
    await close_db()
    await close_redis()


# ========================================
# ENDPOINTS
# ========================================

@app.get("/strategies")
async def list_strategies(
    status_filter: Optional[str] = None,
    current_user: UserContext = Depends(get_current_user)
):
    """
    List all registered strategies
    """
    db = await get_db()
    
    query = """
        SELECT s.id, s.name, s.description, s.type, s.status, s.allocation, 
               s.risk_budget, s.parameters, s.created_by, s.created_at, s.updated_at,
               u.username as created_by_name
        FROM strategies s
        LEFT JOIN users u ON s.created_by = u.id
    """
    
    if status_filter:
        query += f" WHERE s.status = '{status_filter}'"
    
    query += " ORDER BY s.created_at DESC"
    
    strategies = await db.fetch(query)
    
    return {
        "strategies": [
            {
                "id": str(s["id"]),
                "name": s["name"],
                "description": s["description"],
                "type": s["type"],
                "status": s["status"],
                "allocation": float(s["allocation"]) if s["allocation"] else 0,
                "risk_budget": float(s["risk_budget"]) if s["risk_budget"] else None,
                "parameters": s["parameters"],
                "created_by": str(s["created_by"]) if s["created_by"] else None,
                "created_by_name": s["created_by_name"],
                "created_at": s["created_at"].isoformat() if s["created_at"] else None,
                "updated_at": s["updated_at"].isoformat() if s["updated_at"] else None
            }
            for s in strategies
        ],
        "count": len(strategies),
        "active_count": sum(1 for s in strategies if s["status"] == "ACTIVE")
    }


@app.get("/strategies/{strategy_id}")
async def get_strategy(
    strategy_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get strategy details by ID
    """
    db = await get_db()
    
    strategy = await db.fetchrow(
        """
        SELECT s.*, u.username as created_by_name
        FROM strategies s
        LEFT JOIN users u ON s.created_by = u.id
        WHERE s.id = $1
        """,
        UUID(strategy_id)
    )
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Get latest performance
    performance = await db.fetchrow(
        """
        SELECT * FROM strategy_performance
        WHERE strategy_id = $1
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        UUID(strategy_id)
    )
    
    return {
        "id": str(strategy["id"]),
        "name": strategy["name"],
        "description": strategy["description"],
        "type": strategy["type"],
        "status": strategy["status"],
        "allocation": float(strategy["allocation"]) if strategy["allocation"] else 0,
        "risk_budget": float(strategy["risk_budget"]) if strategy["risk_budget"] else None,
        "parameters": strategy["parameters"],
        "created_by": str(strategy["created_by"]) if strategy["created_by"] else None,
        "created_by_name": strategy["created_by_name"],
        "created_at": strategy["created_at"].isoformat(),
        "updated_at": strategy["updated_at"].isoformat(),
        "performance": {
            "pnl": float(performance["pnl"]) if performance and performance["pnl"] else 0,
            "returns": float(performance["returns"]) if performance and performance["returns"] else 0,
            "sharpe_ratio": float(performance["sharpe_ratio"]) if performance and performance["sharpe_ratio"] else 0,
            "max_drawdown": float(performance["max_drawdown"]) if performance and performance["max_drawdown"] else 0,
            "var_usage": float(performance["var_usage"]) if performance and performance["var_usage"] else 0,
            "ytd_return": float(performance["ytd_return"]) if performance and performance["ytd_return"] else 0
        } if performance else None
    }


@app.post("/strategies/register")
async def register_strategy(
    strategy: StrategyCreate,
    current_user: UserContext = Depends(require_permission("strategy_register"))
):
    """
    Register a new strategy
    Requires: ADMIN or QUANT role
    """
    db = await get_db()
    redis = await get_redis()
    
    # Create strategy
    result = await db.fetchrow(
        """
        INSERT INTO strategies (name, description, type, status, allocation, risk_budget, parameters, created_by)
        VALUES ($1, $2, $3, 'INACTIVE', $4, $5, $6, $7)
        RETURNING id, created_at
        """,
        strategy.name,
        strategy.description,
        strategy.type,
        strategy.allocation,
        strategy.risk_budget,
        json.dumps(strategy.parameters),
        UUID(current_user.id)
    )
    
    strategy_id = str(result["id"])
    
    # Log audit
    await log_audit(
        db, current_user.id, "STRATEGY_REGISTER", "strategy", strategy_id,
        after={"name": strategy.name, "type": strategy.type, "status": "INACTIVE"}
    )
    
    # Broadcast state change
    await broadcast_state_change(redis, "STRATEGY_REGISTERED", {
        "strategy_id": strategy_id,
        "name": strategy.name,
        "status": "INACTIVE"
    })
    
    logger.info(f"Strategy registered: {strategy.name}", 
                user_id=current_user.id, action="STRATEGY_REGISTER")
    
    return {
        "success": True,
        "strategy_id": strategy_id,
        "name": strategy.name,
        "status": "INACTIVE",
        "created_at": result["created_at"].isoformat()
    }


@app.post("/strategies/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Activate a strategy
    Requires: ADMIN or QUANT role
    """
    db = await get_db()
    redis = await get_redis()
    
    # Get current state
    strategy = await db.fetchrow(
        "SELECT id, name, status FROM strategies WHERE id = $1",
        UUID(strategy_id)
    )
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    before_status = strategy["status"]
    
    if before_status == "ACTIVE":
        return {"success": True, "message": "Strategy already active", "status": "ACTIVE"}
    
    # Permission check
    if current_user.role not in ["ADMIN", "QUANT"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Update status
    await db.execute(
        "UPDATE strategies SET status = 'ACTIVE', updated_at = $1 WHERE id = $2",
        datetime.utcnow(),
        UUID(strategy_id)
    )
    
    # Log audit
    await log_audit(
        db, current_user.id, "STRATEGY_ACTIVATE", "strategy", strategy_id,
        before={"status": before_status},
        after={"status": "ACTIVE"}
    )
    
    # Broadcast
    await broadcast_state_change(redis, "STRATEGY_ACTIVATED", {
        "strategy_id": strategy_id,
        "name": strategy["name"],
        "status": "ACTIVE",
        "previous_status": before_status
    })
    
    logger.info(f"Strategy activated: {strategy['name']}", 
                user_id=current_user.id, action="STRATEGY_ACTIVATE")
    
    return {
        "success": True,
        "strategy_id": strategy_id,
        "name": strategy["name"],
        "status": "ACTIVE",
        "previous_status": before_status
    }


@app.post("/strategies/{strategy_id}/halt")
async def halt_strategy(
    strategy_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Halt (pause) a strategy
    Requires: ADMIN or QUANT role
    """
    db = await get_db()
    redis = await get_redis()
    
    # Get current state
    strategy = await db.fetchrow(
        "SELECT id, name, status FROM strategies WHERE id = $1",
        UUID(strategy_id)
    )
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    before_status = strategy["status"]
    
    if before_status == "HALTED":
        return {"success": True, "message": "Strategy already halted", "status": "HALTED"}
    
    # Permission check
    if current_user.role not in ["ADMIN", "QUANT"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Update status
    await db.execute(
        "UPDATE strategies SET status = 'HALTED', updated_at = $1 WHERE id = $2",
        datetime.utcnow(),
        UUID(strategy_id)
    )
    
    # Log audit
    await log_audit(
        db, current_user.id, "STRATEGY_HALT", "strategy", strategy_id,
        before={"status": before_status},
        after={"status": "HALTED"}
    )
    
    # Broadcast
    await broadcast_state_change(redis, "STRATEGY_HALTED", {
        "strategy_id": strategy_id,
        "name": strategy["name"],
        "status": "HALTED",
        "previous_status": before_status
    })
    
    logger.info(f"Strategy halted: {strategy['name']}", 
                user_id=current_user.id, action="STRATEGY_HALT")
    
    return {
        "success": True,
        "strategy_id": strategy_id,
        "name": strategy["name"],
        "status": "HALTED",
        "previous_status": before_status
    }


@app.put("/strategies/{strategy_id}/parameters")
async def update_strategy_parameters(
    strategy_id: str,
    parameters: dict,
    current_user: UserContext = Depends(require_permission("parameter_update"))
):
    """
    Update strategy parameters
    Requires: ADMIN or QUANT role
    """
    db = await get_db()
    redis = await get_redis()
    
    # Get current state
    strategy = await db.fetchrow(
        "SELECT id, name, parameters FROM strategies WHERE id = $1",
        UUID(strategy_id)
    )
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    before_params = strategy["parameters"]
    
    # Update parameters
    await db.execute(
        "UPDATE strategies SET parameters = $1, updated_at = $2 WHERE id = $3",
        json.dumps(parameters),
        datetime.utcnow(),
        UUID(strategy_id)
    )
    
    # Log audit
    await log_audit(
        db, current_user.id, "STRATEGY_PARAM_UPDATE", "strategy", strategy_id,
        before={"parameters": before_params},
        after={"parameters": parameters}
    )
    
    # Broadcast
    await broadcast_state_change(redis, "STRATEGY_PARAMS_UPDATED", {
        "strategy_id": strategy_id,
        "name": strategy["name"],
        "parameters": parameters
    })
    
    logger.info(f"Strategy parameters updated: {strategy['name']}", 
                user_id=current_user.id, action="STRATEGY_PARAM_UPDATE")
    
    return {
        "success": True,
        "strategy_id": strategy_id,
        "name": strategy["name"],
        "parameters": parameters
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "strategy-registry", "port": SERVICE_PORT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
