# 03 — Frontend (MamlaAI Active + Previous Webpack)

## Overview

The active frontend is `mamlaAI_ground_zero/frontend`, a **React 18** SPA built with **Webpack 5** and **Tailwind CSS**. It uses **React Router v6** for routes, **Redux Toolkit** for global state, and **Axios** for API calls. Auth is Supabase-based; the app stores a token and sends it on requests.

`frontend_webpack/` remains in the repository as the **previous frontend** for reference, parity checks, and historical debugging only.

## Frontend Status

| Frontend | Path | Status | Notes |
|----------|------|--------|-------|
| MamlaAI active UI | `mamlaAI_ground_zero/frontend/` | Primary | Production-facing Tailwind UI and current route shell |
| Webpack legacy UI | `frontend_webpack/` | Previous only | Keep for reference, do not treat as the default frontend |

---

## Entry and Routing Flow

1. **Entry:** `mamlaAI_ground_zero/frontend/src/index.js`
  - Renders: `<ErrorBoundary><Provider store={store}><App /></Provider></ErrorBoundary>`.
  - `App` (`App.js`): `Router` → `AppContent` and shared Axios interceptor setup.

2. **Routes and auth:** `mamlaAI_ground_zero/frontend/src/AppContent.js`
   - On load (and path change), runs an **auth check** for non-public routes:
     - Public routes: `/`, `/login`, `/signup`, `/reset-password`, `/test-ai-drafting`, `/draft-preview/:draftId`, and paths under `/api/aidrafts/test`, `/aidrafts/test`.
     - For protected routes: optionally waits for token (e.g. from `secureLocalStorage` / `secureSessionStorage`), then calls `GET /api/users/check-auth/`. On success, dispatches user into Redux; on failure or error, redirects to `/login`.
   - **Route definitions:** All `<Route>` elements are in `AppContent.js`. Lazy-loaded components are imported at the top (e.g. `const Home = lazy(() => import('./components/Home'))`).

3. **Layout:** Protected routes are wrapped in `<ProtectedRoute />` and then `<AppShell />`. The shell (`components/layout/AppShell.jsx`) renders `Sidebar` + `TopBar` + `Outlet`.

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

- **Store:** `mamlaAI_ground_zero/frontend/src/store.js` (configureStore with slices).
- **Slices:**
  - **userSlice** (`features/userSlice.js`): `firstname`, `lastname`, `email`, `user_type`, `isAuthenticated`, `sessions`. Set by auth check and login; cleared on logout.
  - **entitlementsSlice** (`features/entitlementsSlice.js`): plan, wallet, and quota state.
  - **chatDocsSlice** (`features/chatDocsSlice.js`): Chat-with-docs state (e.g. selected docs, current session, messages, matter).
- Async work (e.g. auth check, login) is done in components (e.g. `AppContent`, `LoginSupabase`); no thunks in the doc’s scope.

---

## API Client (Axios)

**File:** `mamlaAI_ground_zero/frontend/src/services/api.js`

- **baseURL:**
  - If `process.env.REACT_APP_API_BASE_URL` is set (e.g. in production build), that is used.
  - Else: `window.location.hostname === 'localhost'` → `'/api/'`, else `'https://mamla.ai/api/'`.
- **withCredentials:** `true` (for cookie-based auth if used).
- **Request interceptor:** Adds `Authorization: Bearer <token>` when token exists in `secureLocalStorage` or `secureSessionStorage`; skips for URLs containing `/test/`.
- **Response interceptor:** Setup via `setupResponseInterceptors(navigate)` (e.g. on 401 clears storage and redirects to `/login`; on 403 redirects to `/unauthorized`; logs 5xx). Must be called with the navigate function (e.g. from a component that has access to React Router’s `useNavigate`).

All frontend API calls that go to this backend should use `apiClient` and paths **relative to baseURL** (e.g. `users/check-auth/`, `talkdoc/query/`).

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
| `src/App.js` | Router, interceptor setup, AppContent |
| `src/index.js` | Entry, ErrorBoundary, Redux Provider |
| `src/store.js` | Redux store |
| `src/features/userSlice.js` | User state |
| `src/features/entitlementsSlice.js` | Plan, wallet, quota state |
| `src/features/chatDocsSlice.js` | Chat-docs state |
| `src/services/api.js` | API client (baseURL, auth header, interceptors) |
| `src/components/common/ErrorBoundary.jsx` | Global error boundary (try again / go home) |
| `src/components/layout/AppShell.jsx` | Shell: Sidebar + TopBar + Outlet |
| `src/components/layout/Sidebar.jsx` | Main navigation and sign-out |
| `src/components/layout/TopBar.jsx` | Search, quota pills, quick actions |
| `src/components/layout/ProtectedRoute.jsx` | Route protection for the active app |
| `src/components/auth/Login.jsx` | Login page |
| `src/components/auth/Signup.jsx` | Signup page |
| `src/components/auth/ResetPassword.jsx` | Password reset |
| `src/utils/securityUtils.js` | Secure storage helpers |

## Active eCourts Routes

The active scraper-first eCourts shell lives under `mamlaAI_ground_zero/frontend/src/components/ecourt_scrapper/` and is routed from `src/AppContent.js`.

| Path | Component | Notes |
|------|-----------|-------|
| `/ecourts` | `EcourtsTerminal` | Terminal landing with scraper/runtime status, module entry cards, and an actionable quick CNR lookup |
| `/ecourts/case-status` | `CaseStatusTerminal` | New stitched case-status surface. CNR open + advocate search are live on both courts; High Court party-name search is also live; the remaining stitched tabs are explicitly staged |
| `/ecourts/case-search` | `CaseStatusTerminal` | Compatibility alias for the new case-status surface |
| `/ecourts/court-orders` | `CourtOrdersTerminal` | CNR-driven order access from cached scraper case data |
| `/ecourts/cause-list` | `CauseListTerminal` | High-court daily cause-list flow. Non-daily stitched variants remain staged until the current selectors are re-verified |
| `/ecourts/caveat` | `CaveatTerminal` | Terminal placeholder for caveat modes; reference data is live, scraper selectors are pending |
| `/ecourts/case/:cnr` | `CaseDetail` | Existing case-detail screen reused against the scraper runtime |
| `/ecourts/lawyers` | `LawyerSearch` | Older screen retained temporarily as deprecated reference UI |
| `/ecourts/litigants` | `LitigantSearch` | Older screen retained temporarily as deprecated reference UI |

## Theme Direction

- Active theme uses a deep navy, white, and graphite palette intended to feel like institutional legal software rather than a warm lifestyle brand.
- Typography now uses a firmer, more readable professional pairing: `Source Serif 4` for display headlines and `IBM Plex Sans` for UI/body copy.
- Login, signup, and reset-password now share the same navy visual language as the landing page and include direct links back to `/` so public-entry screens feel like one system.
- The landing page hero now rotates through bench, chamber, and draft-control scenes, and the page includes an additional chamber-visual board section with original illustrations and live-state cues so the first public screen feels active without changing public routes or auth behavior.
- The active frontend now has a shared app-level blocking overlay for long-running actions such as login, signup, password reset, draft generation, template-based draft creation, saved-draft loading, TalkDoc session/message/document operations, and calendar load/save/delete/conflict-check flows. This blocks stray clicks during those waits without adding backend latency because it is only a UI layer.
- The shell top bar is now functional rather than decorative: the search box works as a quick navigator across live app routes, draft-session matches, case-ID shortcuts, and direct CNR lookups; the notification button opens a real alerts tray built from quota state plus `dashboard/home/` upcoming events and court updates; and the help icon opens actionable shortcuts like feedback, command center, and session management. Document Intel now also honors `?caseid=` and `?clientid=` query params so top-bar case searches can land on a pre-filtered matter view instead of a generic library screen.
- eCourts now defaults to the scraper-first module shell rather than the old partner-API home. New work should go through `components/ecourt_scrapper/` and the shared helper at `components/ecourt_scrapper/api.js`; `components/ecourts/` remains only for reused screens like case detail or temporary backward compatibility.
- Landing-page motion is implemented with lightweight CSS animation utilities (`app-fade-in`, `app-rise-in`, `float-slow`) rather than heavier animation libraries.
- Drafting keeps jurisdiction selection in the draft-init flow only; once a draft session is created, the editing workspace treats that location as fixed and gives more width to the document via collapsible outline and AI side rails.
- Shared tokens live in `tailwind.config.js` and `src/index.css`, so global visual adjustments should happen there first.
- The public landing page and the app shell carry the main brand treatment; workflows, routes, and API contracts stay unchanged.

---

## Build and Env

- **Dev:** `webpack.dev.js` — dev server (e.g. port 3000), proxy `/api` → backend (e.g. 8000). No `REACT_APP_API_BASE_URL` needed; baseURL is `/api/`.
- **Prod:** `webpack.prod.js` — `DefinePlugin` sets `process.env.NODE_ENV` and `process.env.REACT_APP_API_BASE_URL` (default `'https://mamla.ai/api/'`). Set `REACT_APP_API_BASE_URL` at build time if the API host differs.

## MamlaAI Entitlements and Quota UX

- Active frontend: `mamlaAI_ground_zero/frontend/`.
- Auth bootstrap: `mamlaAI_ground_zero/frontend/src/AppContent.js` hydrates entitlement data from `GET /api/users/check-auth/` and stores it in `features/entitlementsSlice.js`.
- Shared refresh helper: `mamlaAI_ground_zero/frontend/src/features/entitlementsActions.js` refetches `GET /api/users/entitlements/summary/` after quota-consuming actions so top bar and dashboard counters stay current without a full auth reload.
- Shared refresh helper: `mamlaAI_ground_zero/frontend/src/features/entitlementsActions.js` still refetches `GET /api/users/entitlements/summary/` when a flow does not already return enough entitlement data. TalkDoc chat sends are optimized to avoid that extra round-trip because `POST /api/talkdoc/query/` already returns the updated feature quota payload.
- Global surfaces: `components/layout/TopBar.jsx` and `components/dashboard/Dashboard.jsx` show plan, remaining Brain usage, and wallet credits. They now split TalkDoc-related allowance into both `brain_doc_analysis` and `general_legal_chat` counters so no-document legal chat does not look like document-analysis usage.
- Action-level surfaces:
  - `components/drafting/DraftingWorkspace.jsx` shows quota-aware AI-suggestion warnings, wallet-charge confirmations, disables the AI assistant when suggestion usage is blocked, and refreshes entitlements after draft-generation actions.
  - `components/documents/DocumentWorkspace.jsx` shows Brain quota banners in the chat pane, reads TalkDoc `quota` payloads returned by the backend, switches its active lock/warning state based on whether the session has attached docs, and disables chat input when the relevant feature bucket (`brain_doc_analysis` or `general_legal_chat`) is unavailable. Each chat send now updates the local entitlement slice and the active session timestamp directly, so the UI avoids the previous follow-up `users/entitlements/summary/` and `talkdoc/sessions/` calls after every message. TalkDoc quota payloads also now include session-bundle metadata so the workspace can explain that one charge covers up to 10 chats in the active session window.
- API contract expectation: action handlers should read `response.data.quota` and `error.response.data.quota` when available and surface those states inline instead of falling back to generic errors.

---

## Error Boundary

- **File:** `src/components/common/ErrorBoundary.jsx`
- **Usage:** Wraps the app in `index.js`. On React error, shows a fallback UI (“Something went wrong”, Try again, Go to home) and logs the error.

Use **04-api-reference.md** for the exact list of endpoints and auth requirements the frontend relies on.
