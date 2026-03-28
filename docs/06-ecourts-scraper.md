# 06 -- eCourts Scraper Module

## Overview

The **scraper is the live eCourts runtime again**. `/api/ecourts/` now resolves to `ecourts_scraper`, not the older partner-token `ecourts_api` path.

The **eCourts scraper** is a Django app (`ecourts_scraper`) that fetches live case data, cause lists, order PDFs, and court information from Indian government eCourts websites (High Courts and District Courts) via browser automation. It uses an **agentic architecture**: a deterministic state machine (ScrapeAgent) with CAPTCHA solving, proxy rotation, rate limiting, LLM-based self-healing, and MongoDB caching. All scraping runs asynchronously via Celery; the API returns cached data when available or queues a job and returns a `job_id` for polling.

**Use this doc when:** Working on eCourts APIs, scrapers, Celery tasks for court data, cache/job collections, or frontend that consumes eCourts (case lookup, cause list, court tree, order PDFs).

### eCourts v2 Proxy Runtime (MamlaAI terminals)

Alongside `ecourts_scraper`, the active MamlaAI terminal flows also use `ecourt_scrapped` at `/api/ecourts/v2/` as a Django proxy layer in front of the standalone FastAPI scraper service.

- Django proxy app: `Legalv1/ecourt_scrapped/`
- URL prefix: `/api/ecourts/v2/`
- FastAPI bridge: `ecourt_scrapped/services/scraper_client.py`
- Master data cache: `ecourt_scrapped/services/master_data.py` (Mongo collection `ecourts_master_data`)
- Live fallback crawler: `ecourt_scrapped/services/ecourts_crawler.py`

The v2 layer is used by the stitched terminal UI for location cascades and court-order search workflows.

### Recent v2 Stability Fixes (Mar 2026)

- Court-order-by-date now uses original eCourts field names (`fradorderdt`, `orderflagvalorderdt`, `order_date_captcha_code`) instead of shorthand aliases.
- Court-order-by-date date inputs are normalized from browser `YYYY-MM-DD` to eCourts `DD-MM-YYYY` before submit.
- Court-order captcha namespace is pinned per tab (`div_captcha_order_party`, `div_captcha_order_case`, `div_captcha_court_no`, `div_captcha_order_date`).
- Captcha image requests preserve existing securimage query strings and do not append extra cache-busting params to namespace-hash URLs.
- `est_code` validation was relaxed for v2 order-date and court-number paths.
- Order-court-number options now come from FastAPI `courtorder/court-numbers` so encoded value format stays compatible with submit APIs.
- Court-order PDF fallback now prioritizes `CO_HOME_URL` when session cookies are present; partner-side "file not uploaded" now returns `404` instead of a generic session-expired `422`.

---

## Where It Lives

| Item | Path |
|------|------|
| Django app | `Legalv1/ecourts_scraper/` |
| URL prefix | `api/ecourts/` |
| Main URL config | `Legalv1/Legalv1/urls.py` -> `include('ecourts_scraper.urls')` |
| Views | `ecourts_scraper/views.py` |
| Celery tasks | `ecourts_scraper/tasks.py` |
| Scrapers | `ecourts_scraper/scrapers/` (base, highcourt, districtcourt, causelist) |
| Agent / job state | `ecourts_scraper/agent/` (state_machine.py, job_manager.py, self_heal.py) |
| Infra | `ecourts_scraper/infra/` (browser_pool, captcha, proxy, rate_limiter, parsers) |
| Cache / DB helpers | `ecourts_scraper/cache/` (collections.py, cache_manager.py) |
| Constants | `ecourts_scraper/constants.py` |

---

## API Endpoints (Summary)

Base path: **`/api/ecourts/`**. All require **Supabase** auth unless noted.

| Method | Path | Description |
|--------|------|-------------|
| GET | `case/<cnr>/` | Case detail by CNR. Returns cached data if present; otherwise 202 + `job_id` to poll. |
| POST | `case/<cnr>/refresh/` | Force re-scrape; invalidates cache, returns 202 + `job_id`. |
| GET | `case/<cnr>/orders/` | Orders list from cached case data. |
| GET | `case/<cnr>/orders/<idx>/download/` | Download order PDF (base64). Cache-first; else 202 + `job_id`. |
| GET | `jobs/<job_id>/` | Poll async job status. When `status === "completed"`, `result` contains scraped data. |
| POST | `search/` | Search by advocate on HC/DC, or by party name on High Court. Cache-first with pagination (`page`, `page_size`). Returns 200 if cached; else 202 + `job_id`. |
| GET | `causelist/` | Daily cause list for HC + date. Params: `date`, `high_court_id`, `bench_code`, optional `causelist_type=daily`. Cache-first; else 202 + `job_id`. Unsupported non-daily types return `400`. |
| GET | `causelist/dates/` | Cached cause list dates for a court. Params: `high_court_id`, `bench_code`. |
| GET | `reference/<section>/` | Stored module reference data for the stitched terminal UI (`case-status`, `court-orders`, `cause-list`, `caveat`). |
| GET | `court-structure/` | Top-level tree: high courts (with benches) + district court states. Pure DB read. |
| GET | `court-structure/high-courts/` | All high courts with benches (from constants). |
| GET | `court-structure/district/states/` | District court states. |
| GET | `court-structure/district/states/<state>/districts/` | Districts within a state. |
| GET | `court-structure/district/states/<state>/districts/<district>/complexes/` | Stored or synthetic district-court complexes for dropdown cascades. |
| GET | `court-structure/district/states/<state>/districts/<district>/courts/` | Courts within a district (with `platform_id`). |
| GET | `court-structure/district/states/<state>/districts/<district>/complexes/<complex>/courts/` | Courts scoped to the selected complex. |

Response shapes and request bodies are described in **04-api-reference.md** (eCourts section). Frontend should poll `jobs/<job_id>/` every 3-5 seconds until `status` is `completed` or `failed`.

---

## Architecture (Agentic)

- **Layer 1 -- Orchestrator:** Celery. Two queues: `ecourts_realtime` (user-triggered), `ecourts_background` (scheduled refresh, cleanup). Tasks live in `ecourts_scraper/tasks.py`.
- **Layer 2 -- ScrapeAgent:** Deterministic state machine in `agent/state_machine.py`. States: CHECK_CACHE -> ACQUIRE_BROWSER -> SELECT_PROXY -> NAVIGATE -> SOLVE_CAPTCHA -> FILL_FORM -> SUBMIT -> PARSE -> VALIDATE -> CACHE_RESULT -> RETURN_RESULT. Recovery: ROTATE_PROXY, RETRY_CAPTCHA, BACKOFF, SELF_HEAL.
- **Layer 3 -- Self-heal:** LLM-based selector recovery in `agent/self_heal.py`. When repeated selector failures occur, captures page HTML + screenshot, sends to OpenAI (`gpt-4o-mini` by default via `ECOURTS_SELF_HEAL_MODEL`), receives replacement selector, upserts into `ecourts_selectors` collection. `get_selector()` function reads from DB with fallback to `constants.py`. Up to `SELF_HEAL_MAX_RETRIES` (default 2) attempts before failing. Controlled by `ECOURTS_SELF_HEAL_ENABLED` env var.

Scrapers implement `BaseScraper` in `scrapers/base.py`. Concrete: `HighCourtScraper` (hcservices.ecourts.gov.in), `DistrictCourtScraper` (services.ecourts.gov.in), `CauseListScraper` (HC daily cause lists via the main HC menu plus captcha). They are responsible for: `navigate`, `solve_captcha`, `refresh_captcha`, `fill_form`, `submit_and_check`, `parse_results`, `validate_result`, plus `build_cache_key` and `get_data_type`.

**Court structure** endpoints (`court-structure/`) are pure MongoDB reads from the existing `state_district_court_data` collection (populated by `update_state_district_court_data` task in `utilities/tasks.py`). High court data comes from `HIGH_COURT_CODES` in `constants.py`. No scraping involved -- reuses existing APIs and data.

---

## MongoDB Collections

- **`ecourts_cache`** -- Scraped results with TTL. Keys like `hc:case:<cnr>`, `dc:case:<cnr>`, `hc:search:...`, `hc:causelist:...`, `hc:order_pdf:<cnr>:<idx>`. Fields: `cache_key`, `data_type`, `data`, `source_site`, `scraped_at`, `expires_at`, `scrape_status`. TTL index on `expires_at`.
- **`ecourts_scrape_jobs`** -- Async job tracking. Fields: `_id` (job_id), `user_id`, `type`, `status`, `progress`, `params`, `result`, `error`, `agent_state`, `retry_count`, `created_at`, `updated_at`, `completed_at`. Used for polling.
- **`ecourts_selectors`** -- Healed selectors from self-healing agent. Keyed by `site` + `page` + `element`. Fields: `selector` (the replacement), `previous_selector`, `healed_at`, `heal_count`, `source`. Used by `get_selector()` in `agent/self_heal.py` with fallback to `constants.py`.
- **`state_district_court_data`** -- (existing, shared) District court structure: `state_name`, `district_name`, `court_name`, `court_platform_assigned_id`. Populated by `utilities/tasks.py::update_state_district_court_data` from phoenix.akshit.me.

Indexes and helpers: `ecourts_scraper/cache/collections.py`, `ensure_ecourts_indexes()` (can be called from app ready or a management command).

---

## Celery Queues and Beat

- **Queues:** `ecourts_realtime`, `ecourts_background` (defined in `Legalv1/Legalv1/celery.py`).
- **Tasks:**
  - `scrape_case_by_cnr` -- realtime, 10/m
  - `scrape_advocate_search` -- realtime, 5/m
  - `scrape_party_search` -- realtime, 5/m (High Court only)
  - `scrape_cause_list` -- realtime, 5/m
  - `download_order_pdf_task` -- realtime, 5/m
  - `refresh_subscribed_causelists` -- background, 2/m
  - `refresh_tracked_cases` -- background, 2/m
  - `cleanup_expired_cache` -- background
  - `health_check_selectors` -- background (navigates to sites, validates selectors)
- **Beat schedule** (in `Legalv1/Legalv1/settings.py`):
  - `ecourts-cleanup-expired-cache` -- daily 4:00 AM
  - `ecourts-health-check-selectors` -- daily 3:00 AM
  - `ecourts-refresh-subscribed-causelists` -- 6:30, 12:30, 18:30 (3x daily)
  - `ecourts-refresh-tracked-cases` -- daily 2:00 AM (skips recently cached)
  - `ecourts-populate-case-defaults-daily` -- daily 6:30 AM (`ecourts_api.tasks`)
  - `ecourts-populate-litigant-defaults-daily` -- daily 6:35 AM (`ecourts_api.tasks`)
  - `ecourts-populate-lawyer-defaults-weekly` -- Monday 6:40 AM (`ecourts_api.tasks`)

---

## Dependencies and Env

- **Optional at Django import time:** `playwright`, `easyocr`, `opencv-python-headless`, `httpx`, `openai` are used only when Celery runs scraping/self-heal tasks (lazy imports). Django can start without them.
- **Env (in project root `legalenv`):**
  - `ECOURTS_CAPTCHA_SERVICE` -- `capsolver` (preferred runtime), `easyocr`, or `2captcha`
  - `ECOURTS_CAPSOLVER_API_KEY` / `CAPSOLVER_API_KEY` -- Active CAPTCHA secret for scraper runtime
  - `ECOURTS_2CAPTCHA_API_KEY` -- Legacy fallback only
  - `ECOURTS_MAX_CONCURRENT_BROWSERS` -- Default 3
  - `ECOURTS_PROXY_POOL_URL` -- Optional; comma-separated or HTTP URL to proxy list
  - `ECOURTS_HC_RATE_LIMIT_PER_MIN`, `ECOURTS_DC_RATE_LIMIT_PER_MIN` -- Default 10
  - `ECOURTS_CACHE_DEFAULT_TTL_HOURS` -- Default 24
  - `ECOURTS_SELF_HEAL_ENABLED` -- true/false (default true)
  - `ECOURTS_SELF_HEAL_MODEL` -- OpenAI model for self-heal (default `gpt-4o-mini`)
  - `OPENAI_API_KEY` -- Required for self-heal (shared with TalkDoc)
  - `PLAYWRIGHT_BROWSERS_PATH` -- Optional custom browser path

- **Runtime note:** keep `easyocr` installed in the active backend env even when `ECOURTS_CAPTCHA_SERVICE=capsolver`. Capsolver `ImageToTextTask` returns the OCR solution directly from `createTask`; it should not be polled with `getTaskResult`. The scraper now logs task creation details and treats the direct `createTask` response as authoritative, while EasyOCR remains the immediate local fallback when Capsolver does not return a usable result. On the High Court site, case-status and cause-list share the same page, so case-status submits must use method-specific buttons instead of the generic `.Gobtn` selector or they can collide with the visible cause-list submit control.

- **Background refresh note:** the beat-driven `refresh_subscribed_causelists` task runs independently of user-triggered case-status searches. Legacy `subscribed_courts` entries that do not carry scraper ids (`high_court_id`, `bench_code`) are now skipped instead of queueing invalid cause-list scrapes that only expose hidden captcha controls and add noisy logs.

---

## Conventions for Changes

- **New endpoints:** Add in `ecourts_scraper/views.py` with `@api_view` and `@supabase_required`, then register in `ecourts_scraper/urls.py`. Document in **04-api-reference.md**.
- **New scraper methods:** Implement in the appropriate scraper class; add a Celery task that builds `AgentContext` and runs `ScrapeAgent(scraper, jm).execute(ctx)`; call task from view (lazy import of task in view to avoid pulling Playwright at Django startup).
- **New cache key shape:** Implement `build_cache_key` and `get_data_type` in the scraper; use `EcourtsCacheManager` in agent flow (state CACHE_RESULT).
- **Selectors:** Default selectors live in `constants.py` (HC_SELECTORS, DC_SELECTORS). The self-heal agent writes overrides to `ecourts_selectors` collection. Use `agent.self_heal.get_selector(site, page, element, default)` to read with fallback.

---

## Integration Points (Current / Planned)

- **TodaysUpdates:** Will merge scraped cause list data with WhatsApp updates (Phase 4).
- **Case tracking:** `refresh_tracked_cases` beat task already queries `user_details.case_ids` and re-scrapes stale CNRs (daily 2AM). Phase 4 will add notifications on `next_hearing_date` changes.
- **Court structure:** `court-structure/` endpoints reuse existing `state_district_court_data` (district courts) and `HIGH_COURT_CODES` in `constants.py` (high courts).
- **TalkDoc:** Scraped order PDFs (base64 in cache) can be fed to RAG (Phase 4).
- **AI Drafts:** Case context injection from scraped case data (Phase 4).

---

## Frontend Usage

- **Case by CNR:** GET `case/<cnr>/`. If 200, use `data`; if 202, poll `jobs/<job_id>/` until completed then use `result`.
- **Refresh:** POST `case/<cnr>/refresh/`, then poll `jobs/<job_id>/`.
- **Orders:** GET `case/<cnr>/orders/` for order list. GET `case/<cnr>/orders/<idx>/download/` for PDF (base64); if 202, poll job.
- **Search:** POST `search/` with body (include `page`, `page_size`). Advocate search works on both high courts and district courts. Party-name search currently works on High Court only and additionally requires `registration_year`; optional `case_status` accepts `pending`, `disposed`, or `both`. If 200, use `data.case_list` (paginated). If 202, poll `jobs/<job_id>/`; subsequent requests to same search will be paginated from cache.
- **Cause list:** GET `causelist/?date=2025-03-03&high_court_id=5&bench_code=1&causelist_type=daily`. If 200, use `data.entries`. If 202, poll job. Use `causelist/dates/` to show available cached dates. The live High Court flow is daily-only for now; non-daily types return `400`.
- **Court tree:** GET `court-structure/` for top-level; lazy-load districts/courts via nested endpoints. Use for court selector dropdowns.
- Use existing patterns: `AxiosInstance`, Bearer token, loading state while polling, Snackbar/Alert on error.

For full API contract and response shapes, see **04-api-reference.md**.

---

## Testing the API locally

- **Without HTTP:** From `Legalv1/` run:
  ```bash
  DEBUG=1 python manage.py shell -c "exec(open('ecourts_scraper/test_api_local.py').read()); run_checks()"
  ```
  This hits all eCourts views with a fake user (bypass auth) and checks status codes and response shape. Expect: court-structure and high-courts from constants/DB; case/causelist/search return 202 (job queued) or 200 (cached); orders 404 when case not cached; invalid CNR 400.

- **With Swagger:** Run the server with `DEBUG=True`, open `/api/schema/swagger-ui/`, use **DevBypassAuth** = `1` to skip Supabase, then try endpoints. See **04-api-reference.md** (Testing with Swagger).

---

## Plan and to-dos

Use this section to continue work without losing context. Tick off or update status as you complete items.

### Overall plan

- **Phase 1 (Core):** Scaffold app, cache, HC/DC case-by-CNR scrapers, job polling API. **Done.**
- **Phase 2 (Search + cause list + court tree):** Advocate/party search (cache-first + pagination), cause list scraper + API, court-structure tree API (using existing DB). **Done.**
- **Phase 3 (Scale + resilience):** Order PDF listing/download, Celery beat for subscribed courts + tracked cases, LLM self-healing for broken selectors. **Done.**
- **Phase 4 (Integration):** Merge cause lists into TodaysUpdates, auto-refresh tracked CNRs with notifications, feed order PDFs to TalkDoc, inject case context into AI Drafts, add sidebar nav.

### To-dos (status)

**Phase 1 -- Done**

| ID | Task | Status |
|----|------|--------|
| phase1-scaffold | Scaffold app: urls, views, tasks, constants, ScrapeAgent state machine, Playwright browser pool, CAPTCHA (EasyOCR + 2Captcha), proxy manager; register in settings.py + urls.py | Done |
| phase1-cache | MongoDB ecourts_cache (TTL), ecourts_scrape_jobs, ecourts_selectors; helpers in cache/collections.py, cache_manager.py; ensure_ecourts_indexes() | Done |
| phase1-hc-scraper | HighCourtScraper: case lookup by CNR (and advocate search flow) on hcservices.ecourts.gov.in; ScrapeAgent integration | Done |
| phase1-dc-scraper | DistrictCourtScraper: case by CNR (and advocate search flow) on services.ecourts.gov.in | Done |
| phase1-api | Views: GET case/\<cnr\>/, POST case/\<cnr\>/refresh/, GET jobs/\<job_id\>/, POST search/; @api_view + @supabase_required + JsonResponse | Done |

**Phase 2 -- Done**

| ID | Task | Status |
|----|------|--------|
| phase2-search | Search view checks cache first (same cache key as scraper), returns paginated results (`page`, `page_size`, `total`, `total_pages`). Falls through to scrape+queue if not cached. | Done |
| phase2-causelist | `CauseListScraper` in `scrapers/causelist.py`. Task `scrape_cause_list`. Views: `GET causelist/` (cache-first, else 202 + job), `GET causelist/dates/` (cached date list). Cache key: `hc:causelist:{court}:{bench}:{date}:{type}:{query}`. | Done |
| phase2-court-tree | `GET court-structure/` returns HC list (from `HIGH_COURT_CODES`) + DC states (from `state_district_court_data`). Lazy endpoints for districts/courts. No scraping -- reuses existing data. | Done |

**Phase 3 -- Done**

| ID | Task | Status |
|----|------|--------|
| phase3-orders | `GET case/<cnr>/orders/` reads orders from cached case data. `GET case/<cnr>/orders/<idx>/download/` downloads PDF via browser (clicks order link on re-scraped case page), caches as base64 (7-day TTL). Task `download_order_pdf_task`. | Done |
| phase3-celery-beat | `refresh_subscribed_causelists` (3x daily at 6:30/12:30/18:30) aggregates unique `subscribed_courts` from `user_details`, queues cause list scrapes. `refresh_tracked_cases` (daily 2AM) aggregates unique CNRs from `user_details.case_ids`, re-scrapes stale ones (>12h). `health_check_selectors` now navigates to HC/DC sites and validates all default selectors. | Done |
| phase3-self-heal | `agent/self_heal.py`: `attempt_self_heal()` captures page HTML + screenshot, calls OpenAI (model from `ECOURTS_SELF_HEAL_MODEL`), parses JSON selector response, upserts to `ecourts_selectors`. `get_selector()` reads from DB with fallback. State machine `_self_heal` retries up to `SELF_HEAL_MAX_RETRIES` then fails. | Done |

**Phase 4 -- Pending**

| ID | Task | Status |
|----|------|--------|
| phase4-integration | TodaysUpdates: merge scraped cause list entries with whatsapp_chat_sessions.updates in fetch_updates_for_subscribed_courts (tag source: ecourts vs whatsapp). Case tracking: add notifications when `next_hearing_date` changes after auto-refresh. TalkDoc: allow "add order PDF" from case detail to RAG session. AI Drafts: when drafting for a case_id that is a CNR, load case from ecourts_cache and inject into prompt. Add "eCourts" / "Case lookup" to sidebar (Navbar.jsx). | Pending |

### How to continue

1. **Pick the next todo** from the table above (phase4-integration).
2. **Follow existing patterns:** New scraper method -> implement in appropriate scraper class; new view -> `views.py` + `urls.py`; new task -> `tasks.py` with lazy imports; cache key in scraper's `build_cache_key` / `get_data_type`.
3. **Selectors:** Use `from ecourts_scraper.agent.self_heal import get_selector` to read selectors with DB override support.
4. **Update this doc** when you complete an item: change status to Done and add a one-line note if useful.
5. **API shapes** should stay consistent with **04-api-reference.md** and the frontend tree/table patterns in **03-frontend-webpack.md**.

---

## eCourts Direct API (`ecourts_api`) — Deprecated Historical Reference

`ecourts_api` remains in the repository only as historical fallback/reference code. It is no longer installed in Django, no longer scheduled in Celery Beat, and no longer owns `/api/ecourts/`.

### Where It Lives

| Item | Path |
|------|------|
| Django app | `Legalv1/ecourts_api/` |
| URL prefix | `api/ecourts/` (same as scraper) |
| URL registration | `Legalv1/Legalv1/urls.py` — `include('ecourts_api.urls')` |
| API client | `ecourts_api/client.py` |
| Response transformers | `ecourts_api/transformers.py` |
| Celery tasks | `ecourts_api/tasks.py` |
| Views | `ecourts_api/views.py` |
| Frontend pages | `frontend_webpack/src/components/ecourts/` |

### Swap Back to Scraper

In `Legalv1/Legalv1/urls.py`, uncomment the scraper line and comment out ecourts_api:

```python
path('api/ecourts/', include('ecourts_scraper.urls')),  # restore
# path('api/ecourts/', include('ecourts_api.urls')),     # disable
```

### Key Differences from Scraper

- **Synchronous**: All data returned immediately (HTTP 200). No 202/job polling.
- **External API**: Uses `webapi.ecourtsindia.com` with Bearer token (`ECOURT_TOKEN` in `legalenv`).
- **Court structure**: Uses external API hierarchy (State → District → Complex → Court) instead of `state_district_court_data` collection. Court structure endpoints are FREE.
- **Caching**: Same `ecourts_cache` collection via `EcourtsCacheManager`. Keys prefixed with `api:` (e.g. `api:case:<cnr>`, `api:search:<hash>`). Pre-populated defaults stored under `defaults:cases`, `defaults:litigants`, `defaults:lawyers`.
- **Default landing cache retention**: The direct-API Beat tasks now set explicit TTLs when writing `defaults:*` keys instead of relying on the generic cache-type fallback. Daily case/litigant defaults use a 36-hour TTL, weekly lawyer defaults use an 8-day TTL, and empty refresh runs do not overwrite the previous non-empty cache entry. This prevents the MamlaAI landing pages from going blank when Beat runs late or the partner API temporarily returns no results.
- **Order download**: `client.get_order_stream(cnr, filename)` returns raw `(bytes, content_type)` — does NOT call `resp.json()` (PDF is binary, not JSON). Frontend fetches as Axios blob with `responseType: 'blob'` so the `Authorization` header is sent (plain `window.open()` would 401).
- **MamlaAI case detail flow**: The active Tailwind frontend screen at `mamlaAI_ground_zero/frontend/src/components/ecourts/CaseDetail.jsx` should use the shared helper layer in `common/ecourtsApi.js` instead of calling Axios directly. It reads the normalized payload from `GET case/<cnr>/`, hydrates orders from `GET case/<cnr>/orders/`, refreshes via `POST case/<cnr>/refresh/`, and downloads PDFs through the authenticated blob path so direct API errors stay in-page and users are not bounced onto non-existent legacy routes.

### API Endpoints

| Method | Path | Auth | Cost | Description |
|--------|------|------|------|-------------|
| GET | `case/<cnr>/` | Supabase | Paid | Case detail — cached or live |
| POST | `case/<cnr>/refresh/` | Supabase | Paid | Queue fresh scrape upstream |
| GET | `case/<cnr>/orders/` | Supabase | — | Orders from cached case |
| GET | `case/<cnr>/orders/<idx>/download/` | Supabase | Paid | Streams PDF binary. **Must be called via Axios (not window.open) so `Authorization` header is sent.** Frontend fetches as blob, triggers `<a download>` click. |
| POST | `search/` | Supabase | Paid | Case search (advocate/litigant/judge/general) |
| GET | `defaults/<section>/` | Supabase | FREE | Pre-populated landing-page results. `section` = `cases`\|`lawyers`\|`litigants`. Populated by Beat tasks daily/weekly. Returns `{ status, refreshed_at, data }` or `{ status: "empty" }` on first boot. |
| GET | `causelist/` | Supabase | Paid | Cause list search |
| GET | `causelist/dates/` | Supabase | FREE | Available dates for location |
| GET | `court-structure/` | Supabase | FREE | Top-level (states + high courts) |
| GET | `court-structure/states/` | Supabase | FREE | All states |
| GET | `court-structure/states/<s>/districts/` | Supabase | FREE | Districts in a state |
| GET | `court-structure/states/<s>/districts/<d>/complexes/` | Supabase | FREE | Court complexes |
| GET | `court-structure/states/<s>/districts/<d>/complexes/<c>/courts/` | Supabase | FREE | Courts in a complex |
| GET | `court-structure/high-courts/` | Supabase | — | High courts from constants |
| GET | `jobs/<job_id>/` | Supabase | — | Stub (returns 404 — no async jobs) |

### Frontend Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/ecourts` | `EcourtsHome` | Landing page with quick CNR lookup, free court-structure stats, last-search recovery from sessionStorage, and backend default preview cards for cases/lawyers/litigants. |
| `/ecourts/case-search` | `CaseSearch` | Case search results with faceted filters. On blank mount: restore sessionStorage cache → else fetch `defaults/cases/` → else empty. |
| `/ecourts/case/:cnr` | `CaseDetail` | Full case view — parties, history, orders, IAs. Back button (`navigate(-1)`). Order download via Axios blob. |
| `/ecourts/lawyers` | `LawyerSearch` | Advocate search. Same blank-mount defaults flow (`defaults/lawyers/`). |
| `/ecourts/litigants` | `LitigantSearch` | Litigant/party search. Same blank-mount defaults flow (`defaults/litigants/`). |
| `/ecourts/cause-list` | `CauseListTerminal` | High-court daily cause-list terminal in the active MamlaAI frontend. Uses `high_court_id`, `bench_code`, and `date`, plus cached-date hints from `causelist/dates/`. Non-daily stitched modes remain visible as staged UI only. |

**Blank-mount fallback priority (CaseSearch / LawyerSearch / LitigantSearch):**
1. URL has `?q=` param → call search API directly
2. sessionStorage cache hit (30-min TTL, per section) → show instantly, no API call
3. `GET /api/ecourts/defaults/<section>/` → show with info chip banner, pagination suppressed
4. Nothing → empty page (graceful)

When user types and searches: `isDefault` clears, live search API called, result cached to sessionStorage, full pagination shown.
