import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore, useGlobalStore } from './store';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import Strategies from './pages/Strategies';
import Execution from './pages/Execution';
import RiskManager from './pages/RiskManager';
import MarketData from './pages/MarketData';
import Logs from './pages/Logs';
import Login from './pages/Login';
import './App.css';
import './pages/pages.css';

function ProtectedRoute({ children }) {
    const { isAuthenticated, token, fetchUser } = useAuthStore();

    useEffect(() => {
        if (token && !isAuthenticated) {
            fetchUser();
        }
    }, [token]);

    if (!token) {
        return <Navigate to="/login" replace />;
    }

    return children;
}

function AppLayout() {
    const { fetchGlobalState } = useGlobalStore();

    useEffect(() => {
        // Initial fetch
        fetchGlobalState();

        // Poll for updates every 5 seconds
        const interval = setInterval(fetchGlobalState, 5000);

        return () => clearInterval(interval);
    }, []);

    return (
        <div className="app-container">
            <Sidebar />
            <div className="main-content">
                <Header />
                <div className="page-content">
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/strategies" element={<Strategies />} />
                        <Route path="/execution" element={<Execution />} />
                        <Route path="/risk" element={<RiskManager />} />
                        <Route path="/market" element={<MarketData />} />
                        <Route path="/logs" element={<Logs />} />
                    </Routes>
                </div>
            </div>
        </div>
    );
}

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route
                    path="/*"
                    element={
                        <ProtectedRoute>
                            <AppLayout />
                        </ProtectedRoute>
                    }
                />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
