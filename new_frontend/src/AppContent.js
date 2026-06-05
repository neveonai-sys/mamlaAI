import React, { lazy, Suspense, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { setUser, clearUser } from './features/userSlice';
import { clearEntitlements, setEntitlements } from './features/entitlementsSlice';
import { refreshEntitlements } from './features/entitlementsActions';
import apiClient from './services/api';
import { NATIVE_TOKEN_KEY } from './services/api';
import { Capacitor } from '@capacitor/core';
import { Preferences } from '@capacitor/preferences';
import AppShell from './components/layout/AppShell';
import ProtectedRoute from './components/layout/ProtectedRoute';
import CookieConsentBanner from './components/common/CookieConsentBanner';
import { initializeAnalytics, trackPageView, setAnalyticsUser, clearAnalyticsUser } from './services/analytics';

// ─── Lazy-loaded screens ─────────────────────────────────────────────────────
const MinimalLanding     = lazy(() => import('./components/landing/MinimalLanding'));
const LandingPage        = lazy(() => import('./components/landing/LandingPage'));
const Login              = lazy(() => import('./components/auth/Login'));
const Signup             = lazy(() => import('./components/auth/Signup'));
const ResetPassword      = lazy(() => import('./components/auth/ResetPassword'));

// Protected app screens
const Dashboard          = lazy(() => import('./components/dashboard/Dashboard'));
const DraftingWorkspace  = lazy(() => import('./components/drafting/DraftingWorkspace'));
const DocumentWorkspace  = lazy(() => import('./components/documents/DocumentWorkspace'));
const CalendarPage       = lazy(() => import('./components/calendar/CalendarPage'));
// const CourtUpdates       = lazy(() => import('./components/courts/CourtUpdates'));
// ClientOnboarding route removed — client onboarding now happens inline in CaseRegistry modal
// const ClientOnboarding   = lazy(() => import('./components/clients/ClientOnboarding'));
// const ClientProfile      = lazy(() => import('./components/clients/ClientProfile'));
const Sessions           = lazy(() => import('./components/sessions/Sessions'));
const Feedback           = lazy(() => import('./components/feedback/Feedback'));

// eCourts sub-routes
const EcourtsTerminal    = lazy(() => import('./components/ecourt_scrapper/EcourtsTerminal'));
const CaseStatusTerminal = lazy(() => import('./components/ecourt_scrapper/CaseStatusTerminal'));
const CourtOrdersTerminal = lazy(() => import('./components/ecourt_scrapper/CourtOrdersTerminal'));
const CauseListTerminal  = lazy(() => import('./components/ecourt_scrapper/CauseListTerminal'));
const CaveatTerminal     = lazy(() => import('./components/ecourt_scrapper/CaveatTerminal'));
const CaseDetail         = lazy(() => import('./components/ecourts/CaseDetail'));
const LawyerSearch       = lazy(() => import('./components/ecourts/LawyerSearch'));
const LitigantSearch     = lazy(() => import('./components/ecourts/LitigantSearch'));

// High Court eCourts sub-routes
const HCTerminal            = lazy(() => import('./components/ecourt_scrapper/HCTerminal'));
const HCCaseStatusTerminal  = lazy(() => import('./components/ecourt_scrapper/HCCaseStatusTerminal'));
const HCCourtOrdersTerminal = lazy(() => import('./components/ecourt_scrapper/HCCourtOrdersTerminal'));
const HCCauseListTerminal   = lazy(() => import('./components/ecourt_scrapper/HCCauseListTerminal'));
const HCCaseDetailPage      = lazy(() => import('./components/ecourt_scrapper/HCCaseDetailPage'));

// Owner analytics (owner/admin only)
const OwnerDashboard     = lazy(() => import('./components/dashboard/OwnerDashboard'));

// Case Registry (Phase 1)
const CaseRegistry       = lazy(() => import('./components/cases/CaseRegistry'));
const CaseHub            = lazy(() => import('./components/cases/CaseHub'));
const HearingWorkspace   = lazy(() => import('./components/cases/HearingWorkspace'));
const ClientCasePage     = lazy(() => import('./components/cases/ClientCasePage'));
const GuidedDraftingPage = lazy(() => import('./components/drafting/GuidedDraftingPage'));

// ─── Public routes that skip auth check ─────────────────────────────────────
const PUBLIC_ROUTES = ['/', '/login', '/signup', '/reset-password', '/website'];

function GlobalSpinner() {
  return (
    <div className="flex items-center justify-center h-screen bg-background-light">
      <span className="material-symbols-outlined animate-spin text-primary text-4xl">
        progress_activity
      </span>
    </div>
  );
}

export default function AppContent() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated } = useSelector((s) => s.user);

  // ─── Supabase password-reset deep-link handler ───────────────────────────
  useEffect(() => {
    const hash = window.location.hash;
    if (hash.includes('type=recovery')) {
      navigate('/reset-password' + hash, { replace: true });
    }
  }, [navigate]);

  // ─── Auth probe on mount ──────────────────────────────────────────────────
  useEffect(() => {
    // Initialize analytics once on app load
    initializeAnalytics();

    const isPublic = PUBLIC_ROUTES.some(
      (r) => location.pathname === r || location.pathname.startsWith(r + '#'),
    );
    if (isPublic) {
      if (isAuthenticated === null) {
        dispatch(clearUser());
        dispatch(clearEntitlements());
        clearAnalyticsUser();
      }
      return;
    }

    // If we already have a Redux session skip
    if (isAuthenticated === true) return;

    // Check auth via cookie (web) or Bearer token (native — injected by api.js interceptor).
    // On native, verify we actually have a stored token before hitting the network;
    // if there's none the user hasn't logged in yet and we avoid an unnecessary 401 round-trip.
    const probe = async () => {
      if (Capacitor.isNativePlatform()) {
        const { value } = await Preferences.get({ key: NATIVE_TOKEN_KEY });
        if (!value) {
          dispatch(clearUser());
          dispatch(clearEntitlements());
          clearAnalyticsUser();
          return;
        }
      }

      apiClient
        .get('users/check-auth/')
        .then((res) => {
          if (res.data?.isAuthenticated) {
            dispatch(setUser({
              firstname: res.data.firstname,
              lastname: res.data.lastname,
              email: res.data.email_id,
              user_type: res.data.user_type,
              sessions: res.data.sessions,
            }));
            // Set user in analytics
            setAnalyticsUser(res.data.user_id || res.data.email_id, res.data.email_id, res.data.user_type);
            if (res.data.entitlements) {
              dispatch(setEntitlements(res.data.entitlements));
            } else {
              refreshEntitlements(dispatch);
            }
          } else {
            dispatch(clearUser());
            dispatch(clearEntitlements());
            clearAnalyticsUser();
          }
        })
        .catch(() => {
          dispatch(clearUser());
          dispatch(clearEntitlements());
          clearAnalyticsUser();
        });
    };
    probe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  // ─── Track page views ─────────────────────────────────────────────────────
  useEffect(() => {
    trackPageView(location.pathname);
  }, [location.pathname]);

  return (
    <Suspense fallback={<GlobalSpinner />}>
      <CookieConsentBanner />
      <Routes>
        {/* ── Public ──────────────────────────────────────────────────── */}
        <Route path="/"               element={<MinimalLanding />} />
        <Route path="/website"        element={<LandingPage />} />
        <Route path="/login"          element={<Login />} />
        <Route path="/signup"         element={<Signup />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        {/* ── Protected app shell ─────────────────────────────────────── */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/dashboard"       element={<Dashboard />} />
            <Route path="/command-center"  element={<Navigate to="/dashboard" replace />} />
            <Route path="/drafting"            element={<DraftingWorkspace />} />
            <Route path="/drafting/guided"     element={<GuidedDraftingPage />} />
            <Route path="/drafting/:id"        element={<DraftingWorkspace />} />
            <Route path="/documents"       element={<DocumentWorkspace />} />
            <Route path="/documents/:id"   element={<DocumentWorkspace />} />
            <Route path="/calendar"        element={<CalendarPage />} />
            {/* <Route path="/court-updates"   element={<CourtUpdates />} /> */}
            {/* /clients route removed — onboarding now via CaseRegistry modal */}
            {/* <Route path="/clients"         element={<ClientOnboarding />} /> */}
            {/* <Route path="/clients/:clientId" element={<ClientProfile />} /> */}
            <Route path="/sessions"        element={<Sessions />} />
            <Route path="/feedback"        element={<Feedback />} />

            {/* eCourts nested */}
            <Route path="/ecourts"              element={<EcourtsTerminal />} />
            <Route path="/ecourts/case-search"  element={<CaseStatusTerminal />} />
            <Route path="/ecourts/case-status"  element={<CaseStatusTerminal />} />
            <Route path="/ecourts/court-orders" element={<CourtOrdersTerminal />} />
            <Route path="/ecourts/case/:cnr"    element={<CaseDetail />} />
            <Route path="/ecourts/lawyers"      element={<LawyerSearch />} />
            <Route path="/ecourts/litigants"    element={<LitigantSearch />} />
            <Route path="/ecourts/cause-list"   element={<CauseListTerminal />} />
            <Route path="/ecourts/caveat"       element={<CaveatTerminal />} />

            {/* High Court eCourts nested */}
            <Route path="/ecourts/hc"                element={<HCTerminal />} />
            <Route path="/ecourts/hc/case-status"    element={<HCCaseStatusTerminal />} />
            <Route path="/ecourts/hc/court-orders"   element={<HCCourtOrdersTerminal />} />
            <Route path="/ecourts/hc/cause-list"     element={<HCCauseListTerminal />} />
            <Route path="/ecourts/hc/case/:cino"     element={<HCCaseDetailPage />} />

            {/* Case Registry */}
            <Route path="/cases"                                        element={<CaseRegistry />} />
            <Route path="/cases/:caseId"                                element={<CaseHub />} />
            <Route path="/cases/:caseId/hearings/:hearingId"            element={<HearingWorkspace />} />

            {/* Client portal */}
            <Route path="/my-case"                                      element={<ClientCasePage />} />

            {/* Owner-only analytics */}
            <Route path="/owner-dashboard"                              element={<OwnerDashboard />} />
          </Route>
        </Route>

        {/* ── Fallbacks ────────────────────────────────────────────────── */}
        <Route path="/not-authorized" element={
          <div className="flex flex-col items-center justify-center h-screen gap-4">
            <span className="material-symbols-outlined text-primary text-6xl">lock</span>
            <h1 className="text-2xl font-semibold text-ink">Access Denied</h1>
            <button className="btn-primary" onClick={() => navigate('/dashboard')}>
              Go to Dashboard
            </button>
          </div>
        } />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
