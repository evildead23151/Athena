// Mock data for standalone frontend testing
export const mockUser = {
    id: '550e8400-e29b-41d4-a716-446655440001',
    username: 'admin',
    email: 'admin@athena.io',
    role: 'ADMIN',
    full_name: 'System Administrator'
};

export const mockStrategies = [
    { id: 'strat-001', name: 'Equities L/S Neutral', status: 'ACTIVE', allocation: 45200000, returns_1d: 1.24, returns_ytd: 14.2 },
    { id: 'strat-002', name: 'Vol Arb (VIX)', status: 'ACTIVE', allocation: 22800000, returns_1d: 0.82, returns_ytd: 8.5 },
    { id: 'strat-003', name: 'Momentum Crypto', status: 'HALTED', allocation: 0, returns_1d: 0, returns_ytd: -2.1 },
    { id: 'strat-004', name: 'StatArb Pairs', status: 'ACTIVE', allocation: 31500000, returns_1d: 0.45, returns_ytd: 11.3 }
];

export const mockPrices = {
    'AAPL': { symbol: 'AAPL', bid: 185.42, ask: 185.48, last_price: 185.45, volume: 45231000, timestamp: new Date().toISOString() },
    'GOOGL': { symbol: 'GOOGL', bid: 141.72, ask: 141.85, last_price: 141.78, volume: 12450000, timestamp: new Date().toISOString() },
    'MSFT': { symbol: 'MSFT', bid: 402.15, ask: 402.35, last_price: 402.25, volume: 21340000, timestamp: new Date().toISOString() },
    'TSLA': { symbol: 'TSLA', bid: 248.80, ask: 249.10, last_price: 248.95, volume: 89120000, timestamp: new Date().toISOString() },
    'SPY': { symbol: 'SPY', bid: 495.10, ask: 495.15, last_price: 495.12, volume: 156780000, timestamp: new Date().toISOString() },
    'BTC-USD': { symbol: 'BTC-USD', bid: 62480, ask: 62520, last_price: 62500, volume: 1245670000, timestamp: new Date().toISOString() }
};

export const mockMandates = [
    { mandate_id: 'M-204', description: 'Max Drawdown (Daily)', current_value: -0.028, hard_limit: -0.03, status: 'WARNING', constraint_type: 'DRAWDOWN' },
    { mandate_id: 'M-101', description: 'Sector Exposure: Tech', current_value: 0.145, hard_limit: 0.15, status: 'OK', constraint_type: 'SECTOR_EXPOSURE' },
    { mandate_id: 'M-502', description: 'Liquidity < 1 Day', current_value: 0.88, hard_limit: 0.90, status: 'OK', constraint_type: 'LIQUIDITY' },
    { mandate_id: 'M-330', description: 'Gross Exposure', current_value: 4200000000, hard_limit: 5000000000, status: 'OK', constraint_type: 'GROSS_EXPOSURE' }
];

export const mockOrders = [
    { id: 'ord-001', symbol: 'AAPL', side: 'BUY', type: 'LIMIT', quantity: 500, filled_quantity: 250, price: 185.00, status: 'PARTIAL', created_at: new Date().toISOString() },
    { id: 'ord-002', symbol: 'TSLA', side: 'SELL', type: 'MARKET', quantity: 100, filled_quantity: 0, price: null, status: 'PENDING', created_at: new Date().toISOString() }
];

export const mockPositions = [
    { id: 'pos-001', symbol: 'AAPL', quantity: 1500, entry_price: 178.50, current_price: 185.45, unrealized_pnl: 10425, strategy_name: 'Equities L/S Neutral' },
    { id: 'pos-002', symbol: 'GOOGL', quantity: -800, entry_price: 145.20, current_price: 141.78, unrealized_pnl: 2736, strategy_name: 'Equities L/S Neutral' },
    { id: 'pos-003', symbol: 'MSFT', quantity: 600, entry_price: 395.00, current_price: 402.25, unrealized_pnl: 4350, strategy_name: 'StatArb Pairs' }
];

export const mockAuditEvents = [
    { id: '1', timestamp: new Date(Date.now() - 60000).toISOString(), username: 'admin', service: 'auth-service', action: 'LOGIN_SUCCESS', resource_type: 'session' },
    { id: '2', timestamp: new Date(Date.now() - 120000).toISOString(), username: 'quant_1', service: 'strategy-registry', action: 'STRATEGY_ACTIVATE', resource_type: 'strategy', resource_id: 'strat-001' },
    { id: '3', timestamp: new Date(Date.now() - 180000).toISOString(), username: 'risk_mgr', service: 'risk-engine', action: 'MANDATE_UPDATE', resource_type: 'mandate', resource_id: 'M-204' },
    { id: '4', timestamp: new Date(Date.now() - 240000).toISOString(), username: 'admin', service: 'execution-gateway', action: 'ORDER_SUBMIT', resource_type: 'order', resource_id: 'ord-001' }
];

export const mockScenarios = [
    { id: 'sc-001', name: 'Black Monday Repeat', description: 'Simulates Oct 1987 crash', type: 'HISTORICAL', expected_impact: -0.124 },
    { id: 'sc-002', name: 'Fed Rate Shock (+100bps)', description: 'Sudden rate increase', type: 'SYNTHETIC', expected_impact: -0.041 },
    { id: 'sc-003', name: 'Covid-19 Crash', description: 'Mar 2020 volatility spike', type: 'HISTORICAL', expected_impact: -0.182 },
    { id: 'sc-004', name: 'Liquidity Collapse', description: 'Flash crash scenario', type: 'SYNTHETIC', expected_impact: -0.067 }
];

// Simulate price updates
export const simulatePriceUpdate = (prices) => {
    const updated = { ...prices };
    Object.keys(updated).forEach(symbol => {
        const data = updated[symbol];
        const change = (Math.random() - 0.5) * 0.002 * data.last_price;
        data.last_price = Math.max(0.01, data.last_price + change);
        data.bid = data.last_price * 0.9998;
        data.ask = data.last_price * 1.0002;
        data.timestamp = new Date().toISOString();
    });
    return updated;
};
