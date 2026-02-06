"""
ATHENA Shared Pydantic Models
Common data models used across services
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field


# ========================================
# ENUMS
# ========================================

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    QUANT = "QUANT"
    VIEWER = "VIEWER"


class StrategyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    HALTED = "HALTED"
    ERROR = "ERROR"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class MandateStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    BREACH = "BREACH"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class MarketStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    STALE = "STALE"
    ERROR = "ERROR"


class ScenarioType(str, Enum):
    HISTORICAL = "HISTORICAL"
    SYNTHETIC = "SYNTHETIC"
    CUSTOM = "CUSTOM"


# ========================================
# USER MODELS
# ========================================

class UserBase(BaseModel):
    username: str
    email: str
    role: UserRole


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ========================================
# STRATEGY MODELS
# ========================================

class StrategyBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    allocation: float = 0
    risk_budget: Optional[float] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class StrategyCreate(StrategyBase):
    pass


class StrategyResponse(StrategyBase):
    id: UUID
    status: StrategyStatus
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StrategyPerformance(BaseModel):
    strategy_id: UUID
    timestamp: datetime
    pnl: float
    returns: float
    sharpe_ratio: float
    max_drawdown: float
    var_usage: float
    ytd_return: float


# ========================================
# ORDER MODELS
# ========================================

class OrderBase(BaseModel):
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None


class OrderCreate(OrderBase):
    strategy_id: Optional[UUID] = None


class OrderResponse(OrderBase):
    id: UUID
    strategy_id: Optional[UUID] = None
    status: OrderStatus
    filled_quantity: float = 0
    average_fill_price: Optional[float] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========================================
# RISK MODELS
# ========================================

class RiskSnapshot(BaseModel):
    timestamp: datetime
    net_exposure: float
    gross_exposure: float
    gross_leverage: float
    net_leverage: float
    var_95: float
    var_99: float
    max_drawdown: float
    daily_pnl: float
    sector_exposures: Dict[str, float] = Field(default_factory=dict)
    concentration_risk: float


class RiskMandate(BaseModel):
    id: UUID
    mandate_id: str
    description: str
    constraint_type: str
    soft_limit: Optional[float] = None
    hard_limit: Optional[float] = None
    current_value: Optional[float] = None
    status: MandateStatus
    is_active: bool


class RiskAlert(BaseModel):
    id: UUID
    mandate_id: Optional[UUID] = None
    severity: AlertSeverity
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    is_acknowledged: bool = False
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime


class KillSwitchRequest(BaseModel):
    reason: str
    confirm: bool = False


class KillSwitchResponse(BaseModel):
    success: bool
    orders_cancelled: int
    positions_closed: int
    message: str
    executed_at: datetime


# ========================================
# MARKET DATA MODELS
# ========================================

class MarketTick(BaseModel):
    symbol: str
    timestamp: datetime
    bid: float
    ask: float
    last_price: float
    volume: float


class MarketStatusResponse(BaseModel):
    feed_name: str
    status: MarketStatus
    latency_ms: int
    last_heartbeat: datetime
    message_count: int


class LatencyResponse(BaseModel):
    feeds: List[MarketStatusResponse]
    average_latency_ms: float
    max_latency_ms: float


# ========================================
# STRESS TEST MODELS
# ========================================

class StressScenario(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    scenario_type: ScenarioType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool


class StressRunRequest(BaseModel):
    scenario_ids: List[UUID]
    include_historical: bool = True
    custom_parameters: Optional[Dict[str, Any]] = None


class StressResult(BaseModel):
    scenario_id: UUID
    scenario_name: str
    timestamp: datetime
    portfolio_impact: float
    impact_percentage: float
    max_drawdown: float
    mandate_breaches: List[Dict[str, Any]] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class StressRunResponse(BaseModel):
    run_id: UUID
    results: List[StressResult]
    total_impact: float
    worst_case_drawdown: float
    breached_mandates: List[str]
    executed_at: datetime


# ========================================
# AUDIT MODELS
# ========================================

class AuditEvent(BaseModel):
    id: UUID
    timestamp: datetime
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    service: str
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    correlation_id: Optional[UUID] = None


class AuditQueryParams(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[UUID] = None
    service: Optional[str] = None
    action: Optional[str] = None
    limit: int = 100
    offset: int = 0


# ========================================
# SYSTEM STATE MODELS
# ========================================

class SystemStatus(BaseModel):
    status: str
    algorithms_status: str
    kill_switch_active: bool
    active_strategies: int
    open_orders: int
    net_exposure: float
    gross_leverage: float
    last_updated: datetime


class GlobalState(BaseModel):
    system_status: str
    net_exposure: float
    gross_exposure: float
    gross_leverage: float
    open_orders: int
    active_strategies: int
    nav: float
    daily_pnl: float
    sharpe_ratio: float
    max_drawdown: float
