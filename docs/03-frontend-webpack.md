# 03 — Frontend (frontend_webpack)

## Overview

The frontend is a **React 18** SPA built with **Webpack 5**. It uses **React Router v6** for routes, **Redux Toolkit** for global state (user, chat docs), **MUI v5** for UI, and **Axios** for API calls. Auth is Supabase-based; the app stores a token (e.g. in secure storage) and sends it on requests.

---

## Entry and Routing Flow

1. **Entry:** `frontend_webpack/src/index.js`
   - Renders: `<ErrorBoundary><Provider store={store}><App /></Provider></ErrorBoundary>`.
   - `App` (`App.js`): `ThemeProvider` → `Router` → `AppContent`.

2. **Routes and auth:** `frontend_webpack/src/AppContent.js`
   - On load (and path change), runs an **auth check** for non-public routes:
     - Public routes: `/`, `/login`, `/signup`, `/reset-password`, `/test-ai-drafting`, `/draft-preview/:draftId`, and paths under `/api/aidrafts/test`, `/aidrafts/test`.
     - For protected routes: optionally waits for token (e.g. from `secureLocalStorage` / `secureSessionStorage`), then calls `GET /api/users/check-auth/`. On success, dispatches user into Redux; on failure or error, redirects to `/login`.
   - **Route definitions:** All `<Route>` elements are in `AppContent.js`. Lazy-loaded components are imported at the top (e.g. `const Home = lazy(() => import('./components/Home'))`).

3. **Layout:** Protected routes are wrapped in `<ProtectedRoute />` and then `<Layout />`. Layout (`components/layout/Layout.jsx`) renders `Navbar` + main content (`Outlet`). Navbar holds the sidebar/drawer and top bar; main content has no extra left margin (drawer is fixed).

---

## Public vs Protected Routes (Summary)

| Path | Component | Auth |
|------|-----------|------|
| `/` | WelcomePage | Public |
| `/login` | LoginSupabase | Public |
| `/signup` | SignupSupabase | Public |
| `/reset-password` | ResetPasswordSupabase | Public |
| `/test-ai-drafting` | TestAIDrafting | Public |
| `/draft-preview/:draftId` | DraftPreview | Public |
| `/home`, `/about`, `/todays-updates`, `/sessions`, `/calendar`, `/my-updates`, `/feedback` | Various | Protected (all) |
| `/draft-with-ai`, `/chat-with-docs` | DraftWithAI, ChatWithDocs | Protected (Lawyer or Client) |
| `/onboard-client` | OnboardClient | Protected (Lawyer only) |

Fallback: `*` → `<Navigate to="/" replace />`.

---

## State Management (Redux)

- **Store:** `frontend_webpack/src/store.js` (configureStore with slices).
- **Slices:**
  - **userSlice** (`features/userSlice.js`): `firstname`, `lastname`, `email`, `user_type`, `isAuthenticated`, `sessions`. Set by auth check and login; cleared on logout.
  - **chatDocsSlice** (`features/chatDocsSlice.js`): Chat-with-docs state (e.g. selected docs, current session, messages, matter).
- Async work (e.g. auth check, login) is done in components (e.g. `AppContent`, `LoginSupabase`); no thunks in the doc’s scope.

---

## API Client (Axios)

**File:** `frontend_webpack/src/components/common/AxiosInstance.jsx`

- **baseURL:**
  - If `process.env.REACT_APP_API_BASE_URL` is set (e.g. in production build), that is used.
  - Else: `window.location.hostname === 'localhost'` → `'/api/'`, else `'https://mamla.ai/api/'`.
- **withCredentials:** `true` (for cookie-based auth if used).
- **Request interceptor:** Adds `Authorization: Bearer <token>` when token exists in `secureLocalStorage` or `secureSessionStorage`; skips for URLs containing `/test/`.
- **Response interceptor:** Setup via `setupResponseInterceptors(navigate)` (e.g. on 401 clears storage and redirects to `/login`; on 403 redirects to `/unauthorized`; logs 5xx). Must be called with the navigate function (e.g. from a component that has access to React Router’s `useNavigate`).

All frontend API calls that go to this backend should use `AxiosInstance` and paths **relative to baseURL** (e.g. `users/check-auth/`, `utils/send-email/`).

---

## Auth Flow (User Journey)

1. **Login:** User submits credentials in `LoginSupabase` → `POST /api/users/login-user/` (Supabase). Backend returns user info; frontend stores token (and optionally user) in secure storage and dispatches to Redux, then redirects (e.g. to `/home` or `state.from`).
2. **Protected route load:** `AppContent` runs auth check → `GET /api/users/check-auth/` with credentials/token → backend validates via Supabase; response populates Redux and sessions or redirects to login.
3. **Logout:** Navbar (or similar) calls `POST /api/users/sign-out-user/` (Supabase sign-out), then clears Redux and redirects to `/login`.
4. **Sessions list:** `SessionsList` uses `GET /api/users/check-auth/` for list and `POST /api/users/invalidate-session/` with `session_id` to terminate a session.

---

## Key Directories and Files

| Path | Purpose |
|------|---------|
| `src/AppContent.js` | Route definitions, auth check, public vs protected list |
| `src/App.js` | ThemeProvider, Router, AppContent |
| `src/index.js` | Entry, ErrorBoundary, Redux Provider |
| `src/store.js` | Redux store |
| `src/features/userSlice.js` | User state |
| `src/features/chatDocsSlice.js` | Chat-docs state |
| `src/components/common/AxiosInstance.jsx` | API client (baseURL, auth header, interceptors) |
| `src/components/common/ErrorBoundary.jsx` | Global error boundary (try again / go home) |
| `src/components/layout/Layout.jsx` | Shell: Navbar + Outlet |
| `src/components/layout/Navbar.jsx` | AppBar, drawer, logout (doLogout → sign-out-user) |
| `src/components/layout/ProtectedRoutes.jsx` | Role-based protection for nested routes |
| `src/components/auth/LoginSupabase.js` | Login page |
| `src/components/auth/SignupSupabase.js` | Signup page |
| `src/components/auth/ResetPasswordSupabase.js` | Password reset |
| `src/utils/securityUtils.js` | Secure storage wrappers (e.g. for token) |
| `src/middleware/securityMiddleware.js` | Applied to Axios instance |
| `src/components/unused/` | Deprecated components; not in any route (see README there) |

---

## Build and Env

- **Dev:** `webpack.dev.js` — dev server (e.g. port 3000), proxy `/api` → backend (e.g. 8000). No `REACT_APP_API_BASE_URL` needed; baseURL is `/api/`.
- **Prod:** `webpack.prod.js` — `DefinePlugin` sets `process.env.NODE_ENV` and `process.env.REACT_APP_API_BASE_URL` (default `'https://mamla.ai/api/'`). Set `REACT_APP_API_BASE_URL` at build time if the API host differs.

---

## Error Boundary

- **File:** `src/components/common/ErrorBoundary.jsx`
- **Usage:** Wraps the app in `index.js`. On React error, shows a fallback UI (“Something went wrong”, Try again, Go to home) and logs the error.

Use **04-api-reference.md** for the exact list of endpoints and auth requirements the frontend relies on.
