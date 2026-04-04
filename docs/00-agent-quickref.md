# 00 — Agent Quick Reference

> **Read this first on every task.** This is a single-page map of every key path, convention, and file in the project. Use it to navigate directly to the right file without scanning the codebase.
>
> If you need more detail, the table below tells you which doc to open next.

---

## Task → Doc routing

| Task | Go to |
|------|-------|
| Any backend change (API, auth, DB, Celery) | `docs/02-backend-legalv1.md` |
| Any API endpoint (path, auth, method) | `docs/04-api-reference.md` |
| Any frontend change (routes, Redux, Axios, components) | `docs/03-frontend-webpack.md` |
| eCourts / court data / scraper | `docs/06-ecourts-scraper.md` |
| Big picture / repo layout | `docs/01-architecture-overview.md` |
| What was last changed / what to do next | `docs/05-changelog-and-improvements.md` |
| Mamla Brain framework (RAG+LLM, Case Companion, external API) | `docs/07-mamla-brain-framework.md` |
| **One-stop lawyer workflow plan (case registry, agents, hearing prep, client portal)** | `docs/08-lawyer-workflow-plan.md` |
| **Unified Case Hub + context-aware workflow implementation plan (approved 2026-03-31)** | `docs/10-unified-casehub-plan.md` |
| **Agentic Guided Drafting Flow (conversational intake → draft generation)** | `docs/11-agentic-guided-drafting-plan.md` |
| **Pricing, billing plans, user types, payment gateway architecture** | `docs/09-pricing-and-billing-plan.md` |

---

## Backend — exact file paths

| What | Exact path |
|------|-----------|
| Root URL config | `Legalv1/Legalv1/urls.py` |
| Django settings (env, CORS, DB, Celery) | `Legalv1/Legalv1/settings.py` |
| Auth decorator (`@supabase_required`) | `Legalv1/supabase_required.py` |
| Mongo + Supabase client singletons | `Legalv1/core/init_clients.py` |
| **Centralised LLM client** | `Legalv1/core/llm_client.py` — `chat_complete()` and `vision_complete()` |
| Health check view | `Legalv1/core/views.py` |
| Standard error helper | `Legalv1/core/response_utils.py` |
| Celery app + queue config | `Legalv1/Legalv1/celery.py` (or `Legalv1/celery.py`) |
| Users: Supabase views (login, auth check, onboard) | `Legalv1/users/supabase_views.py` |
| Users: legacy/utility views | `Legalv1/users/views.py` |
| Users: URL config | `Legalv1/users/urls.py` |
| Users: session management | `Legalv1/users/routes/session_manager.py` |
| AI Drafts views + URLs | `Legalv1/ai_draft/views.py` · `Legalv1/ai_draft/urls.py` |
| Create Drafts views + URLs | `Legalv1/create_drafts/views.py` · `Legalv1/create_drafts/urls.py` |
| Calendar views + URLs | `Legalv1/calendar_management/views.py` · `Legalv1/calendar_management/urls.py` |
| Calendar recurring regression script | `Legalv1/scripts/calendar_recurring_regression.py` |
| Utilities (email, state/district/court) | `Legalv1/utilities/views.py` · `Legalv1/utilities/urls.py` |
| TalkDoc (RAG) views + URLs | `Legalv1/talkdoc/views.py` · `Legalv1/talkdoc/urls.py` |
| Mamla Brain framework app | `Legalv1/mamla_brain/` |
| eCourts Scraper (ACTIVE) views + URLs | `Legalv1/ecourts_scraper/views.py` · `Legalv1/ecourts_scraper/urls.py` |
| eCourts v2 proxy to FastAPI scraper (ACTIVE) | `Legalv1/ecourt_scrapped/views.py` · `Legalv1/ecourt_scrapped/urls.py` · `Legalv1/ecourt_scrapped/services/scraper_client.py` · `Legalv1/ecourt_scrapped/services/master_data.py` · `Legalv1/ecourt_scrapped/services/ecourts_crawler.py` |
| Case registry (cases, hearing notes, notes, tasks) | `Legalv1/cases/views.py` · `Legalv1/cases/urls.py` · `Legalv1/cases/routes/` |
| AI agents (intake, doc-intel, hearing prep, post-hearing, draft context, closure, **conversational draft**) | `Legalv1/agents/views.py` · `Legalv1/agents/urls.py` · `Legalv1/agents/base_agent.py` · `Legalv1/agents/*.py` · **`Legalv1/agents/conversational_draft_agent.py`** |
| eCourts direct API (DEPRECATED reference only) | `Legalv1/ecourts_api/` — keep commented/out of runtime |
| Search views + URLs | `Legalv1/search_facility/views.py` · `Legalv1/search_facility/urls.py` |
| Today's Updates views + URLs | `Legalv1/todaysupdates/views.py` · `Legalv1/todaysupdates/urls.py` |
| WhatsApp webhook (do not touch) | `Legalv1/whatsapp_module/views.py` · `Legalv1/whatsapp_module/urls.py` |
| Draft template documents | `draftdocs/` (subfolders by type) |

---

## Backend — MongoDB collections

| Collection | Used by |
|-----------|---------|
| `user_details` | users app (profile, sessions, meetings) |
| `aidrafts_complete_data` | ai_draft app |
| `draft_content_data` · `user_draft_data` | create_drafts app |
| `signup_tokens` · `feedback` | users app |
| `state_district_court_data` | utilities app |
| `ecourts_cache` | ecourts_scraper cache entries (`hc:*`, `dc:*`) |
| `ecourts_reference_data` | ecourts_scraper terminal dropdown/reference datasets |
| `ecourts_scrape_jobs` | ecourts_scraper (disabled) |
| `ecourts_master_data` | ecourt_scrapped (cached dropdown data for v2 API — live scrape + TTL cache) |
| `ecourts_states` · `ecourts_districts` | ecourt_scrapped (pre-seeded location data, read by master_data.py first) |
| `whatsapp_chat_sessions` · `service_orders` | whatsapp_module |
| `cases` | cases app — internal case registry |
| `hearing_notes` | cases app — prep + outcome per hearing |
| `case_notes` | cases app — threaded notes (internal/shared visibility) |
| `case_tasks` | cases app — tasks per case |
| `draft_conversations` | ai_draft app — guided drafting conversational intake sessions (ConversationalDraftAgent) |

Primary DB name: **`legaldb`**. Get client via `core.init_clients.get_mongo_client()`.

---

## Backend — API URL prefixes

| Prefix | App |
|--------|-----|
| `/api/health/` | `core` |
| `/api/users/` | `users` |
| `/api/aidrafts/` | `ai_draft` |
| `/api/drafts/` | `create_drafts` |
| `/api/calendar/` | `calendar_management` |
| `/api/utils/` | `utilities` |
| `/api/search/` | `search_facility` |
| `/api/todaysupdates/` | `todaysupdates` |
| `/api/talkdoc/` | `talkdoc` |
| `/api/brain/` | `mamla_brain` |
| `/api/cases/` | `cases` (case registry, hearing notes, case notes, tasks) |
| `/api/agents/` | `agents` (CaseIntake, DocumentIntel, HearingPrep, PostHearing, DraftContext, CaseClosure) |
| `/api/ecourts/` | `ecourts_scraper` (active) |
| `/api/ecourts/v2/` | `ecourt_scrapped` (proxy to standalone FastAPI scraper) |
| `/api/webhook/` | `whatsapp_module` |
| (root) | `calendersetup` (Google Calendar OAuth) |

---

## Backend — auth rules

- **Decorator:** `@supabase_required` on any view that needs auth.
- Token source (priority order): cookie `access_token` → header `Authorization: Bearer <token>` → raw header value.
- Bypass: set `request.bypass_supabase_auth = True` before the view (test/middleware only).
- **No JWT, no OTP** — all removed. Do not re-add.
- On success: `request.supabase_user` is set with user metadata.

---

## Frontend — exact file paths

Active frontend first. `frontend_webpack/` is the previous UI only.

| What | Exact path |
|------|-----------|
| App entry | `mamlaAI_ground_zero/frontend/src/index.js` |
| Router wrapper | `mamlaAI_ground_zero/frontend/src/App.js` |
| **All routes + auth check** | `mamlaAI_ground_zero/frontend/src/AppContent.js` |
| Redux store | `mamlaAI_ground_zero/frontend/src/store.js` |
| User slice (auth state) | `mamlaAI_ground_zero/frontend/src/features/userSlice.js` |
| Entitlements slice | `mamlaAI_ground_zero/frontend/src/features/entitlementsSlice.js` |
| Chat docs slice | `mamlaAI_ground_zero/frontend/src/features/chatDocsSlice.js` |
| **API client** (baseURL, interceptors, auth header) | `mamlaAI_ground_zero/frontend/src/services/api.js` |
| App shell | `mamlaAI_ground_zero/frontend/src/components/layout/AppShell.jsx` |
| Sidebar | `mamlaAI_ground_zero/frontend/src/components/layout/Sidebar.jsx` |
| Top bar | `mamlaAI_ground_zero/frontend/src/components/layout/TopBar.jsx` |
| Login page | `mamlaAI_ground_zero/frontend/src/components/auth/Login.jsx` |
| Error boundary | `mamlaAI_ground_zero/frontend/src/components/common/ErrorBoundary.jsx` |
| Security utils | `mamlaAI_ground_zero/frontend/src/utils/securityUtils.js` |
| Tailwind tokens | `mamlaAI_ground_zero/frontend/tailwind.config.js` · `mamlaAI_ground_zero/frontend/src/index.css` |
| Previous frontend reference | `frontend_webpack/` |

---

## New UI (mamlaAI_ground_zero) — exact file paths

> Tailwind CSS v3 rebuild. Backend API base: `mamlaAI_ground_zero/frontend/src/services/api.js` (`apiClient`).

| What | Exact path |
|------|-----------|
| API client (apiClient, withCredentials) | `mamlaAI_ground_zero/frontend/src/services/api.js` |
| Redux store | `mamlaAI_ground_zero/frontend/src/store.js` |
| User slice | `mamlaAI_ground_zero/frontend/src/features/userSlice.js` |
| Entitlements slice | `mamlaAI_ground_zero/frontend/src/features/entitlementsSlice.js` |
| Entitlements refresh helper | `mamlaAI_ground_zero/frontend/src/features/entitlementsActions.js` |
| Chat docs slice | `mamlaAI_ground_zero/frontend/src/features/chatDocsSlice.js` |
| App entry / Router | `mamlaAI_ground_zero/frontend/src/index.js` |
| All routes | `mamlaAI_ground_zero/frontend/src/AppContent.js` |
| **Dashboard** (agenda uses `upcoming_events_list`) | `mamlaAI_ground_zero/frontend/src/components/dashboard/Dashboard.jsx` |
| **Command Center** (quick actions, live events) | `mamlaAI_ground_zero/frontend/src/components/dashboard/CommandCenter.jsx` |
| **Drafting Workspace** (new draft, load draft, load template, save/revert, section history, location refresh, quota-aware AI suggestion UX) | `mamlaAI_ground_zero/frontend/src/components/drafting/DraftingWorkspace.jsx` |
| **Guided Drafting Page** (conversational intake → draft_plan → generate; start with case/docs/scratch; mid-chat doc upload; ready banner with DraftPlanCard) | `mamlaAI_ground_zero/frontend/src/components/drafting/GuidedDraftingPage.jsx` |
| **Calendar Page** (advanced legal calendar shell, FullCalendar, conflict workflow, case/client-aware intake, multi-day linked-series UX) | `mamlaAI_ground_zero/frontend/src/components/calendar/CalendarPage.jsx` |
| **Court Updates** (subscription management + filter tabs) | `mamlaAI_ground_zero/frontend/src/components/courts/CourtUpdates.jsx` |
| **Document Workspace** (TalkDoc / RAG chat, two-window flow: setup library for upload/delete/load chats, case/client-aware document filters, timestamped document labels, focused viewer+chat work window, live uploads into active chats, image preview, API-backed case/client suggestions with case→client autofill/filtering, session-scoped docs, session-aware Brain quota banners/locks for both document analysis and general legal chat) | `mamlaAI_ground_zero/frontend/src/components/documents/DocumentWorkspace.jsx` |
| **Case Detail** (hearings, null-safe date rendering) | `mamlaAI_ground_zero/frontend/src/components/cases/CaseDetail.jsx` |
| **Client Onboarding** | `mamlaAI_ground_zero/frontend/src/components/clients/ClientOnboarding.jsx` |
| Webpack dev config (proxy /api) | `mamlaAI_ground_zero/frontend/webpack.dev.js` |
| Webpack prod config | `mamlaAI_ground_zero/frontend/webpack.prod.js` |
| Tailwind config | `mamlaAI_ground_zero/frontend/tailwind.config.js` |
| Build output (static files) | `mamlaAI_ground_zero/frontend/dist/` |

---

## Frontend — routes (all defined in AppContent.js)

| Path | Component | Auth required |
|------|-----------|---------------|
| `/` | WelcomePage | Public |
| `/login` | LoginSupabase | Public |
| `/signup` | SignupSupabase | Public |
| `/reset-password` | ResetPasswordSupabase | Public |
| `/test-ai-drafting` | TestAIDrafting | Public |
| `/draft-preview/:draftId` | DraftPreview | Public |
| `/home`, `/about`, `/sessions`, `/calendar`, `/my-updates`, `/feedback`, `/todays-updates` | Various pages | Protected (all users) |
| `/draft-with-ai`, `/chat-with-docs` | DraftWithAI, ChatWithDocs | Protected (Lawyer or Client) |
| `/onboard-client` | OnboardClient | Protected (Lawyer only) |
| `/drafting` | DraftingWorkspace | Protected |
| `/drafting/guided` | GuidedDraftingPage | Protected |
| `/drafting/:id` | DraftingWorkspace | Protected |
| `*` | — | Redirect to `/` |

---

## Frontend — key conventions

- **All API calls:** use `AxiosInstance` with paths relative to baseURL (e.g. `users/check-auth/`, not `/api/users/check-auth/`).
- **Base URL logic:** `REACT_APP_API_BASE_URL` env → localhost fallback `/api/` → production `https://mamla.ai/api/`.
- **Auth token:** stored in `secureLocalStorage` or `secureSessionStorage`; injected as `Authorization: Bearer` by Axios interceptor. Skip for `/test/` paths.
- **Logout:** call `POST users/sign-out-user/` then clear Redux and storage; do NOT call any JWT endpoints.
- **Route protection:** via `<ProtectedRoute />` wrapper in `AppContent.js`.
- **Never use `alert()`:** use MUI Snackbar/Alert instead.

---

## Environment variables (key ones)

| Variable | Used in | Purpose |
|----------|---------|---------|
| `MONGO_URI` | Backend settings | MongoDB connection string |
| `FRONTEND_URL` | Backend settings | Used in email links, redirects (never hardcode `mamla.ai`) |
| `SUPABASE_URL` · `SUPABASE_ANON_KEY` · `SUPABASE_SERVICE_ROLE_KEY` | Backend settings | Supabase project config |
| `ECOURTS_CAPSOLVER_API_KEY` / `CAPSOLVER_API_KEY` | `ecourts_scraper` | Capsolver token for CAPTCHA solving |
| `BRAIN_T1_MODEL` · `BRAIN_T2_MODEL` · `BRAIN_T3_MODEL` | Backend settings | Mamla Brain tiered model routing |
| `BRAIN_MONTHLY_FREE_QUOTA` | Backend settings | Default external Brain API-key quota |
| `REDIS_URL` | Backend settings | Redis broker + cache |
| `REACT_APP_API_BASE_URL` | Frontend Webpack prod build | API base URL injected at build time |
| `REACT_APP_SUPABASE_URL` · `REACT_APP_SUPABASE_ANON_KEY` | Frontend | Supabase client init on frontend |

Backend env is loaded via `legalenv` (dotenv). File: `Legalv1/legalenv`.  
Frontend env is injected by Webpack DefinePlugin in `webpack.prod.js`.

---

## Doc maintenance — what to update when you change something

| What you changed | Update these docs |
|-----------------|------------------|
| Added / changed API endpoint | `docs/04-api-reference.md` (table) + `docs/02-backend-legalv1.md` (URL table) |
| New Django app | `docs/02-backend-legalv1.md` (app table) + `docs/01-architecture-overview.md` (repo layout) + `docs/00-agent-quickref.md` (prefix table) |
| New/changed frontend route | `docs/03-frontend-webpack.md` (routes table) + `docs/00-agent-quickref.md` (routes table) |
| New env var | `docs/02-backend-legalv1.md` (env section) + `docs/00-agent-quickref.md` (env table) |
| Auth flow change | `docs/02-backend-legalv1.md` (auth section) + `docs/03-frontend-webpack.md` (auth flow) |
| eCourts change | `docs/06-ecourts-scraper.md` |
| Any completed feature / bug fix | `docs/05-changelog-and-improvements.md` (§2 What Was Done table) |
| Architecture / new major component | `docs/01-architecture-overview.md` + `docs/05-changelog-and-improvements.md` |
| Any file path in this quickref is wrong | Update `docs/00-agent-quickref.md` immediately |

---

## Celery queues and tasks

| Queue | Used for |
|-------|---------|
| `default` | General async (email, etc.) |
| `ecourts_realtime` | eCourts scraper — real-time jobs (scraper disabled; queue exists) |
| `ecourts_background` | eCourts scraper — background refresh + ecourts_api defaults population |

Beat tasks (in `Legalv1/Legalv1/settings.py`):
- `ecourts_scraper`: cache cleanup (4AM), health-check selectors (3AM), refresh causelists (6:30/12:30/18:30), refresh tracked cases (2AM)
- `ecourts_scraper.tasks`: `seed_reference_data` (daily 1:15AM), cache cleanup (4AM), health-check selectors (3AM), refresh causelists (6:30/12:30/18:30), refresh tracked cases (2AM)
- `utilities.tasks`: fetch today's meetings (6AM), hourly reminders, cleanup previous-day index (23:59), consolidated reminders (6PM)
- `users.tasks`: cleanup/invalidate sessions (every 5min/15min/weekly)
- `whatsapp_module.tasks`: assign orders (9PM), paralegal reminders (every 2h), notify clients (6PM)

---

## What is intentionally disabled / left as-is

| Thing | Status | Reason |
|-------|--------|--------|
| `ecourts_api` app | **Deprecated reference only** | Keep code for historical rollback/debugging, but do not wire it into runtime, Beat, or frontend helpers. |
| WhatsApp module | **Unchanged** | Low priority; to be refactored later. Do not touch. |
| `src/components/unused/` | **Not in routes** | Deprecated; safe to delete but kept for reference. |
| `models.py` files in apps | **Commented out** | Apps use raw MongoDB. Do not add ORM models. |
