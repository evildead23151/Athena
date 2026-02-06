import { useState, useEffect } from 'react';
import { useGlobalStore } from '../store';
import {
    Monitor,
    Clock,
    Bell,
    Wifi,
    WifiOff
} from 'lucide-react';
import './Header.css';

export default function Header() {
    const { systemStatus, marketStatus, feedLatency, openOrders, activeStrategies } = useGlobalStore();
    const [currentTime, setCurrentTime] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    const formatTime = (date) => {
        return date.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    };

    return (
        <header className="app-header">
            <div className="header-left">
                <div className="system-status">
                    <Monitor size={16} />
                    <span>SYSTEM STATUS:</span>
                    <span className={`status-badge ${systemStatus === 'OPERATIONAL' ? 'success' : 'warning'}`}>
                        {systemStatus}
                    </span>
                </div>
            </div>

            <div className="header-right">
                {/* Live Indicator */}
                <div className="header-item live-indicator">
                    {marketStatus === 'CONNECTED' ? (
                        <Wifi size={14} className="text-success" />
                    ) : (
                        <WifiOff size={14} className="text-danger" />
                    )}
                    <span className="text-success">LIVE: {feedLatency}ms</span>
                </div>

                {/* Market Feed */}
                <div className="header-item">
                    <span className="header-label">BLOOMBERG_L1</span>
                </div>

                {/* UTC Time */}
                <div className="header-item time-display">
                    <Clock size={14} />
                    <span>UTC {formatTime(currentTime)}</span>
                </div>

                {/* Notifications */}
                <button className="header-btn notification-btn">
                    <Bell size={18} />
                    <span className="notification-badge">3</span>
                </button>

                {/* User Menu */}
                <button className="header-btn user-btn">
                    <div className="user-avatar-sm">A</div>
                </button>
            </div>
        </header>
    );
}
