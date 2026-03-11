import axios from 'axios';

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

// Auth is handled via HttpOnly cookie (set by backend on login).
// withCredentials:true above ensures the browser sends it automatically.

// ─── Response interceptors (navigate injected after mount) ───────────────────
let _navigate = null;

export function setupResponseInterceptors(navigate) {
  if (_navigate) return; // only set up once
  _navigate = navigate;

  apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
      const status = error?.response?.status;
      if (status === 401) {
        _navigate('/login', { replace: true });
      } else if (status === 403) {
        _navigate('/not-authorized', { replace: true });
      }
      return Promise.reject(error);
    },
  );
}

export default apiClient;
