import { useState, useEffect } from 'react';
import { useGlobalStore, useRiskStore } from '../store';
import api from '../services/api';
import {
    TrendingUp,
    TrendingDown,
    DollarSign,
    Percent,
    BarChart3,
    Activity,
    AlertTriangle,
    MoreHorizontal,
    ArrowUpRight,
    ArrowDownRight
} from 'lucide-react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Area,
    AreaChart
} from 'recharts';
import './Dashboard.css';

// Format currency
const formatCurrency = (value) => {
    if (value >= 1000000000) return `$${(value / 1000000000).toFixed(2)}B`;
    if (value >= 1000000) return `$${(value / 1000000).toFixed(2)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(2)}K`;
    return `$${value.toFixed(2)}`;
};

const formatPercent = (value) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${(value * 100).toFixed(2)}%`;
};

// Sample equity curve data
const generateEquityData = () => {
    const data = [];
    let value = 130000000;
    for (let i = 0; i < 365; i++) {
        value += (Math.random() - 0.48) * 500000;
        data.push({
            date: new Date(2024, 0, i + 1).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
            nav: value,
            drawdown: Math.random() * -0.05
        });
    }
    return data;
};

export default function Dashboard() {
    const {
        nav, dailyPnl, sharpeRatio, maxDrawdown,
        netExposure, grossExposure, grossLeverage,
        strategies, activeStrategies, openOrders
    } = useGlobalStore();

    const { alerts, fetchRiskData } = useRiskStore();
    const [equityData] = useState(generateEquityData);
    const [timeRange, setTimeRange] = useState('YTD');

    useEffect(() => {
        fetchRiskData();
    }, []);

    const metrics = [
        {
            label: 'NET ASSET VALUE (NAV)',
            value: formatCurrency(nav),
            change: '+0.8% DoD',
            positive: true,
            icon: DollarSign
        },
        {
            label: 'DAILY PNL',
            value: `+${formatCurrency(dailyPnl)}`,
            change: '+42bps',
            positive: true,
            icon: TrendingUp
        },
        {
            label: 'SHARPE RATIO (ANN.)',
            value: sharpeRatio.toFixed(2),
            change: 'Top 5% Quartile',
            positive: true,
            icon: BarChart3
        },
        {
            label: 'MAX DRAWDOWN',
            value: formatPercent(maxDrawdown),
            change: 'Limit: -15.0%',
            positive: false,
            icon: TrendingDown
        }
    ];

    return (
        <div className="dashboard-grid animate-fade-in">
            {/* Metrics Row */}
            <div className="metrics-row">
                {metrics.map((metric, index) => (
                    <div key={index} className="metric-card">
                        <div className="metric-header">
                            <span className="metric-label">{metric.label}</span>
                            <metric.icon size={16} className="metric-icon" />
                        </div>
                        <div className="metric-value">{metric.value}</div>
                        <div className={`metric-change ${metric.positive ? 'positive' : 'negative'}`}>
                            {metric.positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                            {metric.change}
                        </div>
                    </div>
                ))}
            </div>

            {/* Main Grid */}
            <div className="main-grid">
                {/* Equity Chart */}
                <div className="card">
                    <div className="card-header">
                        <div>
                            <h3 className="card-title-lg">Equity vs Drawdown</h3>
                            <p className="card-subtitle">YTD Performance against high water mark.</p>
                        </div>
                        <div className="time-range-buttons">
                            {['1D', '1W', 'YTD'].map((range) => (
                                <button
                                    key={range}
                                    className={`time-btn ${timeRange === range ? 'active' : ''}`}
                                    onClick={() => setTimeRange(range)}
                                >
                                    {range}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height={280}>
                            <AreaChart data={equityData.slice(-90)}>
                                <defs>
                                    <linearGradient id="navGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#7B3FE4" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#7B3FE4" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                                <XAxis
                                    dataKey="date"
                                    stroke="var(--text-tertiary)"
                                    fontSize={11}
                                    tickLine={false}
                                />
                                <YAxis
                                    stroke="var(--text-tertiary)"
                                    fontSize={11}
                                    tickLine={false}
                                    tickFormatter={(val) => `$${(val / 1000000).toFixed(0)}M`}
                                />
                                <Tooltip
                                    contentStyle={{
                                        background: 'var(--bg-elevated)',
                                        border: '1px solid var(--border)',
                                        borderRadius: 'var(--radius-md)',
                                        fontSize: '12px'
                                    }}
                                    formatter={(value) => [formatCurrency(value), 'NAV']}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="nav"
                                    stroke="#7B3FE4"
                                    strokeWidth={2}
                                    fill="url(#navGradient)"
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Right Panel */}
                <div className="right-panel">
                    {/* Net Exposure */}
                    <div className="card">
                        <div className="card-header">
                            <span className="card-title">Net Exposure</span>
                            <span className="badge badge-success">Delta Neutral</span>
                        </div>
                        <div className="exposure-section">
                            <div className="exposure-row">
                                <span className="exposure-label">Long Market Value</span>
                                <span className="exposure-value positive">$142.2M (99.8%)</span>
                            </div>
                            <div className="progress-bar" style={{ marginBottom: 'var(--space-md)' }}>
                                <div className="progress-fill success" style={{ width: '99.8%' }} />
                            </div>

                            <div className="exposure-row">
                                <span className="exposure-label">Short Market Value</span>
                                <span className="exposure-value negative">-$139.1M (-97.6%)</span>
                            </div>
                            <div className="progress-bar" style={{ marginBottom: 'var(--space-md)' }}>
                                <div className="progress-fill danger" style={{ width: '97.6%' }} />
                            </div>

                            <div className="exposure-row" style={{ marginTop: 'var(--space-md)' }}>
                                <span className="exposure-label">Net Exposure</span>
                                <span className="exposure-value">$3.1M (2.2%)</span>
                            </div>
                            <div className="net-exposure-gauge">
                                <div className="gauge-scale">
                                    <span>-100%</span>
                                    <span>0%</span>
                                    <span>+100%</span>
                                </div>
                                <div className="gauge-track">
                                    <div className="gauge-marker" style={{ left: '51%' }} />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Risk Alert */}
                    {alerts.length > 0 && (
                        <div className="risk-alert-card">
                            <div className="risk-alert-icon">
                                <AlertTriangle size={24} />
                            </div>
                            <div className="risk-alert-content">
                                <h4>RISK ALERT</h4>
                                <p>{alerts[0]?.message || 'Strategy approaching VaR limit.'}</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Active Strategies Table */}
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title-lg">Active Strategies</h3>
                    <div className="flex gap-sm">
                        <button className="btn btn-secondary btn-sm">
                            <Activity size={14} />
                            Filter
                        </button>
                        <button className="btn btn-secondary btn-sm">
                            Export
                        </button>
                    </div>
                </div>
                <div className="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>STATUS</th>
                                <th>STRATEGY ID</th>
                                <th>ALLOCATION</th>
                                <th>RISK USAGE (VAR)</th>
                                <th>1D RETURN</th>
                                <th>YTD RETURN</th>
                                <th>ACTIONS</th>
                            </tr>
                        </thead>
                        <tbody>
                            {strategies.length > 0 ? strategies.map((strategy) => (
                                <tr key={strategy.id}>
                                    <td>
                                        <span className={`badge ${strategy.status === 'ACTIVE' ? 'badge-success' : 'badge-warning'}`}>
                                            <span className={`status-dot ${strategy.status === 'ACTIVE' ? 'active' : 'warning'}`} />
                                            {strategy.status}
                                        </span>
                                    </td>
                                    <td>
                                        <div className="strategy-info">
                                            <span className="strategy-name">{strategy.name}</span>
                                            <span className="strategy-id">{strategy.id?.slice(0, 12)}</span>
                                        </div>
                                    </td>
                                    <td className="mono">{formatCurrency(strategy.allocation || 0)}</td>
                                    <td>
                                        <div className="var-usage">
                                            <div className="progress-bar" style={{ width: 80, height: 6 }}>
                                                <div
                                                    className={`progress-fill ${Math.random() > 0.7 ? 'warning' : 'primary'}`}
                                                    style={{ width: `${Math.random() * 100}%` }}
                                                />
                                            </div>
                                        </div>
                                    </td>
                                    <td className="text-success mono">+{(Math.random() * 2).toFixed(2)}%</td>
                                    <td className="text-success mono">+{(Math.random() * 20).toFixed(1)}%</td>
                                    <td>
                                        <button className="btn btn-ghost btn-sm">
                                            <MoreHorizontal size={16} />
                                        </button>
                                    </td>
                                </tr>
                            )) : (
                                <>
                                    <tr>
                                        <td><span className="badge badge-success"><span className="status-dot active" />ACTIVE</span></td>
                                        <td><div className="strategy-info"><span className="strategy-name">Equities L/S Neutral</span><span className="strategy-id">STRAT-EQ-01</span></div></td>
                                        <td className="mono">$45.2M</td>
                                        <td><div className="progress-bar" style={{ width: 80, height: 6 }}><div className="progress-fill primary" style={{ width: '45%' }} /></div></td>
                                        <td className="text-success mono">+1.24%</td>
                                        <td className="text-success mono">+14.2%</td>
                                        <td><button className="btn btn-ghost btn-sm"><MoreHorizontal size={16} /></button></td>
                                    </tr>
                                    <tr>
                                        <td><span className="badge badge-success"><span className="status-dot active" />ACTIVE</span></td>
                                        <td><div className="strategy-info"><span className="strategy-name">Vol Arb (VIX)</span><span className="strategy-id">STRAT-VOL-04</span></div></td>
                                        <td className="mono">$22.8M</td>
                                        <td><div className="progress-bar" style={{ width: 80, height: 6 }}><div className="progress-fill warning" style={{ width: '78%' }} /></div></td>
                                        <td className="text-success mono">+0.82%</td>
                                        <td className="text-success mono">+8.5%</td>
                                        <td><button className="btn btn-ghost btn-sm"><MoreHorizontal size={16} /></button></td>
                                    </tr>
                                    <tr>
                                        <td><span className="badge badge-warning"><span className="status-dot warning" />HALTED</span></td>
                                        <td><div className="strategy-info"><span className="strategy-name">Momentum Crypto</span><span className="strategy-id">STRAT-CRY-09</span></div></td>
                                        <td className="mono">$0.0M</td>
                                        <td><div className="progress-bar" style={{ width: 80, height: 6 }}><div className="progress-fill primary" style={{ width: '0%' }} /></div></td>
                                        <td className="mono">0.00%</td>
                                        <td className="text-danger mono">-2.1%</td>
                                        <td><button className="btn btn-ghost btn-sm"><MoreHorizontal size={16} /></button></td>
                                    </tr>
                                </>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
