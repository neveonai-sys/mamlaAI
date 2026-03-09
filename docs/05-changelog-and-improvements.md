# 05 — Changelog and Incremental Improvement Plans

This document summarizes the **code review outcomes**, **changes already made**, and **incremental plans** so that any developer or AI can continue work without breaking flow.

---

## 1. Code Review Summary (What Was Found)

### Backend (Legalv1)

- **Dual auth:** Legacy JWT/OTP and Supabase coexisted; many endpoints were still wired to JWT or unused OTP flows.
- **Security:** Hardcoded OTP bypass (`'1234'`), test endpoints without auth, password reset without proper verification, FRONTEND_URL and send-email URLs hardcoded.
- **Redundancy:** Duplicate `update_last_activity` in session_manager; commented-out `models.py` across apps; duplicate `check_auth`/onboard logic between `views.py` and `supabase_views.py`.
- **Unused code:** JWT decorator and all JWT/OTP views and URLs (otp-login, send-phone-otp, refresh-token, logout, list-session, etc.) were no longer used by the frontend.
- **Missing:** Health endpoint for monitoring; env-based configuration for frontend URL and Celery callbacks.
- **Quality:** Large functions (e.g. WhatsApp webhook), magic numbers, inconsistent error response shape. WhatsApp left as-is (low priority).

### Frontend (frontend_webpack)

- **Hardcoded URLs:** `SendEmailComponent` used `http://127.0.0.1:8000`; AxiosInstance used fixed production URL.
- **Bugs:** Navbar `handleLogoutConfirm` called undefined `onLogout` (should be `doLogout`); Layout had `marginLeft: open` (boolean instead of pixel value; later reverted to no margin to fix layout).
- **UX:** `alert()` used for success/error in SendEmailComponent; no global error boundary.
- **Unused:** `/unused/` folder contained old Login, Signup, ForgetPassword, TalkDoc variants; not in any route (no bundle impact).

---

## 2. What Was Done (Completed Changes)

### Backend

| Change | Location | Purpose |
|--------|----------|---------|
| Removed all JWT/OTP endpoints and views | `users/urls.py`, `users/views.py` | Single auth system (Supabase only) |
| Deleted `auth_decorators.py` | Legalv1 root | No remaining JWT usage |
| Removed duplicate `update_last_activity` | `users/routes/session_manager.py` | Single implementation |
| Added `GET /api/health/` | `core/views.py`, `Legalv1/urls.py` | Monitoring/load balancer |
| FRONTEND_URL from env | `Legalv1/settings.py` | `os.getenv('FRONTEND_URL', 'https://mamla.ai')` |
| Redirect and callbacks use FRONTEND_URL | `users/views.py`, `users/routes/usermetadata.py`, `users/tasks.py`, `calendar_management/tasks.py`, `create_drafts/tasks.py` | No hardcoded mamla.ai |
| Added `core/response_utils.py` | `error_response(message, status, detail)` | Optional standard error helper (not applied to existing views) |
| Removed dead import | `create_drafts/views.py` | Dropped `auth_decorators.jwt_required` |
| Cleaned commented auth_decorators refs | `calendar_management`, `todaysupdates`, `search_facility` views | Cleaner codebase |
| **Centralised LLM calls** | `core/llm_client.py` (new) · `ai_draft/tasks.py` · `talkdoc/views.py` · `utilities/routes/utils.py` · `Legalv1/settings.py` | All LLM calls go through `core.llm_client.chat_complete()`. Supports OpenAI + OpenRouter. Per-app model routing via `APP_OPENROUTER_MODELS` / `APP_OPENAI_MODELS` dicts. Provider switchable via `LLM_DEFAULT_PROVIDER` env. Fixed `ai_draft` draft-generation temperature (0.7 → 0.3) and added strict JSON-only prompt guard. `utilities` now uses SDK instead of raw `requests.post`. |

### Frontend

| Change | Location | Purpose |
|--------|----------|---------|
| API base URL from env | `AxiosInstance.jsx`, `webpack.prod.js` | `REACT_APP_API_BASE_URL` for production |
| SendEmail uses AxiosInstance + Snackbar | `SendEmailComponent.js` | No hardcoded URL; proper feedback and loading |
| Navbar logout fix | `Navbar.jsx` | `handleLogoutConfirm` calls `doLogout()` |
| Layout main content | `Layout.jsx` | No extra `marginLeft` (reverted) so content is not pushed off-screen |

### eCourts scraper and docs

| Change | Location | Purpose |
|--------|----------|---------|
| New Django app `ecourts_scraper` | `Legalv1/ecourts_scraper/` | Live eCourts data: case by CNR, advocate search, cache, async jobs |
| Agentic scrape flow | `agent/state_machine.py`, `scrapers/highcourt.py`, `districtcourt.py` | State machine + HC/DC scrapers; CAPTCHA, rate limit, cache |
| API under `/api/ecourts/` | `ecourts_scraper/views.py`, `urls.py` | GET case/<cnr>, POST refresh, GET jobs/<job_id>, POST search |
| Celery queues + beat | `Legalv1/celery.py`, `settings.py` | ecourts_realtime, ecourts_background; cleanup + health-check beat tasks |
| Docs and Cursor rule | `docs/06-ecourts-scraper.md`, `docs/README.md`, `04-api-reference.md`, `02-backend-legalv1.md`, `.cursor/rules/docs-first.mdc` | Single source of truth for eCourts; AI reads docs first before editing code |
| Global Error Boundary | `ErrorBoundary.jsx`, `index.js` | Catch React errors, show fallback UI |
| Removed unused LogoutButton | Deleted `LogoutButton.js`, export from layout index | Was calling removed JWT logout |
| Fixed Supabase password-reset link not showing reset form | `frontend_webpack/src/AppContent.js`, `Legalv1/users/routes/usermetadata.py` | Supabase recovery email lands on root URL (`/`) with `#type=recovery` hash. Added one-time `useEffect` in `AppContent.js` that detects `type=recovery` in hash on any path and navigates to `/reset-password` preserving the hash. Backend `generate_password_reset_link` updated to use `options=` keyword arg and logs the redirect URL. Note: also add `https://mamla.ai/reset-password` and `https://www.mamla.ai/reset-password` to Supabase dashboard → Authentication → URL Configuration → Allowed Redirect URLs so the email link goes directly to `/reset-password`. |
| Fixed `<button>` nested inside `<button>` in CaseCard | `frontend_webpack/src/components/ecourts/common/CaseCard.jsx` | `IconButton` (renders `<button>`) was inside `CardActionArea` (also renders `<button>`). Replaced `IconButton` with a purely decorative `Box` (`pointerEvents: none`). Eliminates React DOM nesting warning. |
| Added back button and breadcrumb navigation to CaseDetail | `frontend_webpack/src/components/ecourts/CaseDetail.jsx` | `ArrowBackIcon` `IconButton` using `navigate(-1)`. Breadcrumb "Cases" link also uses `navigate(-1)` so returning from case detail restores the correct search page. |
| Added sessionStorage search cache (30-min TTL) | `frontend_webpack/src/components/ecourts/common/useSearchCache.js` (new), `CaseSearch.jsx`, `LawyerSearch.jsx`, `LitigantSearch.jsx` | `saveSearchCache` / `loadSearchCache` / `loadLastSearchCache` helpers. On back-navigation, cached results are restored instantly without an API call. On blank mount (no URL query), last-used search is restored. Clears on tab close (sessionStorage). |
| Fixed order PDF download: `window.open()` → Axios blob | `frontend_webpack/src/components/ecourts/CaseDetail.jsx`, `ecourtsApi.js` | `window.open()` is a plain browser navigation that does NOT send the `Authorization: Bearer` header → 401. Fixed: `downloadOrder` now uses `responseType: 'blob'`; `handleDownload` fetches blob via Axios, creates object URL, triggers `<a download>` click, then revokes URL. Added `downloadingIdx` spinner and `downloadError` alert in Orders tab. |
| Fixed order PDF download: backend returns binary not JSON | `Legalv1/ecourts_api/client.py`, `Legalv1/ecourts_api/views.py` | `client.get_order()` called `_handle_response()` → `resp.json()` on binary PDF → `JSONDecodeError` → backend 500. Added `get_order_stream(cnr, filename)` that returns raw `(bytes, content_type)` without JSON parsing. `download_order` view rewritten to proxy PDF as `HttpResponse` with `Content-Disposition: attachment`. |
| Created `docs/00-agent-quickref.md` | `docs/00-agent-quickref.md` | Single-page cheat sheet for AI agents: all file paths, collections, API prefixes, routes, env vars, conventions. Agents read this instead of scanning the codebase. |
| Created `.github/copilot-instructions.md` | `.github/copilot-instructions.md` | Auto-loaded by VS Code GitHub Copilot on every task. Enforces docs-first workflow, doc maintenance protocol, and hard constraints (no JWT, no ORM, no hardcoded URLs). |
| Strengthened `.cursor/rules/docs-first.mdc` | `.cursor/rules/docs-first.mdc` | Added 4-step workflow (quickref → detail doc → change → update docs), full doc-maintenance table, and hard constraints. |
| Updated `docs/README.md` | `docs/README.md` | Added `00-agent-quickref.md` as the first and most important entry in the doc map. |
| eCourts search landing pages show pre-populated defaults | `Legalv1/ecourts_api/tasks.py` (new), `ecourts_api/views.py`, `ecourts_api/urls.py`, `Legalv1/settings.py`, `ecourtsApi.js`, `CaseSearch.jsx`, `LawyerSearch.jsx`, `LitigantSearch.jsx` | Users see real case data immediately when landing on eCourts search pages without typing anything. Three Celery Beat tasks store page-1 results from broad seed queries into `EcourtsCacheManager` under `defaults:cases`, `defaults:litigants`, `defaults:lawyers`. New `GET /api/ecourts/defaults/<section>/` endpoint reads them. Frontend falls back to this API when no sessionStorage cache and no URL query. Defaults show an info chip banner; pagination is suppressed in default view. Cases/litigants refresh daily; lawyers weekly (stable data). Pages 3+ and explicit searches always hit the live partner API. |
| Fixed download error message always showing generic fallback | `frontend_webpack/src/components/ecourts/CaseDetail.jsx` | When `responseType:'blob'` is set in Axios, any error response body is delivered as a `Blob` (not a parsed object). `err.response?.data?.error` was always `undefined`, so the catch block always showed "Download failed. Please try again." regardless of the actual error. Fixed `handleDownload` catch block to detect `instanceof Blob`, read it via `.text()`, parse as JSON, and extract `json.error` or `json.message`. Now the real partner-API error message (e.g. "Unable to process document request") is shown to the user. |

---

## 3. What Was Intentionally Not Changed

- **WhatsApp module:** Left as-is; to be revisited later.
- **Existing API response shapes:** No mass change to error format so frontend contracts stay valid.
- **Commented `models.py` files:** Left in place; apps use raw MongoDB. Can be removed or replaced with ODM in a later pass.
- **Unused folder:** Not deleted; only documented. Safe to delete later if desired.
- **Full test coverage / TypeScript / API docs:** Not in scope; listed below as future improvements.

---

## 4. Incremental Improvement Plans

Use these as a **backlog**. Each item can be done independently.

### High impact, low risk

- [ ] **Backend:** Add `.env.example` (or document in README) listing all required env vars (`MONGO_URI`, `FRONTEND_URL`, `SUPABASE_*`, etc.).
- [ ] **Backend:** Fix duplicate imports in `Legalv1/Legalv1/urls.py` (repeated `from django.contrib import admin` and `path, include`).
- [ ] **Frontend:** Ensure `setupResponseInterceptors(navigate)` is called with the correct `navigate` (e.g. from a top-level component that has `useNavigate`), so 401/403 redirects work everywhere.
- [ ] **Both:** Add a short root README that points to `docs/README.md` and describes how to run backend and frontend (and env).

### Security and robustness

- [ ] **Backend:** Add rate limiting to password reset and email verification endpoints if not already present.
- [ ] **Backend:** Enforce `SECURE_SSL_REDIRECT = True` in production (e.g. via env).
- [ ] **Backend:** Validate required env vars at startup and fail fast with a clear message.
- [ ] **Frontend:** Replace weak token obfuscation in `securityUtils.js` with a clearer approach (e.g. rely on HttpOnly cookies where possible and document the rest).

### Consistency and maintainability

- [ ] **Backend:** Gradually adopt `core.response_utils.error_response` for new endpoints and, where safe, for refactors that don’t change existing client behavior.
- [ ] **Backend:** Extract constants for magic numbers (e.g. max sessions, OTP limits) and document them.
- [ ] **Backend:** Add indexes for frequently queried fields (e.g. `sessions.access_token`, `service_orders.order_id`) if not already present; consider running `ensure_indexes()` on deploy.
- [ ] **Frontend:** Replace remaining `alert()` or ad-hoc error UI with Snackbar/Alert where it makes sense.
- [ ] **Frontend:** Add loading/error states for critical flows (e.g. onboarding, draft save) where missing.

### Larger or later

- [ ] **Backend:** Break down the WhatsApp webhook handler into smaller functions and add tests when touching that feature.
- [ ] **Backend:** Add OpenAPI/Swagger (or similar) and keep it in sync with `docs/04-api-reference.md`.
- [ ] **Backend:** Add unit/integration tests for auth and critical user/draft flows.
- [ ] **Frontend:** Consider TypeScript for new or refactored modules.
- [ ] **Frontend:** Remove or archive `src/components/unused/` if no longer needed for reference.
- [ ] **Both:** Document deployment (e.g. Docker, env injection, health check usage).

---

## 5. How to Use This Doc for Continuation

- **“Continue the refactor”** → Pick the next unchecked item in §4 that matches the current goal (e.g. env example, rate limiting, or error response standardization).
- **“Fix a bug in auth”** → Use **02-backend-legalv1.md** (auth flow) and **04-api-reference.md** (users endpoints); ensure both frontend and backend use Supabase-only flows.
- **“Add a new API”** → Follow **04-api-reference.md** for path and auth convention; implement in the correct app (see **02-backend-legalv1.md**); call it via `AxiosInstance` on the frontend (see **03-frontend-webpack.md**).
- **“Onboard a new dev or AI”** → Start with **docs/README.md** and **01-architecture-overview.md**, then **02** and **03** for the layer being worked on, and **04** for endpoint details. Use **05** for context on what changed and what to do next.

When making incremental changes, update this document (and, if needed, **04-api-reference.md**) so the next reader or AI has an up-to-date picture.
