"""
ATHENA Authentication & Authorization
JWT token handling and RBAC
"""
import os
from datetime import datetime, timedelta
from typing import Optional, List
from functools import wraps

import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

JWT_SECRET = os.getenv("JWT_SECRET", "athena_jwt_secret_key_2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

security = HTTPBearer()


class TokenPayload(BaseModel):
    """JWT Token payload structure"""
    user_id: str
    username: str
    email: str
    role: str
    exp: datetime
    iat: datetime


class UserContext(BaseModel):
    """Current user context"""
    id: str
    username: str
    email: str
    role: str


# Role hierarchy and permissions
ROLE_PERMISSIONS = {
    "ADMIN": [
        "kill_switch",
        "strategy_override",
        "manual_execution",
        "strategy_register",
        "parameter_update",
        "read_only",
        "view_audit",
        "manage_users"
    ],
    "QUANT": [
        "strategy_register",
        "parameter_update",
        "read_only",
        "view_audit"
    ],
    "VIEWER": [
        "read_only"
    ]
}


def create_token(user_id: str, username: str, email: str, role: str) -> str:
    """Create JWT token for user"""
    now = datetime.utcnow()
    payload = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRY_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenPayload:
    """FastAPI dependency to verify JWT token"""
    return decode_token(credentials.credentials)


async def get_current_user(token: TokenPayload = Depends(verify_token)) -> UserContext:
    """Get current authenticated user from token"""
    return UserContext(
        id=token.user_id,
        username=token.username,
        email=token.email,
        role=token.role
    )


def has_permission(role: str, permission: str) -> bool:
    """Check if role has specific permission"""
    permissions = ROLE_PERMISSIONS.get(role, [])
    return permission in permissions


def require_role(allowed_roles: List[str]):
    """Decorator to require specific roles"""
    async def dependency(user: UserContext = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}"
            )
        return user
    return dependency


def require_permission(permission: str):
    """Decorator to require specific permission"""
    async def dependency(user: UserContext = Depends(get_current_user)):
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing permission: {permission}"
            )
        return user
    return dependency


class AuthMiddleware:
    """Middleware for authentication context"""
    
    @staticmethod
    def extract_user_from_token(token: str) -> Optional[UserContext]:
        """Extract user from token without raising exceptions"""
        try:
            payload = decode_token(token)
            return UserContext(
                id=payload.user_id,
                username=payload.username,
                email=payload.email,
                role=payload.role
            )
        except:
            return None
