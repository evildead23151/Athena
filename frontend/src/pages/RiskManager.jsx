import { useState, useEffect } from 'react';
import { useAuthStore, useGlobalStore, useRiskStore } from '../store';
import api from '../services/api';
import {
    Shield,
    AlertTriangle,
    TrendingUp,
    Zap,
    Wifi,
    FileText,
    Power,
    Activity
} from 'lucide-react';

export default function RiskManager() {
    const { user } = useAuthStore();
    const { grossLeverage, openOrders, netExposure } = useGlobalStore();
    const { mandates, alerts, fetchRiskData } = useRiskStore();
    const [loading, setLoading] = useState(false);
    const [confirmKill, setConfirmKill] = useState(false);
    const [killReason, setKillReason] = useState('');

    // Gating status
    const [gatingStatus, setGatingStatus] = useState({
        exchangeConnectivity: true,
        auditLogActive: true,
        cancelOnlyMode: false
    });

    useEffect(() => {
        fetchRiskData();
        const interval = setInterval(fetchRiskData, 2000);
        return () => clearInterval(interval);
    }, []);

    const handleKillSwitch = async () => {
        if (!confirmKill) {
            setConfirmKill(true);
            return;
        }

        if (!killReason.trim()) {
            alert('Please provide a reason for activating the kill switch');
            return;
        }

        setLoading(true);
        try {
            const result = await api.risk.killSwitch(killReason);
            alert(`Kill switch executed: ${result.orders_cancelled} orders cancelled, ${result.positions_closed} positions closed`);
            setConfirmKill(false);
            setKillReason('');
            fetchRiskData();
        } catch (error) {
            console.error('Kill switch failed:', error);
            alert('Kill switch failed: ' + (error.response?.data?.detail || 'Unknown error'));
        }
        setLoading(false);
    };

    const toggleGating = (key) => {
        setGatingStatus(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const getStatusBadge = (status) => {
        switch (status) {
            case 'OK': return <span className="badge badge-success">OK</span>;
            case 'WARNING': return <span className="badge badge-warning">WARNING</span>;
            case 'BREACH': return <span className="badge badge-danger">▲ BREACH</span>;
            default: return <span className="badge badge-neutral">{status}</span>;
        }
    };

    const formatValue = (value, type) => {
        if (!value) return '-';
        if (type === 'DRAWDOWN') return `${(value * 100).toFixed(1)}%`;
        if (type === 'SECTOR_EXPOSURE') return `${(value * 100).toFixed(1)}%`;
        if (type === 'LIQUIDITY') return `${(value * 100).toFixed(0)}%`;
        if (value >= 1000000000) return `${(value / 1000000000).toFixed(1)}B`;
        if (value >= 1000000) return `${(value / 1000000).toFixed(0)}M`;
        return value.toFixed(2);
    };

    return (
        <div className="risk-page animate-fade-in">
            <div className="risk-header">
                <div className="risk-title">
                    <Shield size={24} />
                    <h1>ATHENA // RISK CONTROL TOWER</h1>
                </div>
                <div className="status-indicators">
                    <span className="status-item">
                        <span className="status-dot active" />
                        SYSTEM: ONLINE
                    </span>
                    <span className="status-item">
                        <span className="status-dot active" />
                        FEED: 12ms
                    </span>
                </div>
            </div>

            <div className="risk-layout">
                {/* Left - Vitals & Mandates */}
                <div className="risk-main">
                    {/* System Vitals */}
                    <div className="card vitals-card">
                        <h3 className="card-title">⚡ SYSTEM VITALS</h3>
                        <div className="vitals-grid">
                            <div className="vital-box">
                                <div className="vital-header">
                                    <span className="vital-label text-success">GROSS LEVERAGE USAGE</span>
                                    <TrendingUp size={16} />
                                </div>
                                <div className="vital-value">
                                    <span className="big-number">{grossLeverage?.toFixed(1) || '4.2'}x</span>
                                    <span className="limit">/ 5.0x</span>
                                </div>
                                <span className="change text-success">↑ 0.2x WEEK OVER WEEK</span>
                                <div className="leverage-bar">
                                    <div
                                        className="leverage-fill"
                                        style={{ width: `${((grossLeverage || 4.2) / 5) * 100}%` }}
                                    />
                                    <div className="leverage-markers">
                                        <span>0x</span>
                                        <span>2.5x</span>
                                        <span className="critical">CRITICAL 5.0x</span>
                                    </div>
                                </div>
                            </div>

                            <div className="vital-box">
                                <div className="vital-header">
                                    <span className="vital-label">NET CONCENTRATION RISK</span>
                                    <Activity size={16} />
                                </div>
                                <div className="vital-value">
                                    <span className="big-number">18%</span>
                                    <span className="limit">Top 5</span>
                                </div>
                                <span className="change text-success">↑ 1.5% DAY OVER DAY</span>
                                <div className="leverage-bar">
                                    <div className="leverage-fill success" style={{ width: '60%' }} />
                                    <div className="leverage-markers">
                                        <span>0%</span>
                                        <span>10%</span>
                                        <span className="limit-text">LIMIT 30%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Hard Capital Constraints */}
                    <div className="card mandates-card">
                        <div className="card-header">
                            <h3 className="card-title">⚖ HARD CAPITAL CONSTRAINTS</h3>
                            <span className="live-badge">
                                <span className="status-dot active" />
                                LIVE BREACH MONITORING ACTIVE
                            </span>
                        </div>

                        <div className="table-container">
                            <table className="mandates-table">
                                <thead>
                                    <tr>
                                        <th>MANDATE ID</th>
                                        <th>CONSTRAINT DESCRIPTION</th>
                                        <th>CURRENT VAL</th>
                                        <th>HARD LIMIT</th>
                                        <th>DELTA</th>
                                        <th>STATUS</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(mandates.length > 0 ? mandates : [
                                        { mandate_id: 'M-204', description: 'Max Drawdown (Daily)', current_value: -0.028, hard_limit: -0.03, status: 'WARNING', constraint_type: 'DRAWDOWN' },
                                        { mandate_id: 'M-101', description: 'Sector Exposure: Tech', current_value: 0.145, hard_limit: 0.15, status: 'OK', constraint_type: 'SECTOR_EXPOSURE' },
                                        { mandate_id: 'M-502', description: 'Liquidity < 1 Day', current_value: 0.88, hard_limit: 0.90, status: 'BREACH', constraint_type: 'LIQUIDITY' },
                                        { mandate_id: 'M-330', description: 'Gross Exposure', current_value: 4200000000, hard_limit: 5000000000, status: 'OK', constraint_type: 'GROSS_EXPOSURE' },
                                        { mandate_id: 'M-009', description: 'Overnight Margin', current_value: 350000000, hard_limit: 400000000, status: 'OK', constraint_type: 'MARGIN' }
                                    ]).map((mandate) => (
                                        <tr key={mandate.mandate_id} className={mandate.status === 'BREACH' ? 'breach-row' : ''}>
                                            <td className={mandate.status === 'BREACH' ? 'text-danger mono' : 'text-primary mono'}>
                                                {mandate.mandate_id}
                                            </td>
                                            <td>{mandate.description}</td>
                                            <td className={`mono ${mandate.status === 'WARNING' ? 'text-warning' : mandate.status === 'BREACH' ? 'text-danger' : ''}`}>
                                                {formatValue(mandate.current_value, mandate.constraint_type)}
                                            </td>
                                            <td className="mono">{formatValue(mandate.hard_limit, mandate.constraint_type)}</td>
                                            <td className={mandate.delta < 0 ? 'text-danger' : 'text-success'}>
                                                {mandate.delta ? (mandate.delta >= 0 ? '+' : '') + formatValue(mandate.delta, mandate.constraint_type) : '-'}
                                            </td>
                                            <td>{getStatusBadge(mandate.status)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Stress Summaries */}
                    <div className="card stress-summaries">
                        <h3 className="card-title">📊 ADVERSARIAL STRESS SUMMARIES</h3>
                        <div className="stress-grid">
                            <div className="stress-box">
                                <div className="stress-header">
                                    <span>BLACK MONDAY REPEAT</span>
                                    <span className="text-danger">-12.4%</span>
                                </div>
                                <div className="mini-bars">
                                    {[0.6, 0.8, 0.4, 0.9, 0.3, 0.5].map((h, i) => (
                                        <div
                                            key={i}
                                            className="mini-bar"
                                            style={{ height: `${h * 40}px`, background: i < 3 ? 'var(--warning)' : 'var(--danger)' }}
                                        />
                                    ))}
                                </div>
                            </div>
                            <div className="stress-box">
                                <div className="stress-header">
                                    <span>FED RATE SHOCK (+100BPS)</span>
                                    <span className="text-danger">-4.1%</span>
                                </div>
                                <div className="mini-bars">
                                    {[0.3, 0.5, 0.4, 0.6, 0.2, 0.4].map((h, i) => (
                                        <div
                                            key={i}
                                            className="mini-bar"
                                            style={{ height: `${h * 40}px`, background: 'var(--text-tertiary)' }}
                                        />
                                    ))}
                                </div>
                            </div>
                            <div className="stress-box">
                                <div className="stress-header">
                                    <span>CRYPTO FLASH CRASH</span>
                                    <span className="text-success">+1.2%</span>
                                </div>
                                <div className="mini-bars">
                                    {[0.5, 0.6, 0.7, 0.4, 0.8, 0.9].map((h, i) => (
                                        <div
                                            key={i}
                                            className="mini-bar"
                                            style={{ height: `${h * 40}px`, background: i < 4 ? 'var(--success)' : 'var(--danger)' }}
                                        />
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right Panel - Emergency Controls */}
                <div className="emergency-panel">
                    <div className="emergency-box">
                        <h3>EMERGENCY LIQUIDATION</h3>
                        <p className="auth-level">Auth Level: ADMIN // Terminal 4</p>

                        <div className="status-list">
                            <div className="status-row">
                                <span>Algorithms</span>
                                <span className="text-success">● ACTIVE</span>
                            </div>
                            <div className="status-row">
                                <span>Open Orders</span>
                                <span className="mono">{openOrders?.toLocaleString() || '14,203'}</span>
                            </div>
                            <div className="status-row">
                                <span>Net Exposure</span>
                                <span className="mono">${((netExposure || 4200000000) / 1000000000).toFixed(1)}B</span>
                            </div>
                        </div>

                        <div className="gating-section">
                            <h4>GATING STATUS</h4>
                            <div className="gating-row">
                                <span>Exchange Connectivity</span>
                                <button
                                    className={`toggle ${gatingStatus.exchangeConnectivity ? 'active' : ''}`}
                                    onClick={() => toggleGating('exchangeConnectivity')}
                                />
                            </div>
                            <div className="gating-row">
                                <span>Audit Log Active</span>
                                <button
                                    className={`toggle ${gatingStatus.auditLogActive ? 'active' : ''}`}
                                    onClick={() => toggleGating('auditLogActive')}
                                />
                            </div>
                            <div className="gating-row">
                                <span>Cancel-Only Mode</span>
                                <button
                                    className={`toggle ${gatingStatus.cancelOnlyMode ? 'active' : ''}`}
                                    onClick={() => toggleGating('cancelOnlyMode')}
                                />
                            </div>
                        </div>

                        <div className="danger-zone">
                            <span className="danger-label">DANGER ZONE</span>

                            {confirmKill && (
                                <div className="confirm-kill">
                                    <input
                                        type="text"
                                        className="input"
                                        placeholder="Enter reason for kill switch..."
                                        value={killReason}
                                        onChange={(e) => setKillReason(e.target.value)}
                                    />
                                </div>
                            )}

                            <div className="kill-switch-container">
                                <span className="kill-switch-label">
                                    <Power size={14} />
                                    IRREVERSIBLE ACTION
                                </span>
                                <button
                                    className="kill-switch-btn"
                                    onClick={handleKillSwitch}
                                    disabled={loading || user?.role !== 'ADMIN'}
                                >
                                    <Zap size={24} />
                                    {loading ? 'EXECUTING...' : confirmKill ? 'CONFIRM KILL' : 'KILL ALL POSITIONS'}
                                </button>
                                {user?.role !== 'ADMIN' && (
                                    <p className="admin-only">Admin access required</p>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
