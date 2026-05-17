import axios from 'axios';
import { Capacitor } from '@capacitor/core';
import { Preferences } from '@capacitor/preferences';

export const NATIVE_TOKEN_KEY = 'mamla_access_token';

// ─── Determine base URL ───────────────────────────────────────────────────────
function getBaseURL() {
  if (process.env.REACT_APP_API_BASE_URL) {
    return process.env.REACT_APP_API_BASE_URL;
  }
  // In dev, webpack-dev-server proxies /api → :8000 so we just use relative
  return '/api/';
}

const apiClient = axios.create({
  baseURL: getBaseURL(),
  withCredentials: true,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Request interceptor: inject Bearer token on native (Capacitor) ──────────
// On web, auth is handled via HttpOnly cookie (sent automatically via withCredentials).
// On native (Android/iOS), HttpOnly cookies don't cross origins, so we use
// Bearer token stored in @capacitor/preferences (encrypted device storage).
apiClient.interceptors.request.use(async (config) => {
  if (Capacitor.isNativePlatform()) {
    const { value } = await Preferences.get({ key: NATIVE_TOKEN_KEY });
    if (value) {
      config.headers['Authorization'] = `Bearer ${value}`;
    }
  }
  return config;
});

function shouldRedirectToLogin(error) {
  const status = error?.response?.status;
  if (status !== 401) return false;

  const requestUrl = String(error?.config?.url || '');
  const responseCode = String(error?.response?.data?.code || '').toUpperCase();
  const responseMessage = String(error?.response?.data?.error || '').toLowerCase();

  // Partner API token failures are backend integration issues, not user-session failures.
  if (
    requestUrl.includes('ecourts/')
    && (
      responseCode === 'INVALID_TOKEN'
      || responseMessage.includes('bearer token is invalid or malformed')
    )
  ) {
    return false;
  }

  return (
    responseMessage === 'authentication required'
    || responseMessage === 'invalid or expired authentication'
  );
}

// ─── Response interceptors (navigate injected after mount) ───────────────────
let _navigate = null;

export function setupResponseInterceptors(navigate) {
  if (_navigate) return; // only set up once
  _navigate = navigate;

  apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
      const status = error?.response?.status;
      if (shouldRedirectToLogin(error)) {
        _navigate('/login', { replace: true });
      } else if (status === 403) {
        _navigate('/not-authorized', { replace: true });
      }
      return Promise.reject(error);
    },
  );
}

export default apiClient;
