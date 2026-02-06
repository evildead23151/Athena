"""
ATHENA Auth Service
Port: 7001
Handles authentication, JWT tokens, and role validation
"""
import os
import sys
from datetime import datetime
from typing import Optional
from uuid import UUID

# Add shared modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import bcrypt

# Import shared utilities
from common.database import Database, get_db, init_db, close_db
from common.redis_client import RedisClient, get_redis, init_redis, close_redis
from common.auth import create_token, verify_token, get_current_user, UserContext
from common.logging import get_logger
from common.models import (
    UserRole, LoginRequest, LoginResponse, UserResponse, UserCreate
)

# Initialize app
app = FastAPI(
    title="ATHENA Auth Service",
    description="Authentication and authorization service",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logger
logger = get_logger("auth-service")

# Service port
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "7001"))


# ========================================
# LIFECYCLE EVENTS
# ========================================

@app.on_event("startup")
async def startup():
    """Initialize connections on startup"""
    logger.info("Auth Service starting up...")
    await init_db()
    await init_redis()
    logger.info(f"Auth Service running on port {SERVICE_PORT}")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    logger.info("Auth Service shutting down...")
    await close_db()
    await close_redis()


# ========================================
# HELPER FUNCTIONS
# ========================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def hash_password(password: str) -> str:
    """Hash password"""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


async def log_audit_event(
    db: Database,
    user_id: str,
    action: str,
    service: str = "auth-service",
    before_state: dict = None,
    after_state: dict = None,
    ip_address: str = None
):
    """Log audit event to database"""
    await db.execute(
        """
        INSERT INTO audit_events (user_id, service, action, before_state, after_state, ip_address)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        UUID(user_id) if user_id else None,
        service,
        action,
        before_state,
        after_state,
        ip_address
    )


# ========================================
# ENDPOINTS
# ========================================

@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, req: Request):
    """
    Authenticate user and return JWT token
    """
    db = await get_db()
    redis = await get_redis()
    
    # Fetch user
    user = await db.fetchrow(
        """
        SELECT id, username, email, password_hash, role, is_active, last_login, created_at
        FROM users
        WHERE username = $1 OR email = $1
        """,
        request.username
    )
    
    if not user:
        logger.warning(f"Login failed: User not found - {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not user['is_active']:
        logger.warning(f"Login failed: User inactive - {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )
    
    # Verify password
    if not verify_password(request.password, user['password_hash']):
        logger.warning(f"Login failed: Invalid password - {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Generate token
    token = create_token(
        user_id=str(user['id']),
        username=user['username'],
        email=user['email'],
        role=user['role']
    )
    
    # Update last login
    await db.execute(
        "UPDATE users SET last_login = $1 WHERE id = $2",
        datetime.utcnow(),
        user['id']
    )
    
    # Store session in Redis
    await redis.set_json(
        f"session:{str(user['id'])}",
        {
            "username": user['username'],
            "role": user['role'],
            "login_time": datetime.utcnow().isoformat(),
            "ip_address": req.client.host if req.client else None
        },
        ex=86400  # 24 hours
    )
    
    # Log audit event
    await log_audit_event(
        db,
        user_id=str(user['id']),
        action="LOGIN",
        after_state={"username": user['username'], "role": user['role']},
        ip_address=req.client.host if req.client else None
    )
    
    logger.info(f"User logged in successfully", user_id=str(user['id']), action="LOGIN")
    
    return LoginResponse(
        access_token=token,
        user=UserResponse(
            id=user['id'],
            username=user['username'],
            email=user['email'],
            role=UserRole(user['role']),
            is_active=user['is_active'],
            last_login=user['last_login'],
            created_at=user['created_at']
        )
    )


@app.get("/me", response_model=UserResponse)
async def get_me(current_user: UserContext = Depends(get_current_user)):
    """
    Get current authenticated user details
    """
    db = await get_db()
    
    user = await db.fetchrow(
        """
        SELECT id, username, email, role, is_active, last_login, created_at
        FROM users
        WHERE id = $1
        """,
        UUID(current_user.id)
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user['id'],
        username=user['username'],
        email=user['email'],
        role=UserRole(user['role']),
        is_active=user['is_active'],
        last_login=user['last_login'],
        created_at=user['created_at']
    )


@app.post("/logout")
async def logout(current_user: UserContext = Depends(get_current_user)):
    """
    Logout current user and invalidate session
    """
    db = await get_db()
    redis = await get_redis()
    
    # Remove session from Redis
    await redis.delete(f"session:{current_user.id}")
    
    # Log audit event
    await log_audit_event(
        db,
        user_id=current_user.id,
        action="LOGOUT"
    )
    
    logger.info("User logged out", user_id=current_user.id, action="LOGOUT")
    
    return {"message": "Logged out successfully"}


@app.get("/sessions/active")
async def get_active_sessions(current_user: UserContext = Depends(get_current_user)):
    """
    Get all active sessions (admin only)
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    db = await get_db()
    
    sessions = await db.fetch(
        """
        SELECT u.id, u.username, u.role, u.last_login
        FROM users u
        WHERE u.is_active = true AND u.last_login > NOW() - INTERVAL '24 hours'
        ORDER BY u.last_login DESC
        """
    )
    
    return {
        "active_sessions": [
            {
                "user_id": str(s['id']),
                "username": s['username'],
                "role": s['role'],
                "last_login": s['last_login'].isoformat() if s['last_login'] else None
            }
            for s in sessions
        ],
        "total": len(sessions)
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth-service", "port": SERVICE_PORT}


# ========================================
# RUN SERVER
# ========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
