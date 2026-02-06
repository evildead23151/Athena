import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store';
import { Triangle, Eye, EyeOff } from 'lucide-react';

export default function Login() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const { login, loading, error } = useAuthStore();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        const success = await login(username, password);
        if (success) {
            navigate('/');
        }
    };

    return (
        <div className="login-container">
            <div className="login-box animate-scale-in">
                <div className="login-logo">
                    <div className="logo-icon" style={{
                        width: 48,
                        height: 48,
                        background: 'var(--primary)',
                        borderRadius: 'var(--radius-md)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}>
                        <Triangle size={28} color="white" />
                    </div>
                    <div>
                        <h1>ATHENA</h1>
                        <span>Quant Terminal v4.2</span>
                    </div>
                </div>

                <form className="login-form" onSubmit={handleSubmit}>
                    {error && (
                        <div className="login-error">
                            {error}
                        </div>
                    )}

                    <div className="form-group">
                        <label htmlFor="username">Username</label>
                        <input
                            id="username"
                            type="text"
                            className="input"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="Enter username"
                            required
                            autoFocus
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <div style={{ position: 'relative' }}>
                            <input
                                id="password"
                                type={showPassword ? 'text' : 'password'}
                                className="input"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter password"
                                required
                                style={{ paddingRight: 44 }}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                style={{
                                    position: 'absolute',
                                    right: 8,
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    background: 'none',
                                    border: 'none',
                                    color: 'var(--text-tertiary)',
                                    cursor: 'pointer',
                                    padding: 4
                                }}
                            >
                                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                    </div>

                    <button
                        type="submit"
                        className="btn btn-primary btn-lg"
                        disabled={loading}
                        style={{ marginTop: 'var(--space-md)' }}
                    >
                        {loading ? 'Authenticating...' : 'Sign In'}
                    </button>

                    <p style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-tertiary)',
                        textAlign: 'center',
                        marginTop: 'var(--space-lg)'
                    }}>
                        Demo credentials: <code>admin</code> / <code>admin123</code>
                    </p>
                </form>
            </div>
        </div>
    );
}
