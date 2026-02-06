"""
ATHENA Execution Gateway
Port: 7005
Handles trade intents, order routing, and fill tracking
"""
import os
import sys
import asyncio
import random
import json
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from common.database import Database, get_db, init_db, close_db
from common.redis_client import RedisClient, get_redis, init_redis, close_redis
from common.auth import verify_token, get_current_user, require_permission, UserContext
from common.logging import get_logger
from common.models import (
    OrderCreate, OrderResponse, OrderStatus, OrderSide, OrderType
)

app = FastAPI(
    title="ATHENA Execution Gateway",
    description="Order routing and execution management",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = get_logger("execution-gateway")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "7005"))

# Order execution simulator
execution_task = None


async def log_audit(db: Database, user_id: str, action: str, resource_type: str = None,
                    resource_id: str = None, before: dict = None, after: dict = None):
    await db.execute(
        """
        INSERT INTO audit_events (user_id, service, action, resource_type, resource_id, before_state, after_state)
        VALUES ($1, 'execution-gateway', $2, $3, $4, $5, $6)
        """,
        UUID(user_id) if user_id else None, action, resource_type, resource_id,
        json.dumps(before) if before else None,
        json.dumps(after) if after else None
    )


async def simulate_order_execution():
    """Background task to simulate order fills"""
    db = await get_db()
    redis = await get_redis()
    
    while True:
        try:
            # Get open orders
            orders = await db.fetch(
                "SELECT * FROM orders WHERE status IN ('PENDING', 'OPEN', 'PARTIAL') LIMIT 10"
            )
            
            for order in orders:
                # Random chance to fill
                if random.random() < 0.3:
                    remaining = float(order["quantity"]) - float(order["filled_quantity"])
                    fill_qty = random.uniform(0, remaining)
                    
                    if fill_qty > 0:
                        # Get current price
                        price = await redis.get_json(f"price:{order['symbol']}")
                        fill_price = price["last_price"] if price else float(order["price"]) if order["price"] else 100.0
                        
                        # Insert fill
                        await db.execute(
                            """
                            INSERT INTO fills (order_id, quantity, price)
                            VALUES ($1, $2, $3)
                            """,
                            order["id"], fill_qty, fill_price
                        )
                        
                        # Update order
                        new_filled = float(order["filled_quantity"]) + fill_qty
                        new_status = "FILLED" if new_filled >= float(order["quantity"]) else "PARTIAL"
                        avg_price = fill_price  # Simplified
                        
                        await db.execute(
                            """
                            UPDATE orders 
                            SET filled_quantity = $1, average_fill_price = $2, status = $3, updated_at = $4
                            WHERE id = $5
                            """,
                            new_filled, avg_price, new_status, datetime.utcnow(), order["id"]
                        )
                        
                        # Update position
                        existing_pos = await db.fetchrow(
                            "SELECT * FROM positions WHERE symbol = $1 AND strategy_id = $2",
                            order["symbol"], order["strategy_id"]
                        )
                        
                        qty_change = fill_qty if order["side"] == "BUY" else -fill_qty
                        
                        if existing_pos:
                            new_qty = float(existing_pos["quantity"]) + qty_change
                            await db.execute(
                                """
                                UPDATE positions SET quantity = $1, current_price = $2, updated_at = $3
                                WHERE id = $4
                                """,
                                new_qty, fill_price, datetime.utcnow(), existing_pos["id"]
                            )
                        else:
                            await db.execute(
                                """
                                INSERT INTO positions (strategy_id, symbol, quantity, average_entry_price, current_price)
                                VALUES ($1, $2, $3, $4, $5)
                                """,
                                order["strategy_id"], order["symbol"], qty_change, fill_price, fill_price
                            )
            
            # Update open orders count in Redis
            count = await db.fetchval(
                "SELECT COUNT(*) FROM orders WHERE status IN ('PENDING', 'OPEN', 'PARTIAL')"
            )
            await redis.set_json("orders:open_count", {"count": count, "updated": datetime.utcnow().isoformat()})
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Execution simulation error: {e}")
            await asyncio.sleep(2)


@app.on_event("startup")
async def startup():
    global execution_task
    logger.info("Execution Gateway starting up...")
    await init_db()
    await init_redis()
    execution_task = asyncio.create_task(simulate_order_execution())
    logger.info(f"Execution Gateway running on port {SERVICE_PORT}")


@app.on_event("shutdown")
async def shutdown():
    global execution_task
    logger.info("Execution Gateway shutting down...")
    if execution_task:
        execution_task.cancel()
    await close_db()
    await close_redis()


# ========================================
# ENDPOINTS
# ========================================

@app.post("/orders/send")
async def send_order(
    order: OrderCreate,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Submit a new order
    """
    # Permission check
    if current_user.role == "VIEWER":
        raise HTTPException(status_code=403, detail="Viewers cannot submit orders")
    
    db = await get_db()
    redis = await get_redis()
    
    # Check kill switch
    kill_switch = await db.fetchval(
        "SELECT value FROM system_state WHERE key = 'kill_switch_active'"
    )
    if kill_switch and json.loads(kill_switch) == True:
        raise HTTPException(status_code=403, detail="Trading suspended - Kill switch active")
    
    # Validate symbol
    price = await redis.get_json(f"price:{order.symbol}")
    if not price:
        raise HTTPException(status_code=400, detail=f"Unknown symbol: {order.symbol}")
    
    # Create order
    result = await db.fetchrow(
        """
        INSERT INTO orders (strategy_id, symbol, side, order_type, quantity, price, stop_price, status, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, 'PENDING', $8)
        RETURNING id, created_at
        """,
        order.strategy_id,
        order.symbol,
        order.side.value,
        order.order_type.value,
        order.quantity,
        order.price or price["last_price"],
        order.stop_price,
        UUID(current_user.id)
    )
    
    order_id = str(result["id"])
    
    # Log audit
    await log_audit(
        db, current_user.id, "ORDER_SUBMIT", "order", order_id,
        after={
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "type": order.order_type.value
        }
    )
    
    logger.info(f"Order submitted: {order_id}", user_id=current_user.id, action="ORDER_SUBMIT")
    
    return {
        "success": True,
        "order_id": order_id,
        "symbol": order.symbol,
        "side": order.side.value,
        "quantity": order.quantity,
        "status": "PENDING",
        "created_at": result["created_at"].isoformat()
    }


@app.post("/orders/cancel_all")
async def cancel_all_orders(
    current_user: UserContext = Depends(get_current_user)
):
    """
    Cancel all open orders
    Requires: ADMIN role
    """
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = await get_db()
    
    # Get count before
    before_count = await db.fetchval(
        "SELECT COUNT(*) FROM orders WHERE status IN ('PENDING', 'OPEN', 'PARTIAL')"
    )
    
    # Cancel all
    await db.execute(
        """
        UPDATE orders SET status = 'CANCELLED', updated_at = $1
        WHERE status IN ('PENDING', 'OPEN', 'PARTIAL')
        """,
        datetime.utcnow()
    )
    
    # Log audit
    await log_audit(
        db, current_user.id, "ORDERS_CANCEL_ALL", "order", "all",
        before={"open_orders": before_count},
        after={"open_orders": 0}
    )
    
    logger.info(f"All orders cancelled: {before_count}", user_id=current_user.id, action="ORDERS_CANCEL_ALL")
    
    return {
        "success": True,
        "orders_cancelled": before_count,
        "executed_at": datetime.utcnow().isoformat()
    }


@app.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Cancel specific order
    """
    if current_user.role == "VIEWER":
        raise HTTPException(status_code=403, detail="Viewers cannot cancel orders")
    
    db = await get_db()
    
    order = await db.fetchrow("SELECT * FROM orders WHERE id = $1", UUID(order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["status"] in ("FILLED", "CANCELLED", "REJECTED"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel order with status: {order['status']}")
    
    before_status = order["status"]
    
    await db.execute(
        "UPDATE orders SET status = 'CANCELLED', updated_at = $1 WHERE id = $2",
        datetime.utcnow(), UUID(order_id)
    )
    
    await log_audit(
        db, current_user.id, "ORDER_CANCEL", "order", order_id,
        before={"status": before_status},
        after={"status": "CANCELLED"}
    )
    
    return {"success": True, "order_id": order_id, "previous_status": before_status}


@app.get("/orders/open")
async def get_open_orders(
    symbol: Optional[str] = None,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get all open orders
    """
    db = await get_db()
    
    query = """
        SELECT o.*, s.name as strategy_name, u.username as created_by_name
        FROM orders o
        LEFT JOIN strategies s ON o.strategy_id = s.id
        LEFT JOIN users u ON o.created_by = u.id
        WHERE o.status IN ('PENDING', 'OPEN', 'PARTIAL')
    """
    
    if symbol:
        query += f" AND o.symbol = '{symbol}'"
    
    query += " ORDER BY o.created_at DESC"
    
    orders = await db.fetch(query)
    
    return {
        "orders": [
            {
                "id": str(o["id"]),
                "symbol": o["symbol"],
                "side": o["side"],
                "type": o["order_type"],
                "quantity": float(o["quantity"]),
                "filled_quantity": float(o["filled_quantity"]) if o["filled_quantity"] else 0,
                "price": float(o["price"]) if o["price"] else None,
                "status": o["status"],
                "strategy_name": o["strategy_name"],
                "created_by": o["created_by_name"],
                "created_at": o["created_at"].isoformat()
            }
            for o in orders
        ],
        "count": len(orders)
    }


@app.get("/orders/history")
async def get_order_history(
    limit: int = 50,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get order history
    """
    db = await get_db()
    
    orders = await db.fetch(
        """
        SELECT o.*, s.name as strategy_name
        FROM orders o
        LEFT JOIN strategies s ON o.strategy_id = s.id
        ORDER BY o.created_at DESC
        LIMIT $1
        """,
        limit
    )
    
    return {
        "orders": [
            {
                "id": str(o["id"]),
                "symbol": o["symbol"],
                "side": o["side"],
                "type": o["order_type"],
                "quantity": float(o["quantity"]),
                "filled_quantity": float(o["filled_quantity"]) if o["filled_quantity"] else 0,
                "average_fill_price": float(o["average_fill_price"]) if o["average_fill_price"] else None,
                "status": o["status"],
                "strategy_name": o["strategy_name"],
                "created_at": o["created_at"].isoformat()
            }
            for o in orders
        ],
        "count": len(orders)
    }


@app.get("/positions")
async def get_positions(current_user: UserContext = Depends(get_current_user)):
    """
    Get all positions
    """
    db = await get_db()
    redis = await get_redis()
    
    positions = await db.fetch(
        """
        SELECT p.*, s.name as strategy_name
        FROM positions p
        LEFT JOIN strategies s ON p.strategy_id = s.id
        WHERE p.quantity != 0
        ORDER BY ABS(p.quantity) DESC
        """
    )
    
    result = []
    for p in positions:
        # Get current price
        price = await redis.get_json(f"price:{p['symbol']}")
        current_price = price["last_price"] if price else float(p["current_price"]) if p["current_price"] else 0
        
        entry_price = float(p["average_entry_price"]) if p["average_entry_price"] else current_price
        quantity = float(p["quantity"])
        unrealized_pnl = (current_price - entry_price) * quantity
        
        result.append({
            "id": str(p["id"]),
            "symbol": p["symbol"],
            "quantity": quantity,
            "entry_price": entry_price,
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
            "strategy_name": p["strategy_name"]
        })
    
    return {
        "positions": result,
        "count": len(result),
        "total_unrealized_pnl": sum(p["unrealized_pnl"] for p in result)
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "execution-gateway", "port": SERVICE_PORT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
