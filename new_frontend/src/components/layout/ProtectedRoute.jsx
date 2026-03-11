import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useSelector } from 'react-redux';

export default function ProtectedRoute({ roles }) {
  const { isAuthenticated, user_type } = useSelector((s) => s.user);

  // Still probing authentication — render nothing (AppContent shows spinner)
  if (isAuthenticated === null) return null;

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (roles && roles.length > 0 && !roles.includes(user_type)) {
    return <Navigate to="/not-authorized" replace />;
  }

  return <Outlet />;
}
