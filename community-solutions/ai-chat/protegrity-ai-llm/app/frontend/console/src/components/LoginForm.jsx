import { useState } from "react";
import "./LoginForm.css";

/**
 * LoginForm component for user authentication.
 * Displays a centered login card with username/password inputs.
 * 
 * @param {Object} props
 * @param {Function} props.onLogin - Callback when form is submitted: ({ username, password }) => void
 * @param {string} props.error - Error message to display
 * @param {boolean} props.loading - Whether login is in progress
 */
function LoginForm({ onLogin, error, loading }) {
  const defaultUsername = import.meta.env.VITE_DEMO_USERNAME || "Not configured";
  const defaultPassword = import.meta.env.VITE_DEMO_PASSWORD || "Not configured";
  const [username, setUsername] = useState(import.meta.env.VITE_DEMO_USERNAME || "");
  const [password, setPassword] = useState(import.meta.env.VITE_DEMO_PASSWORD || "");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!username || !password || loading) return;
    onLogin({ username, password });
  };

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-logo-container">
          <img 
            src="/images/white-logo.svg" 
            alt="Protegrity" 
            className="login-logo" 
          />
        </div>
        
        <h1 className="login-title">Sign in to Protegrity AI</h1>
        
        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label htmlFor="username" className="login-label">
              Username
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              className="login-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
              placeholder="Enter your username"
            />
          </div>

          <div className="login-field">
            <label htmlFor="password" className="login-label">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className="login-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              placeholder="Enter your password"
            />
          </div>

          {error && (
            <div className="login-error">
              <span className="login-error-icon">⚠️</span>
              {error}
            </div>
          )}

          <button 
            type="submit" 
            className="login-button"
            disabled={loading || !username || !password}
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        
        <p className="login-footnote">
          Use your Protegrity account credentials. Demo users may be seeded in development.
        </p>

        <div className="login-default-creds" aria-live="polite">
          <div className="login-default-creds-title">Default demo login (dev)</div>
          <div className="login-default-creds-row">
            <span className="login-default-creds-label">Username:</span>
            <span className="login-default-creds-value">{defaultUsername}</span>
          </div>
          <div className="login-default-creds-row">
            <span className="login-default-creds-label">Password:</span>
            <span className="login-default-creds-value">{defaultPassword}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginForm;
