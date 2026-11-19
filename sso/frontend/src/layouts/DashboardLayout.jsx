import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { ShieldCheck, LayoutDashboard, Users, Monitor, LogOut } from 'lucide-react';
import { useAuth } from '../app/AuthProvider.jsx';
export function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  async function signOut() {
    await logout();
    navigate('/login', { replace: true });
  }
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">
          <ShieldCheck size={28} />
          <span>
            Sentinel <small>SSO Platform</small>
          </span>
        </div>
        <div className="side-caption">IDENTITY MANAGEMENT</div>
        <NavLink
          to="/dashboard"
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <LayoutDashboard size={18} />
          Overview
        </NavLink>
        {user?.roles.includes('ADMIN') && (
          <NavLink to="/users" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Users size={18} />
            Users & Roles
          </NavLink>
        )}
        <NavLink
          to="/sessions"
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <Monitor size={18} />
          Session
        </NavLink>
        <div className="side-footer">
          <div className="avatar">{user?.display_name?.[0]?.toUpperCase()}</div>
          <div className="identity">
            <strong>{user?.display_name}</strong>
            <small>{user?.roles.join(', ')}</small>
          </div>
          <button className="icon-btn" title="Sign out" onClick={signOut}>
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <div className="main">
        <header className="top">
          <span>Identity Administration</span>
          <span className="environment">LOCAL ENVIRONMENT</span>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
