# 07 — Mamla Brain Framework: Architecture & TODO

> **Self-contained planning doc. Read this before touching any Brain-related code.**
> Status: IN PROGRESS — core framework app implemented, starter legal KB documents added, full primary-law corpus and frontend integration still pending.
> Last updated: 2026-03-14

---

## TL;DR

Mamla Brain is a standalone, API-first reasoning framework built on top of the existing
TalkDoc RAG infrastructure. The first domain is legal, but the framework can also run against
other domain profiles such as banking or market analysis when different knowledge sources are
plugged in. It adds: (1) a tiered LLM routing layer via OpenRouter or OpenAI-compatible APIs,
(2) a domain knowledge-base layer, (3) a Case Companion-style structured reasoning mode,
(4) external API key authentication so third-party apps can call it without Supabase, and
(5) token-efficient prompting to control costs.

The existing `talkdoc/` app stays as-is for internal users. `mamla_brain/` is the new external-
facing, enhanced layer that wraps and extends it.

## Implementation Snapshot

Implemented now in `Legalv1/mamla_brain/`:

- Django app scaffold, URL registration, and settings wiring
- Dual auth via Supabase or `X-Brain-API-Key`
- Tiered LLM router for `t1`, `t2`, and `t3`
- Reusable domain profiles in `prompts.py` for `legal`, `banking`, and `markets`
- Brain session/message persistence in `brain_sessions` and `brain_messages`
- Brain document upload/listing that reuses `rag_documents` and TalkDoc ingestion
- Document Q&A endpoint with query rewrite plus merged doc/KB context assembly
- Case Companion start and advise endpoints with structured JSON output
- Knowledge-base retrieval helpers and ingestion commands
- Starter legal knowledge-base seed files in `legal_kb_sources/`

Still pending:

- Population of a production-grade legal corpus and non-legal domain source files
- Frontend integration
- richer cost telemetry / analytics beyond stored `tokens_used`
- production admin policy around Brain API-key issuance

---

## Research Foundation (Why This Exists)

Two papers in `reserachpaper/` validated this direction:

| Paper | arXiv | Core concept we borrow |
|-------|-------|------------------------|
| TS-RAG (Ning et al., 2025) | 2503.07649 | Retrieve top-k similar instances → augment frozen backbone → generate. We apply this to legal precedents, not time series. |
| Chat-TS (Quinlan et al., 2025) | 2503.10883 | Multimodal vocabulary expansion for joint text+structured reasoning. We apply this selectively to financial/tabular legal data (loan schedules, account statements in banking cases). |

**What we do NOT implement from the papers:**
- ARM module (Adaptive Retrieval Mixer) — overkill, RAG prompt injection is sufficient
- Discrete TS tokenization — not needed; tabular data passed as structured text to LLM
- FAISS — OpenSearch already present; use it for all vector search

---

## Current State (TalkDoc — What Already Exists)

File: `Legalv1/talkdoc/views.py`

| Feature | Status |
|---------|--------|
| Document upload + storage | ✅ Done (`upload_doc`) |
| Async doc ingestion (Celery) | ✅ Done (`ingest_document.delay`) |
| KNN vector search over chunks | ✅ Done (`knn_search`) |
| Session management (create/list/delete/rename) | ✅ Done |
| Chat with documents (RAG mode) | ✅ Done (`send_message`, `has_docs=True`) |
| General legal Q&A (no docs) | ✅ Done (`has_docs=False`) |
| Conversation history (last 6 msgs) | ✅ Done |
| Citations (doc name + page + snippet) | ✅ Done |
| Rate limiting (20/min per user) | ✅ Done |
| Auth | Supabase only (`@supabase_required`) |
| LLM | Centralised via `core/llm_client.py`; TalkDoc can run through OpenAI or OpenRouter depending on env |
| Domain KB / precedent retrieval helpers | ✅ Framework done, source corpora pending |
| Case Companion mode | ✅ Core API done |
| External API key auth | ✅ Done |
| Tiered LLM routing | ✅ Done |
| Token efficiency / prompt compression | ✅ Core rules implemented |

MongoDB collections used by TalkDoc:
- `rag_documents` — uploaded files metadata
- `rag_chat_sessions` — sessions with `doc_ids`, `has_docs`, `user_id`
- `rag_messages` — chat messages with `role`, `content`, `citations`

---

## Architecture Overview

```
                         ┌─────────────────────────────────┐
                         │         Mamla Brain API          │
                         │   /api/brain/v1/...              │
                         │   Auth: API Key OR Supabase      │
                         └────────────┬────────────────────┘
                                      │
              ┌───────────────────────┼────────────────────┐
              │                       │                    │
     ┌────────▼───────┐   ┌──────────▼──────┐   ┌────────▼───────┐
     │  Document Q&A  │   │ Case Companion  │   │  Financial     │
     │  (enhanced     │   │ (reasoning over │   │  Data Parser   │
     │   TalkDoc RAG) │   │  case + law KB) │   │  (banking/loan │
     └────────┬───────┘   └──────────┬──────┘   │  cases only)   │
              │                      │           └────────┬───────┘
              │                      │                    │
     ┌────────▼──────────────────────▼────────────────────▼───────┐
     │                   Retrieval Layer                            │
     │   1. Document chunks (OpenSearch, existing KNN index)       │
     │   2. Legal KB (IPC/CPC/CrPC sections + HC/SC case law)     │
     │      indexed in OpenSearch, separate index: `legal_kb`      │
     └────────────────────────────┬───────────────────────────────┘
                                  │
     ┌────────────────────────────▼───────────────────────────────┐
     │               Tiered LLM Router (OpenRouter)                │
     │  Tier 1 (cheap):    query rewrite, intent classification   │
     │  Tier 2 (balanced): document Q&A, short answers            │
     │  Tier 3 (strong):   case companion, multi-doc reasoning    │
     └────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. New Django App: `mamla_brain/`

Location: `Legalv1/mamla_brain/`
URL prefix: `/api/brain/`
Registered in: `Legalv1/Legalv1/urls.py`

Files to create:
```
mamla_brain/
├── __init__.py
├── apps.py
├── urls.py               # all /api/brain/ routes
├── views.py              # Document Q&A + Case Companion endpoints
├── auth.py               # API key generation + validation decorator
├── llm_router.py         # OpenRouter tiered model selection
├── retrieval.py          # Legal KB search + doc chunk search (calls talkdoc.search)
├── prompts.py            # All prompt templates (keep out of views.py)
├── financial_parser.py   # Tabular/financial data extractor (Phase 2)
└── tasks.py              # Celery: KB ingestion, async jobs
```

Current status: created. Additional package init files were also added for `management/` and `management/commands/` so Django command discovery stays explicit.

### 2. OpenRouter LLM Migration

**Why OpenRouter:** Single API key, access to all models, pay-per-token, no per-model contracts.
**How:** OpenRouter is OpenAI-API-compatible. Change `base_url` + key only.

```python
# In talkdoc/views.py and mamla_brain/llm_router.py
base_url = "https://openrouter.ai/api/v1"
api_key  = os.getenv("OPENROUTER_API_KEY")
```

New env var needed: `OPENROUTER_API_KEY`
Remove/deprecate: `RAG_CHAT_MODEL` (replaced by tiered routing logic)

**Tiered Model Routing (`mamla_brain/llm_router.py`):**

| Tier | Purpose | Suggested Model | Trigger |
|------|---------|-----------------|---------|
| T1 — Micro | Query rewriting, intent classification, KB keyword extraction | `meta-llama/llama-3.1-8b-instruct` | Every request, small task |
| T2 — Balanced | Document Q&A, short factual answers, citation assembly | `anthropic/claude-3-haiku` | Standard doc chat |
| T3 — Strong | Case Companion reasoning, multi-document synthesis, argument generation | `anthropic/claude-sonnet-4-5` | Case Companion, complex multi-doc |

Token limits per tier:
- T1: `max_tokens=256`, context cap 2k
- T2: `max_tokens=1024`, context cap 8k (trim conversation history if needed)
- T3: `max_tokens=2048`, context cap 32k

**Token efficiency rules (enforced in `llm_router.py`):**
1. Retrieve top-10 chunks, pass only top-5 to LLM (by relevance score)
2. Conversation history: last 6 turns only (not 20 as current TalkDoc sends)
3. System prompt cached per session — not re-sent on every turn (OpenRouter prompt caching)
4. T1 rewrites user query before retrieval — better precision, fewer irrelevant chunks fetched

### 3. Legal Knowledge Base

### Storage Model: MongoDB vs OpenSearch

Mamla Brain should follow the same storage split already used by TalkDoc:

- **MongoDB is the system of record.**
  Use it for API keys, sessions, messages, uploaded-document metadata, ownership, quotas, and any workflow state that must survive reindexing.
- **OpenSearch is the retrieval index.**
  Use it for vector search, lexical search, ranking, and fast retrieval over document chunks and knowledge-base chunks.

This means the Brain app is **not** OpenSearch-only.

Current implementation:
- `brain_api_keys`, `brain_sessions`, and `brain_messages` are stored in MongoDB.
- Uploaded source documents reuse TalkDoc's MongoDB/GridFS-backed storage and metadata model.
- `legal_kb`, `banking_kb`, and `markets_kb` are OpenSearch indexes used for retrieval, not as the canonical source of business state.

Operational guidance:
- Treat OpenSearch indexes as derived and rebuildable, but still back them up because re-embedding and reindexing can be expensive.
- For production, prefer a persistent or managed OpenSearch deployment over an ad hoc local-only node.
- Do not store canonical workflow state only in OpenSearch.

Implementation note: the retrieval/injection layer is now generic. `prompts.py` defines domain profiles for `legal`, `banking`, and `markets`, and `retrieval.py` resolves a per-domain OpenSearch index (`legal_kb`, `banking_kb`, `markets_kb`). The current repo now includes original starter legal seed files for ingestion and retrieval validation, but a production-grade corpus still needs curated primary-law and case-law material.

**Current legal seed corpus included in repo:**
- `civil_procedure_foundations.txt`
- `criminal_procedure_foundations.txt`
- `evidence_foundations.txt`
- `contract_and_obligation_disputes.txt`
- `limitation_and_interim_relief.txt`
- `cpc_jurisdiction_injunction_execution_map.txt`
- `crpc_bail_investigation_trial_map.txt`
- `evidence_admissions_electronic_records_map.txt`
- `ipc_offence_analysis_map.txt`
- `negotiable_instruments_cheque_dishonour_map.txt`
- `specific_relief_contract_remedies_map.txt`
- `bail_and_personal_liberty_precedents.txt`
- `criminal_vs_civil_wrong_precedents.txt`
- `electronic_evidence_precedents.txt`
- `injunction_and_specific_relief_precedents.txt`
- `cheque_dishonour_presumption_precedents.txt`
- `property_title_and_possession_precedents.txt`
- `matrimonial_custody_and_maintenance_precedents.txt`
- `company_director_and_vicarious_liability_precedents.txt`

These are original Mamla Brain seed documents intended for framework testing and early retrieval quality. They now include general litigation foundations, statute-oriented section maps, and precedent-oriented case notes across several major dispute families, but they are still not authoritative bare-act replacements or a complete research corpus.

**Next production corpus to add:**
- Curated primary-law text for key statutes
- Broader verified precedent coverage or licensed case-law material
- Domain corpora for `banking` and `markets`

**Index name in OpenSearch:** `legal_kb`
**Chunk size:** 512 tokens, 64 token overlap (smaller than doc chunks — legal sections are dense)
**Metadata per chunk:** `{ act, section_number, section_title, subsection, source_url, jurisdiction }`

**Ingestion pipeline (`mamla_brain/tasks.py`):**
1. Load raw text of each source file (store source files in `Legalv1/mamla_brain/legal_kb_sources/`, plain text, one file per source body)
2. Chunk by section boundary (not fixed token count — respect section structure)
3. Embed with same encoder used by TalkDoc (`embed_texts` from `talkdoc/tasks.py`)
4. Upsert into OpenSearch `legal_kb` index
5. Run once via management command: `python manage.py ingest_legal_kb`

Starter seed status:
- `legal_kb_sources/` is no longer empty.
- The current seed corpus is enough to validate ingestion, retrieval, and prompt assembly flows.
- Replace or augment these starter files with higher-authority sources before claiming legal-research completeness.

### 4. API Key Authentication

**For:** External third-party apps calling `/api/brain/`
**Not for:** Internal Mamla.AI frontend (uses Supabase as always)

MongoDB collection: `brain_api_keys`
```json
{
  "_id": "ObjectId",
  "key_hash": "sha256 of the raw key",
  "key_prefix": "mbk_live_xxxx",
  "owner_name": "string",
  "owner_email": "string",
  "plan": "free|pro|enterprise",
  "quota_monthly": 100,
  "quota_used": 0,
  "quota_reset_at": "ISODate (1st of next month)",
  "scopes": ["doc_qa", "case_companion"],
  "created_at": "ISODate",
  "last_used_at": "ISODate",
  "active": true
}
```

Decorator: `@brain_api_key_required` in `mamla_brain/auth.py`
- Read `X-Brain-API-Key` header
- Hash it, look up in MongoDB
- Check `active`, quota
- Set `request.brain_client` with plan + scopes
- Also accept Supabase token (dual auth) — internal users skip API key entirely

API key generation endpoint (admin only, no frontend for now):
`POST /api/brain/v1/admin/keys/` — generate key, return raw key exactly once

### 5. Endpoints (`mamla_brain/urls.py`)

```
/api/brain/v1/
├── health/                          GET   — Brain health check (no auth)
├── docs/upload/                     POST  — Upload doc (brain-authed)
├── docs/                            GET   — List docs
├── sessions/                        POST  — Create brain session
├── sessions/list/                   GET   — List sessions
├── sessions/<id>/messages/          GET   — Get messages
├── sessions/<id>/message/           POST  — Send message (Q&A or Case Companion)
├── sessions/<id>/                   DELETE
├── case-companion/start/            POST  — Start Case Companion session
├── case-companion/<id>/advise/      POST  — Get advice/arguments (structured JSON)
└── admin/keys/                      POST  — Generate API key (Supabase admin only)
```

### 6. Case Companion Mode

**Input:** case type, party role (petitioner/respondent), uploaded documents, optional FIR/charge sheet
**Output:** structured advice — applicable sections of law, suggested arguments, weaknesses, recommended next steps

**Flow per request:**
1. T1 LLM: classify case type + extract key legal issues (JSON output, ~200 tokens)
2. Retrieval: query Legal KB with extracted issues → top-8 relevant sections
3. Retrieval: query user docs (if any) → top-5 chunks
4. T3 LLM: full reasoning over assembled context → structured JSON response

**Structured response schema:**
```json
{
  "summary": "brief case summary",
  "applicable_law": [
    { "act": "IPC", "section": "302", "relevance": "..." }
  ],
  "arguments_for": ["..."],
  "arguments_against": ["..."],
  "weaknesses": ["..."],
  "recommended_steps": ["..."],
  "citations": [
    { "source": "...", "snippet": "..." }
  ]
}
```

System prompt lives in `mamla_brain/prompts.py` → constant `CASE_COMPANION_SYSTEM`.

### 7. Financial/Tabular Data Parser (Phase 2 — defer)

For banking/loan/cheque dishonour cases where documents contain repayment schedules, EMI tables,
or account statements:
- `mamla_brain/financial_parser.py`
- Detect tabular chunks from already-ingested `rag_documents` chunks
- Reformat as structured text: `"EMI 3: Due 2023-03-01, Amount ₹12,500, Status: Defaulted"`
- Inject as separate context block in T3 prompt with a specialized sub-prompt
- Trigger: `case_type: "banking"` in session metadata, or keyword heuristic on first message

---

## MongoDB Collections Summary (Brain-specific)

| Collection | Purpose |
|------------|---------|
| `brain_api_keys` | External API key store |
| `brain_sessions` | Brain sessions (extends rag_chat_sessions pattern, adds `mode`, `case_type`, `party_role`) |
| `brain_messages` | Brain messages (extends rag_messages pattern, adds `tier_used`, `tokens_used`) |
| `brain_legal_kb_meta` | Metadata of ingested legal acts/sections (admin/debugging) |

**Reuse from TalkDoc (no duplication):**
- `rag_documents` — brain uploads stored here too, same schema
- OpenSearch `documents` index — same vector index, brain queries it via `talkdoc.search.knn_search`

---

## Environment Variables to Add

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | Single key for all LLM calls via OpenRouter |
| `BRAIN_T1_MODEL` | Tier 1 model ID (default: `meta-llama/llama-3.1-8b-instruct`) |
| `BRAIN_T2_MODEL` | Tier 2 model ID (default: `anthropic/claude-3-haiku`) |
| `BRAIN_T3_MODEL` | Tier 3 model ID (default: `anthropic/claude-sonnet-4-5`) |
| `BRAIN_MONTHLY_FREE_QUOTA` | Default monthly quota for free tier (default: `100`) |

Add to: `Legalv1/legalenv` and document in `docs/02-backend-legalv1.md` env section.

---

## TODO List (Ordered — Start Here)

### Phase 0: TalkDoc Prep (minimal, non-breaking)

- [x] **P0-1** — ~~Swap TalkDoc's OpenAI call to OpenRouter in `talkdoc/views.py`~~
  **Done differently:** Centralised in `core/llm_client.py`. `talkdoc/views.py` now calls
  `chat_complete(messages, app_scenario='talkdoc:rag'/'talkdoc:general')`. Switch to OpenRouter
  by setting `LLM_DEFAULT_PROVIDER=openrouter` in `legalenv`.

- [x] **P0-2** — Reduce conversation history in `talkdoc/views.py` from last 20 to last 6 messages.
  This is already present in both TalkDoc message endpoints.

- [x] **P0-3** — ~~Add `OPENROUTER_API_KEY` to `.env`~~  Already in `legalenv`. `RAG_CHAT_MODEL` kept
  as a per-app override env var (see `docs/02-backend-legalv1.md` LLM Settings table).

### Phase 1: Core Brain App

- [x] **P1-1** — Create `Legalv1/mamla_brain/` Django app (all files listed in Component 1 above).
  Register in `INSTALLED_APPS` in `settings.py`. Add `path('api/brain/', include('mamla_brain.urls'))`
  to `Legalv1/Legalv1/urls.py`.

- [x] **P1-2** — Build `mamla_brain/llm_router.py`: single `call_llm(messages, tier)` function
  that picks model + `max_tokens` based on tier (T1/T2/T3). All Brain LLM calls go through this.
  Never call `openai` directly from views.

- [x] **P1-3** — Build `mamla_brain/prompts.py`: store all system prompts as named constants
  (`DOC_QA_SYSTEM`, `GENERAL_LEGAL_SYSTEM`, `CASE_COMPANION_SYSTEM`, `QUERY_REWRITE_SYSTEM`).
  Nothing hardcoded in views.py.

- [x] **P1-4** — Build `mamla_brain/auth.py`: `@brain_api_key_required` decorator that accepts
  either `X-Brain-API-Key` header (external) or Supabase token (internal). Quota check on every
  request. `generate_api_key()` helper to create + store key hash.

- [x] **P1-5** — Build brain session + message endpoints in `mamla_brain/views.py` using
  `brain_sessions` / `brain_messages` collections. Mirror TalkDoc session API surface.

- [x] **P1-6** — Build `POST /api/brain/v1/sessions/<id>/message/` — same RAG flow as TalkDoc
  `send_message` but uses `llm_router.py` (T2), `prompts.py`, and stores `tier_used`+`tokens_used`.

### Phase 2: Legal Knowledge Base

- [ ] **P2-1** — Collect and save raw text of IPC, CrPC, CPC, Evidence Act as plain `.txt` files
  in `Legalv1/mamla_brain/legal_kb_sources/`. Source: IndiaCode.nic.in (public domain).

- [x] **P2-2** — Write `mamla_brain/tasks.py`: `ingest_knowledge_base(domain_key=...)` — section-boundary chunking
  → embed via `talkdoc.tasks.embed_texts` → upsert to OpenSearch `legal_kb` index with metadata
  (`act`, `section_number`, `section_title`).

- [x] **P2-3** — Write Django management command `mamla_brain/management/commands/ingest_legal_kb.py`
  to trigger ingestion: `python manage.py ingest_legal_kb`.

- [x] **P2-4** — Build `mamla_brain/retrieval.py`:
  - `search_knowledge_base(query, domain_key='legal', k=8)` — query the domain KB index
  - `search_user_docs(query, user_id, doc_ids, k=5)` — calls `talkdoc.search.knn_search`
  - `merge_context(kb_hits, doc_hits)` — deduplicate + rank combined results

### Phase 3: Case Companion

- [x] **P3-1** — Build `POST /api/brain/v1/case-companion/start/` — create session with
  `mode="case_companion"`, store `case_type`, `party_role`, `doc_ids` in `brain_sessions`.

- [x] **P3-2** — Build `POST /api/brain/v1/case-companion/<id>/advise/` — full 3-step pipeline:
  T1 classify → KB retrieval → T3 reason → return structured JSON response schema (see above).

- [x] **P3-3** — Write `CASE_COMPANION_SYSTEM` prompt in `prompts.py`. Must instruct model to
  output strict JSON matching the schema. Include few-shot example in prompt.

- [x] **P3-4** — Add `tokens_used` and `tier_used` fields to every `brain_messages` insert
  for cost tracking. Read `usage.total_tokens` from OpenRouter response.

### Phase 4: External API Polish

- [x] **P4-1** — Build `POST /api/brain/v1/admin/keys/` — Supabase-admin-only endpoint to
  generate API keys. Returns raw key exactly once; only hash stored in DB.

- [x] **P4-2** — Add quota enforcement in `@brain_api_key_required`: atomic `$inc quota_used`
  after each successful request. Return HTTP 429 with `{"error": "quota_exceeded"}` if over limit.

- [x] **P4-3** — Build `GET /api/brain/v1/health/` — returns model tiers in use, KB index doc
  count, no auth required.

- [x] **P4-4** — Log `X-App-Name` request header to `brain_messages.app_name` — tracks which
  external app called what for analytics.

### Phase 5: Financial Parser (defer — only when banking clients onboard)

- [ ] **P5-1** — Build `mamla_brain/financial_parser.py`: detect tabular chunks from `rag_documents`
  and reformat as structured text (EMI rows, balance columns, etc.).

- [ ] **P5-2** — Add `case_type: "banking"` detection heuristic to Case Companion start endpoint
  (keyword match on initial message or explicit param).

- [ ] **P5-3** — Inject formatted financial context as a separate labelled block in T3 prompt
  (`--- FINANCIAL DATA ---`), separate from document and KB context blocks.

### Phase 6: Frontend Integration

- [ ] **P6-1** — Add `GET /case-companion` route in `frontend_webpack/src/AppContent.js`
  (protected, Lawyer/Client only). Create `CaseCompanion.jsx` component.

- [ ] **P6-2** — Frontend calls `/api/brain/v1/` via existing `AxiosInstance.jsx`
  (Supabase token — no API key for internal users, dual auth handles it).

- [ ] **P6-3** — Display Case Companion structured response in a formatted card UI:
  sections for Applicable Law, Arguments For/Against, Weaknesses, Next Steps.

---

## Docs to Update When Implementing

| Change | Update |
|--------|--------|
| New `/api/brain/` endpoints | `docs/04-api-reference.md` |
| New `mamla_brain/` app added | `docs/02-backend-legalv1.md` (app table) + `docs/01-architecture-overview.md` (repo layout) |
| New env vars | `docs/02-backend-legalv1.md` (env section) |
| New frontend route `/case-companion` | `docs/03-frontend-webpack.md` (route table) |
| Each completed TODO phase | `docs/05-changelog-and-improvements.md` |
| This doc added | `docs/00-agent-quickref.md` (add `Brain framework` row to task→doc table) |

---

## What NOT to Do

- ❌ Do NOT implement TS-RAG's ARM module or FAISS — OpenSearch handles all vector search
- ❌ Do NOT implement Chat-TS's discrete TS tokenization — structured text prompt is enough
- ❌ Do NOT duplicate TalkDoc's document storage/ingestion — Brain reuses `rag_documents` + `talkdoc.tasks`
- ❌ Do NOT add another auth system — external = API key, internal = Supabase, nothing else
- ❌ Do NOT hardcode model names in views — all LLM calls go through `llm_router.py`
- ❌ Do NOT expand conversation history beyond 6 turns for T2/T3 — token cost explodes
- ❌ Do NOT use Django ORM models — raw MongoDB like every other app
