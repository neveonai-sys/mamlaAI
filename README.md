# Mamla.AI — Legal Tech Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2%2B-green)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://reactjs.org/)
[![MongoDB](https://img.shields.io/badge/Database-MongoDB-47A248)](https://www.mongodb.com/)
[![Auth](https://img.shields.io/badge/Auth-Supabase-3ECF8E)](https://supabase.com/)

> AI-native legal workspace for lawyers — from case intake to court-ready drafts.

---

## What Mamla.AI Does

Mamla.AI gives lawyers a full AI-assisted workspace to manage cases, clients, documents, and court research in one place. It is built specifically for the Indian legal system.

### Case & Client Management
- **Case Registry** — create and track cases with auto-generated `MC-YYYY-XXXXXX` reference IDs
- **7-tab Case Hub** — hearings, notes, tasks, drafts, documents, calendar, and eCourts — all scoped to one case
- **Client Onboarding** — invite clients via token-based signup link; link existing users to cases
- **Client Profile** — contact card with full linked-case history

### AI-Powered Legal Drafting
- **DraftingWorkspace** — multi-section AI draft editor with section reorder, history, revert, and PDF export
- **Guided Drafting** — conversational intake agent (up to 10 turns) extracts facts from the lawyer, generates a structured draft plan, then produces the full draft
- **Template-based Drafts** — load from pre-built templates or upload your own reference document
- **Draft Context Agent** — pre-loads case facts and linked documents before generating

### TalkDoc — Document Intelligence
- Upload PDFs, DOCX, CSV, XLSX, or images; chat with them using RAG retrieval
- Session-scoped document context — each chat locks its own document set
- Scanned PDF / image OCR via multimodal LLM fallback
- Table extraction from PDF/DOCX, CSV/XLSX formatting into indexable text
- Two usage buckets: `brain_doc_analysis` (with documents) and `general_legal_chat` (no documents)
- Session-bundle charging — one quota unit covers up to 10 turns per session

### Mamla Brain Framework
- Domain-reasoning API usable as `legal`, `banking`, or `markets` mode
- Dual auth: first-party Supabase token or third-party `X-Brain-API-Key`
- Tiered LLM routing (T1 micro / T2 balanced / T3 strong) per request complexity
- Knowledge-base retrieval per domain (OpenSearch-backed, ingestible from source files)
- Case Companion — structured legal reasoning with citations

### eCourts Intelligence
- **Scraper-first runtime** at `/api/ecourts/` — CNR lookup, case status (party/advocate/filing/FIR), cause list, court orders, caveat (staged)
- **LangGraph orchestration** (opt-in via `ECOURTS_USE_LANGGRAPH=true`) — 8 shared skill nodes, 3 learning-registry modules (navigation selector tracking, CAPTCHA strategy ranking, workflow metrics)
- **eCourts v2 proxy** at `/api/ecourts/v2/` — FastAPI scraper bridge for full dropdown hierarchy (state → district → complex → establishment), court orders by party / case number / court number / order date with PDF download
- **High Court support** — 5 HC terminal screens (case status, court orders, cause list, case detail, HC/bench selector) with `DLHC`/`UPHC`/`WBCHCJ`-aware CNR auto-routing
- CAPTCHA solving via Capsolver + local EasyOCR fallback

### Legal Calendar
- FullCalendar-powered legal calendar with month/week/day/agenda views
- Linked multi-day series with `only once` / `this and following` / `entire series` edit/delete semantics
- Conflict intelligence — time-overlap detection with advisory resolution
- Case/client-aware event intake; separate email delivery to creator and each participant

### Other
- **Court Update Subscriptions** — subscribe to specific courts; receive daily cause-list alerts
- **Search** — OpenSearch-backed document search with index management
- **WhatsApp Webhook** — integrated (low priority; left stable)

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Django 4.2, MongoDB (PyMongo), Supabase Auth, Redis, Celery, OpenSearch |
| **Email** | Resend SDK — `mamla@noreply.mamla.ai` |
| **LLM** | OpenAI + OpenRouter (provider-switchable via `LLM_DEFAULT_PROVIDER`) |
| **Frontend** | React 18, Redux Toolkit, Tailwind CSS, Webpack 5, FullCalendar |
| **eCourts** | LangGraph, curl_cffi (TLS impersonation), Capsolver, EasyOCR |
| **Infra** | Gunicorn (prod) + Nginx, Redis, MongoDB Atlas (or local) |

---

## Repository Layout

```
Adalatai_ground_zero/
├── Legalv1/                        # Django backend
│   ├── Legalv1/                    #   Project settings + root URLs
│   ├── core/                       #   Shared clients (Mongo, Supabase), health, init command
│   ├── users/                      #   Auth, profiles, onboarding
│   ├── ai_draft/                   #   AI drafting sessions + guided intake
│   ├── create_drafts/              #   Template-based drafts
│   ├── cases/                      #   Case registry, hearings, notes, tasks
│   ├── agents/                     #   6 focused agents (intake → closure + conversational draft)
│   ├── calendar_management/        #   Events CRUD + recurring series
│   ├── talkdoc/                    #   RAG document Q&A
│   ├── mamla_brain/                #   Domain reasoning framework
│   ├── ecourts_scraper/            #   Scraper-first eCourts runtime (active)
│   ├── ecourt_scrapped/            #   eCourts v2 FastAPI proxy layer (active)
│   ├── ecourts_api/                #   Partner-token eCourts client (deprecated — reference only)
│   ├── search_facility/            #   OpenSearch document search
│   ├── utilities/                  #   Email, state/district/court lookups
│   ├── todaysupdates/              #   Court subscriptions + daily updates
│   ├── whatsapp_module/            #   WhatsApp webhook
│   ├── scripts/                    #   One-off DB index/backfill scripts
│   ├── legalenv                    #   Prod env file (git-ignored)
│   └── legalenv.dev                #   Dev env file (git-ignored)
│
├── mamlaAI_ground_zero/
│   └── frontend/                   # Active React SPA (Tailwind + Webpack)
│       ├── src/
│       │   ├── AppContent.js       #   All route definitions (start here)
│       │   ├── store.js            #   Redux store
│       │   ├── features/           #   userSlice, entitlementsSlice, chatDocsSlice, uiSlice
│       │   ├── components/         #   All pages and UI components
│       │   └── services/           #   apiClient + casesApi
│       ├── webpack.dev.js          #   Dev server — proxies /api → backend :8100
│       └── webpack.prod.js         #   Production build + env injection
│
├── frontend_webpack/               # Previous React SPA (reference only)
├── docs/                           # Architecture, API reference, changelog ← read first
├── advocate_list/                  # Lawyer directory CSV exports
├── draftdocs/                      # Legal draft templates
└── logs/                           # Runtime logs (git-ignored)
```

---

## Documentation

Everything needed to understand, extend, or deploy the codebase lives in [`docs/`](docs/):

| Doc | Contents |
|-----|----------|
| [`docs/00-agent-quickref.md`](docs/00-agent-quickref.md) | One-page map of every key file, collection, API prefix, route, and env var |
| [`docs/01-architecture-overview.md`](docs/01-architecture-overview.md) | Repo layout, component relationships, auth + data flow |
| [`docs/02-backend-legalv1.md`](docs/02-backend-legalv1.md) | Django apps, MongoDB, auth, Celery, env vars, LLM config |
| [`docs/03-frontend-webpack.md`](docs/03-frontend-webpack.md) | React routes, Redux slices, API client, build config |
| [`docs/04-api-reference.md`](docs/04-api-reference.md) | Full endpoint reference (method, path, auth, description) |
| [`docs/05-changelog-and-improvements.md`](docs/05-changelog-and-improvements.md) | What was changed, why, and what comes next |
| [`docs/06-ecourts-scraper.md`](docs/06-ecourts-scraper.md) | eCourts scraper architecture, terminal flows, selectors |
| [`docs/00-running-locally.md`](docs/00-running-locally.md) | Local dev setup and production start commands |

---

## License

MIT — see [LICENSE](LICENSE).

<div align="center">Made with ❤️ by the Mamla.AI team</div>