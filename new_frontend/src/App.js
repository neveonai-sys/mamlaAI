import React, { useEffect } from 'react';
import { BrowserRouter as Router, useNavigate } from 'react-router-dom';
import AppContent from './AppContent';
import GlobalLoadingOverlay from './components/common/GlobalLoadingOverlay';
import { setupResponseInterceptors } from './services/api';

// Inner wrapper to get access to `useNavigate` for Axios interceptor setup
function AppInner() {
  const navigate = useNavigate();
  useEffect(() => {
    setupResponseInterceptors(navigate);
  }, [navigate]);
  return (
    <>
      <AppContent />
      <GlobalLoadingOverlay />
    </>
  );
}

export default function App() {
  return (
    <Router>
      <AppInner />
    </Router>
  );
}
