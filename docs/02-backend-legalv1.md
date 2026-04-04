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
| `api/brain/` | `mamla_brain.urls` |
| `api/ecourts/` | `ecourts_scraper.urls` (scraper-first runtime) |
| `api/ecourts/v2/` | `ecourt_scrapped.urls` (Django proxy to FastAPI scraper) |

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
- **Indexes:** `ensure_indexes()` in `init_clients.py` defines MongoDB indexes (user_details, draft_content_data, aidrafts_complete_data, **cases.case_ref unique**). It is currently commented out at module load; run manually after verifying no legacy constraint conflicts before enabling at startup.

---

## Main Django Apps (What Lives Where)

| App | Purpose | Key models / storage |
|-----|---------|----------------------|
| **users** | Auth (Supabase), profile, onboarding, signup (Mongo), courts/states/districts, feedback | MongoDB: user_details, sessions (legacy), feedback, signup_tokens, etc. |
| **ai_draft** | AI drafting sessions, sections, save/load, PDF, templates. Also hosts the Guided Drafting conversational intake flow (`guide/*` endpoints). | MongoDB: aidrafts_complete_data, **draft_conversations** |
| **create_drafts** | Template-based drafts, submit, auto-save, PDF | MongoDB: draft_content_data, user_draft_data; local files under draftdocs |
| **calendar_management** | Events CRUD plus REST aliases and conflict APIs. The service layer stores recurring chains as per-day meeting entries, supports `only once`, `this and following`, and `entire series` operations, syncs participant copies into linked user records, and now sends creator/participant emails as separate deliveries instead of CC-style batching. | MongoDB (user_details.meetings, etc.) |
| **calendersetup** | Google Calendar OAuth (init, redirect, events) | N/A |
| **utilities** | Send email, state/district/court list | MongoDB: state_district_court_data |
| **search_facility** | Index documents, search, fetch content | OpenSearch + MongoDB |
| **whatsapp_module** | WhatsApp webhook (verify + handler) | MongoDB: whatsapp_chat_sessions, service_orders |
| **todaysupdates** | Court subscriptions, fetch updates (lawyer + paralegal) | MongoDB |
| **talkdoc** | RAG: upload docs, sessions, messages | MongoDB / OpenSearch (see talkdoc app) |
| **mamla_brain** | API-first domain reasoning framework on top of TalkDoc primitives. Supports tiered LLM routing, reusable domain prompts, external API-key auth, knowledge-base retrieval, document Q&A, and Case Companion-style structured reasoning for legal plus other configured domains such as banking or markets. | MongoDB: brain_api_keys, brain_sessions, brain_messages; OpenSearch knowledge-base indexes per domain; reuses rag_documents for uploaded source docs |
| **ecourt_scrapped** | **Active for eCourts v2 in MamlaAI terminals.** Django proxy layer for dropdown/master-data APIs and court-order/case-status/cause-list requests forwarded to the standalone FastAPI scraper service. | MongoDB: ecourts_master_data, ecourts_states, ecourts_districts; service modules in `services/scraper_client.py`, `services/master_data.py`, `services/ecourts_crawler.py` |
| **ecourts_scraper** | **Active.** Scraper-first eCourts runtime with async jobs, Mongo cache, stored reference datasets for stitched terminal dropdowns, and Capsolver-backed CAPTCHA solving. | MongoDB: ecourts_cache, ecourts_scrape_jobs, ecourts_selectors, ecourts_reference_data; Celery queues ecourts_realtime, ecourts_background |
| **ecourts_api** | **Deprecated reference only.** Previous partner-API implementation retained in the repo for rollback/debugging comments, not wired into runtime. | No active runtime usage. Do not depend on `ECOURT_TOKEN`. |
| **core** | Health check view, init_clients, response_utils | N/A |
| **cases** | Case CRUD (create/list/get/update/close), hearing notes, case notes, case tasks, agentic operations (intake, hearing-prep, post-hearing, draft-context, case-closure). `case_ref` field is now auto-generated (`MC-{YYYY}-{6-char}`) and has a unique MongoDB index. `ecourts_params` is a storable dict on the case record. | MongoDB: `cases`, `hearing_notes`, `case_notes`, `case_tasks` |

See **06-ecourts-scraper.md** for eCourts architecture, APIs, and conventions.

### eCourts v2 Notes (Current)

- `ecourt_scrapped` is the Django API surface used by MamlaAI eCourts terminal screens under `/api/ecourts/v2/`.
- FastAPI scraper requests are proxied through `services/scraper_client.py`; dropdown hierarchy data is read-through cached in Mongo via `services/master_data.py`.
- Court-order-by-date now uses the original eCourts POST parameter names (`fradorderdt`, `orderflagvalorderdt`, `order_date_captcha_code`) and the per-tab captcha namespace.
- Court-order-by-date input accepts browser `YYYY-MM-DD` and forwards normalized `DD-MM-YYYY` to eCourts.
- `est_code` is optional for v2 order-date and court-number flows.
- Court-number options for order search are sourced from the FastAPI `courtorder/court-numbers` endpoint to preserve the required encoded value format (for example `4$1^from^to`).

---

## Users App — Two View Modules

- **`users/views.py`** — Unprotected or legacy-style endpoints: `signup_user`, `verify_email`, `get_prefilled_data`, `verify_barcode`, `get_states`, `get_districts`, `get_courts`. No `@supabase_required` here.
- **`users/supabase_views.py`** — Supabase-protected endpoints: `check_auth`, `invalidate_session`, `onboard_new_client`, `check_existing_user`, `onboard_existing_client`, `filter_cases_clients_with_details`, `submit_feedback`, `check_username`, `onboarding_new_user`, `get_profile`, `supabase_login`, `send_reset_password_link`, `reset_password`, `sign_out_supabase`, `profile_update_of_client_onboarded_by_lawyer`, `add_case_client`, `list_clients` (flat client list, `?search=` supported).

User-related **URLs** are in `Legalv1/users/urls.py`; each path points to either `views.*` or `supabase_views.*`.

---

## Environment and Configuration

### Dual Environment (dev + prod on same machine)

The backend supports running **prod and dev simultaneously** on the same host without interference.

| Item | Prod | Dev |
|------|------|-----|
| Env file | `Legalv1/legalenv` | `Legalv1/legalenv.dev` |
| Trigger | `DJANGO_MODE=prod` (default) | `DJANGO_MODE=dev` |
| Django server | Gunicorn on **port 8000** | `runserver` on **port 8100** |
| Frontend | Nginx (mamla.ai) | webpack-dev-server **port 3001** → proxy `/api` → `:8100` |
| Redis DB | **0** | **1** |
| Celery workers | `prod_worker@%h`, `prod_ecourts@%h` | `dev_worker@%h`, `dev_ecourts@%h` |
| Celery concurrency | gevent × 100, prefork × 4 | gevent × 10, prefork × 2 |
| Celery beat | ✅ runs | ❌ skipped (no double emails) |
| OpenSearch prefix | _(empty)_ | `dev_` |
| Logs | `logs/` | `logs/dev/` |

**How it works:**
- `settings.py` reads `DJANGO_MODE` env var set by `start_backend.sh` and selects `legalenv` or `legalenv.dev` accordingly.
- `start_backend.sh prod` kills only port 8000 + prod-named workers — dev keeps running. Same in reverse.
- `stop.sh [dev|prod|both]` targets only the chosen environment.

**Start commands:**
```bash
./start_backend.sh prod    # Gunicorn on :8000, Redis DB 0
./start_backend.sh dev     # runserver on :8100, Redis DB 1
./start_frontend.sh prod   # build static → Nginx
./start_frontend.sh dev    # webpack-dev-server on :3001
```

**New env vars common to both files:**

| Env var | Purpose | Prod default | Dev value |
|---------|---------|-------------|-----------|
| `DJANGO_MODE` | Set by start script; picks env file | `prod` | `dev` |
| `BACKEND_PORT` | Port for Django/Gunicorn | `8000` | `8100` |
| `CELERY_BROKER_URL` | Redis broker URL | `redis://localhost:6379/0` | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | Redis result backend URL | `redis://localhost:6379/0` | `redis://localhost:6379/1` |
| `REDIS_URL` | Django cache Redis URL | `redis://localhost:6379/0` | `redis://localhost:6379/1` |
| `OPENSEARCH_INDEX_PREFIX` | Prepended to all OpenSearch index names | _(empty)_ | `dev_` |
| `GUNICORN_WORKERS` | Number of Gunicorn workers | `8` | N/A (runserver in dev) |
| `GUNICORN_WORKER_CONNECTIONS` | Gunicorn worker connections | `1000` | N/A |
| `FRONTEND_URL` | Base URL for email links / redirects | `https://mamla.ai` | `http://localhost:3001` |

Both `legalenv` and `legalenv.dev` are in `.gitignore` — never committed.

---

- **Env file:** Project root `legalenv` (loaded via env-file selection in `Legalv1/Legalv1/settings.py`).
- Backend start scripts now fail fast if the relevant env file is missing or if `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `ENCRYPTION_KEY`, and Mongo configuration are empty, so runtime bootstrap errors are surfaced before Django/Celery are launched in the background.
- Env aliases currently accepted for compatibility with the checked-in `legalenv` file: `CAPSOLVER_API` is treated the same as `CAPSOLVER_API_KEY` for the scraper runtime, and TalkDoc search accepts either `RAG_OS_*` or `OPENSEARCH_*` names for OpenSearch connectivity.
- **Important settings (names to look for in settings.py):**
  - `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
  - `MONGO_URI`, `FRONTEND_URL` (used for redirects and Celery callbacks; default `https://mamla.ai`)
  - `CORS_ALLOWED_ORIGINS`
  - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_TOKEN` (or equivalent)
  - Redis/Celery configuration

### LLM Settings

All LLM calls are centralised in **`Legalv1/core/llm_client.py`** (`chat_complete()` for text, `vision_complete()` for multimodal image inputs). Do **not** instantiate OpenAI clients directly in app views/tasks.

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
| `BRAIN_MONTHLY_FREE_QUOTA` | Default monthly request quota for externally issued Brain API keys | `100` |
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

### TalkDoc Notes

- TalkDoc conversation history for both legacy and REST-style query endpoints is already trimmed to the last 6 stored messages before sending context to the LLM, matching the Mamla Brain token-efficiency target.
- `talkdoc/views.py` now sanitizes document-processing errors before returning them to the frontend. Internal failure detail stays in Mongo (`error_detail`) and logs, while API responses expose only user-safe summaries.
- `GET /api/talkdoc/documents/<doc_id>/file/` streams the original uploaded file back to the authenticated owner for inline preview or download.
- `DELETE /api/talkdoc/documents/<doc_id>/` removes an uploaded TalkDoc file for its owner and strips that document id out of any surviving non-deleted chat sessions.
- Session reads and deletes in TalkDoc now enforce ownership checks consistently across both legacy and REST-style endpoints.
- `create_session` and `create_session_v2` default new titles to a timestamped label instead of generic `Chat Session` / `General Chat`, and they preserve optional `matter` context (`caseid`, `clientid`).
- TalkDoc retrieval is now session-scoped: the active session's stored `doc_ids` are the only document ids used during RAG retrieval. Per-turn document overrides are not used in `query_v2`.
- TalkDoc chat usage is now session-aware across two entitlement buckets. Sessions with attached documents consume `brain_doc_analysis`, while no-document legal chats consume `general_legal_chat`. For TalkDoc only, one successful charge now opens a bounded session bundle of up to 10 chat turns in the current session before the next quota unit is consumed. Both `POST /api/talkdoc/query/` and `POST /api/talkdoc/sessions/<session_id>/message` return a `quota` payload on success and on quota exhaustion, matching the Mamla Brain contract.
- For no-document TalkDoc sessions (`has_docs=False`), the backend now applies a lightweight local keyword gate before any LLM call. Clearly non-legal prompts are rejected immediately without a quota charge, which saves cost without adding latency.
- `modify_session_docs` allows adding more documents to an existing session, but once the session has started exchanging messages it rejects document removal so earlier context cannot silently disappear from the conversation history.
- `talkdoc/tasks.py` now extracts tables from PDF and DOCX uploads, formats CSV and XLSX uploads into indexable table text, rasterizes scanned PDF pages through `pypdfium2` when a page has no text layer, and uses the shared OpenAI/OpenRouter multimodal path for OCR-style extraction from image uploads and scanned-page images when plain server-side parsing is not available.
- The rebuilt TalkDoc frontend now supports uploading additional documents after a chat has already started; those new files are automatically attached to the active session through `POST /api/talkdoc/sessions/<session_id>/docs`.
- The rebuilt TalkDoc setup screen now uses `users/filter_with_details/` semantically: choosing a case filters linked clients and auto-fills the client field when the backend mapping resolves to a single client.
- TalkDoc uploads now store a timestamped display name alongside the original filename, and document records keep denormalized `case_ids` / `client_ids` metadata derived from the upload `matter` payload so document filtering and chat citations stay distinguishable across sessions.
- Production TalkDoc uploads depend on the Nginx proxy allowing larger multipart bodies; the checked-in `nginx_mamla.ai_optimized.conf` now raises `client_max_body_size` for `/api/` traffic to support larger post-chat uploads.
- The tracked live site file is `mamla.ai`, which should be copied to `/etc/nginx/sites-available/mamla.ai` (or merged there directly). Nginx will not read repo copies automatically; after updating the server file, validate with `nginx -t` and reload with `systemctl reload nginx`.
- Existing TalkDoc documents can be backfilled with `python scripts/backfill_talkdoc_document_metadata.py` from `Legalv1/`. That script populates `name_display`, `case_ids`, `client_ids`, `primary_case_id`, and `primary_client_id` for older `rag_documents` rows.

### Mamla Brain Notes

- `mamla_brain/views.py` exposes `/api/brain/v1/` endpoints for health, document upload/listing, session CRUD, document Q&A, Case Companion reasoning, and admin API-key generation.
- `mamla_brain/auth.py` implements dual auth: first-party callers may use the existing Supabase token, while third-party callers can use `X-Brain-API-Key` against the `brain_api_keys` collection with quota enforcement.
- `ai_draft/views.py` now applies `ai_draft_generation` entitlements to draft-creation endpoints (`initial_request/`, `upload_template`, `start_session_for_casedocument`) and returns `quota` payloads on success or exhaustion. The active frontend uses those responses to refresh entitlement state immediately after draft creation.
- `mamla_brain/prompts.py` defines reusable domain profiles and system prompts. Current built-in domain keys are `legal`, `banking`, and `markets`, so the framework can act as a self-standing reasoning service outside legal-only use cases.
- `mamla_brain/retrieval.py` reuses TalkDoc document vectors for user-owned source documents and adds separate OpenSearch knowledge-base indexes per domain (`legal_kb`, `banking_kb`, `markets_kb`).
- `mamla_brain/tasks.py` and `mamla_brain/management/commands/ingest_legal_kb.py` / `ingest_knowledge_base.py` provide chunking and ingestion for plain-text knowledge sources stored under `Legalv1/mamla_brain/legal_kb_sources/` or domain-specific source directories.
