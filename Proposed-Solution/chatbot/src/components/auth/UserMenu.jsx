import React, { useEffect, useRef, useState } from 'react';
import { ChevronDown, LogOut, Settings2, UserRound, SlidersHorizontal } from 'lucide-react';
import { signOut } from '../../services/authService';
import './UserMenu.css';

export default function UserMenu({ user }) {
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState('');
  const menuRef = useRef(null);

  // /auth/me currently supplies id and roles, not the user's name or email.
  // Show only information actually supplied by the authenticated Gateway.
  const name = user?.displayName || user?.name || 'Charter26 account';
  const detail = user?.email || (user?.id ? `ID: ${user.id.slice(0, 8)}…` : 'Signed in with Charter26 SSO');
  const initial = (user?.displayName || user?.name || 'U').charAt(0).toUpperCase();

  useEffect(() => {
    const handlePointerDown = (event) => {
      if (!menuRef.current?.contains(event.target)) setOpen(false);
    };
    const handleEscape = (event) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, []);

  async function handleLogout() {
    if (signingOut) return;
    setSigningOut(true);
    setError('');
    try {
      await signOut();
      window.location.replace('/signed-out');
    } catch {
      setError('Unable to sign out. Please try again.');
      setSigningOut(false);
    }
  }

  return (
    <div className="account-menu" ref={menuRef}>
      <button
        type="button"
        className="account-menu-trigger"
        aria-label="Account menu"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((previous) => !previous)}
      >
        <span className="account-menu-avatar account-menu-avatar-sm">{initial}</span>
        <span className="account-menu-trigger-label">My Account</span>
        <ChevronDown size={15} aria-hidden="true" />
      </button>

      {open && (
        <div className="account-menu-dropdown" aria-label="Account options">
          <div className="account-menu-identity">
            <span className="account-menu-avatar account-menu-avatar-lg">{initial}</span>
            <strong title={name}>{name}</strong>
            <span title={user?.email || user?.id || ''}>{detail}</span>
            <small>Charter26 SSO</small>
          </div>
          <div className="account-menu-actions">
            <button type="button" className="account-menu-action" disabled title="Coming later">
              <UserRound size={17} aria-hidden="true" />
              <span>My profile</span><small>Soon</small>
            </button>
            <button type="button" className="account-menu-action" disabled title="Coming later">
              <SlidersHorizontal size={17} aria-hidden="true" />
              <span>RAG &amp; LLM preferences</span><small>Soon</small>
            </button>
            <button type="button" className="account-menu-action" disabled title="Coming later">
              <Settings2 size={17} aria-hidden="true" />
              <span>Benchmarking</span><small>Soon</small>
            </button>
          </div>
          <div className="account-menu-separator" />
          <button type="button" className="account-menu-action account-menu-signout" disabled={signingOut} onClick={handleLogout}>
            <LogOut size={17} aria-hidden="true" />
            <span>{signingOut ? 'Signing out…' : 'Sign out'}</span>
          </button>
          {error && <p className="account-menu-error" role="alert">{error}</p>}
        </div>
      )}
    </div>
  );
}
