import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import apiClient from '../../services/api';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import AuthShowcase from './AuthShowcase';
import MamlaLogo from '../common/MamlaLogo';

const USER_TYPE_OPTIONS = ['Lawyer', 'Client', 'Paralegal'];

export default function Signup() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [form, setForm] = useState({
    firstName: '',
    lastName: '',
    email: '',
    organization: '',
    user_type: 'Lawyer',
    password: '',
  });
  const [showPwd, setShowPwd] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (!agreed) {
      setError('Please accept the terms and conditions to continue.');
      return;
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setLoading(true);
    dispatch(beginBlocking({ message: 'Creating your account...' }));

    try {
      await apiClient.post('users/onboard/', {
        fname: form.firstName,
        lname: form.lastName,
        email: form.email,
        password: form.password,
        user_type: form.user_type,
        agreedTnC: true,
      });
      setSuccess('Account created! Please check your email to confirm, then sign in.');
    } catch (err) {
      const msg = err.response?.data?.message || err.response?.data?.error || err.message || 'Registration failed.';
      setError(msg);
    } finally {
      dispatch(stopBlocking());
      setLoading(false);
    }
  }

  return (
    <div className="flex-1 flex flex-col lg:flex-row min-h-screen bg-background-light">
      <AuthShowcase
        eyebrow="Create account"
        title="Set up your Mamla.AI workspace."
        description="Create an account to start drafting, reviewing documents, and managing chamber work from one system."
        highlights={[
          { title: 'Drafting', text: 'Prepare petitions, agreements, and replies in one workspace.' },
          { title: 'Documents', text: 'Review filings and exhibits with chamber context preserved.' },
          { title: 'Operations', text: 'Track schedules, updates, and team activity together.' },
        ]}
      />

      {/* ── Right form panel ──────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center bg-background-light p-6 sm:p-8 lg:min-h-screen lg:p-10 xl:p-12">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center justify-between">
            <Link to="/" className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:text-primary-dark transition-colors">
              <span className="material-symbols-outlined text-base">arrow_back</span>
              Back to Landing Page
            </Link>
          </div>

          {/* Mobile logo */}
          <div className="lg:hidden flex items-center mb-8">
            <MamlaLogo height={44} />
          </div>

          <div className="rounded-[1.75rem] border border-slate-200/80 bg-white p-7 shadow-card lg:p-8">
            <div className="mb-8">
              <h2 className="text-3xl font-bold text-ink mb-2">Create your account</h2>
              <p className="font-medium text-slate-600">Start your Mamla.AI workspace. No credit card required.</p>
            </div>

          {success ? (
            <div className="flex flex-col items-center gap-4 text-center py-8">
              <span className="material-symbols-outlined text-primary text-6xl icon-filled">mark_email_read</span>
              <h3 className="text-xl font-bold text-ink">Check Your Email</h3>
              <p className="text-sm text-slate-500">{success}</p>
              <Link to="/login" className="btn-primary mt-2">Go to Sign In</Link>
            </div>
          ) : (
            <form className="space-y-5" onSubmit={handleSubmit}>
              {/* Name row */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-semibold mb-2 text-slate-700" htmlFor="firstName">
                    First Name
                  </label>
                  <input
                    id="firstName"
                    name="firstName"
                    type="text"
                    required
                    placeholder="Priya"
                    value={form.firstName}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg
                               focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition-all"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-2 text-slate-700" htmlFor="lastName">
                    Last Name
                  </label>
                  <input
                    id="lastName"
                    name="lastName"
                    type="text"
                    required
                    placeholder="Doe"
                    value={form.lastName}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg
                               focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition-all"
                  />
                </div>
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-semibold mb-2 text-slate-700" htmlFor="email">
                  Professional Email
                </label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xl">mail</span>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    autoComplete="email"
                    placeholder="jane@lawfirm.com"
                    value={form.email}
                    onChange={handleChange}
                    className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-lg
                               focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition-all"
                  />
                </div>
              </div>

              {/* Organization */}
              <div>
                <label className="block text-sm font-semibold mb-2 text-slate-700" htmlFor="organization">
                  Law Firm / Organization
                </label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xl">corporate_fare</span>
                  <input
                    id="organization"
                    name="organization"
                    type="text"
                    placeholder="Doe &amp; Associates"
                    value={form.organization}
                    onChange={handleChange}
                    className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-lg
                               focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition-all"
                  />
                </div>
              </div>

              {/* User type */}
              <div>
                <label className="block text-sm font-semibold mb-2 text-slate-700">
                  Role
                </label>
                <div className="flex gap-2">
                  {USER_TYPE_OPTIONS.map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => setForm((f) => ({ ...f, user_type: opt }))}
                      className={`flex-1 py-2.5 text-sm font-semibold rounded-lg border transition-all ${
                        form.user_type === opt
                          ? 'bg-primary text-ivory border-primary'
                          : 'bg-slate-50 text-slate-600 border-slate-200 hover:border-primary/50'
                      }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-semibold mb-2 text-slate-700" htmlFor="password">
                  Secure Password
                </label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xl">lock</span>
                  <input
                    id="password"
                    name="password"
                    type={showPwd ? 'text' : 'password'}
                    required
                    placeholder="••••••••"
                    value={form.password}
                    onChange={handleChange}
                    className="w-full pl-10 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-lg
                               focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPwd((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    <span className="material-symbols-outlined text-xl">
                      {showPwd ? 'visibility_off' : 'visibility'}
                    </span>
                  </button>
                </div>
                <p className="mt-1.5 text-xs text-slate-500">At least 8 characters, including a number and symbol.</p>
              </div>

              {/* Terms */}
              <div className="flex items-start gap-3 py-1">
                <input
                  id="terms"
                  type="checkbox"
                  checked={agreed}
                  onChange={(e) => setAgreed(e.target.checked)}
                  className="h-4 w-4 mt-0.5 rounded border-slate-300 text-primary focus:ring-primary/30 bg-white flex-shrink-0"
                />
                <label htmlFor="terms" className="text-sm text-slate-600">
                  I agree to the{' '}
                  <a href="#" className="font-semibold text-primary hover:text-primary/80">
                    Terms of Service
                  </a>{' '}
                  and{' '}
                  <a href="#" className="font-semibold text-primary hover:text-primary/80">
                    Privacy Policy
                  </a>
                </label>
              </div>

              {/* Error */}
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
                className="w-full py-4 text-base font-bold text-ivory bg-primary hover:bg-primary/90
                           rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2
                           focus:ring-primary transition-all active:scale-[0.98]
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="material-symbols-outlined text-xl animate-spin">progress_activity</span>
                    Creating Account…
                  </span>
                ) : (
                  'Create Account'
                )}
              </button>
            </form>
          )}

            <p className="mt-6 text-center text-sm text-slate-500">
              Already have an account?{' '}
              <Link to="/login" className="font-semibold text-primary hover:text-primary/80">
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
