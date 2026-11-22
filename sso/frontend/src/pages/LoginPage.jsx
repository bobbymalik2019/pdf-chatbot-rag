import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ShieldCheck, LockKeyhole, ArrowRight } from 'lucide-react';
import { useAuth } from '../app/AuthProvider.jsx';
export function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState(''),
    [password, setPassword] = useState(''),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  const rawNext = params.get('next') || '';
  // Only permit internal OAuth authorization continuation (never arbitrary external redirects).
  const destination =
    rawNext.startsWith('/oauth/authorize?') && !rawNext.includes('\\') && !rawNext.includes('\n')
      ? rawNext
      : '/dashboard';
  useEffect(() => {
    if (user) {
      if (destination.startsWith('/oauth/')) window.location.assign(destination);
      else navigate(destination, { replace: true });
    }
  }, [user, destination, navigate]);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(email, password);
    } catch (ex) {
      setError(ex.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-root">
      <div className="login-story">
        <div className="story-logo">
          <img
            src="/branding/charter26.svg"
            alt="Charter26 logo"
            className="story-brand-logo"
          />
      <span>Single Sign-On</span>
        </div>
        <div>
          <div className="kicker">TRUSTED IDENTITY PLATFORM</div>
          <h1>
            One identity.
            <br />
            Every application.
          </h1>
          <p>
            Centralized authentication and administrative controls, built around secure application
            boundaries.
          </p>
        </div>
        <div className="story-bottom">
          Authentication & Authorization · Secure sessions · Access control
        </div>
      </div>
      <div className="login-pane">
        <div className="login-card">
          <div className="lock-badge">
            <LockKeyhole size={24} />
          </div>
          <h2>Welcome back</h2>
          <p>Sign in to your identity workspace.</p>
          <form onSubmit={submit}>
            <label>
              Email address
              <input
                autoComplete="username"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="admin@example.com"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <button className="primary full" disabled={busy}>
              {busy ? 'Signing in…' : 'Sign in'}
              <ArrowRight size={16} />
            </button>
          </form>
          <div className="footnote">Accounts are provisioned by your SSO administrator.</div>
        </div>
      </div>
    </div>
  );
}
