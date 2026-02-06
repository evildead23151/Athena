import { useState, useEffect } from 'react';
import api, { createMarketWebSocket } from '../services/api';
import { Activity, Wifi, WifiOff, Clock, RefreshCw } from 'lucide-react';

export default function MarketData() {
    const [prices, setPrices] = useState({});
    const [latency, setLatency] = useState(null);
    const [wsConnected, setWsConnected] = useState(false);

    useEffect(() => {
        fetchMarketData();
        const ws = createMarketWebSocket((data) => {
            if (data.channel === 'market_ticks' && data.data) {
                setPrices(prev => ({ ...prev, [data.data.symbol]: data.data }));
            }
        });
        ws.onopen = () => setWsConnected(true);
        ws.onclose = () => setWsConnected(false);
        const interval = setInterval(() => api.market.getLatency().then(setLatency).catch(() => { }), 5000);
        return () => { ws.close(); clearInterval(interval); };
    }, []);

    const fetchMarketData = async () => {
        try {
            const [pricesData, latencyData] = await Promise.all([
                api.market.getPrices().catch(() => ({ prices: {} })),
                api.market.getLatency().catch(() => null)
            ]);
            setPrices(pricesData.prices || {});
            setLatency(latencyData);
        } catch (error) { console.error('Failed to fetch:', error); }
    };

    const formatPrice = (p) => p >= 1000 ? p.toLocaleString('en-US', { minimumFractionDigits: 2 }) : p?.toFixed(4) || '-';
    const getSpread = (b, a) => b && a ? ((a - b) / b * 10000).toFixed(2) + ' bps' : '-';

    const defaultData = [
        { symbol: 'AAPL', bid: 185.42, ask: 185.48, last: 185.45, volume: 45231000 },
        { symbol: 'GOOGL', bid: 141.72, ask: 141.85, last: 141.78, volume: 12450000 },
        { symbol: 'MSFT', bid: 402.15, ask: 402.35, last: 402.25, volume: 21340000 },
        { symbol: 'BTC-USD', bid: 62480, ask: 62520, last: 62500, volume: 1245670000 }
    ];

    return (
        <div className="market-page animate-fade-in">
            <div className="market-header" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><Activity size={24} /><h1>Market Data Feed</h1></div>
                <div style={{ display: 'flex', gap: 12 }}>
                    <span className={`badge ${wsConnected ? 'badge-success' : 'badge-danger'}`}>
                        {wsConnected ? <><Wifi size={14} /> LIVE</> : <><WifiOff size={14} /> OFFLINE</>}
                    </span>
                    <button className="btn btn-secondary btn-sm" onClick={fetchMarketData}><RefreshCw size={14} /></button>
                </div>
            </div>

            <div className="card">
                <div className="card-header"><h3 className="card-title">Real-Time Prices</h3></div>
                <table>
                    <thead><tr><th>Symbol</th><th>Bid</th><th>Ask</th><th>Last</th><th>Spread</th><th>Volume</th></tr></thead>
                    <tbody>
                        {(Object.keys(prices).length ? Object.entries(prices) : defaultData.map(d => [d.symbol, d])).map(([sym, data]) => (
                            <tr key={sym}>
                                <td className="mono" style={{ fontWeight: 600 }}>{sym}</td>
                                <td className="mono text-success">{formatPrice(data.bid)}</td>
                                <td className="mono text-danger">{formatPrice(data.ask)}</td>
                                <td className="mono">{formatPrice(data.last_price || data.last)}</td>
                                <td className="mono">{getSpread(data.bid, data.ask)}</td>
                                <td className="mono">{data.volume?.toLocaleString()}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
