import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { useAuth } from '../app/AuthProvider.jsx';
export function SessionsPage() {
  const { user } = useAuth();
  return (
    <>
      <div className="page-heading">
        <div className="eyebrow">ACCOUNT SECURITY</div>
        <h1>Current session</h1>
        <p>Session cookies are HttpOnly and verified server-side.</p>
      </div>
      <div className="panel session-info">
        <ShieldCheck size={36} />
        <div>
          <h3>Authenticated session</h3>
          <p>User: {user?.display_name}</p>
          <p>Roles: {user?.roles.join(', ')}</p>
          <small>Sign out using the sidebar to revoke this session.</small>
        </div>
      </div>
    </>
  );
}
