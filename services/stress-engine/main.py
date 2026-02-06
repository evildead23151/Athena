"""
ATHENA Stress Engine Service
Port: 7006
Handles stress testing, scenario simulation, and impact analysis
"""
import os
import sys
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
from common.auth import verify_token, get_current_user, UserContext
from common.logging import get_logger
from common.models import (
    StressScenario, StressRunRequest, StressResult, StressRunResponse, ScenarioType
)

app = FastAPI(
    title="ATHENA Stress Engine Service",
    description="Stress testing and scenario analysis",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = get_logger("stress-engine")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "7006"))


# Scenario impact models (simplified)
SCENARIO_IMPACTS = {
    "Black Monday Repeat": {"impact_pct": -0.124, "drawdown": -0.22, "duration": "1 day"},
    "Fed Rate Shock (+100bps)": {"impact_pct": -0.041, "drawdown": -0.08, "duration": "5 days"},
    "Crypto Flash Crash": {"impact_pct": 0.012, "drawdown": -0.05, "duration": "1 day"},
    "Covid-19 Crash": {"impact_pct": -0.182, "drawdown": -0.34, "duration": "30 days"},
    "2008 GFC": {"impact_pct": -0.312, "drawdown": -0.50, "duration": "120 days"},
    "Liquidity Collapse": {"impact_pct": -0.067, "drawdown": -0.12, "duration": "7 days"},
    "Rate Hike Cycle": {"impact_pct": -0.089, "drawdown": -0.15, "duration": "90 days"}
}


async def log_audit(db: Database, user_id: str, action: str, resource_type: str = None,
                    resource_id: str = None, before: dict = None, after: dict = None):
    await db.execute(
        """
        INSERT INTO audit_events (user_id, service, action, resource_type, resource_id, before_state, after_state)
        VALUES ($1, 'stress-engine', $2, $3, $4, $5, $6)
        """,
        UUID(user_id) if user_id else None, action, resource_type, resource_id,
        json.dumps(before) if before else None,
        json.dumps(after) if after else None
    )


def simulate_scenario_impact(scenario_name: str, portfolio_value: float, mandates: list) -> dict:
    """Simulate the impact of a stress scenario"""
    base_impact = SCENARIO_IMPACTS.get(scenario_name, {"impact_pct": -0.05, "drawdown": -0.10})
    
    # Add some randomness
    impact_pct = base_impact["impact_pct"] * (1 + random.uniform(-0.1, 0.1))
    drawdown = base_impact["drawdown"] * (1 + random.uniform(-0.1, 0.1))
    
    portfolio_impact = portfolio_value * impact_pct
    
    # Check mandate breaches
    breaches = []
    for mandate in mandates:
        hard_limit = float(mandate["hard_limit"]) if mandate["hard_limit"] else None
        if hard_limit:
            # Simulate if drawdown would breach mandate
            if mandate["constraint_type"] == "DRAWDOWN":
                if drawdown < hard_limit:
                    breaches.append({
                        "mandate_id": mandate["mandate_id"],
                        "description": mandate["description"],
                        "limit": hard_limit,
                        "projected_value": drawdown,
                        "breach_amount": drawdown - hard_limit
                    })
    
    return {
        "impact_pct": impact_pct,
        "portfolio_impact": portfolio_impact,
        "max_drawdown": drawdown,
        "mandate_breaches": breaches,
        "duration": base_impact.get("duration", "Unknown")
    }


@app.on_event("startup")
async def startup():
    logger.info("Stress Engine Service starting up...")
    await init_db()
    await init_redis()
    logger.info(f"Stress Engine Service running on port {SERVICE_PORT}")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Stress Engine Service shutting down...")
    await close_db()
    await close_redis()


# ========================================
# ENDPOINTS
# ========================================

@app.get("/scenarios")
async def list_scenarios(current_user: UserContext = Depends(get_current_user)):
    """
    List all available stress scenarios
    """
    db = await get_db()
    
    scenarios = await db.fetch(
        "SELECT * FROM stress_scenarios WHERE is_active = true ORDER BY name"
    )
    
    return {
        "scenarios": [
            {
                "id": str(s["id"]),
                "name": s["name"],
                "description": s["description"],
                "type": s["scenario_type"],
                "parameters": s["parameters"],
                "expected_impact": SCENARIO_IMPACTS.get(s["name"], {}).get("impact_pct", "Unknown")
            }
            for s in scenarios
        ],
        "count": len(scenarios)
    }


@app.post("/stress/run", response_model=StressRunResponse)
async def run_stress_test(
    request: StressRunRequest,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Run stress test with selected scenarios
    Returns impact metrics and mandate breach analysis
    """
    db = await get_db()
    redis = await get_redis()
    
    run_id = uuid4()
    
    logger.info(f"Stress test initiated: {len(request.scenario_ids)} scenarios", 
                user_id=current_user.id, action="STRESS_RUN")
    
    # Get current portfolio value (from strategies allocation)
    portfolio_value = await db.fetchval(
        "SELECT COALESCE(SUM(allocation), 0) FROM strategies WHERE status = 'ACTIVE'"
    )
    portfolio_value = float(portfolio_value) if portfolio_value else 142500231  # Default from mockup
    
    # Get mandates for breach checking
    mandates = await db.fetch(
        "SELECT * FROM risk_mandates WHERE is_active = true"
    )
    
    results = []
    total_impact = 0
    worst_drawdown = 0
    all_breaches = []
    
    # Process each scenario
    for scenario_id in request.scenario_ids:
        scenario = await db.fetchrow(
            "SELECT * FROM stress_scenarios WHERE id = $1",
            scenario_id
        )
        
        if not scenario:
            continue
        
        # Simulate impact
        impact = simulate_scenario_impact(scenario["name"], portfolio_value, mandates)
        
        # Store result
        result_id = await db.fetchval(
            """
            INSERT INTO stress_results 
            (scenario_id, run_by, portfolio_impact, impact_percentage, max_drawdown, mandate_breaches, details)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            scenario_id,
            UUID(current_user.id),
            impact["portfolio_impact"],
            impact["impact_pct"],
            impact["max_drawdown"],
            json.dumps(impact["mandate_breaches"]),
            json.dumps({
                "duration": impact["duration"],
                "custom_params": request.custom_parameters
            })
        )
        
        results.append(StressResult(
            scenario_id=scenario_id,
            scenario_name=scenario["name"],
            timestamp=datetime.utcnow(),
            portfolio_impact=impact["portfolio_impact"],
            impact_percentage=impact["impact_pct"],
            max_drawdown=impact["max_drawdown"],
            mandate_breaches=impact["mandate_breaches"],
            details={"duration": impact["duration"]}
        ))
        
        total_impact += impact["portfolio_impact"]
        worst_drawdown = min(worst_drawdown, impact["max_drawdown"])
        all_breaches.extend([b["mandate_id"] for b in impact["mandate_breaches"]])
    
    # Log audit
    await log_audit(
        db, current_user.id, "STRESS_RUN", "stress_test", str(run_id),
        after={
            "scenarios_run": len(results),
            "total_impact": total_impact,
            "worst_drawdown": worst_drawdown,
            "breaches": list(set(all_breaches))
        }
    )
    
    # Store summary in Redis for quick access
    await redis.set_json(f"stress:run:{run_id}", {
        "run_id": str(run_id),
        "scenarios": len(results),
        "total_impact": total_impact,
        "worst_drawdown": worst_drawdown,
        "timestamp": datetime.utcnow().isoformat()
    }, ex=3600)
    
    return StressRunResponse(
        run_id=run_id,
        results=results,
        total_impact=total_impact,
        worst_case_drawdown=worst_drawdown,
        breached_mandates=list(set(all_breaches)),
        executed_at=datetime.utcnow()
    )


@app.get("/stress/history")
async def get_stress_history(
    limit: int = 20,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get stress test history
    """
    db = await get_db()
    
    results = await db.fetch(
        """
        SELECT sr.*, ss.name as scenario_name, u.username as run_by_name
        FROM stress_results sr
        JOIN stress_scenarios ss ON sr.scenario_id = ss.id
        LEFT JOIN users u ON sr.run_by = u.id
        ORDER BY sr.timestamp DESC
        LIMIT $1
        """,
        limit
    )
    
    return {
        "results": [
            {
                "id": str(r["id"]),
                "scenario_name": r["scenario_name"],
                "portfolio_impact": float(r["portfolio_impact"]) if r["portfolio_impact"] else 0,
                "impact_percentage": float(r["impact_percentage"]) if r["impact_percentage"] else 0,
                "max_drawdown": float(r["max_drawdown"]) if r["max_drawdown"] else 0,
                "mandate_breaches": r["mandate_breaches"],
                "run_by": r["run_by_name"],
                "timestamp": r["timestamp"].isoformat()
            }
            for r in results
        ],
        "count": len(results)
    }


@app.post("/scenarios/create")
async def create_scenario(
    name: str,
    description: str,
    scenario_type: str,
    parameters: dict,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Create custom stress scenario
    Requires: ADMIN or QUANT role
    """
    if current_user.role == "VIEWER":
        raise HTTPException(status_code=403, detail="Viewers cannot create scenarios")
    
    db = await get_db()
    
    result = await db.fetchrow(
        """
        INSERT INTO stress_scenarios (name, description, scenario_type, parameters)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        name, description, scenario_type, json.dumps(parameters)
    )
    
    await log_audit(
        db, current_user.id, "SCENARIO_CREATE", "scenario", str(result["id"]),
        after={"name": name, "type": scenario_type}
    )
    
    return {
        "success": True,
        "scenario_id": str(result["id"]),
        "name": name
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "stress-engine", "port": SERVICE_PORT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
