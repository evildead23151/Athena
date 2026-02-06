import { useState, useEffect } from 'react';
import { useGlobalStore } from '../store';
import api from '../services/api';
import {
    Play,
    Pause,
    Settings,
    Plus,
    TrendingUp,
    TrendingDown,
    BarChart3,
    Filter,
    Download,
    RefreshCw
} from 'lucide-react';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer
} from 'recharts';

// Generate sample backtest data
const generateBacktestData = () => {
    const data = [];
    let equity = 100;
    for (let i = 0; i < 200; i++) {
        equity *= (1 + (Math.random() - 0.48) * 0.02);
        data.push({
            day: i,
            equity: equity,
            drawdown: equity < 100 ? ((equity - 100) / 100) * 100 : 0
        });
    }
    return data;
};

export default function Strategies() {
    const { strategies, fetchGlobalState } = useGlobalStore();
    const [selectedStrategy, setSelectedStrategy] = useState(null);
    const [loading, setLoading] = useState(false);
    const [backtestData] = useState(generateBacktestData);
    const [stressResults, setStressResults] = useState(null);

    // Configuration state
    const [config, setConfig] = useState({
        assetUniverse: 'US_EQUITY_L_CAP',
        startDate: '2018-01-01',
        endDate: '2024-05-15',
        lookbackWindow: 14,
        volScalar: 0.85,
        meanRevThreshold: 2.5,
        stopLoss: 5.00,
        maxLeverage: 4
    });

    // Stress scenarios
    const [scenarios, setScenarios] = useState([
        { id: 1, name: 'Liquidity Collapse', enabled: false },
        { id: 2, name: 'Rate Hike Cycle', enabled: true },
        { id: 3, name: 'Covid-19 Crash', enabled: true },
        { id: 4, name: '2008 GFC', enabled: false }
    ]);

    const handleToggleStrategy = async (strategyId, currentStatus) => {
        setLoading(true);
        try {
            if (currentStatus === 'ACTIVE') {
                await api.strategy.halt(strategyId);
            } else {
                await api.strategy.activate(strategyId);
            }
            await fetchGlobalState();
        } catch (error) {
            console.error('Failed to toggle strategy:', error);
        }
        setLoading(false);
    };

    const handleRunBacktest = async () => {
        setLoading(true);
        try {
            const enabledScenarios = scenarios
                .filter(s => s.enabled)
                .map(s => s.id);

            // This would call the stress engine
            const result = await api.stress.run(enabledScenarios).catch(() => ({
                total_impact: -12.4,
                worst_case_drawdown: -18.2,
                breached_mandates: ['M-204']
            }));

            setStressResults(result);
        } catch (error) {
            console.error('Backtest failed:', error);
        }
        setLoading(false);
    };

    return (
        <div className="strategies-page animate-fade-in">
            <div className="strategies-layout">
                {/* Left Sidebar - Configuration */}
                <div className="config-panel card">
                    <h3 className="panel-title">CONFIGURATION</h3>
                    <p className="panel-subtitle">Backtest Parameters</p>

                    <div className="config-section">
                        <label>ASSET UNIVERSE</label>
                        <select
                            className="input"
                            value={config.assetUniverse}
                            onChange={(e) => setConfig({ ...config, assetUniverse: e.target.value })}
                        >
                            <option value="US_EQUITY_L_CAP">US_EQUITY_L_CAP</option>
                            <option value="US_EQUITY_ALL">US_EQUITY_ALL</option>
                            <option value="GLOBAL_EQUITY">GLOBAL_EQUITY</option>
                        </select>
                    </div>

                    <div className="config-section">
                        <label>TIME HORIZON</label>
                        <div className="date-range">
                            <div className="date-input">
                                <span className="date-label">START</span>
                                <input
                                    type="date"
                                    className="input"
                                    value={config.startDate}
                                    onChange={(e) => setConfig({ ...config, startDate: e.target.value })}
                                />
                            </div>
                            <div className="date-input">
                                <span className="date-label">END</span>
                                <input
                                    type="date"
                                    className="input"
                                    value={config.endDate}
                                    onChange={(e) => setConfig({ ...config, endDate: e.target.value })}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="config-section">
                        <h4>ALPHA FACTORS</h4>
                        <div className="param-row">
                            <label>Lookback Window</label>
                            <input
                                type="number"
                                className="input param-input"
                                value={config.lookbackWindow}
                                onChange={(e) => setConfig({ ...config, lookbackWindow: Number(e.target.value) })}
                            />
                        </div>
                        <div className="param-row">
                            <label>Vol Scalar</label>
                            <input
                                type="number"
                                step="0.01"
                                className="input param-input"
                                value={config.volScalar}
                                onChange={(e) => setConfig({ ...config, volScalar: Number(e.target.value) })}
                            />
                        </div>
                        <div className="param-row">
                            <label>Mean Rev Threshold</label>
                            <input
                                type="number"
                                step="0.1"
                                className="input param-input"
                                value={config.meanRevThreshold}
                                onChange={(e) => setConfig({ ...config, meanRevThreshold: Number(e.target.value) })}
                            />
                        </div>
                    </div>

                    <div className="config-section">
                        <h4 className="text-danger">RISK CONSTRAINTS</h4>
                        <div className="param-row">
                            <label>Stop Loss %</label>
                            <input
                                type="number"
                                step="0.01"
                                className="input param-input danger"
                                value={config.stopLoss}
                                onChange={(e) => setConfig({ ...config, stopLoss: Number(e.target.value) })}
                            />
                        </div>
                        <div className="param-row">
                            <label>Max Leverage</label>
                            <div className="leverage-slider">
                                <input
                                    type="range"
                                    min="1"
                                    max="10"
                                    value={config.maxLeverage}
                                    onChange={(e) => setConfig({ ...config, maxLeverage: Number(e.target.value) })}
                                />
                            </div>
                        </div>
                    </div>

                    <button
                        className="btn btn-primary btn-lg run-backtest-btn"
                        onClick={handleRunBacktest}
                        disabled={loading}
                    >
                        <Play size={18} />
                        {loading ? 'RUNNING...' : 'RUN BACKTEST'}
                    </button>
                    <p className="runtime-estimate">EST. RUNTIME: 4.2s &nbsp;&nbsp; CORES: 64</p>
                </div>

                {/* Center - Chart */}
                <div className="main-panel">
                    <div className="card">
                        <div className="card-header">
                            <div>
                                <span className="breadcrumb">Strategies &gt; </span>
                                <span className="strategy-title">Mean Reversion A-14</span>
                                <span className="badge badge-success" style={{ marginLeft: 8 }}>ACTIVE</span>
                            </div>
                        </div>

                        <h2 className="chart-title">Equity vs. Underwater</h2>
                        <p className="chart-subtitle">Dual-axis performance analysis with automated drawdown filling.</p>

                        {/* Metrics Row */}
                        <div className="strategy-metrics">
                            <div className="strategy-metric">
                                <span className="label">TOTAL RETURN</span>
                                <span className="value success">+142.8%</span>
                            </div>
                            <div className="strategy-metric">
                                <span className="label">SHARPE RATIO</span>
                                <span className="value">1.84</span>
                            </div>
                            <div className="strategy-metric">
                                <span className="label">MAX DRAWDOWN</span>
                                <span className="value danger">-12.4%</span>
                            </div>
                            <div className="strategy-metric">
                                <span className="label">CALMAR</span>
                                <span className="value">2.15</span>
                            </div>
                            <button className="btn btn-secondary btn-sm">
                                <Download size={14} />
                                Export CSV
                            </button>
                        </div>

                        {/* Chart */}
                        <div className="chart-container" style={{ height: 320, marginTop: 'var(--space-lg)' }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={backtestData}>
                                    <defs>
                                        <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                                        </linearGradient>
                                        <linearGradient id="drawdownGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#DC2626" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#DC2626" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                                    <XAxis dataKey="day" stroke="var(--text-tertiary)" fontSize={10} />
                                    <YAxis yAxisId="equity" stroke="var(--text-tertiary)" fontSize={10} />
                                    <YAxis yAxisId="drawdown" orientation="right" stroke="var(--text-tertiary)" fontSize={10} />
                                    <Tooltip
                                        contentStyle={{
                                            background: 'var(--bg-elevated)',
                                            border: '1px solid var(--border)',
                                            borderRadius: 'var(--radius-md)',
                                            fontSize: '12px'
                                        }}
                                    />
                                    <Area
                                        yAxisId="equity"
                                        type="monotone"
                                        dataKey="equity"
                                        stroke="#10B981"
                                        strokeWidth={2}
                                        fill="url(#equityGrad)"
                                    />
                                    <Area
                                        yAxisId="drawdown"
                                        type="monotone"
                                        dataKey="drawdown"
                                        stroke="#DC2626"
                                        strokeWidth={2}
                                        fill="url(#drawdownGrad)"
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>

                {/* Right Sidebar - Stress Engine */}
                <div className="stress-panel card">
                    <div className="stress-header">
                        <span className="danger-icon">⚠</span>
                        <h3>STRESS ENGINE</h3>
                    </div>
                    <p className="panel-subtitle">Simulate market shocks & regime changes.</p>

                    <div className="scenario-section">
                        <h4>MACRO SHOCKS</h4>
                        {scenarios.slice(0, 2).map(scenario => (
                            <div key={scenario.id} className="scenario-row">
                                <span>{scenario.name}</span>
                                <button
                                    className={`toggle ${scenario.enabled ? 'active' : ''}`}
                                    onClick={() => setScenarios(scenarios.map(s =>
                                        s.id === scenario.id ? { ...s, enabled: !s.enabled } : s
                                    ))}
                                />
                            </div>
                        ))}
                    </div>

                    <div className="scenario-section">
                        <h4>HISTORICAL SCENARIOS</h4>
                        {scenarios.slice(2).map(scenario => (
                            <div key={scenario.id} className="scenario-row">
                                <div>
                                    <span>{scenario.name}</span>
                                    <span className="scenario-detail">
                                        {scenario.name === 'Covid-19 Crash' ? 'Mar 2020 Volatility > 80' : 'Lehman Default Event'}
                                    </span>
                                </div>
                                <button
                                    className={`toggle ${scenario.enabled ? 'active' : ''}`}
                                    onClick={() => setScenarios(scenarios.map(s =>
                                        s.id === scenario.id ? { ...s, enabled: !s.enabled } : s
                                    ))}
                                />
                            </div>
                        ))}
                    </div>

                    {stressResults && (
                        <div className="mandate-breach-alert">
                            <div className="breach-icon">⊘</div>
                            <h4>MANDATE BREACH</h4>
                            <p>Strategy fails under <strong>Rate Hike Cycle</strong> scenario. Max Drawdown exceeds 15% limit.</p>
                            <div className="breach-stats">
                                <div>
                                    <span>DD:</span>
                                    <span className="text-danger">-{Math.abs(stressResults.worst_case_drawdown || 18.2)}%</span>
                                </div>
                                <div>
                                    <span>Limit:</span>
                                    <span>-15.0%</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
