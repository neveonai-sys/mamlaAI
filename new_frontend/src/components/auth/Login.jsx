import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { setUser, clearUser } from '../../features/userSlice';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import apiClient from '../../services/api';
import AuthShowcase from './AuthShowcase';
import MamlaLogo from '../common/MamlaLogo';

export default function Login() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    dispatch(beginBlocking({ message: 'Signing you in...' }));

    try {
      // Backend handles Supabase auth and sets HttpOnly cookie
      await apiClient.post('users/login-user/', { email, password });

      // Fetch user info via cookie (auto-sent by browser)
      const res = await apiClient.get('users/check-auth/');
      if (res.data?.isAuthenticated) {
        dispatch(setUser({
          firstname: res.data.firstname,
          lastname: res.data.lastname,
          email: res.data.email_id,
          user_type: res.data.user_type,
          sessions: res.data.sessions,
        }));
        navigate('/dashboard', { replace: true });
      } else {
        throw new Error('Authentication check failed.');
      }
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.message || err.message || 'Login failed.';
      setError(msg);
      dispatch(clearUser());
    } finally {
      dispatch(stopBlocking());
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen w-full flex-col lg:flex-row bg-background-light">
      <AuthShowcase
        eyebrow="Sign in"
        title="Access your Mamla.AI workspace."
        description="Continue with drafting, document review, court updates, and chamber operations from one place."
        highlights={[
          { title: 'Drafting', text: 'Open active drafts, edits, and saved matter work.' },
          { title: 'Documents', text: 'Continue document analysis and chamber research.' },
          { title: 'Secure', text: 'Protected access for counsel, clients, and paralegals.' },
        ]}
      />

      {/* ── Right form panel ──────────────────────────────────── */}
      <div className="flex w-full flex-col justify-center px-6 py-6 lg:min-h-screen lg:w-1/2 lg:px-20 lg:py-8 xl:px-28 bg-background-light">
        <div className="mx-auto w-full max-w-md rounded-[1.75rem] border border-slate-200/80 bg-white p-7 shadow-card lg:p-8">
          <div className="mb-8 flex items-center justify-between">
            <Link to="/" className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:text-primary-dark transition-colors">
              <span className="material-symbols-outlined text-base">arrow_back</span>
              Back to Landing Page
            </Link>
          </div>

          {/* Mobile logo */}
          <div className="lg:hidden flex items-center mb-10">
            <MamlaLogo height={44} />
          </div>

          <div className="mb-8">
            <h2 className="text-3xl font-bold text-ink tracking-tight">Welcome Back</h2>
            <p className="mt-2 font-medium leading-7 text-slate-600">
              Please enter your credentials to access your dashboard.
            </p>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* Email */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700" htmlFor="email">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                placeholder="name@firm.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3.5 bg-white border border-slate-200 rounded-lg
                           focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none
                           transition-all text-ink placeholder:text-slate-400"
              />
            </div>

            {/* Password */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-slate-700" htmlFor="password">
                  Password
                </label>
                <Link
                  to="/reset-password"
                  className="text-sm font-semibold text-primary hover:text-primary/80 transition-colors"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={showPwd ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3.5 bg-white border border-slate-200 rounded-lg pr-12
                             focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none
                             transition-all text-ink placeholder:text-slate-400"
                />
                <button
                  type="button"
                  onClick={() => setShowPwd((v) => !v)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                >
                  <span className="material-symbols-outlined text-xl">
                    {showPwd ? 'visibility_off' : 'visibility'}
                  </span>
                </button>
              </div>
            </div>

            {/* Error message */}
            {error && (
              <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                <span className="material-symbols-outlined text-base flex-shrink-0">error</span>
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-4 px-4 rounded-lg shadow-sm text-base
                         font-bold text-ivory bg-primary hover:bg-primary/90
                         focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary
                         transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-xl animate-spin">progress_activity</span>
                  Signing In…
                </span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Sign up link */}
          <p className="mt-8 text-center text-sm text-slate-500">
            Don&apos;t have an account?{' '}
            <Link to="/signup" className="font-semibold text-primary hover:text-primary/80 transition-colors">
              Create one free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
