import React from 'react';
import { createRoot } from 'react-dom/client';
import { AuthProvider } from './app/AuthProvider.jsx';
import { AppRouter } from './app/Router.jsx';
import './styles/index.css';
createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  </React.StrictMode>,
);
