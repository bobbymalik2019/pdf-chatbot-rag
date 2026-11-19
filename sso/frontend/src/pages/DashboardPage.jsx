import React from 'react';
import { ShieldCheck, Users, KeyRound, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../app/AuthProvider.jsx';
export function DashboardPage() {
  const { user } = useAuth();
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">OVERVIEW</div>
          <h1>Identity dashboard</h1>
          <p>Manage identities and protect your connected applications.</p>
        </div>
      </div>
      <div className="stats">
        <div className="stat">
          <ShieldCheck size={22} />
          <span>Authentication</span>
          <strong>Active</strong>
          <small>SSO session established</small>
        </div>
        <div className="stat">
          <Users size={22} />
          <span>Signed in as</span>
          <strong>{user?.display_name}</strong>
          <small>{user?.roles.join(', ')}</small>
        </div>
        <div className="stat">
          <KeyRound size={22} />
          <span>Authorization</span>
          <strong>Roles enforced</strong>
          <small>Validated by FastAPI</small>
        </div>
      </div>
      {user?.roles.includes('ADMIN') && (
        <Link className="action-card" to="/users">
          <div>
            <strong>User management</strong>
            <p>Create accounts and manage global roles.</p>
          </div>
          <ArrowUpRight size={20} />
        </Link>
      )}
    </>
  );
}
