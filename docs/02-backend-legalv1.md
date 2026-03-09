# 02 — Backend (Legalv1)

## Overview

The backend is a **Django 5.x** project under `Legalv1/`. It exposes REST-style APIs under the `/api/` prefix, uses **MongoDB** as the primary data store, **Supabase** for authentication, **Redis** for cache/Celery broker, and **Celery** for async tasks (e.g. email). OpenSearch is used for document search.

---

## Root URL Configuration

**File:** `Legalv1/Legalv1/urls.py`

| URL prefix | App / view |
|------------|------------|
| `api/health/` | `core.views.health` |
| `api/users/` | `users.urls` |
| (root) | `calendersetup.urls` (Google Calendar) |
| `api/drafts/` | `create_drafts.urls` |
| `api/aidrafts/` | `ai_draft.urls` |
| `api/calendar/` | `calendar_management.urls` |
| `api/utils/` | `utilities.urls` |
| `api/search/` | `search_facility.urls` |
| `api/webhook/` | `whatsapp_module.urls` |
| `api/todaysupdates/` | `todaysupdates.urls` |
| `api/talkdoc/` | `talkdoc.urls` |
| `api/ecourts/` | `ecourts_api.urls` (direct partner API; scraper disabled) |

All user-facing API base path is effectively **`/api/`** (e.g. full path `https://<host>/api/users/check-auth/`).

---

## Authentication (Supabase Only)

- **No JWT/OTP legacy:** Previous JWT and OTP-based login/signup/session endpoints were removed. Auth is **Supabase-only**.
- **Decorator:** `supabase_required` in `Legalv1/supabase_required.py`:
  - Reads **Supabase access token** from:
    - Cookie `access_token`, or
    - Header `Authorization: Bearer <token>` (or raw token).
  - Calls `get_supabase_client().auth.get_user(access_token)` to validate.
  - On success: sets `request.supabase_user` (user metadata) and runs the view.
  - On failure or missing token: returns `401` with a JSON error.
- **Bypass:** If `request.bypass_supabase_auth` is True (e.g. set by middleware for test routes), the decorator skips auth.
- **Where used:** Most protected views use `@supabase_required` (e.g. `users/supabase_views.py`, `ai_draft/views.py`, `create_drafts/views.py`, `calendar_management/views.py`, `todaysupdates/views.py`, `talkdoc/views.py`). Unprotected views (e.g. login, signup, webhook verify) do not use it.

---

## Database and Shared Clients

**File:** `Legalv1/core/init_clients.py`

- **MongoDB:** `get_mongo_client()` returns a singleton `MongoClient`. Primary DB name: `legaldb` (see `settings.MONGO_URI`).
- **Supabase:** `get_supabase_client()` returns the app’s Supabase client (from `core.apps`). Used for auth and any Supabase-backed logic.
- **Redis:** Used as Django cache backend and Celery broker (see `Legalv1/Legalv1/settings.py`).
- **Indexes:** `ensure_indexes()` in `init_clients.py` defines MongoDB indexes (user_details, draft_content_data, aidrafts_complete_data). It is currently commented out at module load; can be run manually or on startup if needed.

---

## Main Django Apps (What Lives Where)

| App | Purpose | Key models / storage |
|-----|---------|----------------------|
| **users** | Auth (Supabase), profile, onboarding, signup (Mongo), courts/states/districts, feedback | MongoDB: user_details, sessions (legacy), feedback, signup_tokens, etc. |
| **ai_draft** | AI drafting sessions, sections, save/load, PDF, templates | MongoDB: aidrafts_complete_data |
| **create_drafts** | Template-based drafts, submit, auto-save, PDF | MongoDB: draft_content_data, user_draft_data; local files under draftdocs |
| **calendar_management** | Events CRUD | MongoDB (user_details.meetings, etc.) |
| **calendersetup** | Google Calendar OAuth (init, redirect, events) | N/A |
| **utilities** | Send email, state/district/court list | MongoDB: state_district_court_data |
| **search_facility** | Index documents, search, fetch content | OpenSearch + MongoDB |
| **whatsapp_module** | WhatsApp webhook (verify + handler) | MongoDB: whatsapp_chat_sessions, service_orders |
| **todaysupdates** | Court subscriptions, fetch updates (lawyer + paralegal) | MongoDB |
| **talkdoc** | RAG: upload docs, sessions, messages | MongoDB / OpenSearch (see talkdoc app) |
| **ecourts_scraper** | eCourts live data via browser automation: case by CNR, search, cause list, court structure. **Currently disabled** (CAPTCHA issues). | MongoDB: ecourts_cache, ecourts_scrape_jobs, ecourts_selectors; Celery queues ecourts_realtime, ecourts_background |
| **ecourts_api** | **Active.** Drop-in replacement for ecourts_scraper. Calls eCourts partner API directly (synchronous, no Celery). Caches in ecourts_cache. | MongoDB: ecourts_cache (shared); no Celery. Env: `ECOURT_TOKEN`. |
| **core** | Health check view, init_clients, response_utils | N/A |

See **06-ecourts-scraper.md** for eCourts architecture, APIs, and conventions.

---

## Users App — Two View Modules

- **`users/views.py`** — Unprotected or legacy-style endpoints: `signup_user`, `verify_email`, `get_prefilled_data`, `verify_barcode`, `get_states`, `get_districts`, `get_courts`. No `@supabase_required` here.
- **`users/supabase_views.py`** — Supabase-protected endpoints: `check_auth`, `invalidate_session`, `onboard_new_client`, `check_existing_user`, `onboard_existing_client`, `filter_cases_clients_with_details`, `submit_feedback`, `check_username`, `onboarding_new_user`, `get_profile`, `supabase_login`, `send_reset_password_link`, `reset_password`, `sign_out_supabase`, `profile_update_of_client_onboarded_by_lawyer`, `add_case_client`.

User-related **URLs** are in `Legalv1/users/urls.py`; each path points to either `views.*` or `supabase_views.*`.

---

## Environment and Configuration

- **Env file:** Project root `legalenv` (loaded via `load_dotenv(BASE_DIR / 'legalenv')` in `Legalv1/Legalv1/settings.py`).
- **Important settings (names to look for in settings.py):**
  - `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
  - `MONGO_URI`, `FRONTEND_URL` (used for redirects and Celery callbacks; default `https://mamla.ai`)
  - `CORS_ALLOWED_ORIGINS`
  - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_TOKEN` (or equivalent)
  - Redis/Celery configuration

### LLM Settings

All LLM calls are centralised in **`Legalv1/core/llm_client.py`** (`chat_complete()`). Do **not** instantiate OpenAI clients directly in app views/tasks.

| Env var | Purpose | Default |
|---------|---------|--------|
| `OPENAI_API_KEY` | OpenAI API key | — |
| `OPENROUTER_API_KEY` | OpenRouter API key (single key, all models) | — |
| `LLM_DEFAULT_PROVIDER` | Which provider to use: `openai` or `openrouter` | `openai` |
| `OPENAI_AI_DRAFT_MODEL` | OpenAI model for AI draft generation/editing | `gpt-4o-mini` |
| `RAG_CHAT_MODEL` | OpenAI model for TalkDoc RAG + general Q&A | `gpt-4o` |
| `OPENAI_UTILS_MODEL` | OpenAI model for draft description (utilities app) | `gpt-4o-mini` |
| `OPENAI_CREATE_DRAFTS_MODEL` | OpenAI model for create_drafts field extraction/fill | `gpt-4o` |
| `OPENROUTER_AI_DRAFT_MODEL` | OpenRouter model for AI draft | `openai/gpt-4o-mini` |
| `OPENROUTER_TALKDOC_RAG_MODEL` | OpenRouter model for TalkDoc RAG | `anthropic/claude-3-haiku` |
| `OPENROUTER_TALKDOC_GENERAL_MODEL` | OpenRouter model for TalkDoc general Q&A | `anthropic/claude-3-haiku` |
| `OPENROUTER_UTILS_MODEL` | OpenRouter model for draft description | `openai/gpt-4o-mini` |
| `OPENROUTER_CREATE_DRAFTS_MODEL` | OpenRouter model for create_drafts | `openai/gpt-4o` |
| `BRAIN_T1_MODEL` | Mamla-Brain tier-1 (micro) model | `meta-llama/llama-3.1-8b-instruct` |
| `BRAIN_T2_MODEL` | Mamla-Brain tier-2 (balanced) model | `anthropic/claude-3-haiku` |
| `BRAIN_T3_MODEL` | Mamla-Brain tier-3 (strong) model | `anthropic/claude-sonnet-4-5` |
| `TALKDOC_ENABLE_LLM` | Set to `0` to disable LLM in TalkDoc (test mode) | `1` |

---

## Health Check

- **Endpoint:** `GET /api/health/`
- **View:** `Legalv1/core/views.py` — `health(request)`
- **Response:** `200` with `{"status": "ok", "service": "legalv1"}`. Used for load balancers and monitoring.

---

## Error Response Helper (Optional)

**File:** `Legalv1/core/response_utils.py`

- `error_response(message, status=400, detail=None)` returns a standard `JsonResponse` with an `error` key (and optional `detail`). Available for future use; existing views were not changed to keep current API contracts.

---

## Where to Look for Specific Logic

- **Login / logout / session list:** `users/supabase_views.py` (e.g. `supabase_login`, `sign_out_supabase`, `check_auth`, `invalidate_session`).
- **Signup (Mongo + email verification):** `users/views.py` (`signup_user`), `users/views.py` (`verify_email`), plus `users/routes/checkusers.py` (e.g. `create_new_user`, `verify_signup_token`).
- **Onboarding (lawyer → client):** `users/supabase_views.py` (`onboard_new_client`, `onboard_existing_client`), `users/views.py` (`get_prefilled_data`), `users/routes/checkusers.py`.
- **AI draft lifecycle:** `ai_draft/views.py` and `ai_draft/urls.py` (start_session, sections, save_draft, etc.).
- **Session manager (legacy MongoDB sessions):** `users/routes/session_manager.py` (still used by some flows; Supabase is the source of truth for auth).

For a full list of endpoints and which require auth, see **04-api-reference.md**.
