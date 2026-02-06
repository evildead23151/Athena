import { NavLink } from 'react-router-dom';
import { useAuthStore, useGlobalStore } from '../store';
import {
    LayoutDashboard,
    LineChart,
    ArrowRightLeft,
    Shield,
    Activity,
    ScrollText,
    Settings,
    LogOut,
    Triangle
} from 'lucide-react';
import './Sidebar.css';

const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/strategies', icon: LineChart, label: 'Strategies' },
    { path: '/execution', icon: ArrowRightLeft, label: 'Execution' },
    { path: '/risk', icon: Shield, label: 'Risk Manager' },
    { path: '/market', icon: Activity, label: 'Market Data' },
    { path: '/logs', icon: ScrollText, label: 'Logs' },
];

export default function Sidebar() {
    const { user, logout } = useAuthStore();
    const { systemStatus } = useGlobalStore();

    return (
        <aside className="sidebar">
            {/* Logo */}
            <div className="sidebar-header">
                <div className="logo">
                    <div className="logo-icon">
                        <Triangle size={24} />
                    </div>
                    <div className="logo-text">
                        <span className="logo-name">ATHENA</span>
                        <span className="logo-version">TERMINAL v4.2</span>
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <nav className="sidebar-nav">
                {navItems.map(({ path, icon: Icon, label }) => (
                    <NavLink
                        key={path}
                        to={path}
                        className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                    >
                        <Icon size={20} />
                        <span>{label}</span>
                    </NavLink>
                ))}
            </nav>

            {/* Bottom Section */}
            <div className="sidebar-footer">
                <NavLink to="/settings" className="nav-item">
                    <Settings size={20} />
                    <span>Settings</span>
                </NavLink>

                {/* User Info */}
                <div className="user-info">
                    <div className="user-avatar">
                        {user?.username?.charAt(0).toUpperCase() || 'A'}
                    </div>
                    <div className="user-details">
                        <span className="user-name">{user?.username || 'Admin User'}</span>
                        <span className="user-status">
                            <span className={`status-dot ${systemStatus === 'OPERATIONAL' ? 'active' : 'warning'}`} />
                            CONNECTED
                        </span>
                    </div>
                    <button className="logout-btn" onClick={logout} title="Logout">
                        <LogOut size={18} />
                    </button>
                </div>
            </div>
        </aside>
    );
}
