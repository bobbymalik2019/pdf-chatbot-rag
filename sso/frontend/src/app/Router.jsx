import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './AuthProvider.jsx';
import { DashboardLayout } from '../layouts/DashboardLayout.jsx';
import { LoginPage } from '../pages/LoginPage.jsx';
import { DashboardPage } from '../pages/DashboardPage.jsx';
import { UsersPage } from '../pages/UsersPage.jsx';
import { SessionsPage } from '../pages/SessionsPage.jsx';
function Guard({ children, role }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-center">Checking session…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (role && !user.roles.includes(role)) return <Navigate to="/dashboard" replace />;
  return children;
}
export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <Guard>
              <DashboardLayout />
            </Guard>
          }
        >
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route
            path="/users"
            element={
              <Guard role="ADMIN">
                <UsersPage />
              </Guard>
            }
          />
          <Route path="/sessions" element={<SessionsPage />} />
        </Route>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<div className="page-center">Page not found</div>} />
      </Routes>
    </BrowserRouter>
  );
}
