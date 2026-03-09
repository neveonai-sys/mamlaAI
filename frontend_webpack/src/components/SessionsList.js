import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import AxiosInstance from './common/AxiosInstance'; // Adjust the import path accordingly
import { clearUser, setUser } from '../features/userSlice';

const SessionsList = () => {
  const dispatch = useDispatch();
  const sessions = useSelector((state) => state.user.sessions);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleTerminateSession = async (session_id) => {
    if (!window.confirm('Are you sure you want to terminate this session?')) {
      return;
    }

    try {
      setLoading(true);
      await AxiosInstance.post('/users/invalidate-session/', { session_id });
      // Refresh session list
      const response = await AxiosInstance.get('/users/check-auth/');
      if (response.data.isAuthenticated) {
        dispatch(setUser({
          firstname: response.data.firstname,
          lastname: response.data.lastname,
          email: response.data.email_id,
          sessions: response.data.sessions,
        }));
      } else {
        dispatch(clearUser());
      }
      setError(null);
    } catch (err) {
      console.error('Error terminating session:', err);
      setError('Failed to terminate the session. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const renderSessions = () => {
    if (!sessions || sessions.length === 0) {
      return <p>No active sessions found.</p>;
    }

    return (
      <ul style={{ listStyleType: 'none', padding: 0 }}>
        {sessions.map((session) => (
          <li key={session.session_id} style={{ border: '1px solid #ccc', padding: '10px', marginBottom: '10px' }}>
            <p><strong>IP Address:</strong> {session.ip_address}</p>
            <p><strong>Location:</strong> {session.location}</p>
            <p><strong>Device Type:</strong> {session.device_type}</p>
            <p><strong>Login Time:</strong> {session.login_time}</p>
            <p><strong>Last Activity:</strong> {session.last_activity}</p>
            {session.is_current ? (
              <button disabled style={{ backgroundColor: '#ccc', cursor: 'not-allowed' }}>
                Current Session
              </button>
            ) : (
              <button onClick={() => handleTerminateSession(session.session_id)} disabled={loading}>
                Terminate Session
              </button>
            )}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div>
      <h3>Active Sessions</h3>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {loading && <p>Processing...</p>}
      {renderSessions()}
    </div>
  );
};

export default SessionsList;
