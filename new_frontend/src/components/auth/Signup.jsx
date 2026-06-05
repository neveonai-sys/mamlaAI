import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import apiClient from '../../services/api';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import AuthShowcase from './AuthShowcase';
import MamlaLogo from '../common/MamlaLogo';
import { useIconFont } from '../../hooks/useIconFont';
import { usePostHog } from '@posthog/react';

const USER_TYPE_OPTIONS = [
  { value: 'Lawyer',    label: 'Lawyer',           desc: 'I practice law' },
  { value: 'Client',   label: 'Nagrik (Citizen)',  desc: 'I need legal help' },
  { value: 'Paralegal', label: 'Paralegal',         desc: 'I assist a legal team' },
];

const INPUT_CLS = `w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg
                   focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition-all`;
const ICON_INPUT_CLS = `w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-lg
                         focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition-all`;
const LABEL_CLS = 'block text-sm font-semibold mb-2 text-slate-700';

export default function Signup() {
  useIconFont();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const posthog = usePostHog();

  const [form, setForm] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    whatsappOptIn: false,
    user_type: 'Lawyer',
    barcode_id: '',
    law_firm_name: '',
    state_code: '',
    state_name: '',
    dist_code: '',
    dist_name: '',
    password: '',
  });
  const [showPwd, setShowPwd] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showConfirmPwd, setShowConfirmPwd] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Email existence check
  const [emailChecking, setEmailChecking] = useState(false);
  const [emailExists, setEmailExists] = useState(null); // null | true | false

  // Court location dropdowns
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [loadingDistricts, setLoadingDistricts] = useState(false);

  // Load states on mount
  useEffect(() => {
    apiClient.get('users/get-states/')
      .then((res) => {
        const data = Array.isArray(res.data) ? res.data : [];
        setStates(data);
      })
      .catch(() => {}); // optional field — silent fail
  }, []);

  // Load districts when state changes
  useEffect(() => {
    if (!form.state_code) {
      setDistricts([]);
      return;
    }
    setLoadingDistricts(true);
    setDistricts([]);
    apiClient.get(`users/get-districts/?state_code=${form.state_code}`)
      .then((res) => {
        const data = Array.isArray(res.data) ? res.data : [];
        setDistricts(data);
      })
      .catch(() => {})
      .finally(() => setLoadingDistricts(false));
  }, [form.state_code]);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
  }

  function handleStateChange(e) {
    const opt = e.target.options[e.target.selectedIndex];
    setForm((f) => ({
      ...f,
      state_code: e.target.value,
      state_name: opt.text === '— Select State —' ? '' : opt.text,
      dist_code: '',
      dist_name: '',
    }));
  }

  function handleDistrictChange(e) {
    const opt = e.target.options[e.target.selectedIndex];
    setForm((f) => ({
      ...f,
      dist_code: e.target.value,
      dist_name: opt.text === '— Select District —' ? '' : opt.text,
    }));
  }

  async function handleEmailBlur() {
    const email = form.email.trim();
    if (!email.includes('@')) return;
    setEmailChecking(true);
    setEmailExists(null);
    try {
      const res = await apiClient.post('users/check-existing-user/', { email });
      setEmailExists(res.data?.exists ?? null);
    } catch {
      setEmailExists(null); // don't block on network error
    } finally {
      setEmailChecking(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (!agreed) {
      setError('Please accept the terms and conditions to continue.');
      return;
    }
    if (emailExists === true) {
      setError('An account with this email already exists. Please sign in instead.');
      return;
    }
    if (form.phone && !/^\d{10}$/.test(form.phone)) {
      setError('Enter a valid 10-digit mobile number (without country code).');
      return;
    }
    const pwdRules = {
      length: form.password.length >= 8,
      upper: /[A-Z]/.test(form.password),
      lower: /[a-z]/.test(form.password),
      number: /[0-9]/.test(form.password),
      symbol: /[^A-Za-z0-9]/.test(form.password),
    };
    if (!Object.values(pwdRules).every(Boolean)) {
      setError('Password must be at least 8 characters and include 1 uppercase letter, 1 lowercase letter, 1 number, and 1 symbol.');
      return;
    }
    if (confirmPassword !== form.password) {
      setError('Passwords do not match. Please re-enter your password.');
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
        agreedTnC: agreed,
        phonenumber: form.phone ? `+91${form.phone}` : '',
        whatsappOptIn: form.whatsappOptIn,
        barcode_id: form.user_type === 'Lawyer' ? form.barcode_id.trim() : '',
        organization: form.user_type === 'Lawyer' ? form.law_firm_name.trim() : '',
        state: form.state_name,
        district: form.dist_name,
        courts: [],
      });
      // Record T&C + Privacy Policy consent at signup time
      try {
        await apiClient.post('users/consent-events/', {
          consent_type: 'terms_of_service',
          preferences: { agreed: true },
          source: 'signup',
        });
        await apiClient.post('users/consent-events/', {
          consent_type: 'privacy_policy',
          preferences: { agreed: true },
          source: 'signup',
        });
      } catch (_) { /* consent recording is non-blocking */ }

      posthog?.identify(form.email, {
        email: form.email,
        name: `${form.firstName} ${form.lastName}`.trim(),
        user_type: form.user_type,
      });
      posthog?.capture('user_signed_up', {
        user_type: form.user_type,
        has_bar_id: !!form.barcode_id,
        has_phone: !!form.phone,
        whatsapp_opt_in: form.whatsappOptIn,
        state: form.state_name || null,
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

                {/* ── Name ── */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={LABEL_CLS} htmlFor="firstName">First Name</label>
                    <input
                      id="firstName" name="firstName" type="text" required
                      placeholder="Priya" value={form.firstName} onChange={handleChange}
                      className={INPUT_CLS}
                    />
                  </div>
                  <div>
                    <label className={LABEL_CLS} htmlFor="lastName">Last Name</label>
                    <input
                      id="lastName" name="lastName" type="text" required
                      placeholder="Sharma" value={form.lastName} onChange={handleChange}
                      className={INPUT_CLS}
                    />
                  </div>
                </div>

                {/* ── Email ── */}
                <div>
                  <label className={LABEL_CLS} htmlFor="email">Professional Email</label>
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xl">mail</span>
                    <input
                      id="email" name="email" type="email" required autoComplete="email"
                      placeholder="you@lawfirm.com" value={form.email}
                      onChange={(e) => { handleChange(e); setEmailExists(null); }}
                      onBlur={handleEmailBlur}
                      className={`${ICON_INPUT_CLS} ${emailExists === true ? 'border-red-400 focus:ring-red-300' : emailExists === false ? 'border-emerald-400 focus:ring-emerald-300' : ''}`}
                    />
                  </div>
                  {emailChecking && (
                    <p className="mt-1 flex items-center gap-1 text-xs text-slate-400">
                      <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                      Checking…
                    </p>
                  )}
                  {emailExists === true && !emailChecking && (
                    <p className="mt-1 flex items-center gap-1 text-xs text-red-600">
                      <span className="material-symbols-outlined text-sm">error</span>
                      An account with this email already exists.{' '}
                      <Link to="/login" className="underline font-semibold">Sign in</Link>
                    </p>
                  )}
                  {emailExists === false && !emailChecking && (
                    <p className="mt-1 flex items-center gap-1 text-xs text-emerald-600">
                      <span className="material-symbols-outlined text-sm">check_circle</span>
                      Email is available.
                    </p>
                  )}
                </div>

                {/* ── Phone ── */}
                <div>
                  <label className={LABEL_CLS} htmlFor="phone">WhatsApp / Mobile Number</label>
                  <div className="flex gap-2 items-stretch">
                    <span className="inline-flex items-center px-3 rounded-lg border border-slate-200 bg-slate-100 text-slate-500 text-sm font-semibold select-none">
                      +91
                    </span>
                    <input
                      id="phone" name="phone" type="tel"
                      maxLength={10} pattern="[0-9]{10}"
                      placeholder="9876543210"
                      value={form.phone} onChange={handleChange}
                      className={`flex-1 ${INPUT_CLS}`}
                    />
                  </div>
                  <label className="mt-2 flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox" name="whatsappOptIn"
                      checked={form.whatsappOptIn} onChange={handleChange}
                      className="h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary/30 bg-white flex-shrink-0"
                    />
                    <span className="text-xs text-slate-600">Send case updates on WhatsApp</span>
                  </label>
                </div>

                {/* ── User type ── */}
                <div>
                  <label className={LABEL_CLS}>I am a</label>
                  <div className="flex gap-2">
                    {USER_TYPE_OPTIONS.map((opt) => (
                      <button
                        key={opt.value} type="button"
                        onClick={() => setForm((f) => ({ ...f, user_type: opt.value, barcode_id: '', law_firm_name: '' }))}
                        className={`flex-1 py-2.5 px-2 text-sm font-semibold rounded-lg border transition-all text-center ${
                          form.user_type === opt.value
                            ? 'bg-primary text-ivory border-primary'
                            : 'bg-slate-50 text-slate-600 border-slate-200 hover:border-primary/50'
                        }`}
                      >
                        <span className="block text-sm font-bold">{opt.label}</span>
                        <span className={`block text-[10px] mt-0.5 ${form.user_type === opt.value ? 'text-ivory/70' : 'text-slate-400'}`}>
                          {opt.desc}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* ── Lawyer-only fields ── */}
                {form.user_type === 'Lawyer' && (
                  <div className="space-y-4 rounded-xl border border-primary/10 bg-slate-50 p-4">
                    <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Lawyer Details</p>
                    <div>
                      <label className={LABEL_CLS} htmlFor="barcode_id">Bar Council Enrolment No.</label>
                      <div className="relative">
                        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xl">badge</span>
                        <input
                          id="barcode_id" name="barcode_id" type="text"
                          placeholder="MH/1234/2010"
                          value={form.barcode_id} onChange={handleChange}
                          className={ICON_INPUT_CLS}
                        />
                      </div>
                    </div>
                    <div>
                      <label className={LABEL_CLS} htmlFor="law_firm_name">Law Firm / Chamber Name <span className="font-normal text-slate-400">(optional)</span></label>
                      <div className="relative">
                        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xl">corporate_fare</span>
                        <input
                          id="law_firm_name" name="law_firm_name" type="text"
                          placeholder="Doe &amp; Associates"
                          value={form.law_firm_name} onChange={handleChange}
                          className={ICON_INPUT_CLS}
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* ── Court location (state + district, all user types, optional) ── */}
                <div>
                  <label className={LABEL_CLS}>
                    Primary Court Location{' '}
                    <span className="font-normal text-slate-400">(optional)</span>
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    {/* State */}
                    <div>
                      <select
                        value={form.state_code} onChange={handleStateChange}
                        className={`${INPUT_CLS} text-sm`}
                      >
                        <option value="">— Select State —</option>
                        {states.map((s) => (
                          <option key={s.state_code} value={s.state_code}>{s.name}</option>
                        ))}
                      </select>
                    </div>
                    {/* District */}
                    <div>
                      <select
                        value={form.dist_code} onChange={handleDistrictChange}
                        disabled={!form.state_code || loadingDistricts}
                        className={`${INPUT_CLS} text-sm disabled:opacity-50 disabled:cursor-not-allowed`}
                      >
                        <option value="">
                          {loadingDistricts ? 'Loading…' : !form.state_code ? '— Select State first —' : '— Select District —'}
                        </option>
                        {districts.map((d) => (
                          <option key={d.dist_code} value={d.dist_code}>{d.name}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* ── Password ── */}
                <div>
                  <label className={LABEL_CLS} htmlFor="password">Secure Password</label>
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xl">lock</span>
                    <input
                      id="password" name="password"
                      type={showPwd ? 'text' : 'password'}
                      required placeholder="••••••••"
                      value={form.password} onChange={handleChange}
                      className={`${ICON_INPUT_CLS} pr-12`}
                    />
                    <button
                      type="button" onClick={() => setShowPwd((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      <span className="material-symbols-outlined text-xl">
                        {showPwd ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                  {form.password.length > 0 && (() => {
                    const rules = [
                      { key: 'length', label: 'At least 8 characters',    ok: form.password.length >= 8 },
                      { key: 'upper',  label: '1 uppercase letter (A–Z)', ok: /[A-Z]/.test(form.password) },
                      { key: 'lower',  label: '1 lowercase letter (a–z)', ok: /[a-z]/.test(form.password) },
                      { key: 'number', label: '1 number (0–9)',            ok: /[0-9]/.test(form.password) },
                      { key: 'symbol', label: '1 symbol (!@#$…)',          ok: /[^A-Za-z0-9]/.test(form.password) },
                    ];
                    const allOk = rules.every((r) => r.ok);
                    return (
                      <div className={`mt-2 rounded-lg border px-3 py-2.5 ${
                        allOk ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-slate-50'
                      }`}>
                        <ul className="space-y-1">
                          {rules.map((r) => (
                            <li key={r.key} className="flex items-center gap-2 text-xs">
                              <span className={`material-symbols-outlined text-sm ${
                                r.ok ? 'text-emerald-600' : 'text-slate-300'
                              }`}>
                                {r.ok ? 'check_circle' : 'radio_button_unchecked'}
                              </span>
                              <span className={r.ok ? 'text-emerald-700 font-medium' : 'text-slate-500'}>{r.label}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    );
                  })()}
                  {form.password.length === 0 && (
                    <p className="mt-1.5 text-xs text-slate-400">At least 8 characters including 1 uppercase, 1 lowercase, 1 number, and 1 symbol.</p>
                  )}
                </div>

                {/* ── Confirm Password ── */}
                <div>
                  <label className={LABEL_CLS} htmlFor="confirmPassword">Confirm Password</label>
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xl">lock</span>
                    <input
                      id="confirmPassword" name="confirmPassword"
                      type={showConfirmPwd ? 'text' : 'password'}
                      required placeholder="••••••••"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className={`${ICON_INPUT_CLS} pr-12 ${
                        confirmPassword.length > 0
                          ? confirmPassword === form.password
                            ? 'border-emerald-400 focus:ring-emerald-300'
                            : 'border-red-400 focus:ring-red-300'
                          : ''
                      }`}
                    />
                    <button
                      type="button" onClick={() => setShowConfirmPwd((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      <span className="material-symbols-outlined text-xl">
                        {showConfirmPwd ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                  {confirmPassword.length > 0 && (
                    confirmPassword === form.password ? (
                      <p className="mt-1.5 flex items-center gap-1 text-xs text-emerald-600">
                        <span className="material-symbols-outlined text-sm">check_circle</span>
                        Passwords match.
                      </p>
                    ) : (
                      <p className="mt-1.5 flex items-center gap-1 text-xs text-red-600">
                        <span className="material-symbols-outlined text-sm">error</span>
                        Passwords do not match.
                      </p>
                    )
                  )}
                </div>

                {/* ── Terms ── */}
                <div className="flex items-start gap-3 py-1">
                  <input
                    id="terms" type="checkbox"
                    checked={agreed} onChange={(e) => setAgreed(e.target.checked)}
                    className="h-4 w-4 mt-0.5 rounded border-slate-300 text-primary focus:ring-primary/30 bg-white flex-shrink-0"
                  />
                  <label htmlFor="terms" className="text-sm text-slate-600">
                    I agree to the{' '}
                    <a href="/website" target="_blank" rel="noopener noreferrer" className="font-semibold text-primary hover:text-primary/80">Terms of Service</a>{' '}
                    and{' '}
                    <a href="/website" target="_blank" rel="noopener noreferrer" className="font-semibold text-primary hover:text-primary/80">Privacy Policy</a>
                  </label>
                </div>

                {/* ── Error ── */}
                {error && (
                  <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                    <span className="material-symbols-outlined text-base flex-shrink-0">error</span>
                    {error}
                  </div>
                )}

                {/* ── Submit ── */}
                <button
                  type="submit" disabled={loading}
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
              <Link to="/login" className="font-semibold text-primary hover:text-primary/80">Sign In</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

