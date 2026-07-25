# 19 — FastAPI + Next.js End-to-End Migration & Redesign Plan

> Status: APPROVED DIRECTION (2026-07-19). Big-bang rewrite, web-only, "Modern SaaS crisp" UI, drop-dead/park-dormant code policy.

## Context

Mamla.AI is an AI-native legal workspace for Indian lawyers: case/client management, AI drafting, TalkDoc RAG document chat, Mamla Brain reasoning (SSE streaming), eCourts scraping (district/HC/SCI/CAT), legal calendar with Google sync, entitlements/wallet billing, and OpenSearch-backed search.

**Why this change**: The Django backend is fully synchronous (blocking LLM calls, 120s scraper proxies, per-request Supabase network auth) and carries real security bugs; the React SPA has god-components up to 2,337 lines and a UI users describe as boring. The goal is an async FastAPI backend + Next.js 15 frontend with a crisp modern design system — zero feature loss, production-ready, secure, and maintainable.

**Current state (verified by code audit)**:
- Backend: Django, ~33.8k LOC, ~200 endpoints across 16 active apps. MongoDB-only via PyMongo (NO Django ORM — no models/migrations, which makes the port dramatically easier). Celery on Redis (4 queues + beat), OpenSearch, Redis cache. A separate FastAPI scraper service already runs on :8002 (`scrapping_codes_ecourt/` — stays as-is).
- Frontend: React 18 + Webpack SPA, ~31.4k LOC, Tailwind 3.4, Redux Toolkit (only ~226 LOC of slices), react-snap prerender for 6 marketing pages.
- Deployment: bare-metal single host, nginx, no Docker, no CI. Env via untracked `legalenv` files.
- Security bugs confirmed first-hand:
  - `ai_draft/middleware.py` auth bypass NOT DEBUG-gated — `/api/aidrafts/test/*`, `/test-ai-drafting/*`, `/draft-preview/*` are unauthenticated + CSRF-exempt in production.
  - `CELERY_ACCEPT_CONTENT` includes pickle (RCE risk on broker).
  - `supabase_required.py` does a live Supabase network call per request (~230 call sites) — latency + hard dependency.
  - No rate limiting anywhere.
  - Frontend `services/api.js` logs login request/response bodies via leftover `[native-debug]` console.logs.
- Dead code: ~3.7k LOC unused React components; deprecated `ecourts_scraper`/`ecourts_api` apps; 5 Celery beat entries pointing at an uninstalled app (NotRegistered errors); `@supabase/supabase-js` dep never imported.
- Dependency conflict: `environment.yml` (runtime truth: openai 0.28.0) vs `requirements.txt` (openai ≥1.30, Django 4.2 vs 5.1.1).
- Frontend hotspots: DraftingWorkspace 2337L/66 useState, CalendarPage 1867L, DocumentWorkspace 1691L (leaky 8s polling), CaseHub 1032L, CaseRegistry 863L; SSE stream with no AbortController; 13 components disable exhaustive-deps; check-auth network probe on every route change.

## Locked Decisions

1. **Big-bang rewrite** — build the complete FastAPI backend in parallel while Django serves prod; full parity regression; single cutover day (nginx flips `/api/*`); rollback = flip back.
2. **Web-only** — Android/Capacitor app is not deployed; ignore it. Full SSR/SSG freedom; drop all Capacitor packages and native token paths.
3. **UI: "Modern SaaS crisp"** — Linear/Vercel-inspired: near-black/paper-white, electric indigo accent, Inter, hairline borders, dark+light themes, Framer Motion micro-interactions, skeleton loaders, ⌘K command palette.
4. **Dormant code** — DROP dead code; PARK (port, clearly marked) WhatsApp webhook + billing/Razorpay skeleton; port all 16 live domains.

---

## 1. Target Backend — `mamla_api/` (new dir beside `Legalv1/`)

### Stack
- FastAPI + uvicorn/uvloop, **Python 3.12**, single `pyproject.toml` + `uv` lock (kills the environment.yml/requirements.txt conflict; openai 1.x).
- **PyMongo Async API** (`AsyncMongoClient`) — Motor is EOL May 2026; one dependency covers async API + sync Celery tasks.
- `httpx.AsyncClient` (lifespan-managed) for scraper proxy + external calls; `redis.asyncio`; **keep Celery 5** (json-only, same 4 queue names + beat) — tasks are ported, not rewritten; revisit arq/taskiq post-cutover.
- SSE via `sse-starlette` (client-disconnect cancellation). Settings via `pydantic-settings` reading existing `legalenv` var names.

### Layout
```
mamla_api/app/
  main.py                 # create_app, lifespan (clients + index bootstrap)
  settings.py
  core/                   # shared kernel — ported from Django, not rewritten:
    auth.py               #   CurrentUser dep (cookie→Bearer, local JWKS verify)
    entitlements.py       #   port of Legalv1/core/entitlements.py (659L) + require_feature() dep
    brain_api_key.py      #   port of mamla_brain/auth.py (228L)
    llm/                  #   UNIFIED: merges core/llm_client.py + mamla_brain/llm_router.py
                          #   (t0–t3 tiers, retry/fallback) + circuit_breaker.py port
    mongo.py redis.py opensearch.py ratelimit.py problems.py logging.py audit.py email/
  domains/<domain>/{router,service,repository,schemas,tasks}.py   # OpenAPI tag per domain
  parked/{whatsapp,billing}/   # whatsapp router mounted (HMAC webhook); billing unmounted
tests/  tools/parity/  worker.py
```

### Domain map (16 apps → 13 domains + 2 parked)

| New domain | From | Notes |
|---|---|---|
| platform | core views | health, dashboard, admin wallet (+audit log, admin-role check) |
| identity | users/ (1187L) | cookies `access_token`/`refresh_token` preserved EXACTLY (zero-relogin cutover) |
| drafting | ai_draft/ + create_drafts/ | keep `/api/aidraft` alias until cleanup; test/preview endpoints NOT ported |
| cases | cases/ | straight CRUD port |
| agents | agents/ | 6 lifecycle agents |
| calendar | calendar_management/ + calendersetup/ | Google OAuth callback paths preserved exactly |
| talkdoc | talkdoc/ | RAG chat + Celery ingest |
| brain | mamla_brain/ | SSE contract from orchestrator/views_v2.py:437 preserved |
| ecourts | ecourt_scrapped/ | httpx proxy (connect 5s/read 120s) + Mongo cache → scraper :8002 (unchanged, localhost-bound) |
| search / notifications / court_updates / analytics | search_facility / utilities / todaysupdates / analytics | direct ports |

Dropped: `ecourts_scraper`/`ecourts_api` remnants, one-off root scripts, `ai_draft/middleware.py` entirely.

### Auth (the big performance + security win)
Replace per-request `sb.auth.get_user()` network call with **local JWT verification**: PyJWT + Supabase JWKS (cached in-process + Redis 10 min, keyed by `kid`; HS256 fallback via `SUPABASE_JWT_SECRET` if project uses legacy secret — detect at startup). Validate exp/aud/iss. Logout → token `session_id` in Redis denylist (TTL = remaining life). Staging flag `AUTH_DOUBLE_CHECK=true` runs both paths and logs divergence; off before cutover. Claims map into `UserContext` matching today's `request.supabase_user` shape so ported logic reads identically.

### Entitlements
Port engine verbatim (plans, 8 feature codes, wallet overage, monthly reset); wrap as `require_feature(code)` dependency → authorize in dep, `consume_feature_use` in service on success only. **Day-one enforcement parity** (currently-ungated domains stay ungated for clean parity diffs); per-feature `ENFORCEMENT_FLAGS` allows gating post-cutover without code changes. DEBUG-quota-bypass replaced by explicit `ENTITLEMENTS_ENFORCED` (prod refuses false).

### Middleware / errors / responses
RequestID → structured logging (structlog) → CORS allowlist → Origin/Sec-Fetch-Site CSRF guard on non-GET → **custom Redis sliding-window rate limiter** (slowapi's sync storage fights async) → GZip. Errors: **RFC7807 problem+json** `{type,title,status,detail,instance,request_id}` + transitional `"error"` alias key (dropped post-cutover). Success responses: raw resource JSON, no envelope — matches Django output for clean parity diffs. Swagger admin-gated in prod.

### Fix-during-port register

| # | Bug today | Fix in new stack |
|---|---|---|
| F1 | test-endpoint auth bypass live in prod | not ported; `ENABLE_TEST_ROUTES` refused when ENV=prod |
| F2 | Celery accepts pickle | json-only; Django flipped json-only at T-7d to drain |
| F3 | no rate limiting | Redis sliding-window limiter with per-plan tiers |
| F4 | SecurityMiddleware duplicated | moot — new explicit stack |
| F5 | 5 dead `ecourts_scraper` beat entries | not ported |
| F6 | login-body console.logs in frontend | moot + ESLint `no-console: error` in CI |
| F7 | per-request Supabase network auth | local JWKS verification |
| F8 | duplicated LLM client factories | single `app/core/llm/` |
| F9 | ~55 raw `json.loads(request.body)` sites | pydantic schemas, 422 field errors |
| F10 | `{"error"}` vs `{"detail"}` inconsistency | RFC7807 envelope |
| F11 | DEBUG=True bypasses all quota | explicit `ENTITLEMENTS_ENFORCED` |
| F12 | SSE ignores client disconnect | sse-starlette cancellation aborts LLM call |
| F13 | `requests` + blanket 120s proxy timeouts | httpx tuned timeouts + circuit breaker |
| F14 | environment.yml vs requirements.txt conflict | pyproject + uv lock |
| F15 | check-auth network probe per route change | Next middleware JWT check + cached `me` query |

---

## 2. Target Frontend — `mamla_web/` (Next.js 15, App Router, TypeScript strict)

### Stack
- **TanStack Query v5** for server state (app is ~90% server state; replaces hand-rolled polling); **Zustand replaces Redux** (existing 4 slices ≈ 226 LOC; auth/entitlements become queries; only UI overlay + chat-panel state remain).
- **shadcn/ui + Tailwind v4 (`@theme` CSS-first tokens) + Framer Motion + next-themes**; `cmdk` command palette; react-hook-form + zod; **keep FullCalendar 6** (recurring series + drag/resize would cost 2–3 weeks to rebuild; restyles cleanly via CSS vars).
- Typed client: `lib/api/client.ts` (fetch, `credentials:'include'`, problem+json parsing, 401→login) + `lib/api/sse.ts` (**AbortController — fixes the stream leak**, backoff reconnect) + `types.gen.ts` from FastAPI OpenAPI via openapi-typescript (drift-checked in CI).
- Dropped: Capacitor (7 pkgs), `@supabase/supabase-js`, react-snap, react-helmet-async, Redux, axios.

### Layout
```
middleware.ts            # (app) group: cookie presence + jose JWT sig check (JWKS cached) → /login
app/(marketing)/         # SSG/ISR, generateMetadata replaces Seo.jsx + react-snap (11 pages)
app/(auth)/              # login, signup, forgot-password
app/(app)/               # server layout reads cookie, prefetches me+entitlements;
                         # pages CSR-heavy under it; per-route loading.tsx skeletons
features/<feature>/{components,hooks,api}/
components/ui/           # shadcn primitives + Skeleton, EmptyState, StatCard
styles/tokens.css
```

### God-component decomposition (~300-line file cap)
- **DraftingWorkspace 2337L/66 useState** → DraftingShell + TemplatePicker + IntakeForm (RHF+zod) + EditorPane + GenerationPanel + VersionHistory; `useDraftGeneration` (mutation + `refetchInterval` poll), `useDraftAutosave`.
- **CalendarPage 1867L** → CalendarView (FullCalendar) + EventSheet + RecurrenceEditor + HearingSyncBanner; `useCalendarEvents(range)`.
- **DocumentWorkspace 1691L** → DocViewer + ChatPane (SSE lib) + IngestStatus (`refetchInterval` w/ backoff — replaces raw 8s setInterval).
- **CaseHub 1032L / CaseRegistry 863L** → CaseTable (TanStack Table) + CaseFilters (URL params) + CaseDetailTabs (lazy).
- Dead components (~3.7k LOC: DistrictTools, GuidedDraftingPage, CauseListBrowser, ClientOnboarding, CourtUpdates, EcourtsHome, CommandCenter, CaseSearch, ClientProfile, securityUtils) are NOT ported.

### Design tokens — "Modern SaaS crisp" (dark default, light via next-themes)
- **Color** (dark/light): bg `#0A0A0B`/`#FAFAF9` · surface `#111113`/`#FFFFFF` · border rgba(255,255,255,.08)/rgba(0,0,0,.08) hairlines · accent electric indigo `#6E6EF7`/`#5B5BD6` · fg `#EDEDEF`/`#18181B` + muted/subtle steps · semantic success `#30A46C`, warning `#F5A623`, danger `#E5484D` with 12%-alpha tints.
- **Type**: Inter Variable; 12–40px scale, body 14/1.5, headings tracking-tight semibold, tabular-nums for case numbers/dates.
- **Shape**: 4px grid; radii 6/8/12/full; shadows only light-mode + overlays; dark mode = borders not shadows.
- **Motion**: 120ms hover/press, 160ms fades, 200ms overlays (scale .98→1 + fade); easing `cubic-bezier(0.32,0.72,0,1)`; `prefers-reduced-motion` respected; skeleton shimmer 1.6s matching final layout.

### Frontend cutover posture
Ship **(marketing) group early** (zero API dependency, pure SEO upside, validates deploy path). The **(app) group cuts over the same day as the backend** (built against problem+json + generated types). Rollback = nginx flips `/` and `/api` together.

---

## 3. Security Hardening Register

| # | Item | Action |
|---|---|---|
| S1 | test-route bypass | killed; prod refuses `ENABLE_TEST_ROUTES` |
| S2 | Celery pickle | json-only both sides pre-cutover |
| S3 | rate limiting | auth 5/min/IP + 20/hr/IP; LLM endpoints per-plan (free 10/hr, pro 60/hr…); general 120/min/user; ecourts 30/min/user; 429 + Retry-After |
| S4 | headers | nginx HSTS/nosniff/Referrer-Policy/Permissions-Policy; Next CSP (nonce scripts, frame-ancestors none, connect-src self+supabase+posthog) |
| S5 | cookies | names + HttpOnly+Secure+SameSite=Lax preserved (users/supabase_views.py:235-256) — zero re-login at cutover |
| S6 | CSRF | Origin/Sec-Fetch-Site validation on non-GET; drop Django csrftoken machinery |
| S7 | auth verify | local JWKS + logout denylist; API keys hashed + `secrets.compare_digest` |
| S8 | credential logging | ESLint no-console:error; PostHog input masking |
| S9 | env safety | startup assertion: ENV=prod ⇒ enforcement on, docs off, test routes off |
| S10 | secrets | `/etc/mamla/env` mode 600, fail-fast validation, pip-audit/npm-audit in CI |
| S11 | audit log | mandatory on admin wallet top-up, plan changes, login, API-key use |
| S12 | whatsapp webhook | HMAC constant-time + replay window |
| S13 | scraper | stays localhost-only, single worker (session-store flaw documented follow-up) |
| S14 | input hardening | pydantic constraints + upload size/MIME allowlists |

---

## 4. Cutover Mechanics

- **Parity harness** (`mamla_api/tools/parity/`): capture middleware on Django (staging + short prod window) → sanitized samples in Mongo `parity_captures`; golden set = ~200 routes × happy path + ≥1 4xx; `replay.py` fires at :9000 with per-plan test tokens, diffs status+body with per-route ignore lists (timestamps/ObjectIds). Final week: nginx `mirror` top-20 **idempotent GET** endpoints to :9000, diff logged output.
- **Staging on same host**: FastAPI :9000, Next :3002, same Mongo/OpenSearch (mutations only against seeded test users), Redis cache DB 1; Celery broker DB matches prod at cutover.
- **Data layer — no migration**, verify: (a) index bootstrap parity vs `core/init_clients.py` (idempotent); (b) datetime/ObjectId serialization matches Django in parity diffs; (c) grep-confirm nothing depends on Django `sessionid`; (d) **identical Celery task names** so either worker generation consumes either producer during swap.
- **Runbook**: T-7d Django Celery→json-only, freeze Legalv1, mirroring on. T-1d parity green 3 days, beat side-by-side review, mongodump+Redis snapshot. T-0 (low traffic): stop Django beat → drain queues → swap workers → nginx flip `/api` :8000→:9000 and `/` old-SPA→Next → smoke (Playwright critical flows + SSE manual). Rollback within 72h = flip back, restart Django workers/beat; shared DB = no reconciliation. Keep Django warm 2 weeks.

---

## 5. Testing & CI

- **Backend**: pytest + httpx ASGITransport; fixture layer = fake LLM router, minted test JWTs vs test JWKS, real Mongo+Redis as GitHub Actions services (app too Mongo-shaped for mocks). Port intent of existing tests (`Legalv1/tests/` + ai_draft 556L, users 175L, analytics 180L). New: entitlements matrix, rate-limit, RFC7807 shape, JWKS rotation tests.
- **Frontend**: Playwright smoke (login, dashboard, case CRUD, calendar CRUD, draft generate w/ mock-LLM flag, talkdoc upload+chat, brain SSE start/abort, quota-limit UX); Vitest for hooks/utils.
- **GitHub Actions**: `api.yml` (ruff, mypy, pytest, pip-audit) · `web.yml` (eslint, tsc, OpenAPI drift check, build, Playwright) · `parity.yml` (manual dispatch replay). Branch protection on all.

---

## 6. Milestones (2 devs, parallel tracks; ew = engineer-weeks)

| | Scope | Size |
|---|---|---|
| M0 | API foundation: skeleton, settings, clients, auth, entitlements, middleware, unified LLM, Celery, CI | 2 ew |
| M1 | identity + platform + parity harness | 2 ew |
| M2 | CRUD belt: cases, calendar+google, court_updates, search, notifications, analytics | 4 ew |
| M3 | ecourts proxy + drafting (incl. Celery generation/polling) | 4 ew |
| M4 | talkdoc + agents | 3 ew |
| M5 | brain (SSE, tiers, API-key quota) | 2 ew |
| M6 | parked modules + beat schedule | 1 ew |
| F0–F6 | Frontend parallel: tokens+shell+codegen 2 · marketing (ships early) 1 · auth+dashboard 1.5 · cases+calendar 2.5 · drafting 3 · talkdoc+brain 2 · palette/skeletons/polish 1.5 | 13.5 ew |
| P | parity green + shadow week + security sweep + load sanity | 2 ew |
| C | cutover + stabilization | 1 ew |
| X | cleanup: delete Legalv1/old SPA from serving, drop aliases, archive | 1 ew |

**≈ 18–20 calendar weeks to cutover** with 2 devs, assuming port-not-redesign discipline for the entitlements engine, LLM router, email templates, and scraper clients, and golden-set parity as per-domain definition of done.

## Verification

1. Per-domain: parity replay green (status+body diff vs Django golden set) before a domain counts as done.
2. Pre-cutover: 3 consecutive green parity days + 1 shadow-mirror week on top-20 GETs; security register S1–S14 checked off; load sanity on :9000.
3. Cutover day: Playwright critical-flow suite against prod + manual SSE/dashboard/health checks; users' existing cookies must work without re-login.
4. Post-cutover 72h: error-rate + latency dashboards vs Django baseline; rollback runbook armed.

## Key files

- Port sources: `Legalv1/core/entitlements.py`, `Legalv1/supabase_required.py` (token semantics), `Legalv1/Legalv1/settings.py` (queues/beat/env names), `Legalv1/mamla_brain/orchestrator/views_v2.py` (SSE contract), `Legalv1/core/llm_client.py` + `Legalv1/mamla_brain/llm_router.py` (merge), `Legalv1/core/circuit_breaker.py`, `Legalv1/mamla_brain/auth.py`, `Legalv1/core/init_clients.py` (indexes), `Legalv1/core/email_templates.py`.
- Contract references: `new_frontend/src/services/api.js` (implicit API contracts), `new_frontend/src/AppContent.js` (route inventory).
- New roots: `mamla_api/`, `mamla_web/` beside existing dirs; `scrapping_codes_ecourt/` untouched.
