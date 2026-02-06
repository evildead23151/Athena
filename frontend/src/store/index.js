import { create } from 'zustand';
import api from '../services/api';

// Auth Store
export const useAuthStore = create((set, get) => ({
    user: null,
    token: localStorage.getItem('athena_token'),
    isAuthenticated: !!localStorage.getItem('athena_token'),
    loading: false,
    error: null,

    login: async (username, password) => {
        set({ loading: true, error: null });
        try {
            const response = await api.auth.login(username, password);
            const { access_token, user } = response;

            localStorage.setItem('athena_token', access_token);
            set({
                token: access_token,
                user,
                isAuthenticated: true,
                loading: false
            });
            return true;
        } catch (error) {
            set({
                error: error.response?.data?.detail || 'Login failed',
                loading: false
            });
            return false;
        }
    },

    logout: () => {
        localStorage.removeItem('athena_token');
        set({ user: null, token: null, isAuthenticated: false });
    },

    fetchUser: async () => {
        if (!get().token) return;
        try {
            const user = await api.auth.me();
            set({ user, isAuthenticated: true });
        } catch (error) {
            get().logout();
        }
    }
}));

// Global State Store
export const useGlobalStore = create((set, get) => ({
    systemStatus: 'OPERATIONAL',
    killSwitchActive: false,
    lastUpdate: null,

    // Metrics
    nav: 142500231,
    dailyPnl: 124002,
    sharpeRatio: 2.41,
    maxDrawdown: -0.042,

    // Risk
    netExposure: 3100000,
    grossExposure: 4200000000,
    grossLeverage: 4.2,
    openOrders: 14203,

    // Strategies
    activeStrategies: 2,
    strategies: [],

    // Market Status
    marketStatus: 'CONNECTED',
    feedLatency: 12,

    // Real-time updates
    updateMetrics: (metrics) => set(metrics),

    setSystemStatus: (status) => set({ systemStatus: status }),

    setKillSwitchActive: (active) => set({ killSwitchActive: active }),

    fetchGlobalState: async () => {
        try {
            // Fetch from multiple services
            const [riskSnapshot, strategies, openOrders] = await Promise.all([
                api.risk.getSnapshot().catch(() => null),
                api.strategy.list().catch(() => ({ strategies: [] })),
                api.execution.getOpenOrders().catch(() => ({ count: 0 }))
            ]);

            if (riskSnapshot) {
                set({
                    netExposure: riskSnapshot.snapshot?.net_exposure || get().netExposure,
                    grossExposure: riskSnapshot.snapshot?.gross_exposure || get().grossExposure,
                    grossLeverage: riskSnapshot.snapshot?.gross_leverage || get().grossLeverage,
                    maxDrawdown: riskSnapshot.snapshot?.max_drawdown || get().maxDrawdown
                });
            }

            if (strategies) {
                set({
                    strategies: strategies.strategies || [],
                    activeStrategies: strategies.active_count || 0
                });
            }

            set({
                openOrders: openOrders?.count || get().openOrders,
                lastUpdate: new Date().toISOString()
            });

        } catch (error) {
            console.error('Failed to fetch global state:', error);
        }
    }
}));

// Risk Alerts Store
export const useRiskStore = create((set, get) => ({
    alerts: [],
    mandates: [],
    snapshot: null,

    addAlert: (alert) => set((state) => ({
        alerts: [alert, ...state.alerts].slice(0, 50)
    })),

    acknowledgeAlert: async (alertId) => {
        try {
            await api.risk.acknowledgeAlert(alertId);
            set((state) => ({
                alerts: state.alerts.filter(a => a.id !== alertId)
            }));
        } catch (error) {
            console.error('Failed to acknowledge alert:', error);
        }
    },

    fetchRiskData: async () => {
        try {
            const data = await api.risk.getSnapshot();
            set({
                snapshot: data.snapshot,
                mandates: data.mandates || [],
                alerts: data.active_alerts || []
            });
        } catch (error) {
            console.error('Failed to fetch risk data:', error);
        }
    }
}));

// Audit Store
export const useAuditStore = create((set) => ({
    events: [],
    loading: false,
    hasMore: true,

    fetchEvents: async (filters = {}) => {
        set({ loading: true });
        try {
            const data = await api.audit.getEvents(filters);
            set({
                events: data.events || [],
                hasMore: data.has_more,
                loading: false
            });
        } catch (error) {
            console.error('Failed to fetch audit events:', error);
            set({ loading: false });
        }
    }
}));
