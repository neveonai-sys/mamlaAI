// AppContent.js
import React, { useEffect, useState, lazy, Suspense } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { setUser, clearUser } from './features/userSlice';
import AxiosInstance from './components/common/AxiosInstance';
import { Routes, Route, useLocation, Navigate, useNavigate } from 'react-router-dom';
import ProtectedRoute from './components/layout/ProtectedRoutes';
import Layout from './components/layout/Layout';
import { CircularProgress, Box } from '@mui/material';
import { secureLocalStorage, secureSessionStorage } from './utils/securityUtils';

// Lazy load components for better performance
const Home = lazy(() => import('./components/Home'));
const Signup = lazy(() => import('./components/auth/SignupSupabase'));
const Login = lazy(() => import('./components/auth/LoginSupabase'));
const ResetPassword = lazy(() => import('./components/auth/ResetPasswordSupabase'));
const About = lazy(() => import('./components/About'));
const CalendarComponent = lazy(() => import('./components/calendar/CalendarComponent'));
const CreateDrafts = lazy(() => import('./components/CreateDrafts'));
const SendEmailComponent = lazy(() => import('./components/SendEmailComponent'));
const SessionsList = lazy(() => import('./components/SessionsList'));
const DraftWithAI = lazy(() => import('./components/ai-drafting/DraftWithAI'));
const ChatWithDocs = lazy(() => import('./components/chat/ChatWithDocs'));
const OnboardClient = lazy(() => import('./components/OnboardClient'));
const TodaysUpdates = lazy(() => import('./components/TodaysUpdates'));
const MyUpdates = lazy(() => import('./components/MyUpdates'));
const Feedback = lazy(() => import('./components/Feedback'));
const WelcomePage = lazy(() => import('./components/WelcomePage'));
const TestAIDrafting = lazy(() => import('./components/ai-drafting/TestAIDrafting'));
const DraftPreview = lazy(() => import('./components/ai-drafting/DraftPreview'));

// eCourts pages
const EcourtsHome = lazy(() => import('./components/ecourts/EcourtsHome'));
const CaseSearch = lazy(() => import('./components/ecourts/CaseSearch'));
const CaseDetail = lazy(() => import('./components/ecourts/CaseDetail'));
const LawyerSearch = lazy(() => import('./components/ecourts/LawyerSearch'));
const LawyerProfile = lazy(() => import('./components/ecourts/LawyerProfile'));
const LitigantSearch = lazy(() => import('./components/ecourts/LitigantSearch'));
const CauseListBrowser = lazy(() => import('./components/ecourts/CauseListBrowser'));

// Loading fallback component
const LoadingFallback = () => (
  <Box 
    display="flex" 
    justifyContent="center" 
    alignItems="center" 
    minHeight="100vh"
  >
    <CircularProgress />
  </Box>
);

// Utility to wait until auth token is available (max 2 s)
const waitForToken = (timeout = 2000) => {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    (function poll() {
      const token =
        secureLocalStorage.getItem('authToken') ||
        secureSessionStorage.getItem('authToken');
      if (token) return resolve(token);
      if (Date.now() - start > timeout) return reject(new Error('token-timeout'));
      setTimeout(poll, 50);
    })();
  });
};

function AppContent() {
  const dispatch = useDispatch();
  const location = useLocation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [authCheckComplete, setAuthCheckComplete] = useState(false);
  const { isAuthenticated } = useSelector((state) => state.user);

  // Handle Supabase recovery / email-confirmation links.
  // Supabase appends tokens as a hash fragment and redirects to the configured
  // Site URL (e.g. https://www.mamla.ai/) — NOT to /reset-password — when
  // /reset-password is not in the Supabase dashboard Allowed Redirect URLs.
  // This effect detects type=recovery in the hash on any path and forwards the
  // user to the correct page while preserving the full hash so the token is readable.
  useEffect(() => {
    const hash = window.location.hash;
    if (!hash) return;
    const params = new URLSearchParams(hash.substring(1));
    const type = params.get('type');
    if (type === 'recovery') {
      // /reset-password#access_token=...&type=recovery&...
      navigate('/reset-password' + hash, { replace: true });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Define public routes that don't require authentication
  const publicRoutes = [
    '/',
    '/login',
    '/signup',
    '/reset-password',
    '/test-ai-drafting',
    '/draft-preview/:draftId',
    '/api/aidrafts/test',
    '/aidrafts/test',
  ];

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      if (isMounted) {
        console.warn('Auth check timed out after 5 seconds');
        setLoading(false);
      }
    }, 5000);

    const checkAuth = async () => {
      try {
        // Check if current route is public
        const isPublicRoute = publicRoutes.some(route => {
          if (route.includes(':')) {
            const routeParts = route.split('/');
            const pathParts = location.pathname.split('/');
            if (routeParts.length !== pathParts.length) return false;
            return routeParts.every((part, index) => {
              return part.startsWith(':') || part === pathParts[index];
            });
          }
          return location.pathname === route || 
                 (route !== '/' && location.pathname.startsWith(route + '/'));
        });

        if (isPublicRoute) {
          console.log('[Auth] Public route, skipping auth check');
          if (isMounted) {
            setLoading(false);
            setAuthCheckComplete(true);
          }
          return;
        }

        // For protected routes, ensure token exists then check authentication
        try {
          await waitForToken();
        } catch {
          console.info('Proceeding with auth check even though local token not found; relying on HttpOnly cookie');
        }

        // Now call backend auth check
        console.log('[Auth] Checking authentication...');
        const response = await AxiosInstance.get('/users/check-auth/', {
          signal: controller.signal,
          timeout: 3000 // 3 second timeout
        });

        if (!isMounted) return;

        if (response.data?.isAuthenticated) {
          console.log('[Auth] User authenticated');
          dispatch(setUser({
            firstname: response.data.firstname,
            lastname: response.data.lastname,
            email: response.data.email_id,
            user_type: response.data.user_type,
            sessions: response.data.sessions,
          }));
        } else {
          console.log('[Auth] Not authenticated, redirecting to login');
          dispatch(clearUser());
          navigate('/login', { state: { from: location.pathname } });
        }
      } catch (error) {
        if (!isMounted) return;
        
        if (error.code === 'ECONNABORTED' || error.message === 'canceled') {
          console.warn('Auth check timed out');
        } else {
          console.error('[Auth] Error during auth check:', error);
        }
        
        // On any error, redirect to login but don't show error to user
        if (!publicRoutes.includes(location.pathname) && location.pathname !== '/login') {
          navigate('/login', { state: { from: location.pathname } });
        }
      } finally {
        if (isMounted) {
          setLoading(false);
          setAuthCheckComplete(true);
        }
        clearTimeout(timeoutId);
      }
    };

    checkAuth();
    
    return () => {
      isMounted = false;
      controller.abort();
      clearTimeout(timeoutId);
    };
  }, [dispatch, location.pathname, navigate]);

  // Show loading spinner while checking auth
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        <div className="spinner"></div>
        <p>Loading application...</p>
        {!authCheckComplete && (
          <p style={{ color: '#666', fontSize: '0.9rem' }}>
            Taking longer than expected? Check your internet connection
          </p>
        )}
      </div>
    );
  }

  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<WelcomePage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/test-ai-drafting" element={<TestAIDrafting />} />
        <Route path="/draft-preview/:draftId" element={<DraftPreview />} />

        {/* Protected Routes for all authenticated users */}
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/home" element={<Home />} />
            <Route path="/about" element={<About />} />
            <Route path="/todays-updates" element={<TodaysUpdates />} />
            <Route path="/sessions" element={<SessionsList />} />
            <Route path="/calendar" element={<CalendarComponent />} />
            <Route path="/my-updates" element={<MyUpdates />} />
            <Route path="/feedback" element={<Feedback />} />

            {/* eCourts routes */}
            <Route path="/ecourts" element={<EcourtsHome />} />
            <Route path="/ecourts/search" element={<CaseSearch />} />
            <Route path="/ecourts/case/:cnr" element={<CaseDetail />} />
            <Route path="/ecourts/lawyers" element={<LawyerSearch />} />
            <Route path="/ecourts/lawyers/:name" element={<LawyerProfile />} />
            <Route path="/ecourts/litigants" element={<LitigantSearch />} />
            <Route path="/ecourts/causelist" element={<CauseListBrowser />} />

            {/* Routes accessible to both Lawyers and Clients */}
            <Route element={<ProtectedRoute allowedRoles={['Lawyer', 'Client']} />}>
              <Route path="/draft-with-ai" element={<DraftWithAI />} />
              <Route path="/chat-with-docs" element={<ChatWithDocs />} />
            </Route>

            {/* Lawyer-only Routes */}
            <Route element={<ProtectedRoute requiredRole="Lawyer" />}>
              <Route path="/onboard-client" element={<OnboardClient />} />
            </Route>
          </Route>
        </Route>

        {/* Fallback Route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export default AppContent;
