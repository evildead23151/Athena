"""
ATHENA Audit Ledger Service
Port: 7007
Immutable append-only event log for action tracking and compliance
"""
import os
import sys
import json
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from common.database import Database, get_db, init_db, close_db
from common.redis_client import RedisClient, get_redis, init_redis, close_redis
from common.auth import verify_token, get_current_user, UserContext
from common.logging import get_logger
from common.models import AuditEvent, AuditQueryParams

app = FastAPI(
    title="ATHENA Audit Ledger Service",
    description="Immutable audit trail and event logging",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = get_logger("audit-ledger")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "7007"))


@app.on_event("startup")
async def startup():
    logger.info("Audit Ledger Service starting up...")
    await init_db()
    await init_redis()
    logger.info(f"Audit Ledger Service running on port {SERVICE_PORT}")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Audit Ledger Service shutting down...")
    await close_db()
    await close_redis()


# ========================================
# ENDPOINTS
# ========================================

@app.get("/audit/events")
async def get_audit_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[str] = None,
    service: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Query audit events with filters
    Returns immutable event log with full attribution
    """
    db = await get_db()
    
    # Build query
    conditions = []
    params = []
    param_idx = 1
    
    if start_date:
        conditions.append(f"ae.timestamp >= ${param_idx}")
        params.append(datetime.fromisoformat(start_date))
        param_idx += 1
    
    if end_date:
        conditions.append(f"ae.timestamp <= ${param_idx}")
        params.append(datetime.fromisoformat(end_date))
        param_idx += 1
    
    if user_id:
        conditions.append(f"ae.user_id = ${param_idx}")
        params.append(UUID(user_id))
        param_idx += 1
    
    if service:
        conditions.append(f"ae.service = ${param_idx}")
        params.append(service)
        param_idx += 1
    
    if action:
        conditions.append(f"ae.action ILIKE ${param_idx}")
        params.append(f"%{action}%")
        param_idx += 1
    
    if resource_type:
        conditions.append(f"ae.resource_type = ${param_idx}")
        params.append(resource_type)
        param_idx += 1
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT ae.*, u.username
        FROM audit_events ae
        LEFT JOIN users u ON ae.user_id = u.id
        WHERE {where_clause}
        ORDER BY ae.timestamp DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    
    params.extend([limit, offset])
    
    events = await db.fetch(query, *params)
    
    # Get total count
    count_query = f"""
        SELECT COUNT(*) FROM audit_events ae WHERE {where_clause}
    """
    total = await db.fetchval(count_query, *params[:-2])
    
    return {
        "events": [
            {
                "id": str(e["id"]),
                "timestamp": e["timestamp"].isoformat(),
                "user_id": str(e["user_id"]) if e["user_id"] else None,
                "username": e["username"],
                "service": e["service"],
                "action": e["action"],
                "resource_type": e["resource_type"],
                "resource_id": e["resource_id"],
                "before_state": json.loads(e["before_state"]) if e["before_state"] else None,
                "after_state": json.loads(e["after_state"]) if e["after_state"] else None,
                "ip_address": e["ip_address"],
                "correlation_id": str(e["correlation_id"]) if e["correlation_id"] else None
            }
            for e in events
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total
    }


@app.get("/audit/events/{event_id}")
async def get_audit_event(
    event_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get single audit event by ID
    """
    db = await get_db()
    
    event = await db.fetchrow(
        """
        SELECT ae.*, u.username
        FROM audit_events ae
        LEFT JOIN users u ON ae.user_id = u.id
        WHERE ae.id = $1
        """,
        UUID(event_id)
    )
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {
        "id": str(event["id"]),
        "timestamp": event["timestamp"].isoformat(),
        "user_id": str(event["user_id"]) if event["user_id"] else None,
        "username": event["username"],
        "service": event["service"],
        "action": event["action"],
        "resource_type": event["resource_type"],
        "resource_id": event["resource_id"],
        "before_state": json.loads(event["before_state"]) if event["before_state"] else None,
        "after_state": json.loads(event["after_state"]) if event["after_state"] else None,
        "ip_address": event["ip_address"],
        "correlation_id": str(event["correlation_id"]) if event["correlation_id"] else None
    }


@app.get("/audit/summary")
async def get_audit_summary(
    hours: int = 24,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get audit activity summary
    """
    db = await get_db()
    
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Events by service
    by_service = await db.fetch(
        """
        SELECT service, COUNT(*) as count
        FROM audit_events
        WHERE timestamp >= $1
        GROUP BY service
        ORDER BY count DESC
        """,
        since
    )
    
    # Events by action type
    by_action = await db.fetch(
        """
        SELECT action, COUNT(*) as count
        FROM audit_events
        WHERE timestamp >= $1
        GROUP BY action
        ORDER BY count DESC
        LIMIT 10
        """,
        since
    )
    
    # Active users
    active_users = await db.fetch(
        """
        SELECT u.username, COUNT(*) as action_count
        FROM audit_events ae
        JOIN users u ON ae.user_id = u.id
        WHERE ae.timestamp >= $1
        GROUP BY u.username
        ORDER BY action_count DESC
        LIMIT 10
        """,
        since
    )
    
    # Critical actions
    critical_actions = await db.fetch(
        """
        SELECT ae.*, u.username
        FROM audit_events ae
        LEFT JOIN users u ON ae.user_id = u.id
        WHERE ae.timestamp >= $1 
        AND ae.action IN ('KILL_SWITCH_EXECUTE', 'ORDERS_CANCEL_ALL', 'STRATEGY_HALT')
        ORDER BY ae.timestamp DESC
        LIMIT 10
        """,
        since
    )
    
    # Total count
    total = await db.fetchval(
        "SELECT COUNT(*) FROM audit_events WHERE timestamp >= $1",
        since
    )
    
    return {
        "period_hours": hours,
        "total_events": total,
        "by_service": [{"service": s["service"], "count": s["count"]} for s in by_service],
        "by_action": [{"action": a["action"], "count": a["count"]} for a in by_action],
        "active_users": [{"username": u["username"], "actions": u["action_count"]} for u in active_users],
        "critical_actions": [
            {
                "id": str(c["id"]),
                "action": c["action"],
                "username": c["username"],
                "timestamp": c["timestamp"].isoformat(),
                "service": c["service"]
            }
            for c in critical_actions
        ]
    }


@app.get("/audit/export")
async def export_audit_log(
    start_date: str,
    end_date: str,
    format: str = "json",
    current_user: UserContext = Depends(get_current_user)
):
    """
    Export audit log for compliance
    Requires: ADMIN role
    """
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required for export")
    
    db = await get_db()
    
    events = await db.fetch(
        """
        SELECT ae.*, u.username
        FROM audit_events ae
        LEFT JOIN users u ON ae.user_id = u.id
        WHERE ae.timestamp >= $1 AND ae.timestamp <= $2
        ORDER BY ae.timestamp ASC
        """,
        datetime.fromisoformat(start_date),
        datetime.fromisoformat(end_date)
    )
    
    # Log the export itself
    await db.execute(
        """
        INSERT INTO audit_events (user_id, service, action, resource_type, after_state)
        VALUES ($1, 'audit-ledger', 'AUDIT_EXPORT', 'audit', $2)
        """,
        UUID(current_user.id),
        json.dumps({
            "start_date": start_date,
            "end_date": end_date,
            "event_count": len(events)
        })
    )
    
    return {
        "export": {
            "start_date": start_date,
            "end_date": end_date,
            "total_events": len(events),
            "exported_by": current_user.username,
            "exported_at": datetime.utcnow().isoformat()
        },
        "events": [
            {
                "id": str(e["id"]),
                "timestamp": e["timestamp"].isoformat(),
                "user": e["username"],
                "service": e["service"],
                "action": e["action"],
                "resource": f"{e['resource_type']}:{e['resource_id']}" if e["resource_type"] else None,
                "delta": {
                    "before": json.loads(e["before_state"]) if e["before_state"] else None,
                    "after": json.loads(e["after_state"]) if e["after_state"] else None
                }
            }
            for e in events
        ]
    }


@app.get("/audit/timeline")
async def get_activity_timeline(
    resource_type: str,
    resource_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get activity timeline for a specific resource
    """
    db = await get_db()
    
    events = await db.fetch(
        """
        SELECT ae.*, u.username
        FROM audit_events ae
        LEFT JOIN users u ON ae.user_id = u.id
        WHERE ae.resource_type = $1 AND ae.resource_id = $2
        ORDER BY ae.timestamp DESC
        LIMIT 50
        """,
        resource_type,
        resource_id
    )
    
    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "timeline": [
            {
                "timestamp": e["timestamp"].isoformat(),
                "action": e["action"],
                "user": e["username"],
                "service": e["service"],
                "changes": {
                    "before": json.loads(e["before_state"]) if e["before_state"] else None,
                    "after": json.loads(e["after_state"]) if e["after_state"] else None
                }
            }
            for e in events
        ]
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "audit-ledger", "port": SERVICE_PORT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
