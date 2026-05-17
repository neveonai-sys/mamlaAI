import React, { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import apiClient from '../../services/api';
import { setUser } from '../../features/userSlice';

function formatDate(str) {
  if (!str) return '—';
  try {
    return new Date(str).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return str;
  }
}

function DeviceIcon({ deviceType }) {
  const type = deviceType?.toLowerCase() ?? '';
  const icon = type.includes('mobile') ? 'smartphone' : type.includes('tablet') ? 'tablet' : 'computer';
  return <span className="material-symbols-outlined text-2xl text-primary/60">{icon}</span>;
}

function SessionCard({ session, onSignOut, signingOut }) {
  return (
    <div
      className={`rounded-2xl border p-5 transition-all ${
        session.is_current
          ? 'border-primary/30 bg-primary/5'
          : 'border-primary/10 bg-white hover:border-primary/20'
      }`}
    >
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 mt-0.5">
          <DeviceIcon deviceType={session.device_type} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-sm font-bold text-ink truncate">
              {session.device_type || 'Unknown device'}
            </span>
            {session.is_current && (
              <span className="text-[10px] font-black px-2 py-0.5 rounded-full bg-primary/10 text-primary uppercase tracking-wide">
                This device
              </span>
            )}
          </div>
          <div className="space-y-0.5">
            {session.ip_address && (
              <p className="text-xs text-slate-500 flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[14px]">location_on</span>
                {session.location && session.location !== 'Unknown' ? `${session.location} · ` : ''}
                {session.ip_address}
              </p>
            )}
            <p className="text-xs text-slate-500 flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[14px]">login</span>
              Signed in {formatDate(session.login_time)}
            </p>
            <p className="text-xs text-slate-400 flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[14px]">schedule</span>
              Last active {formatDate(session.last_activity)}
            </p>
          </div>
        </div>
      </div>

      {!session.is_current && (
        <div className="mt-4 pt-4 border-t border-primary/10 flex justify-end">
          <button
            onClick={() => onSignOut(session.session_id)}
            disabled={signingOut === session.session_id}
            className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-xs font-semibold text-red-600
                       transition-colors hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {signingOut === session.session_id ? 'Signing out…' : 'Sign out this device'}
          </button>
        </div>
      )}
    </div>
  );
}

export default function Sessions() {
  const dispatch = useDispatch();
  const reduxUser = useSelector((s) => s.user);
  const [sessions, setSessions] = useState(reduxUser.sessions ?? []);
  const [loading, setLoading] = useState(false);
  const [signingOut, setSigningOut] = useState(null);
  const [error, setError] = useState('');

  // Refresh sessions from check-auth on mount so data is always current
  useEffect(() => {
    setLoading(true);
    apiClient.get('users/check-auth/')
      .then((res) => {
        if (res.data?.sessions) {
          setSessions(res.data.sessions);
          dispatch(setUser({
            firstname: res.data.firstname ?? reduxUser.firstname,
            lastname: res.data.lastname ?? reduxUser.lastname,
            email: res.data.email_id ?? reduxUser.email,
            user_type: res.data.user_type ?? reduxUser.user_type,
            sessions: res.data.sessions,
          }));
        }
      })
      .catch(() => setError('Could not load sessions. Please refresh the page.'))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSignOut(sessionId) {
    setSigningOut(sessionId);
    setError('');
    try {
      await apiClient.post('users/invalidate-session/', { session_id: sessionId });
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    } catch (err) {
      setError(err.response?.data?.error_message || 'Failed to sign out that device. Please try again.');
    } finally {
      setSigningOut(null);
    }
  }

  const currentSession = sessions.find((s) => s.is_current);
  const otherSessions = sessions.filter((s) => !s.is_current);

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-primary">Security</p>
        <h1 className="mt-2 text-2xl font-black text-ink tracking-tight">Active Login Sessions</h1>
        <p className="mt-1 text-sm text-slate-500">
          These devices are currently signed in to your account. Sign out any devices you don't recognise.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="h-28 rounded-2xl border border-primary/10 bg-white animate-pulse" />
          ))}
        </div>
      ) : sessions.length === 0 ? (
        <div className="rounded-2xl border border-primary/10 bg-white p-10 text-center">
          <span className="material-symbols-outlined text-slate-300 text-5xl block mb-3">devices</span>
          <p className="text-sm font-semibold text-slate-500">No session data available.</p>
          <p className="text-xs text-slate-400 mt-1">Try refreshing the page.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {currentSession && (
            <section>
              <h2 className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500 mb-3">
                Current device
              </h2>
              <SessionCard session={currentSession} onSignOut={handleSignOut} signingOut={signingOut} />
            </section>
          )}

          {otherSessions.length > 0 ? (
            <section>
              <h2 className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500 mb-3">
                Other signed-in devices
              </h2>
              <div className="space-y-3">
                {otherSessions.map((s) => (
                  <SessionCard
                    key={s.session_id}
                    session={s}
                    onSignOut={handleSignOut}
                    signingOut={signingOut}
                  />
                ))}
              </div>
            </section>
          ) : (
            <div className="rounded-2xl border border-slate-100 bg-slate-50 px-5 py-4 text-sm text-slate-500">
              No other devices are signed in.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
