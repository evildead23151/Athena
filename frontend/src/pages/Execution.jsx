import { useState, useEffect } from 'react';
import api from '../services/api';
import {
    ArrowUpRight,
    ArrowDownRight,
    X,
    CheckCircle,
    XCircle,
    Clock,
    RefreshCw,
    Send
} from 'lucide-react';

export default function Execution() {
    const [orders, setOrders] = useState([]);
    const [positions, setPositions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [newOrder, setNewOrder] = useState({
        symbol: 'AAPL',
        side: 'BUY',
        quantity: 100,
        orderType: 'MARKET',
        price: null
    });

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 3000);
        return () => clearInterval(interval);
    }, []);

    const fetchData = async () => {
        try {
            const [ordersData, positionsData] = await Promise.all([
                api.execution.getOpenOrders().catch(() => ({ orders: [] })),
                api.execution.getPositions().catch(() => ({ positions: [] }))
            ]);
            setOrders(ordersData.orders || []);
            setPositions(positionsData.positions || []);
        } catch (error) {
            console.error('Failed to fetch execution data:', error);
        }
        setLoading(false);
    };

    const handleSubmitOrder = async () => {
        try {
            await api.execution.sendOrder({
                symbol: newOrder.symbol,
                side: newOrder.side,
                order_type: newOrder.orderType,
                quantity: newOrder.quantity,
                price: newOrder.price
            });
            await fetchData();
        } catch (error) {
            console.error('Failed to submit order:', error);
        }
    };

    const handleCancelOrder = async (orderId) => {
        try {
            await api.execution.cancelOrder(orderId);
            await fetchData();
        } catch (error) {
            console.error('Failed to cancel order:', error);
        }
    };

    const handleCancelAll = async () => {
        if (!confirm('Cancel all open orders?')) return;
        try {
            await api.execution.cancelAll();
            await fetchData();
        } catch (error) {
            console.error('Failed to cancel all orders:', error);
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'FILLED': return <CheckCircle size={14} className="text-success" />;
            case 'CANCELLED': return <XCircle size={14} className="text-danger" />;
            case 'PENDING': return <Clock size={14} className="text-warning" />;
            default: return <RefreshCw size={14} className="text-primary" />;
        }
    };

    return (
        <div className="execution-page animate-fade-in">
            <div className="execution-grid">
                {/* Order Entry */}
                <div className="card order-entry">
                    <h3 className="card-title">Order Entry</h3>

                    <div className="order-form">
                        <div className="form-row">
                            <label>Symbol</label>
                            <select
                                className="input"
                                value={newOrder.symbol}
                                onChange={(e) => setNewOrder({ ...newOrder, symbol: e.target.value })}
                            >
                                {['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'SPY', 'BTC-USD'].map(sym => (
                                    <option key={sym} value={sym}>{sym}</option>
                                ))}
                            </select>
                        </div>

                        <div className="form-row side-buttons">
                            <button
                                className={`side-btn buy ${newOrder.side === 'BUY' ? 'active' : ''}`}
                                onClick={() => setNewOrder({ ...newOrder, side: 'BUY' })}
                            >
                                <ArrowUpRight size={16} />
                                BUY
                            </button>
                            <button
                                className={`side-btn sell ${newOrder.side === 'SELL' ? 'active' : ''}`}
                                onClick={() => setNewOrder({ ...newOrder, side: 'SELL' })}
                            >
                                <ArrowDownRight size={16} />
                                SELL
                            </button>
                        </div>

                        <div className="form-row">
                            <label>Quantity</label>
                            <input
                                type="number"
                                className="input"
                                value={newOrder.quantity}
                                onChange={(e) => setNewOrder({ ...newOrder, quantity: Number(e.target.value) })}
                            />
                        </div>

                        <div className="form-row">
                            <label>Order Type</label>
                            <select
                                className="input"
                                value={newOrder.orderType}
                                onChange={(e) => setNewOrder({ ...newOrder, orderType: e.target.value })}
                            >
                                <option value="MARKET">Market</option>
                                <option value="LIMIT">Limit</option>
                                <option value="STOP">Stop</option>
                            </select>
                        </div>

                        {newOrder.orderType !== 'MARKET' && (
                            <div className="form-row">
                                <label>Price</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    className="input"
                                    value={newOrder.price || ''}
                                    onChange={(e) => setNewOrder({ ...newOrder, price: Number(e.target.value) })}
                                    placeholder="Enter price"
                                />
                            </div>
                        )}

                        <button
                            className="btn btn-primary btn-lg submit-order-btn"
                            onClick={handleSubmitOrder}
                        >
                            <Send size={16} />
                            Submit Order
                        </button>
                    </div>
                </div>

                {/* Open Orders */}
                <div className="card open-orders">
                    <div className="card-header">
                        <h3 className="card-title">Open Orders</h3>
                        <button className="btn btn-danger btn-sm" onClick={handleCancelAll}>
                            <X size={14} />
                            Cancel All
                        </button>
                    </div>

                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Symbol</th>
                                    <th>Side</th>
                                    <th>Type</th>
                                    <th>Qty</th>
                                    <th>Filled</th>
                                    <th>Price</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {orders.length > 0 ? orders.map((order) => (
                                    <tr key={order.id}>
                                        <td className="mono">{order.symbol}</td>
                                        <td>
                                            <span className={`badge ${order.side === 'BUY' ? 'badge-success' : 'badge-danger'}`}>
                                                {order.side}
                                            </span>
                                        </td>
                                        <td>{order.type}</td>
                                        <td className="mono">{order.quantity}</td>
                                        <td className="mono">{order.filled_quantity || 0}</td>
                                        <td className="mono">${order.price?.toFixed(2) || 'MKT'}</td>
                                        <td>
                                            <span className="flex items-center gap-sm">
                                                {getStatusIcon(order.status)}
                                                {order.status}
                                            </span>
                                        </td>
                                        <td>
                                            <button
                                                className="btn btn-ghost btn-sm"
                                                onClick={() => handleCancelOrder(order.id)}
                                            >
                                                <X size={14} />
                                            </button>
                                        </td>
                                    </tr>
                                )) : (
                                    <tr>
                                        <td colSpan={8} style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: 'var(--space-xl)' }}>
                                            No open orders
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Positions */}
                <div className="card positions">
                    <h3 className="card-title">Active Positions</h3>

                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Symbol</th>
                                    <th>Qty</th>
                                    <th>Entry</th>
                                    <th>Current</th>
                                    <th>Unrealized P&L</th>
                                    <th>Strategy</th>
                                </tr>
                            </thead>
                            <tbody>
                                {positions.length > 0 ? positions.map((pos) => (
                                    <tr key={pos.id}>
                                        <td className="mono">{pos.symbol}</td>
                                        <td className={pos.quantity >= 0 ? 'text-success' : 'text-danger'}>
                                            {pos.quantity >= 0 ? '+' : ''}{pos.quantity}
                                        </td>
                                        <td className="mono">${pos.entry_price?.toFixed(2)}</td>
                                        <td className="mono">${pos.current_price?.toFixed(2)}</td>
                                        <td className={pos.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}>
                                            {pos.unrealized_pnl >= 0 ? '+' : ''}${pos.unrealized_pnl?.toFixed(2)}
                                        </td>
                                        <td>{pos.strategy_name || '-'}</td>
                                    </tr>
                                )) : (
                                    <tr>
                                        <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: 'var(--space-xl)' }}>
                                            No active positions
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                    {positions.length > 0 && (
                        <div className="positions-summary">
                            <div className="summary-item">
                                <span>Total Unrealized P&L</span>
                                <span className={positions.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0) >= 0 ? 'text-success' : 'text-danger'}>
                                    ${positions.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0).toFixed(2)}
                                </span>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
