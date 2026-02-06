import axios from 'axios';
import {
    mockUser, mockStrategies, mockPrices, mockMandates,
    mockOrders, mockPositions, mockAuditEvents, mockScenarios, simulatePriceUpdate
} from './mockData';

// Enable mock mode when backend is unavailable
const MOCK_MODE = true; // Set to false when backend services are running

// Create axios instance with defaults
const axiosInstance = axios.create({
    timeout: 5000,
    headers: { 'Content-Type': 'application/json' }
});

// Request interceptor to add auth token
axiosInstance.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('athena_token');
        if (token) config.headers.Authorization = `Bearer ${token}`;
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor for error handling
axiosInstance.interceptors.response.use(
    (response) => response.data,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('athena_token');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

// API endpoints
const API_URLS = {
    auth: 'http://localhost:7001',
    market: 'http://localhost:7002',
    strategy: 'http://localhost:7003',
    risk: 'http://localhost:7004',
    execution: 'http://localhost:7005',
    stress: 'http://localhost:7006',
    audit: 'http://localhost:7007'
};

// Helper for mock delay
const mockDelay = (ms = 300) => new Promise(resolve => setTimeout(resolve, ms));

// Mock API implementation
const mockApi = {
    auth: {
        login: async (username, password) => {
            await mockDelay(500);
            if (username === 'admin' && password === 'admin123') {
                const token = 'mock_jwt_token_' + Date.now();
                return { access_token: token, user: mockUser };
            }
            throw { response: { data: { detail: 'Invalid credentials' } } };
        },
        me: async () => { await mockDelay(); return mockUser; },
        logout: async () => { await mockDelay(); return { success: true }; }
    },
    market: {
        getStatus: async () => ({ status: 'CONNECTED', feeds: 3, uptime: '99.99%' }),
        getLatency: async () => ({
            average_latency_ms: 12,
            feeds: [
                { feed_name: 'BLOOMBERG_L1', status: 'CONNECTED', latency_ms: 12, message_count: 1284523 },
                { feed_name: 'REFINITIV', status: 'CONNECTED', latency_ms: 8, message_count: 892341 }
            ]
        }),
        getPrices: async () => ({ prices: mockPrices }),
        getPrice: async (symbol) => mockPrices[symbol] || null,
        getSymbols: async () => ({ symbols: Object.keys(mockPrices) })
    },
    strategy: {
        list: async () => ({ strategies: mockStrategies, active_count: mockStrategies.filter(s => s.status === 'ACTIVE').length }),
        get: async (id) => mockStrategies.find(s => s.id === id),
        register: async (data) => ({ success: true, id: 'strat-new-' + Date.now(), ...data }),
        activate: async (id) => { await mockDelay(); return { success: true, id, status: 'ACTIVE' }; },
        halt: async (id) => { await mockDelay(); return { success: true, id, status: 'HALTED' }; },
        updateParameters: async (id, params) => ({ success: true, id, parameters: params })
    },
    risk: {
        getSnapshot: async () => ({
            snapshot: { net_exposure: 3100000, gross_exposure: 4200000000, gross_leverage: 4.2, max_drawdown: -0.042 },
            mandates: mockMandates,
            active_alerts: [{ id: 'alert-1', message: 'Strategy approaching VaR limit', severity: 'WARNING' }]
        }),
        killSwitch: async (reason) => {
            await mockDelay(1000);
            return { success: true, orders_cancelled: 142, positions_closed: 28, reason };
        },
        getMandates: async () => ({ mandates: mockMandates }),
        updateSettings: async (settings) => ({ success: true, ...settings }),
        acknowledgeAlert: async (alertId) => ({ success: true, alertId })
    },
    execution: {
        sendOrder: async (order) => {
            await mockDelay();
            return { success: true, order_id: 'ord-' + Date.now(), ...order, status: 'PENDING' };
        },
        cancelAll: async () => { await mockDelay(); return { success: true, orders_cancelled: mockOrders.length }; },
        cancelOrder: async (orderId) => ({ success: true, order_id: orderId }),
        getOpenOrders: async () => ({ orders: mockOrders, count: mockOrders.length }),
        getOrderHistory: async () => ({ orders: mockOrders }),
        getPositions: async () => ({ positions: mockPositions, total_unrealized_pnl: mockPositions.reduce((sum, p) => sum + p.unrealized_pnl, 0) })
    },
    stress: {
        getScenarios: async () => ({ scenarios: mockScenarios, count: mockScenarios.length }),
        run: async (scenarioIds) => {
            await mockDelay(2000);
            return {
                run_id: 'run-' + Date.now(),
                results: scenarioIds.map(id => ({ scenario_id: id, impact: -Math.random() * 0.15 })),
                total_impact: -12.4,
                worst_case_drawdown: -18.2,
                breached_mandates: ['M-204']
            };
        },
        getHistory: async () => ({ results: [] }),
        createScenario: async (name, desc, type, params) => ({ success: true, id: 'sc-new-' + Date.now() })
    },
    audit: {
        getEvents: async () => ({ events: mockAuditEvents, total: mockAuditEvents.length, has_more: false }),
        getEvent: async (id) => mockAuditEvents.find(e => e.id === id),
        getSummary: async () => ({
            total_events: 1247,
            period_hours: 24,
            by_service: [{ service: 'execution-gateway', count: 523 }, { service: 'risk-engine', count: 342 }],
            by_action: [{ action: 'ORDER_SUBMIT', count: 423 }, { action: 'STRATEGY_UPDATE', count: 156 }],
            active_users: [{ username: 'admin', actions: 89 }, { username: 'quant_1', actions: 45 }],
            critical_actions: []
        }),
        export: async () => ({ events: mockAuditEvents }),
        getTimeline: async () => ({ timeline: mockAuditEvents })
    }
};

// Real API implementation
const realApi = {
    auth: {
        login: (username, password) => axiosInstance.post(`${API_URLS.auth}/login`, { username, password }),
        me: () => axiosInstance.get(`${API_URLS.auth}/me`),
        logout: () => axiosInstance.post(`${API_URLS.auth}/logout`)
    },
    market: {
        getStatus: () => axiosInstance.get(`${API_URLS.market}/status`),
        getLatency: () => axiosInstance.get(`${API_URLS.market}/latency`),
        getPrices: () => axiosInstance.get(`${API_URLS.market}/prices`),
        getPrice: (symbol) => axiosInstance.get(`${API_URLS.market}/prices/${symbol}`),
        getSymbols: () => axiosInstance.get(`${API_URLS.market}/symbols`)
    },
    strategy: {
        list: (statusFilter) => axiosInstance.get(`${API_URLS.strategy}/strategies`, { params: { status_filter: statusFilter } }),
        get: (id) => axiosInstance.get(`${API_URLS.strategy}/strategies/${id}`),
        register: (data) => axiosInstance.post(`${API_URLS.strategy}/strategies/register`, data),
        activate: (id) => axiosInstance.post(`${API_URLS.strategy}/strategies/${id}/activate`),
        halt: (id) => axiosInstance.post(`${API_URLS.strategy}/strategies/${id}/halt`),
        updateParameters: (id, parameters) => axiosInstance.put(`${API_URLS.strategy}/strategies/${id}/parameters`, parameters)
    },
    risk: {
        getSnapshot: () => axiosInstance.get(`${API_URLS.risk}/risk/snapshot`),
        killSwitch: (reason) => axiosInstance.post(`${API_URLS.risk}/risk/kill-switch`, { reason, confirm: true }),
        getMandates: () => axiosInstance.get(`${API_URLS.risk}/risk/mandates`),
        updateSettings: (settings) => axiosInstance.post(`${API_URLS.risk}/risk/update`, settings),
        acknowledgeAlert: (alertId) => axiosInstance.post(`${API_URLS.risk}/risk/alerts/${alertId}/acknowledge`)
    },
    execution: {
        sendOrder: (order) => axiosInstance.post(`${API_URLS.execution}/orders/send`, order),
        cancelAll: () => axiosInstance.post(`${API_URLS.execution}/orders/cancel_all`),
        cancelOrder: (orderId) => axiosInstance.post(`${API_URLS.execution}/orders/${orderId}/cancel`),
        getOpenOrders: (symbol) => axiosInstance.get(`${API_URLS.execution}/orders/open`, { params: { symbol } }),
        getOrderHistory: (limit = 50) => axiosInstance.get(`${API_URLS.execution}/orders/history`, { params: { limit } }),
        getPositions: () => axiosInstance.get(`${API_URLS.execution}/positions`)
    },
    stress: {
        getScenarios: () => axiosInstance.get(`${API_URLS.stress}/scenarios`),
        run: (scenarioIds, includeHistorical = true, customParams = null) => axiosInstance.post(`${API_URLS.stress}/stress/run`, { scenario_ids: scenarioIds, include_historical: includeHistorical, custom_parameters: customParams }),
        getHistory: (limit = 20) => axiosInstance.get(`${API_URLS.stress}/stress/history`, { params: { limit } }),
        createScenario: (name, description, type, parameters) => axiosInstance.post(`${API_URLS.stress}/scenarios/create`, { name, description, scenario_type: type, parameters })
    },
    audit: {
        getEvents: (filters = {}) => axiosInstance.get(`${API_URLS.audit}/audit/events`, { params: filters }),
        getEvent: (eventId) => axiosInstance.get(`${API_URLS.audit}/audit/events/${eventId}`),
        getSummary: (hours = 24) => axiosInstance.get(`${API_URLS.audit}/audit/summary`, { params: { hours } }),
        export: (startDate, endDate) => axiosInstance.get(`${API_URLS.audit}/audit/export`, { params: { start_date: startDate, end_date: endDate } }),
        getTimeline: (resourceType, resourceId) => axiosInstance.get(`${API_URLS.audit}/audit/timeline`, { params: { resource_type: resourceType, resource_id: resourceId } })
    }
};

// Export the appropriate API based on mode
const api = MOCK_MODE ? mockApi : realApi;

// WebSocket connections (mock in demo mode)
export const createMarketWebSocket = (onMessage) => {
    if (MOCK_MODE) {
        let prices = { ...mockPrices };
        const interval = setInterval(() => {
            prices = simulatePriceUpdate(prices);
            const symbol = Object.keys(prices)[Math.floor(Math.random() * Object.keys(prices).length)];
            onMessage({ channel: 'market_ticks', data: prices[symbol] });
        }, 500);
        return { close: () => clearInterval(interval), onopen: null, onclose: null, onerror: null };
    }
    const ws = new WebSocket('ws://localhost:7002/ws');
    ws.onopen = () => console.log('Market WebSocket connected');
    ws.onmessage = (event) => onMessage(JSON.parse(event.data));
    ws.onerror = (error) => console.error('Market WebSocket error:', error);
    ws.onclose = () => console.log('Market WebSocket disconnected');
    return ws;
};

export const createRiskWebSocket = (onMessage) => {
    if (MOCK_MODE) {
        const interval = setInterval(() => {
            if (Math.random() > 0.95) {
                onMessage({ channel: 'risk_alerts', data: { severity: 'WARNING', message: 'VaR approaching limit' } });
            }
        }, 5000);
        return { close: () => clearInterval(interval) };
    }
    const ws = new WebSocket('ws://localhost:7004/ws');
    ws.onopen = () => console.log('Risk WebSocket connected');
    ws.onmessage = (event) => onMessage(JSON.parse(event.data));
    return ws;
};

export default api;
