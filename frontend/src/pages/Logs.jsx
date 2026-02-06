import { useState, useEffect } from 'react';
import { useAuditStore } from '../store';
import api from '../services/api';
import { ScrollText, Filter, Download, Search, Clock, User } from 'lucide-react';

export default function Logs() {
    const { events, loading, fetchEvents } = useAuditStore();
    const [filters, setFilters] = useState({ service: '', action: '', user_id: '' });
    const [summary, setSummary] = useState(null);

    useEffect(() => {
        fetchEvents(filters);
        api.audit.getSummary(24).then(setSummary).catch(() => { });
    }, []);

    const handleSearch = () => fetchEvents(filters);

    const getActionColor = (action) => {
        if (action?.includes('KILL') || action?.includes('HALT')) return 'text-danger';
        if (action?.includes('ACTIVATE') || action?.includes('LOGIN')) return 'text-success';
        return 'text-secondary';
    };

    return (
        <div className="logs-page animate-fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><ScrollText size={24} /><h1>Audit Ledger</h1></div>
                <button className="btn btn-secondary btn-sm"><Download size={14} /> Export</button>
            </div>

            {summary && (
                <div className="grid grid-cols-4" style={{ marginBottom: 24 }}>
                    <div className="metric-card"><span className="metric-label">Total Events (24h)</span><div className="metric-value">{summary.total_events}</div></div>
                    <div className="metric-card"><span className="metric-label">Active Users</span><div className="metric-value">{summary.active_users?.length || 0}</div></div>
                    <div className="metric-card"><span className="metric-label">Critical Actions</span><div className="metric-value text-danger">{summary.critical_actions?.length || 0}</div></div>
                    <div className="metric-card"><span className="metric-label">Services</span><div className="metric-value">{summary.by_service?.length || 0}</div></div>
                </div>
            )}

            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">Event Log</h3>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <input type="text" className="input" style={{ width: 120 }} placeholder="Service..." value={filters.service} onChange={(e) => setFilters({ ...filters, service: e.target.value })} />
                        <input type="text" className="input" style={{ width: 120 }} placeholder="Action..." value={filters.action} onChange={(e) => setFilters({ ...filters, action: e.target.value })} />
                        <button className="btn btn-primary btn-sm" onClick={handleSearch}><Search size={14} /> Search</button>
                    </div>
                </div>

                <table>
                    <thead><tr><th>Timestamp</th><th>User</th><th>Service</th><th>Action</th><th>Resource</th><th>Details</th></tr></thead>
                    <tbody>
                        {(events.length ? events : [
                            { id: '1', timestamp: new Date().toISOString(), username: 'admin', service: 'auth-service', action: 'LOGIN_SUCCESS', resource_type: 'session' },
                            { id: '2', timestamp: new Date().toISOString(), username: 'quant_1', service: 'strategy-registry', action: 'STRATEGY_ACTIVATE', resource_type: 'strategy', resource_id: 'STRAT-EQ-01' },
                            { id: '3', timestamp: new Date().toISOString(), username: 'risk_mgr', service: 'risk-engine', action: 'MANDATE_UPDATE', resource_type: 'mandate', resource_id: 'M-204' },
                            { id: '4', timestamp: new Date().toISOString(), username: 'admin', service: 'execution-gateway', action: 'ORDER_SUBMIT', resource_type: 'order' }
                        ]).map((event) => (
                            <tr key={event.id}>
                                <td className="mono" style={{ fontSize: 12 }}><Clock size={12} style={{ marginRight: 4 }} />{new Date(event.timestamp).toLocaleString()}</td>
                                <td><span className="badge badge-neutral"><User size={10} /> {event.username || '-'}</span></td>
                                <td className="text-primary">{event.service}</td>
                                <td className={getActionColor(event.action)}>{event.action}</td>
                                <td className="mono">{event.resource_type}{event.resource_id ? `:${event.resource_id}` : ''}</td>
                                <td><button className="btn btn-ghost btn-sm">View</button></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {loading && <div style={{ textAlign: 'center', padding: 24, color: 'var(--text-tertiary)' }}>Loading...</div>}
            </div>
        </div>
    );
}
