-- ========================================
-- ATHENA Database Initialization Script
-- ========================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ========================================
-- USERS & AUTH
-- ========================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('ADMIN', 'QUANT', 'VIEWER')),
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- STRATEGIES
-- ========================================
CREATE TABLE IF NOT EXISTS strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'INACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'HALTED', 'ERROR')),
    allocation DECIMAL(20, 2) DEFAULT 0,
    risk_budget DECIMAL(10, 4),
    parameters JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS strategy_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pnl DECIMAL(20, 2),
    returns DECIMAL(10, 6),
    sharpe_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    var_usage DECIMAL(10, 4),
    ytd_return DECIMAL(10, 4)
);

-- ========================================
-- ORDERS & EXECUTION
-- ========================================
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID REFERENCES strategies(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT')),
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8),
    stop_price DECIMAL(20, 8),
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'OPEN', 'FILLED', 'PARTIAL', 'CANCELLED', 'REJECTED')),
    filled_quantity DECIMAL(20, 8) DEFAULT 0,
    average_fill_price DECIMAL(20, 8),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    commission DECIMAL(20, 8) DEFAULT 0,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- POSITIONS
-- ========================================
CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID REFERENCES strategies(id),
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    average_entry_price DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8),
    unrealized_pnl DECIMAL(20, 2),
    realized_pnl DECIMAL(20, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(strategy_id, symbol)
);

-- ========================================
-- RISK MANAGEMENT
-- ========================================
CREATE TABLE IF NOT EXISTS risk_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    net_exposure DECIMAL(20, 2),
    gross_exposure DECIMAL(20, 2),
    gross_leverage DECIMAL(10, 4),
    net_leverage DECIMAL(10, 4),
    var_95 DECIMAL(20, 2),
    var_99 DECIMAL(20, 2),
    max_drawdown DECIMAL(10, 4),
    daily_pnl DECIMAL(20, 2),
    sector_exposures JSONB DEFAULT '{}',
    concentration_risk DECIMAL(10, 4)
);

CREATE TABLE IF NOT EXISTS risk_mandates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mandate_id VARCHAR(20) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    constraint_type VARCHAR(50) NOT NULL,
    soft_limit DECIMAL(20, 8),
    hard_limit DECIMAL(20, 8),
    current_value DECIMAL(20, 8),
    status VARCHAR(20) DEFAULT 'OK' CHECK (status IN ('OK', 'WARNING', 'BREACH')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS risk_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mandate_id UUID REFERENCES risk_mandates(id),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL')),
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}',
    is_acknowledged BOOLEAN DEFAULT false,
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- MARKET DATA
-- ========================================
CREATE TABLE IF NOT EXISTS market_instruments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    asset_class VARCHAR(50),
    exchange VARCHAR(50),
    currency VARCHAR(10) DEFAULT 'USD',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_prices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bid DECIMAL(20, 8),
    ask DECIMAL(20, 8),
    last_price DECIMAL(20, 8),
    volume DECIMAL(20, 2),
    UNIQUE(symbol, timestamp)
);

CREATE TABLE IF NOT EXISTS market_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feed_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'CONNECTED' CHECK (status IN ('CONNECTED', 'DISCONNECTED', 'STALE', 'ERROR')),
    latency_ms INTEGER,
    last_heartbeat TIMESTAMP,
    message_count BIGINT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- STRESS TESTING
-- ========================================
CREATE TABLE IF NOT EXISTS stress_scenarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    scenario_type VARCHAR(50) NOT NULL CHECK (scenario_type IN ('HISTORICAL', 'SYNTHETIC', 'CUSTOM')),
    parameters JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stress_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scenario_id UUID REFERENCES stress_scenarios(id),
    run_by UUID REFERENCES users(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    portfolio_impact DECIMAL(20, 2),
    impact_percentage DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    mandate_breaches JSONB DEFAULT '[]',
    details JSONB DEFAULT '{}'
);

-- ========================================
-- AUDIT LEDGER
-- ========================================
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id UUID REFERENCES users(id),
    service VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    before_state JSONB,
    after_state JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    correlation_id UUID
);

-- Create index for audit queries
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_service ON audit_events(service);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action);

-- ========================================
-- SYSTEM STATE
-- ========================================
CREATE TABLE IF NOT EXISTS system_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- INITIAL DATA SEEDING
-- ========================================

-- Default Admin User (password: admin123)
INSERT INTO users (username, email, password_hash, role) VALUES 
('admin', 'admin@athena.io', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.HJyJjC3m8YzKTC', 'ADMIN'),
('quant_user', 'quant@athena.io', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.HJyJjC3m8YzKTC', 'QUANT'),
('viewer', 'viewer@athena.io', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.HJyJjC3m8YzKTC', 'VIEWER')
ON CONFLICT (username) DO NOTHING;

-- Default Strategies
INSERT INTO strategies (name, description, type, status, allocation, risk_budget, parameters) VALUES 
('Equities L/S Neutral', 'Long/short equity market neutral strategy', 'EQUITY_LS', 'ACTIVE', 45200000, 0.15, '{"lookback": 14, "vol_scalar": 0.85}'),
('Vol Arb (VIX)', 'Volatility arbitrage focusing on VIX instruments', 'VOL_ARB', 'ACTIVE', 22800000, 0.10, '{"threshold": 2.5}'),
('Momentum Crypto', 'Crypto momentum strategy', 'MOMENTUM', 'HALTED', 0, 0.05, '{"window": 7}')
ON CONFLICT DO NOTHING;

-- Default Risk Mandates
INSERT INTO risk_mandates (mandate_id, description, constraint_type, soft_limit, hard_limit, current_value, status) VALUES 
('M-204', 'Max Drawdown (Daily)', 'DRAWDOWN', -0.025, -0.030, -0.028, 'WARNING'),
('M-101', 'Sector Exposure: Tech', 'SECTOR_EXPOSURE', 0.12, 0.15, 0.145, 'OK'),
('M-502', 'Liquidity < 1 Day', 'LIQUIDITY', 0.85, 0.90, 0.88, 'BREACH'),
('M-330', 'Gross Exposure', 'GROSS_EXPOSURE', 4500000000, 5000000000, 4200000000, 'OK'),
('M-009', 'Overnight Margin', 'MARGIN', 375000000, 400000000, 350000000, 'OK')
ON CONFLICT (mandate_id) DO NOTHING;

-- Market Instruments
INSERT INTO market_instruments (symbol, name, asset_class, exchange, currency) VALUES 
('AAPL', 'Apple Inc.', 'EQUITY', 'NASDAQ', 'USD'),
('GOOGL', 'Alphabet Inc.', 'EQUITY', 'NASDAQ', 'USD'),
('MSFT', 'Microsoft Corp.', 'EQUITY', 'NASDAQ', 'USD'),
('TSLA', 'Tesla Inc.', 'EQUITY', 'NASDAQ', 'USD'),
('SPY', 'SPDR S&P 500 ETF', 'ETF', 'NYSE', 'USD'),
('VIX', 'CBOE Volatility Index', 'INDEX', 'CBOE', 'USD'),
('BTC-USD', 'Bitcoin USD', 'CRYPTO', 'BINANCE', 'USD'),
('ETH-USD', 'Ethereum USD', 'CRYPTO', 'BINANCE', 'USD')
ON CONFLICT (symbol) DO NOTHING;

-- Stress Scenarios
INSERT INTO stress_scenarios (name, description, scenario_type, parameters) VALUES 
('Black Monday Repeat', '1987-style market crash simulation', 'HISTORICAL', '{"drawdown": -0.22, "duration_days": 1}'),
('Fed Rate Shock (+100bps)', 'Sudden 100bps rate hike', 'SYNTHETIC', '{"rate_change": 0.01, "duration_days": 5}'),
('Crypto Flash Crash', 'Crypto market flash crash', 'HISTORICAL', '{"drawdown": -0.40, "asset_class": "CRYPTO"}'),
('Covid-19 Crash', 'March 2020 volatility scenario', 'HISTORICAL', '{"vol_spike": 80, "drawdown": -0.34}'),
('2008 GFC', 'Lehman default event simulation', 'HISTORICAL', '{"drawdown": -0.50, "duration_days": 30}'),
('Liquidity Collapse', 'Market liquidity dries up scenario', 'SYNTHETIC', '{"bid_ask_spread_multiplier": 3}'),
('Rate Hike Cycle', '+50bps parallel shift', 'SYNTHETIC', '{"rate_change": 0.005, "duration_days": 90}')
ON CONFLICT DO NOTHING;

-- Initial System State
INSERT INTO system_state (key, value) VALUES 
('system_status', '"OPERATIONAL"'),
('algorithms_status', '"ACTIVE"'),
('kill_switch_active', 'false'),
('last_risk_check', 'null')
ON CONFLICT (key) DO NOTHING;

-- Create update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON strategies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_risk_mandates_updated_at BEFORE UPDATE ON risk_mandates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
