"""
ATHENA Database Connection Manager
PostgreSQL connection pooling and utilities
"""
import os
import asyncpg
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://athena:athena_secret_2024@localhost:5432/athena_db")


class Database:
    """Async PostgreSQL database connection pool manager"""
    
    def __init__(self, dsn: str = None):
        self.dsn = dsn or DATABASE_URL
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Initialize database connection pool"""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
    
    async def disconnect(self):
        """Close all database connections"""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    async def execute(self, query: str, *args):
        """Execute a query without returning results"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """Execute a query and return all results"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """Execute a query and return single row"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Execute a query and return single value"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactions"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn


# Global database instance
_db: Optional[Database] = None


async def get_db() -> Database:
    """Get or create database instance"""
    global _db
    if _db is None:
        _db = Database()
        await _db.connect()
    return _db


async def init_db():
    """Initialize database on startup"""
    db = await get_db()
    return db


async def close_db():
    """Close database on shutdown"""
    global _db
    if _db:
        await _db.disconnect()
        _db = None
