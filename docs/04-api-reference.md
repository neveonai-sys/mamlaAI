# 04 — API Reference

Base path for all APIs below: **`/api/`** (e.g. production: `https://mamla.ai/api/`). Auth is **Supabase**: send a valid Supabase access token via cookie `access_token` or header `Authorization: Bearer <token>` unless the endpoint is marked **No auth**.

---

## Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health/` | No auth | Returns `{"status": "ok", "service": "legalv1"}`. For load balancers/monitoring. |

---

## Users (`/api/users/`)

**Module:** `users/views.py` (legacy) and `users/supabase_views.py` (Supabase-protected).  
**URL config:** `Legalv1/users/urls.py`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `signup-user/` | No auth | Main signup (Mongo). Token-based or standard; email verification link. |
| GET | `check-auth/` | **Supabase** | Returns user + sessions. Used by frontend for auth check and session list. |
| GET | `entitlements/summary/` | **Supabase** | Returns the current entitlement summary (`plan_code`, wallet, trial, `features`) for live quota refreshes in the active frontend. |
| POST | `invalidate-session/` | **Supabase** | Body: `{ "session_id": "..." }`. Invalidates that session. |
| POST | `get-prefilled-data/` | No auth | Body: `{ "token": "..." }`. Returns prefilled signup data for token. |
| POST | `onboard-client/` | **Supabase** | Lawyer onboard new client (creates signup link). |
| POST | `check-existing-user/` | **Supabase** | Body: phone/email. Returns whether user exists. |
| POST | `onboard-existing-client/` | **Supabase** | Link existing user as client to lawyer/case. |
| GET | `filter_with_details/` | **Supabase** | Returns cases/clients with details for current user. |
| GET | `get-courts/` | No auth | Query: `state`, `district`. Returns courts list. |
| GET | `get-districts/` | No auth | Query: `state`. Returns districts. |
| GET | `get-states/` | No auth | Returns states list. |
| POST | `verify-barcode/` | No auth | Body: `barcode_id`. Validates lawyer barcode. |
| GET | `verify-email/` | No auth | Query: `token`. Marks email verified, redirects to frontend login. |
| POST | `submit-feedback/` | **Supabase** | Submits user feedback (Mongo). |
| GET | `auth/check-username` | **Supabase** | Check username availability. |
| POST | `onboard/` | No auth | New user onboarding (Supabase). |
| GET | `get-profile` | **Supabase** | Get current user profile. |
| POST | `login-user/` | No auth | **Supabase login.** Returns user info; frontend stores token. |
| POST | `send-reset-password-link/` | No auth | Sends password reset email (Supabase). |
| POST | `reset-user-password/` | No auth | Supabase password reset (token in body/link). |
| POST | `sign-out-user/` | **Supabase** | Sign out (scope e.g. local). Frontend logout. |
| POST | `signup-onboarded-client/` | **Supabase** | Profile update for client onboarded by lawyer. |
| POST | `add_case_client` | **Supabase** | Add case–client relationship. |

---

## AI Drafts (`/api/aidrafts/`)

**Module:** `ai_draft/views.py`. Protected by `@supabase_required` (except test).  
**URL config:** `Legalv1/ai_draft/urls.py`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `get-draft-count/` | Supabase | Total drafts count. |
| POST | `start_session` | Supabase | Start drafting session. Consumes `ai_draft_generation` and returns `quota` on success or exhaustion. |
| POST | `set_location` | Supabase | Set draft location. |
| POST | `update_section` | Supabase | Update a section. |
| POST | `download_draft` | Supabase | Download draft (e.g. PDF). |
| GET | `get_draft_sections` | Supabase | All sections. |
| GET | `get_draft_single_section` | Supabase | Single section. |
| POST | `delete_section` | Supabase | Delete section. |
| POST | `suggest_section` | Supabase | AI suggestion for section. |
| POST | `add_section` | Supabase | Add section. |
| POST | `revert_to_original` | Supabase | Revert section. |
| POST | `update_section_order` | Supabase | Reorder sections. |
| GET | `get_section_history` | Supabase | Section edit history. |
| POST | `save_draft` | Supabase | Save draft. |
| GET | `get_user_saved_drafts` | Supabase | User's saved drafts. |
| GET | `get_user_saved_drafts_v2` | Supabase | Saved drafts v2. |
| POST | `load_saved_draft` | Supabase | Load saved draft. |
| POST | `delete_saved_draft` | Supabase | Delete saved draft. |
| POST | `upload_template` | Supabase | Upload template. Consumes `ai_draft_generation` and returns `quota` on success or exhaustion. |
| POST | `start_session_for_casedocument` | Supabase | Start session from case document. Consumes `ai_draft_generation` and returns `quota` on success or exhaustion. |
| GET | `download_template` | Supabase | Default template. |
| GET | `get_draft_for` | Supabase | Draft by session ID. |
| GET | `get_supported_languages` | Supabase | Supported languages. |
| GET | `test/hello/` | No auth | Test. |
| POST | `test/create/` | No auth | Create test draft. |
| POST | `test/update/` | No auth | Update test section. |
| GET | `test/download/` | No auth | Download test draft. |
| GET | `test/status/<uuid:session_id>/` | No auth | Test draft status. |
| GET | `test/sections/<str:session_id>/` | No auth | Test draft sections. |
| POST | `guide/start/` | Supabase | Start a guided-drafting conversation. Body: `{case_id?, document_ids?}`. Returns `{conv_id, message}`. |
| POST | `guide/message/` | Supabase | Send a user message in a guided conversation. Body: `{conv_id, message}`. Returns `{reply, ready, draft_plan?}`. |
| POST | `guide/upload_doc/` | Supabase | Process newly uploaded docs mid-conversation. Body: `{conv_id, document_ids}`. Returns `{reply}`. |
| POST | `guide/generate/` | Supabase | Trigger draft generation from the gathered context. Consumes `ai_draft_generation` quota. Body: `{conv_id}`. Returns `{session_id}`. |

---

## Create Drafts (`/api/drafts/`)

**Module:** `create_drafts/views.py`. All `@supabase_required`.  
**URL config:** `Legalv1/create_drafts/urls.py`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `get-all-drafts/` | Supabase | All draft types. |
| GET | `draft-items` | Supabase | Drafts by type. |
| GET | `draft-fields/` | Supabase | Required fields from doc. |
| POST | `submit-draft/` | Supabase | Create final draft, send PDF. |
| GET | `get-saved-drafts/` | Supabase | Saved drafts. |
| POST | `load-saved-draft/` | Supabase | Load saved draft. |
| POST | `auto-save/` | Supabase | Auto-save. |
| GET | `get-template/` | Supabase | PDF template. |
| POST | `get-updated-template/` | Supabase | Template with suggestions. |

---

## Calendar (`/api/calendar/`)

**Module:** `calendar_management/views.py`. All `@supabase_required`.  
**URL config:** `Legalv1/calendar_management/urls.py`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `add-event/` | Supabase | Create event. |
| GET | `get-all-events` | Supabase | All events. |
| POST | `delete-event/` | Supabase | Delete event. |
| POST | `update-event/` | Supabase | Update event. |
| GET | `events/` | Supabase | REST list endpoint used by the new MamlaAI calendar. Query: `start_date`, `end_date`, `page_size`, optional `search`, optional `upcoming`. |
| POST | `events/` | Supabase | REST create endpoint used by the new MamlaAI calendar. Persists all legacy event fields, creates recurring per-day instances when applicable, and sends creator/participant notifications. |
| PUT | `events/<event_id>/` | Supabase | REST update endpoint. Infers changed fields when the frontend does not send `updatedFields`, reuses the legacy recurring-aware service layer, and supports `only once`, `this and following`, and `entire series` semantics. |
| DELETE | `events/<event_id>/` | Supabase | REST delete endpoint. Infers recurring/title/party metadata from the stored event when omitted and routes through the legacy delete service. |
| POST | `conflicts/check/` | Supabase | Returns overlap analysis, reasons, next available slot, and alternate assignee recommendations for a proposed event payload. |
| POST | `conflicts/resolve/` | Supabase | Prepares a conflict resolution strategy (`reschedule`, `reassign`, `override`) and returns a patched event payload plus status/summary. |

---

## Google Calendar (root include)

**Base path:** `/` (from `calendersetup.urls`).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `api/v1/calendar/init/` | — | Google Calendar OAuth init. |
| GET | `api/v1/calendar/redirect/` | — | OAuth redirect. |
| GET | `api/v1/calendar/events/` | — | Google Calendar events. |

---

## Utilities (`/api/utils/`)

**Module:** `utilities/views.py`.  
**URL config:** `Legalv1/utilities/urls.py`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `send-simple-mail/` | — | Send simple email. |
| POST | `send-email/` | — | Send email (used by frontend Send Email and Celery). |
| GET | `state-district-court/` | — | State/district/court list. |

---

## Search (`/api/search/`)

**Module:** `search_facility/views.py`.  
**URL config:** `Legalv1/search_facility/urls.py`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `index-documents/` | — | Index documents. |
| GET | `search-by-index` | — | Search. |
| GET | `fetch-content/` | — | Content by draft type and filename. |

---

## WhatsApp Webhook (`/api/webhook/`)

**Module:** `whatsapp_module/views.py`. No Supabase; verification via Meta.  
**URL config:** `Legalv1/whatsapp_module/urls.py`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `verify/` | No auth | Meta webhook verification. |
| POST | `` | No auth | Webhook handler. |

---

## Today's Updates (`/api/todaysupdates/`)

**Module:** `todaysupdates/views.py`. All `@supabase_required`.  
**URL config:** `Legalv1/todaysupdates/urls.py`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `get-subscriptions/` | Supabase | Subscriptions. |
| POST | `subscribe-court/` | Supabase | Subscribe to court. |
| POST | `unsubscribe-court/` | Supabase | Unsubscribe. |
| GET | `fetch-updates/` | Supabase | Fetch updates. |
| GET | `get-paralegal-subscriptions/` | Supabase | Paralegal subscriptions. |
| POST | `paralegal-subscribe-court/` | Supabase | Paralegal subscribe. |
| POST | `paralegal-unsubscribe-court/` | Supabase | Paralegal unsubscribe. |
| GET | `fetch-paralegal-updates/` | Supabase | Paralegal fetch updates. |

---

## TalkDoc (`/api/talkdoc/`)

**Module:** `talkdoc/views.py`. All `@supabase_required`.  
**URL config:** `Legalv1/talkdoc/urls.py`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `docs/upload` | Supabase | Upload document. |
| GET | `docs` | Supabase | List documents. |
| GET | `documents/` | Supabase | REST-style document list for the rebuilt frontend. Supports optional `caseid` and `clientid` filters, and matches search against original, display, and stored filenames. |
| DELETE | `documents/<doc_id>/` | Supabase | Delete an uploaded TalkDoc document and remove it from any remaining non-deleted chat sessions owned by the caller. |
| GET | `documents/<doc_id>/file/` | Supabase | Stream the uploaded document back to its owner for inline preview or download (`?download=1`). |
| POST | `sessions` | Supabase | Create session. |
| GET | `sessions/list` | Supabase | List sessions. |
| GET | `sessions/` | Supabase | REST-style session list for the rebuilt frontend. |
| GET | `session_messages/?session_id=<id>` | Supabase | REST-style message list for the rebuilt frontend. |
| POST | `upload/` | Supabase | REST-style multipart upload endpoint used by the rebuilt frontend. Supports PDF, DOCX, TXT, CSV, XLSX, and image uploads used for OCR-style extraction. Uploaded records preserve the original filename and also generate a timestamped display/stored name for clearer chat citations and document lists. |
| POST | `create_session/` | Supabase | REST-style session creation endpoint. Accepts `doc_ids`, optional `matter`, optional `title`. |
| POST | `query/` | Supabase | REST-style chat query endpoint. Accepts `session_id` and `query`. Retrieval is scoped to the session's stored `doc_ids` and `matter`. Returns `answer`, `message`, `citations`, and a Mamla-Brain-compatible `quota` payload. Consumes `brain_doc_analysis` for sessions with docs and `general_legal_chat` for no-document sessions. In TalkDoc, one successful charge opens a bounded 10-chat session bundle before the next quota unit is consumed; the response `quota` includes `session_turn_limit`, `session_turns_used`, and `session_turns_remaining`. For no-document sessions, clearly non-legal prompts are rejected locally before any LLM call or quota charge. |
| GET | `sessions/<session_id>/messages` | Supabase | Get messages. |
| POST | `sessions/<session_id>/message` | Supabase | Send message. Returns `message`, `citations`, and `quota`. Consumes `brain_doc_analysis` for sessions with docs and `general_legal_chat` for no-document sessions. In TalkDoc, one successful charge opens a bounded 10-chat session bundle before the next quota unit is consumed; the response `quota` includes `session_turn_limit`, `session_turns_used`, and `session_turns_remaining`. For no-document sessions, clearly non-legal prompts are rejected locally before any LLM call or quota charge. |
| POST | `sessions/<session_id>/docs` | Supabase | Modify session docs. Adds are allowed and are used for live uploads into an active chat; removals are rejected after the session has started exchanging messages. |
| DELETE | `sessions/<session_id>` | Supabase | Delete session. |
| POST | `rename_session/<session_id>` | Supabase | Rename session. |

---

## Mamla Brain (`/api/brain/`)

**Module:** `mamla_brain/views.py`.  
**URL config:** `Legalv1/mamla_brain/urls.py`.  
**Auth model:** Dual. First-party callers can use **Supabase** exactly like the rest of the backend. Third-party callers can use **`X-Brain-API-Key`**. `GET /api/brain/v1/health/` is public.

### Core ideas

- The framework is API-first and can be used beyond legal-only workflows.
- Built-in `domain_key` values are currently `legal`, `banking`, and `markets`.
- User-uploaded source documents are still stored in `rag_documents`; Brain adds its own session/message/auth collections and domain knowledge-base retrieval.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `v1/health/` | No auth | Health/status endpoint. Returns configured LLM tiers plus knowledge-base index stats per domain. |
| POST | `v1/docs/upload/` | Supabase or API key with `doc_qa` | Multipart upload for Brain source documents. Accepts `file`, optional `matter`, optional `domain_key`. Stores metadata in `rag_documents` and queues TalkDoc ingestion. |
| GET | `v1/docs/` | Supabase or API key with `doc_qa` | List caller-owned Brain documents. Supports pagination and optional `q` / `domain_key` filtering. |
| POST | `v1/sessions/` | Supabase or API key with `doc_qa` | Create a Brain session. Body supports `domain_key`, `mode`, `doc_ids`, optional `matter`, `case_type`, `party_role`, `metadata`, `title`. |
| GET | `v1/sessions/list/` | Supabase or API key with `doc_qa` | List Brain sessions for the authenticated caller. Supports pagination, optional `q`, optional `domain_key`. |
| GET | `v1/sessions/<session_id>/messages/` | Supabase or API key with `doc_qa` | Return all stored Brain messages for a session. |
| POST | `v1/sessions/<session_id>/message/` | Supabase or API key with `doc_qa` | Standard Brain message endpoint. Runs tier-1 query rewrite, document retrieval, optional KB retrieval, then tier-2 answering. Returns `message`, `answer`, `citations`, and `rewritten_query`. |
| DELETE | `v1/sessions/<session_id>/` | Supabase or API key with `doc_qa` | Soft-delete a Brain session. |
| POST | `v1/case-companion/start/` | Supabase or API key with `case_companion` | Create a Case Companion session (`mode=case_companion`). Supports `domain_key`, `doc_ids`, `matter`, `case_type`, `party_role`, `metadata`, `title`. |
| POST | `v1/case-companion/<session_id>/advise/` | Supabase or API key with `case_companion` | Structured reasoning endpoint. Runs tier-1 issue classification, knowledge-base retrieval, document retrieval, then tier-3 JSON response generation. |
| POST | `v1/admin/keys/` | Supabase admin only | Generate an external Brain API key. Returns the raw key once; only the hash is stored in MongoDB. |

### Example Brain session payload

```json
{
  "domain_key": "banking",
  "mode": "doc_qa",
  "doc_ids": ["67d3b3b3b3b3b3b3b3b3b3b3"],
  "matter": {
    "caseid": ["BANK-2026-014"],
    "clientid": ["client-112"]
  },
  "metadata": {
    "product": "loan-recovery"
  }
}
```

### Example Case Companion response shape

```json
{
  "summary": "brief case or matter summary",
  "applicable_law": [
    {"act": "Negotiable Instruments Act", "section": "138", "relevance": "dishonour notice and complaint framing"}
  ],
  "arguments_for": ["..."],
  "arguments_against": ["..."],
  "weaknesses": ["..."],
  "recommended_steps": ["..."],
  "citations": [
    {"source": "loan_agreement_20260314.pdf", "snippet": "..."}
  ]
}
```

---

## eCourts (`/api/ecourts/`)

**Active v2 module:** `ecourt_scrapped/views.py` — registered at `/api/ecourts/v2/`. All `@supabase_required`.  
**URL config:** `Legalv1/ecourt_scrapped/urls.py`.  
**Master data** (states/districts/…) cached in MongoDB `ecourts_master_data`. Seed via `POST /api/ecourts/v2/seed/` or `python manage.py seed_ecourts_hierarchy`.  
**Deprecated (old v1):** `ecourts_scraper/views.py` at `/api/ecourts/` — do not add new features here.

### v2 Dropdown / Master Data

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET  | `v2/health/` | Supabase | FastAPI scraper connectivity check |
| GET  | `v2/states/` | Supabase | All 37 states `[{name, code}]` — read-through cache in MongoDB |
| POST | `v2/districts/` | Supabase | Districts for a state `{state_code}` |
| POST | `v2/complexes/` | Supabase | Court complexes `{state_code, dist_code}` |
| POST | `v2/establishments/` | Supabase | Establishments `{state_code, dist_code, court_complex_code}` |
| POST | `v2/courts/` | Supabase | Courts `{state_code, dist_code, court_complex_code, est_code}` |
| POST | `v2/police-stations/` | Supabase | Police stations (FIR search) |
| POST | `v2/order-case-types/` | Supabase | Case types for court-order search |
| POST | `v2/order-court-numbers/` | Supabase | Court numbers for court-order search |
| POST | `v2/seed/` | Supabase | Seed states immediately; enqueue district seeding if `seed_districts: true` |

### v2 Case Search (Flow C)

| Method | Path | Body fields | Description |
|--------|------|-------------|-------------|
| POST | `v2/casestatus/by-party/` | state_code, dist_code, court_complex_code, est_code, party_name | Search by party name |
| POST | `v2/casestatus/by-filing/` | + filing_number, registration_year, case_type | By filing number |
| POST | `v2/casestatus/by-advocate/` | + advocate_name / advocate_code / enrollment_number | By advocate |
| POST | `v2/casestatus/by-fir/` | + police_station_code, fir_year, fir_number | By FIR |

### v2 Cause List (Flow B)

| Method | Path | Body fields | Description |
|--------|------|-------------|-------------|
| POST | `v2/causelist/fetch/` | state_code, dist_code, court_complex_code, est_code, court_no, court_name, date, list_type (civil|criminal) | Fetch cause list |

### v2 Court Orders (Flow D)

| Method | Path | Description |
|--------|------|-------------|
| POST | `v2/courtorder/by-party/` | Orders by party name |
| POST | `v2/courtorder/by-case-number/` | Orders by case number + case type |
| POST | `v2/courtorder/by-court-number/` | Orders by court number |
| POST | `v2/courtorder/by-order-date/` | Orders by date range |

#### v2 Court Orders Contract Notes

- `est_code` is optional for `v2/courtorder/by-court-number/` and `v2/courtorder/by-order-date/`.
- `from_date` and `to_date` can be sent as `YYYY-MM-DD` (frontend date input) or `DD-MM-YYYY`; the scraper normalizes to eCourts-compatible `DD-MM-YYYY`.
- For `v2/courtorder/by-order-date/`, the upstream eCourts form contract uses `fradorderdt` + `orderflagvalorderdt` and captcha field `order_date_captcha_code`.
- For `v2/courtorder/by-court-number/`, use the encoded value returned by `POST v2/order-court-numbers/` (example format: `4$1^2015-10-05^2016-08-31`).
- Court-order PDF download behavior: partner-side "file not uploaded" responses are surfaced as HTTP `404`; expired/invalid partner sessions return `422` and require re-running search.

### v2 Direct Lookup (Flow A / Shared)

| Method | Path | Description |
|--------|------|-------------|
| POST | `v2/cnr/search/` | Case by CNR (16-char) |
| POST | `v2/case/by-cino/` | Case by CINO |
| POST | `v2/case/from-url/` | Case from eCourts URL |
| POST | `v2/case/history/` | Case history |
| POST | `v2/case/detail/` | Case detail |
| GET  | `v2/case/order-pdf/` | Download order PDF |

---

### Legacy: Scraper-first Runtime (`ecourts_scraper`) — deprecated

Registered at `/api/ecourts/` (no v2 prefix). Do **not** add new features here.

### Active: Scraper-first Runtime (`ecourts_scraper`)

Case lookup, search, cause-list, and order-download flows are **async/cache-first**. Cache hits return `200`; cache misses queue a job and return `202` with `job_id`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `case/<cnr>/` | Supabase | Case detail by CNR. Returns cached data or `202` + `job_id`. |
| POST | `case/<cnr>/refresh/` | Supabase | Force a fresh scrape and return `202` + `job_id`. |
| GET | `case/<cnr>/orders/` | Supabase | Orders list from cached case data. |
| GET | `case/<cnr>/orders/<idx>/download/` | Supabase | Cached PDF or `202` + `job_id` for scraper download. |
| POST | `search/` | Supabase | Scraper search endpoint. Current live support is `search_type: advocate` on both courts and `search_type: party` on High Court; unsupported stitched search modes or unsupported court/mode combinations return `400`. |
| GET | `jobs/<job_id>/` | Supabase | Poll async scraper job status. |
| GET | `causelist/` | Supabase | High-court daily cause-list scrape. Requires `date`, `high_court_id`, `bench_code`, and optionally `causelist_type=daily`. Any other `causelist_type` returns `400`. Returns cached data or `202` + `job_id`. |
| GET | `causelist/dates/` | Supabase | Available cached cause-list dates for a bench. |
| GET | `reference/<section>/` | Supabase | Stored terminal reference data. Sections: `case-status`, `court-orders`, `cause-list`, `caveat`. |

---

## High Court eCourts (`/api/ecourts/v2/hc/`)

**Module:** `ecourt_scrapped/hc_views.py` — all `@supabase_required`.  
**URL config:** `Legalv1/ecourt_scrapped/hc_urls.py`, included via `hc/` in `ecourt_scrapped/urls.py`.  
**Backend proxies to:** HC FastAPI scraper at `HC_SCRAPER_BASE_URL` (default `http://localhost:8001`).  
**No master data caching** — HC courts list is static (fetched from scraper's in-memory dict).  
**Date format note:** `/hc/orders/by-court/` expects `YYYY-MM-DD`; `/hc/orders/by-date/` and `/hc/causelist/` expect `DD-MM-YYYY`. The frontend converts automatically.

### HC Info / Metadata

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `v2/hc/health/` | Supabase | HC scraper service reachability check |
| GET | `v2/hc/courts/` | Supabase | All 25+ HCs + bench slugs + labels. Shape: `{ hc_slug: { name, benches: { bench_slug: label } } }` |
| GET | `v2/hc/meta/police-stations/?hc=&bench=` | Supabase | Police station list for FIR search `[{code, name}]` |
| GET | `v2/hc/meta/court-numbers/?hc=&bench=` | Supabase | Judge/court list for orders-by-court `[{court_code, judge_name, ...}]` |

### HC Case Lookup

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `v2/hc/case/cnr/<cino>/` | Supabase | Full `HCCaseDetail` — HC/bench auto-detected from CNR prefix |

### HC Case Status Searches

| Method | Path | Body fields | Description |
|--------|------|-------------|-------------|
| POST | `v2/hc/case/party/` | hc, bench, name, year, status | Search by party name (min 3 chars) |
| POST | `v2/hc/case/advocate/` | hc, bench, query, status | Search by advocate name (min 3 chars) |
| POST | `v2/hc/case/bar-code/` | hc, bench, bar_code, status | Search by bar registration number |
| POST | `v2/hc/case/filing/` | hc, bench, filing_number, year | Search by filing/diary number |
| POST | `v2/hc/case/fir/` | hc, bench, police_station, status, fir_number?, fir_year? | Search FIR cases |

### HC Court Orders

| Method | Path | Body fields | Description |
|--------|------|-------------|-------------|
| POST | `v2/hc/orders/search/` | hc, bench, name, year? | Orders by party name — returns PDF URLs |
| POST | `v2/hc/orders/by-court/` | hc, bench, judge_code, date_from (YYYY-MM-DD), date_to | Orders by judge/court and date range |
| POST | `v2/hc/orders/by-date/` | hc, bench, date_from (DD-MM-YYYY), date_to | Orders by date range |

### HC Cause List

| Method | Path | Body fields | Description |
|--------|------|-------------|-------------|
| POST | `v2/hc/causelist/` | hc, bench, list_date? (DD-MM-YYYY) | Daily bench cause list with PDF links |

### HC `hc` / `bench` Slug Reference

Use `GET /api/ecourts/v2/hc/courts/` to enumerate all valid slugs. Examples:

| `hc` slug | HC Name | Example `bench` slug |
|---|---|---|
| `allahabad` | Allahabad High Court | `allahabad`, `lucknow` |
| `delhi` | High Court of Delhi | `delhi` |
| `bombay` | Bombay High Court | `bombay`, `nagpur`, `aurangabad`, `goa` |
| `calcutta` | Calcutta High Court | `calcutta`, `appellate`, `jalpaiguri`, `port_blair` |
| `madras` | Madras High Court | `madras`, `madurai` |
| `karnataka` | High Court of Karnataka | `bangalore`, `dharwad`, `kalaburagi` |
| GET | `court-structure/` | Supabase | Top-level high courts plus district-court states. |
| GET | `court-structure/high-courts/` | Supabase | High courts from constants. |
| GET | `court-structure/district/states/` | Supabase | Stored district-court states reference data. |
| GET | `court-structure/district/states/<state>/districts/` | Supabase | Districts for a selected state. |
| GET | `court-structure/district/states/<state>/districts/<district>/complexes/` | Supabase | Stored or synthetic district-court complexes. |
| GET | `court-structure/district/states/<state>/districts/<district>/courts/` | Supabase | Flattened court list for the district's primary complex. |
| GET | `court-structure/district/states/<state>/districts/<district>/complexes/<complex>/courts/` | Supabase | Courts scoped to a selected complex. |

**Search body example:**
```json
{
  "search_type": "advocate",
  "query": "Sharma",
  "court_type": "high_court",
  "high_court_id": "5",
  "bench_code": "1",
  "page": 1,
  "page_size": 20
}
```

For district-court advocate search, replace the high-court selectors above with `state_id`, `district_id`, and `court_complex_id`.

**High Court party-name example:**
```json
{
  "search_type": "party",
  "query": "Sharma",
  "court_type": "high_court",
  "high_court_id": "5",
  "bench_code": "1",
  "registration_year": "2024",
  "case_status": "both",
  "page": 1,
  "page_size": 20
}
```

**Search response:** cache hit returns `data.case_list`, `data.total`, `data.page`, `data.page_size`, `data.total_pages`; cache miss returns `202` with `job_id`, and the completed job result exposes `result.case_list`.

---

## Cases (`/api/cases/`)

**Module:** `cases/views.py`. All `@supabase_required`.  
**URL config:** `Legalv1/cases/urls.py`.  
**Collections:** `cases`, `hearing_notes`, `case_notes`, `case_tasks`.  
**Access rules:** Lawyer sees/edits all cases they own. Paralegal sees cases where their user_id is in `paralegal_ids`. Client sees cases where their user_id is in `client_ids` (notes filtered to `visibility=shared`).

### Case CRUD

| Method | Path | Description |
|--------|------|-------------|
| POST | `cases/create/` | Create internal case. Required: `title`. Returns `{case}`. |
| GET | `cases/list/` | Lawyer's case list. Query: `status`, `stage`, `search`. Returns `{cases: [...]}`. |
| GET | `cases/<id>/` | Full case detail. Returns `{case}`. |
| PUT/PATCH | `cases/<id>/update/` | Partial update (lawyer only). Returns `{case}`. |
| POST | `cases/<id>/close/` | Close/archive. Body: `{resolution_type, summary}`. Returns `{case}`. |
| GET | `cases/<id>/timeline/` | All hearings + notes + tasks aggregated. Returns `{case, hearings, notes, tasks}`. |

### Hearing Notes

| Method | Path | Description |
|--------|------|-------------|
| POST | `cases/<id>/hearing-notes/` | Create hearing note. Required: `hearing_date`, `type` (prep\|outcome). Returns `{hearing_note}`. |
| GET | `cases/<id>/hearing-notes/list/` | List hearing notes for case. Returns `{hearing_notes: [...]}`. |
| GET | `cases/<id>/hearing-notes/<note_id>/` | Get hearing note detail. Returns `{hearing_note}`. |
| PATCH | `cases/<id>/hearing-notes/<note_id>/update/` | Update outcome, next_date, content, ai_brief. Returns `{hearing_note}`. |

### Case Notes

| Method | Path | Description |
|--------|------|-------------|
| POST | `cases/<id>/notes/` | Add note. Required: `content`. Optional: `visibility` (internal\|shared). Returns `{note}`. |
| GET | `cases/<id>/notes/list/` | List notes (clients see shared only). Returns `{notes: [...]}`. |
| PATCH | `cases/<id>/notes/<note_id>/update/` | Edit note (author only). Returns `{note}`. |
| DELETE | `cases/<id>/notes/<note_id>/delete/` | Delete note. Returns `{deleted: true}`. |

### Case Tasks

| Method | Path | Description |
|--------|------|-------------|
| POST | `cases/<id>/tasks/` | Create task. Required: `title`. Optional: `due_date`, `priority`, `assigned_to`, `source`. Returns `{task}`. |
| GET | `cases/<id>/tasks/list/` | List tasks. Query: `status`, `assigned_to`. Returns `{tasks: [...]}`. |
| PATCH | `cases/<id>/tasks/<task_id>/update/` | Update task (not clients). Returns `{task}`. |
| DELETE | `cases/<id>/tasks/<task_id>/delete/` | Delete task (lawyer only). Returns `{deleted: true}`. |

---

## Request/Response Conventions

- **Content-Type:** JSON where applicable (`application/json`). Multipart for file uploads (e.g. send-email, uploads).
- **Errors:** Backend often returns `JsonResponse` with `message` or `error` key and appropriate 4xx/5xx status. Frontend Axios interceptor handles 401/403 (redirect) and logs 5xx.
- **Auth:** Supabase token in cookie `access_token` or header `Authorization: Bearer <token>`. `withCredentials: true` when using cookies.

For architectural context and where each app lives, see **02-backend-legalv1.md** and **03-frontend-webpack.md**.

---

## Dashboard Aggregation

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/dashboard/home/` | Supabase | Aggregated home metrics: `pending_drafts` (int), `upcoming_events` (int, next 30 days), `upcoming_events_list` (array of upcoming events: `[{id, title, start, event_type}]` sorted by start), `recent_drafts` (array of 5: session_id / draft_name / status / created_at), `recent_updates` (array of 5: court / update / time). Implemented in `core/views.py`. |

---

## Agents (/api/agents/)

All endpoints: `POST`, `@supabase_required`. Each returns `{"ok": true, ...result}` on success or `{"ok": false, "error": "..."}` on failure.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/agents/case-intake/` | Create case with eCourts enrichment + LLM classification. Body: `title` (req), `case_description`, `cnr`, `court`, `client_ids`, `filing_date`. Returns `{case, enrichment_notes, next_suggested_action}`. |
| POST | `/api/agents/document-intel/` | Extract structured facts from uploaded TalkDoc documents. Body: `case_id` (req), `document_ids` (req, list). Returns `{facts, brief_updated, chunks_retrieved, next_suggested_action}`. |
| POST | `/api/agents/hearing-prep/` | Generate AI hearing brief; stored as `hearing_notes` type=prep. Body: `case_id` (req), `hearing_date` (req), `purpose`, `document_ids`, `calendar_event_id`. Returns `{note_id, ai_brief, context_used, next_suggested_action}`. |
| POST | `/api/agents/post-hearing/` | Record outcome, update case, auto-create follow-up tasks. Body: `case_id` (req), `hearing_notes_id` (req), `outcome_text` (req), `next_date`. Returns `{hearing_status, tasks_created, next_suggested_action}`. |
| POST | `/api/agents/draft-context/` | Build enriched context for DraftingWorkspace pre-fill. Body: `case_id` (req), `draft_type`, `document_ids`. Returns `{draft_context: {draft_for, location, context_summary, suggested_sections, key_facts}}`. |
| POST | `/api/agents/case-closure/` | Archive case, generate summary, cancel pending tasks, create shared client note. Body: `case_id` (req), `resolution_type`, `resolution_summary` (req). Returns `{case_summary, stats, client_note_id, next_suggested_action}`. |

**Agent architecture:** Each agent is a deterministic fixed-step Python class in `Legalv1/agents/`. No LangChain/LangGraph — max 2-3 LLM calls per agent via `core/llm_client.chat_complete()`. See `docs/08-lawyer-workflow-plan.md` Section 10.
