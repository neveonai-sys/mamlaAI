import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import apiClient from '../../services/api';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import AuthShowcase from './AuthShowcase';
import { useIconFont } from '../../hooks/useIconFont';

export default function ResetPassword() {
  useIconFont();
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();

  const [phase, setPhase] = useState('request'); // 'request' | 'set-new' | 'done'
  const [email, setEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  // Detect password-recovery hash from Supabase email link
  useEffect(() => {
    if (location.hash.includes('type=recovery')) {
      setPhase('set-new');
    }
  }, [location.hash]);

  async function handleRequest(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    dispatch(beginBlocking({ message: 'Sending reset link...' }));
    try {
      await apiClient.post('users/send-reset-password-link/', { email_id: email });
      setMessage('Password reset email sent! Please check your inbox.');
    } catch (err) {
      const msg = err.response?.data?.message || err.message || 'Failed to send reset email.';
      setError(msg);
    } finally {
      dispatch(stopBlocking());
      setLoading(false);
    }
  }

  async function handleSetNew(e) {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setError('');
    setLoading(true);
    dispatch(beginBlocking({ message: 'Updating your password...' }));
    try {
      // Extract recovery token from URL hash (Supabase email link format)
      const hashParams = new URLSearchParams(location.hash.replace('#', '?'));
      const recoveryToken = hashParams.get('access_token');
      if (!recoveryToken) throw new Error('Recovery token not found. Please request a new reset link.');
      await apiClient.post('users/reset-user-password/', {
        recovery_access_token: recoveryToken,
        new_password: newPassword,
      });
      setPhase('done');
    } catch (err) {
      const msg = err.response?.data?.message || err.message || 'Failed to update password.';
      setError(msg);
    } finally {
      dispatch(stopBlocking());
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen w-full flex-col bg-background-light lg:flex-row">
      <AuthShowcase
        eyebrow="Password reset"
        title="Recover access without leaving the chamber flow."
        description="Reset your password and return to the same drafting, document, and operations workspace without a separate auth experience."
        highlights={[
          { title: 'Recover', text: 'Request a reset link and continue with minimal friction.' },
          { title: 'Secure', text: 'Recovery links stay scoped to verified account access.' },
          { title: 'Return', text: 'Go straight back into the active Mamla.AI workspace.' },
        ]}
      />

      <div className="flex w-full flex-col justify-center bg-background-light px-6 py-6 lg:min-h-screen lg:w-1/2 lg:px-20 lg:py-8 xl:px-28">
        <div className="mx-auto w-full max-w-md rounded-[1.75rem] border border-slate-200/80 bg-white p-7 shadow-card lg:p-8">
          <div className="mb-8 flex items-center justify-between">
            <Link to="/" className="inline-flex items-center gap-2 text-sm font-semibold text-primary transition-colors hover:text-primary-dark">
              <span className="material-symbols-outlined text-base">arrow_back</span>
              Back to Landing Page
            </Link>
          </div>

          <div className="mb-8 lg:hidden">
            <div className="flex items-center gap-2 text-primary">
              <span className="material-symbols-outlined text-3xl icon-filled">gavel</span>
              <span className="text-xl font-semibold tracking-tight text-ink">Mamla.AI</span>
            </div>
          </div>

          {phase === 'request' && (
            <>
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-ink mb-2">Reset your password</h2>
                <p className="text-sm font-medium leading-7 text-slate-600">
                  Enter your email address and we&apos;ll send you a link to reset your password.
                </p>
              </div>

              {message ? (
                <div className="flex flex-col items-center gap-3 py-6 text-center">
                  <span className="material-symbols-outlined text-primary text-5xl icon-filled">mark_email_read</span>
                  <p className="text-sm text-slate-600">{message}</p>
                  <Link to="/login" className="btn-primary mt-2">Back to Sign In</Link>
                </div>
              ) : (
                <form onSubmit={handleRequest} className="space-y-5">
                  <div>
                    <label className="block text-sm font-semibold mb-2 text-slate-700" htmlFor="email">
                      Email Address
                    </label>
                    <input
                      id="email"
                      type="email"
                      required
                      placeholder="name@firm.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full px-4 py-3.5 bg-white border border-slate-200 rounded-lg
                                 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none
                                 transition-all text-ink placeholder:text-slate-400"
                    />
                  </div>
                  {error && (
                    <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                      <span className="material-symbols-outlined text-base">error</span>
                      {error}
                    </div>
                  )}
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3.5 font-bold text-ivory bg-primary hover:bg-primary/90
                               rounded-lg transition-all disabled:opacity-50"
                  >
                    {loading ? 'Sending…' : 'Send Reset Link'}
                  </button>
                </form>
              )}
            </>
          )}

          {phase === 'set-new' && (
            <>
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-ink mb-2">Set new password</h2>
                <p className="text-sm font-medium leading-7 text-slate-600">Choose a strong new password for your account.</p>
              </div>
              <form onSubmit={handleSetNew} className="space-y-5">
                <div>
                  <label className="block text-sm font-semibold mb-2 text-slate-700" htmlFor="new-pwd">
                    New Password
                  </label>
                  <div className="relative">
                    <input
                      id="new-pwd"
                      type={showPwd ? 'text' : 'password'}
                      required
                      placeholder="••••••••"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full px-4 py-3.5 bg-white border border-slate-200 rounded-lg pr-12
                                 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPwd((v) => !v)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      <span className="material-symbols-outlined text-xl">
                        {showPwd ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-2 text-slate-700" htmlFor="confirm-pwd">
                    Confirm Password
                  </label>
                  <input
                    id="confirm-pwd"
                    type="password"
                    required
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full px-4 py-3.5 bg-white border border-slate-200 rounded-lg
                               focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                  />
                </div>
                {error && (
                  <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                    <span className="material-symbols-outlined text-base">error</span>
                    {error}
                  </div>
                )}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3.5 font-bold text-ivory bg-primary hover:bg-primary/90
                             rounded-lg transition-all disabled:opacity-50"
                >
                  {loading ? 'Updating…' : 'Update Password'}
                </button>
              </form>
            </>
          )}

          {phase === 'done' && (
            <div className="flex flex-col items-center gap-4 py-8 text-center">
              <span className="material-symbols-outlined text-primary text-6xl icon-filled">check_circle</span>
              <h3 className="text-xl font-bold text-ink">Password Updated!</h3>
              <p className="text-sm font-medium text-slate-600">Your password has been successfully changed.</p>
              <button className="btn-primary mt-2" onClick={() => navigate('/login')}>
                Sign In with New Password
              </button>
            </div>
          )}
        </div>

        <p className="mt-6 text-center text-sm text-slate-500">
          <Link to="/login" className="font-semibold text-primary hover:text-primary/80">
            ← Back to Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}
