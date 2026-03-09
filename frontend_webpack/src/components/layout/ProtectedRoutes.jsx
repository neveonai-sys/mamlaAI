// ProtectedRoute.js
import React from 'react';
import { useSelector } from 'react-redux';
import { Navigate, Outlet } from 'react-router-dom';

const ProtectedRoute = ({ requiredRole, allowedRoles }) => {
  const { isAuthenticated, user_type } = useSelector((state) => state.user);

  if (isAuthenticated === null) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <p>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Check for allowedRoles first (if provided)
  if (allowedRoles && Array.isArray(allowedRoles) && !allowedRoles.includes(user_type)) {
    return <Navigate to="/home" replace />;
  }

  // Fallback to requiredRole for backward compatibility
  if (requiredRole && user_type !== requiredRole) {
    return <Navigate to="/home" replace />;
  }

  return <Outlet />;
};

export default ProtectedRoute;
