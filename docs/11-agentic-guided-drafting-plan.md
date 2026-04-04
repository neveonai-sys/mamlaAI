# 11 — Agentic Guided Drafting Flow: Plan

> **Status:** IMPLEMENTED — Phase 1, 2, 3 completed 2026-04-04.
> All changes are additive. The existing Quick Draft form (`/drafting`) is untouched.
> Each phase is a separate execution sprint. Update this file when a phase completes.

---

## Why

The current flow (form → instant full draft → edit) produces generic output because the model
gets one shot with minimal context. Legal drafts are sensitive to small details — which party,
which prayer, which act, what relief sought — that the user never fills in a flat form.

A conversational intake agent gathers those details one-by-one, tells the user whether each is
mandatory or optional, and only generates the draft once it has enough to work with. The
output quality is demonstrably higher, and the interaction builds user trust.

---

## What Does NOT Change

The Quick Draft form at `/drafting` continues to work exactly as before. All existing routes,
API endpoints, MongoDB collections, and components are untouched. Zero regression risk.

---

## Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Coexist or replace? | **Coexist** — "Guided Draft" tab alongside "Quick Draft" | Power users keep the fast path; new/occasional users get the guided path |
| Who triggers generation? | **User clicks "Generate Draft"** after AI signals readiness | Avoids surprise; lawyer stays in control |
| Doc upload mid-conversation | **AI extracts facts immediately** and continues conversation using them | Reduces redundant questions |
| Case linkage | **Yes** — `DraftContextAgent` pre-fills context; AI skips known fields | Case page → guided draft should feel seamless |
| UI location | **New route `/drafting/guided`** with start-options for case / doc / scratch | Clean separation; no cramming into existing workspace |

---

## Architecture Overview

```
User at /drafting/guided
        │
        ├── Start with a Case  ──►  DraftContextAgent.run(case_id)
        │                               └─► key_facts + suggested_sections injected into system prompt
        │
        ├── Start with Documents  ──►  TalkDoc upload  ──►  retrieval.search_user_docs()
        │                               └─► extracted facts injected into system prompt
        │
        └── Start from Scratch  ──►  blank conversation
                │
                ▼
        [ConversationalDraftAgent]
          state: gathering → ready → generating
          LLM: mamla_brain.llm_router.call_llm(messages, tier='t2')
          RAG: mamla_brain.retrieval (user docs + legal KB)
          JSON signal: { ready, missing_fields, draft_plan, message }
          Stored in: draft_conversations (MongoDB)
                │
                │  (AI signals ready)
                ▼
        User reviews Draft Plan summary card (sections + key facts)
        Clicks "Generate Draft"
                │
                ▼
        guide/generate/  →  reuses initiate_drafting_session logic (same quota/entitlement path)
                │
                ▼
        navigate('/drafting/:session_id')  →  existing 3-pane editing workspace
```

---

## Phase 1 — Backend

### 1A — New system prompt

**File:** `Legalv1/mamla_brain/prompts.py`

Add `DRAFT_INTAKE_SYSTEM` prompt. The prompt instructs the agent to:
- Identify draft type early (mandatory first step)
- Ask **one question at a time** — never dump a list
- Explicitly tell the user whether each detail is **mandatory** or **optional**
- Never generate the draft itself during conversation — only gather requirements
- Signal readiness by embedding valid JSON in its reply:
  ```json
  {
    "ready": true,
    "missing_fields": [],
    "draft_plan": {
      "draft_type": "...",
      "sections_plan": ["..."],
      "key_facts": { "party_name": "...", "court": "...", "relief_sought": "..." }
    },
    "message": "I have everything I need. Here's the plan for your draft..."
  }
  ```
- When `ready=false`, `missing_fields` lists remaining required items.

Use `CASE_COMPANION_SYSTEM` and `DOC_QA_SYSTEM` (already in the file) as style references.

---

### 1B — New agent

**File:** `Legalv1/agents/conversational_draft_agent.py` (new)

Follows the `BaseAgent` contract (`run()` / `_run()`, `safe_json_loads()`).

MongoDB collection: `draft_conversations`
```json
{
  "conv_id": "<uuid>",
  "user_id": "<supabase_uid>",
  "state": "gathering | ready | generating",
  "messages": [
    { "role": "system | user | assistant", "content": "...", "ts": "..." }
  ],
  "doc_context": ["...extracted fact strings..."],
  "draft_plan": { ... },
  "case_id": "<optional>",
  "created_at": "...",
  "updated_at": "..."
}
```

**Methods:**

`start(user_id, case_id=None, document_ids=None)` — Creates a new `draft_conversations` doc.
- If `case_id` → calls `DraftContextAgent.run()` → injects `context_summary`, `key_facts`,
  `suggested_sections` into system prompt as pre-known facts. AI's first message acknowledges
  what it already knows and asks only about gaps.
- If `document_ids` → calls `retrieval.search_user_docs()` with seeding queries
  (parties, dates, applicable law, relief) → injects rendered context.
- If neither → blank conversation; AI asks "What kind of legal document do you need?"
- Returns `{ok, conv_id, message}` (AI's opening turn).

`message(conv_id, user_id, user_text)` — Main conversation loop.
- Appends user turn to `messages[]`.
- Calls `llm_router.call_llm(messages, tier='t2')`.
- Appends AI turn to `messages[]`.
- Runs `safe_json_loads()` to detect `{ready: true}` in the response.
- If ready: sets `state='ready'`, stores `draft_plan`.
- Returns `{ok, reply, ready, draft_plan}`.

`handle_doc_upload(conv_id, user_id, document_ids)` — Mid-conversation doc upload.
- Calls `retrieval.search_user_docs()` on newly uploaded docs.
- Merges new facts into `doc_context[]`.
- Injects a synthetic system context message so the AI "sees" the new facts.
- Gets AI to react ("I found the following relevant facts in your document…").
- Returns `{ok, reply}`.

`generate(conv_id, user_id)` — Triggers draft generation.
- Asserts `state='ready'`.
- Builds enriched `user_query` from `draft_plan` + conversation summary.
- Sets `state='generating'`.
- Calls existing `CreateupdatefetchAIdrafts.start_new_session()` with the enriched query
  (same MongoDB write path, same LLM generation, same auto-save logic).
- Returns `{ok, session_id}`.

**Soft cap:** 10 turns maximum. At turn 8 the system prompt receives an injected instruction
to signal `ready=true` on the next reply regardless of remaining gaps; this bounds LLM cost.

---

### 1C — New endpoints

**Files:** `Legalv1/ai_draft/views.py` · `Legalv1/ai_draft/urls.py`

All endpoints are `@supabase_required`.

| Endpoint | Method | Body | Returns |
|----------|--------|------|---------|
| `/api/aidrafts/guide/start/` | POST | `case_id?`, `document_ids?` | `{conv_id, message}` |
| `/api/aidrafts/guide/message/` | POST | `conv_id`, `message` | `{reply, ready, draft_plan?}` |
| `/api/aidrafts/guide/upload_doc/` | POST | `conv_id`, `document_ids` | `{reply}` |
| `/api/aidrafts/guide/generate/` | POST | `conv_id` | `{session_id}` |

---

## Phase 2 — Frontend

### 2A — New page component

**File:** `mamlaAI_ground_zero/frontend/src/components/drafting/GuidedDraftingPage.jsx` (new)

**Part 1 — Start screen** (shown until `conv_id` exists)

Three cards:
- **"Start with a Case"** → case selector dropdown (`GET /api/cases/list/`) → on select:
  `POST /api/aidrafts/guide/start/` with `case_id` → transitions to chat
- **"Start with Documents"** → inline doc upload (reuses TalkDoc `POST /api/talkdoc/upload_doc`) →
  on complete: `POST /api/aidrafts/guide/start/` with `document_ids` → transitions to chat
- **"Start from Scratch"** → `POST /api/aidrafts/guide/start/` with no context → transitions to chat

**Part 2 — Chat pane** (active once `conv_id` exists)

- Message list: user bubbles (right-aligned) + AI bubbles (left-aligned, with Mamla Brain avatar)
- Typing indicator (three-dot animation) while awaiting AI response
- Input bar with a paper-clip "Attach Document" icon:
  - Triggers TalkDoc upload → on complete → `POST /api/aidrafts/guide/upload_doc/`
  - AI reaction message appended to chat
- Turn counter shown subtly when nearing the 8-turn soft cap

**Part 3 — Ready banner** (shown when `ready=true` arrives)

- AI's last message rendered as normal chat bubble
- Below it, a "Draft Plan" summary card:
  - Section list chips matching `draft_plan.sections_plan`
  - Key facts row (party names, court, relief, etc.) from `draft_plan.key_facts`
- Two actions:
  - "Continue Conversation" (plain link — dismisses banner, focus returns to input)
  - **"Generate Draft"** (prominent primary button) → `POST /api/aidrafts/guide/generate/` →
    loading state → on success → `navigate('/drafting/:session_id')` → existing editing workspace

**State shape (local React state):**
```js
{
  phase: 'start' | 'chat' | 'generating',
  convId: null,
  messages: [{ role, content, ts }],
  ready: false,
  draftPlan: null,
  loading: false,
}
```

---

### 2B — Register route

**File:** `mamlaAI_ground_zero/frontend/src/AppContent.js`

Add before the existing `/drafting` routes (so `/drafting/guided` does not match `/drafting/:id`):
```jsx
<Route path="/drafting/guided" element={<GuidedDraftingPage />} />
```

---

### 2C — Entry points

**`DraftingWorkspace.jsx`** — Init screen header area:
- Add a "Guided Draft" button above the existing tab row.
- `onClick → navigate('/drafting/guided')`
- Style: secondary/ghost button; label "Guided Draft (Recommended)"

**`CaseHub.jsx`** — Drafts tab:
- Add "Guided Draft" button alongside the existing "New Draft" button.
- `onClick → navigate('/drafting/guided?case_id=' + caseId)`
- `GuidedDraftingPage` reads `?case_id` on mount and auto-calls `guide/start/` with that case_id,
  skipping the start screen and going directly to the chat pane.

---

## Phase 3 — Docs Update

Update alongside implementation (same commit):

| Doc | What to add |
|-----|------------|
| `docs/04-api-reference.md` | Add 4 `guide/*` endpoints to the ai_draft section |
| `docs/02-backend-legalv1.md` | Add `draft_conversations` to MongoDB collection table |
| `docs/00-agent-quickref.md` | Add `conversational_draft_agent.py` to agents row; add `/drafting/guided` to frontend routes |
| `docs/05-changelog-and-improvements.md` | Log feature completion |

---

## Key Files Reference

| File | Role |
|------|------|
| `Legalv1/mamla_brain/prompts.py` | Add `DRAFT_INTAKE_SYSTEM` |
| `Legalv1/mamla_brain/llm_router.py` | Reuse `call_llm(messages, tier)` — no changes |
| `Legalv1/mamla_brain/retrieval.py` | Reuse `search_user_docs()`, `merge_context()`, `render_context()` — no changes |
| `Legalv1/agents/base_agent.py` | Reference for `BaseAgent` pattern + `safe_json_loads()` — no changes |
| `Legalv1/agents/draft_context.py` | Called when `case_id` provided — no changes |
| `Legalv1/agents/conversational_draft_agent.py` | **NEW** |
| `Legalv1/ai_draft/views.py` | Add 4 guide endpoints |
| `Legalv1/ai_draft/urls.py` | Register `/guide/*` paths |
| `mamlaAI_ground_zero/frontend/src/components/drafting/GuidedDraftingPage.jsx` | **NEW** |
| `mamlaAI_ground_zero/frontend/src/AppContent.js` | Register `/drafting/guided` route |
| `mamlaAI_ground_zero/frontend/src/components/drafting/DraftingWorkspace.jsx` | Add Guided Draft entry button |
| `mamlaAI_ground_zero/frontend/src/components/cases/CaseHub.jsx` | Add Guided Draft button in Drafts tab |

---

## Verification Checklist

- [x] `DRAFT_INTAKE_SYSTEM` prompt added to `mamla_brain/prompts.py`
- [x] `ConversationalDraftAgent` module created at `agents/conversational_draft_agent.py`
- [x] 4 guide endpoints added to `ai_draft/views.py` and registered in `ai_draft/urls.py`
- [x] `GuidedDraftingPage.jsx` created with start / chat / ready phases
- [x] `/drafting/guided` route registered in `AppContent.js` (before `/drafting/:id`)
- [x] "Guided Draft" button added to `DraftingWorkspace.jsx` init screen
- [x] "Guided Draft" button added to `CaseHub.jsx` Drafts tab with `?case_id=` param
- [x] `docs/04-api-reference.md`, `docs/02-backend-legalv1.md`, `docs/00-agent-quickref.md`, `docs/05-changelog-and-improvements.md` all updated
- [ ] **Runtime:** Start with a case → AI's first message references case facts and skips those questions
- [ ] **Runtime:** Upload a doc mid-conversation → AI's reply acknowledges extracted facts
- [ ] **Runtime:** Answer questions until `ready=true` → Draft Plan card renders with sections list
- [ ] **Runtime:** Click "Generate Draft" → redirects to `/drafting/:session_id` with valid draft
- [ ] **Runtime:** `/drafting` Quick Draft route fully functional — no regression
- [ ] **Runtime:** `draft_conversations` doc in MongoDB has all turns + `draft_plan` after readiness signal
- [ ] **Runtime:** `?case_id=` param on `/drafting/guided` auto-starts with case context, skips start screen

---

## Open Questions / Follow-up Sprints

1. **Resumable conversations** — `draft_conversations` is persisted per turn, so resuming is free.
   Add a "Resume Conversation" entry in the Drafts tab (Phase 4, separate sprint).
2. **Streaming responses** — v1 is request/response. Add SSE streaming in a follow-up for
   perceived speed improvement on slow connections.
3. **Mobile layout** — The chat UI is inherently single-column and mobile-friendly. Design it
   responsively from the start; the existing 3-pane editing workspace is a separate concern.
4. **Tier promotion** — Conversation turns use `t2`. If case + doc context combined exceeds ~2000
   tokens of injected context, auto-promote that turn to `t3` in `ConversationalDraftAgent.message()`.
