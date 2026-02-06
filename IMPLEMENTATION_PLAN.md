# ATHENA v0.1.0 - Implementation Plan

## 🎯 Objective
Build a fully functional, production-grade backend control plane for a quantitative trading platform.

---

## 📁 Project Structure

```
athena/
├── docker-compose.yml
├── .env.example
├── README.md
│
├── services/
│   ├── auth-service/          (Port 7001)
│   ├── market-data-service/   (Port 7002)
│   ├── strategy-registry/     (Port 7003)
│   ├── risk-engine/           (Port 7004)
│   ├── execution-gateway/     (Port 7005)
│   ├── stress-engine/         (Port 7006)
│   └── audit-ledger/          (Port 7007)
│
├── shared/
│   ├── database/              (PostgreSQL schemas)
│   ├── redis/                 (Redis config)
│   └── common/                (Shared utilities)
│
└── frontend/
    ├── src/
    │   ├── components/
    │   ├── pages/
    │   ├── hooks/
    │   ├── services/
    │   └── store/
    └── public/
```

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | Python FastAPI |
| Database | PostgreSQL |
| Cache/Realtime | Redis |
| Event Bus | Redis Streams |
| Auth | JWT + RBAC |
| WebSockets | FastAPI WebSockets |
| Frontend | React + Vite |
| Styling | Vanilla CSS |
| Deployment | Docker Compose |

---

## 🎨 Color Palette

```css
--primary: #7B3FE4;
--secondary: #A855F7;
--background: #0B0E14;
--panel: #111827;
--danger: #DC2626;
--warning: #F59E0B;
--success: #10B981;
--text-primary: #E5E7EB;
--text-secondary: #9CA3AF;
```

---

## 📦 Phase 1: Backend Services

### 1.1 Auth Service (Port 7001)
- [x] User authentication (login)
- [x] JWT token generation
- [x] Role validation (ADMIN, QUANT, VIEWER)
- [x] Session tracking
- [x] `/login` - POST
- [x] `/me` - GET

### 1.2 Market Data Service (Port 7002)
- [x] Live market feed simulation
- [x] Normalized price snapshots
- [x] Heartbeat monitoring
- [x] Latency tracking
- [x] WebSocket: `market_ticks`
- [x] `/status` - GET
- [x] `/latency` - GET

### 1.3 Strategy Registry Service (Port 7003)
- [x] Strategy registration
- [x] Activate/deactivate strategies
- [x] Strategy metadata exposure
- [x] `/strategies/register` - POST
- [x] `/strategies/:id/activate` - POST
- [x] `/strategies/:id/halt` - POST

### 1.4 Risk Engine Service (Port 7004)
- [x] Track leverage, exposure, drawdown
- [x] Mandate breach evaluation
- [x] Real-time risk alerts via WebSocket
- [x] Kill switch functionality
- [x] `/risk/snapshot` - GET
- [x] `/risk/kill-switch` - POST
- [x] WebSocket: `risk_alerts`

### 1.5 Execution Gateway (Port 7005)
- [x] Accept trade intents
- [x] Simulate order routing
- [x] Track open orders & fills
- [x] `/orders/send` - POST
- [x] `/orders/cancel_all` - POST
- [x] `/orders/open` - GET

### 1.6 Stress Engine Service (Port 7006)
- [x] Historical stress scenarios
- [x] Synthetic stress scenarios
- [x] Impact metrics calculation
- [x] Mandate violation flagging
- [x] `/stress/run` - POST

### 1.7 Audit Ledger Service (Port 7007)
- [x] Append-only event log
- [x] Immutable action tracking
- [x] User action attribution
- [x] `/audit/events` - GET

---

## 📦 Phase 2: Frontend Dashboard

### 2.1 Dashboard Page
- [x] System status display
- [x] NAV, PnL, Sharpe metrics
- [x] Equity vs Drawdown chart
- [x] Net Exposure panel
- [x] Active strategies table
- [x] Risk alerts panel

### 2.2 Strategies Page
- [x] Strategy configuration
- [x] Backtest parameters
- [x] Equity curve visualization
- [x] Stress engine integration
- [x] RUN BACKTEST button

### 2.3 Risk Control Tower
- [x] System vitals display
- [x] Gross leverage monitoring
- [x] Mandate constraints table
- [x] Kill switch button (ADMIN only)
- [x] Adversarial stress summaries

### 2.4 Execution Page
- [x] Order entry form
- [x] Open orders table
- [x] Positions table
- [x] Cancel order functionality

### 2.5 Market Data Page
- [x] Real-time price feed
- [x] WebSocket streaming
- [x] Feed status monitoring

### 2.6 Logs Page
- [x] Audit event viewer
- [x] Filtering and search
- [x] Event details

---

## 📦 Phase 3: Integration

### 3.1 State Propagation
- [x] WebSocket connections for real-time updates
- [x] PostgreSQL snapshots every 1s
- [x] Event-driven state updates

### 3.2 Permission System
- [x] ADMIN: kill_switch, strategy_override, manual_execution
- [x] QUANT: strategy_register, parameter_update
- [x] VIEWER: read_only

### 3.3 Logging
- [x] Structured JSON logs
- [x] Immutable audit trail
- [x] User action attribution

---

## ✅ Success Criteria

1. All buttons trigger real backend calls
2. All state updates are observable in real-time
3. All actions appear in audit log
4. Kill switch works under load
5. No UI element is decorative-only

---

## 🚀 Getting Started

```bash
# Start all services
docker-compose up -d

# Or run individually
cd services/auth-service && python -m uvicorn main:app --port 7001
cd frontend && npm run dev
```
