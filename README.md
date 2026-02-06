# 🏛️ ATHENA - Quantitative Trading Control Plane

A production-grade backend control plane for a quantitative trading platform with real-time monitoring, risk management, and strategy execution.

![ATHENA Dashboard](./docs/dashboard-preview.png)

## 🚀 Quick Start

### Option 1: Demo Mode (No Backend Required)

The frontend includes a mock mode that simulates all backend functionality:

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:3000 and login with:
- **Username**: `admin`
- **Password**: `admin123`

### Option 2: Full Stack with Docker

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- All 7 microservices (ports 7001-7007)
- Frontend (port 3000)

## 📁 Project Structure

```
athena/
├── docker-compose.yml       # Orchestration
├── .env                     # Environment config
│
├── services/
│   ├── auth-service/        # JWT Auth (7001)
│   ├── market-data-service/ # Market Feed (7002)
│   ├── strategy-registry/   # Strategy Mgmt (7003)
│   ├── risk-engine/         # Risk Monitor (7004)
│   ├── execution-gateway/   # Order Routing (7005)
│   ├── stress-engine/       # Stress Testing (7006)
│   └── audit-ledger/        # Audit Trail (7007)
│
├── shared/
│   ├── database/            # PostgreSQL init
│   └── common/              # Shared utilities
│
└── frontend/
    └── src/
        ├── components/      # React components
        ├── pages/           # Dashboard pages
        ├── services/        # API & mock data
        └── store/           # Zustand stores
```

## 🎨 Features

### Dashboard
- Real-time NAV, P&L, and Sharpe metrics
- Equity curve visualization
- Net exposure gauge
- Active strategies with live stats
- Risk alerts panel

### Strategies
- Backtest configuration
- Stress scenario testing
- Equity vs Drawdown charts
- Parameter tuning

### Risk Control Tower
- System vitals monitoring
- Mandate constraint tracking
- Kill switch (ADMIN only)
- Adversarial stress summaries

### Execution
- Order entry (Market/Limit/Stop)
- Open orders management
- Position tracking
- Cancel all functionality

### Market Data
- Real-time price streaming
- Feed latency monitoring
- WebSocket connection status

### Audit Logs
- Immutable event log
- Filtering by service/action
- Timeline visualization

## 🔒 User Roles

| Role | Permissions |
|------|-------------|
| ADMIN | Full access, kill switch, strategy override |
| QUANT | Strategy registration, parameter updates |
| VIEWER | Read-only access to all dashboards |

## 🔧 Configuration

Edit `.env` to customize:

```env
# JWT Secret (change in production!)
JWT_SECRET=your-production-secret

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis
REDIS_URL=redis://localhost:6379
```

## 📡 API Endpoints

| Service | Port | Key Endpoints |
|---------|------|---------------|
| Auth | 7001 | `POST /login`, `GET /me` |
| Market | 7002 | `GET /prices`, `WS /ws` |
| Strategy | 7003 | `GET /strategies`, `POST /activate` |
| Risk | 7004 | `GET /snapshot`, `POST /kill-switch` |
| Execution | 7005 | `POST /orders/send`, `GET /positions` |
| Stress | 7006 | `POST /stress/run`, `GET /scenarios` |
| Audit | 7007 | `GET /events`, `GET /timeline` |

## 🛠️ Development

### Run Services Individually

```bash
# Backend service
cd services/auth-service
pip install -r requirements.txt
python -m uvicorn main:app --port 7001 --reload

# Frontend
cd frontend
npm run dev
```

### Switch from Mock to Real API

Edit `frontend/src/services/api.js`:

```javascript
const MOCK_MODE = false; // Change to false for real API
```

## 📦 Tech Stack

- **Backend**: Python FastAPI
- **Database**: PostgreSQL
- **Cache**: Redis
- **Frontend**: React + Vite
- **Styling**: Vanilla CSS
- **State**: Zustand
- **Charts**: Recharts
- **Auth**: JWT + RBAC

## 🎯 Success Criteria

- ✅ All buttons trigger real backend calls (or mocks)
- ✅ All state updates are observable in real-time
- ✅ All actions appear in audit log
- ✅ Kill switch works under load
- ✅ No UI element is decorative-only

## 📄 License

MIT License - See LICENSE file for details.
