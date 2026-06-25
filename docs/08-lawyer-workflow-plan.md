# 08 — One-Stop Lawyer Workflow: Plan & Agentic Architecture

> **Status:** PLANNING — This is the design document for the full lawyer lifecycle platform.
> Do not touch code in any section below until the plan is agreed. Each phase is a separate
> execution sprint. Update this file whenever a phase is completed or the plan changes.
> Last updated: 2026-03-29

---

## 1. Vision

Transform Mamla.AI from a collection of useful tools (drafting, eCourts, calendar, document chat)
into a **single, coherent workflow** where a lawyer can take a client from first contact to case
resolution without leaving the platform. Every action — onboarding, filing, hearing prep,
drafting, discussion, archiving — is a connected step in one case-centred flow, with AI
assistance available at each step.

---

## 2. The Workflow Spine

The **Case** is the unifying entity. Everything else hangs off it.

```
Client Onboarding
       │
       ▼
  [Case Created]  ←──── linked eCourts case (CNR)
       │
       ├── Documents uploaded
       │        └── Document Intelligence Agent: extract facts, flag gaps
       │
       ├── Hearings (Calendar events)
       │        ├── Pre-hearing: Hearing Prep Agent (briefing + arguments)
       │        └── Post-hearing: Outcome recorded, tasks generated
       │
       ├── Drafts (context-aware: case + docs + hearing notes auto-injected)
       │
       ├── Case Notes / Discussion Thread (lawyer ↔ paralegal ↔ client)
       │
       ├── Tasks (deadlines, assignments)
       │
       └── Case Resolution
                └── Closure Agent: summary, archive, client notification
```

---

## 3. What Already Exists (Do Not Rebuild)

| Capability | Location | Notes |
|------------|----------|-------|
| Client onboarding (invite + link) | `ClientOnboarding` component, `onboard-client` API | Working |
| AI drafting (session, sections, PDF) | `DraftingWorkspace`, `ai_draft` app | Working |
| Document chat / RAG | `DocumentWorkspace`, `talkdoc` app | Working |
| Calendar events (hearings, meetings) | `CalendarPage`, `calendar_management` app | Working |
| eCourts case lookup (CNR, cause list) | eCourts pages, `ecourt_scrapped` app | Working |
| Mamla Brain (Case Companion, tiered LLM) | `mamla_brain` app | Core API done |
| Court update subscriptions | `CourtUpdates` component, `todaysupdates` app | Working |
| Dashboard + Command Center | `Dashboard`, `CommandCenter` | Working |
| Centralised LLM routing | `core/llm_client.py` → `chat_complete()` | Working |

---

## 4. Gap Analysis — What Is Missing

### 4.1 Internal Case Registry

**Problem:** A "case" is currently just an ID string referenced inside `user_details`.  
There is no first-class `cases` MongoDB document containing case title, type, status, court,
timeline, or related metadata. Lawyers cannot create, track, or close internal case records.

**Need:** A new `cases` Django app with a `cases` MongoDB collection that is the single
source of truth for all case-level data.

---

### 4.2 Hearing Preparation & Recording

**Problem:** Calendar events can be tagged as court hearings but there is no:
- AI-generated pre-hearing briefing (arguments to make, questions to ask, relevant law)
- Post-hearing outcome recording (what happened, next date, judge notes)
- Link between a calendar event (hearing) and the case documents/history

**Need:** A Hearing Prep Agent that, given a case ID + hearing date, pulls:
1. eCourts history (past hearings, orders)
2. Case documents (via TalkDoc chunks)
3. Previous hearing notes recorded in the system
4. Case Companion analysis (applicable law, arguments)

…and returns a structured "hearing brief" the lawyer reads before walking into court.

---

### 4.3 Context-Aware Drafting

**Problem:** When the lawyer starts a draft, they manually fill in case ID, client ID, and
re-describe the case. The system does not automatically inject the case context from the
internal registry, linked eCourts data, or uploaded documents.

**Need:** When a draft session is started from within a case, the system should:
1. Pre-fill `draft_for` with case + client IDs
2. Optionally auto-generate a context summary from the case's TalkDoc documents
3. Suggest draft type based on the current case stage

---

### 4.4 Case Notes & Discussion Thread

**Problem:** There is no per-case communication layer. Lawyers cannot write notes about
a case, paralegals cannot add observations, and clients cannot see case updates.

**Need:** A simple threaded `case_notes` structure with author, timestamp, visibility
(`internal` for lawyer+paralegal only, `shared` visible to client).

---

### 4.5 Task Management

**Problem:** Post-hearing there are always follow-up tasks (file a document, research a
point, call the client). These have no home in the current system, so they fall through.

**Need:** A lightweight `case_tasks` layer (title, due date, assigned to, status) per case.
The Post-Hearing Agent should auto-suggest tasks based on the hearing outcome.

---

### 4.6 Agentic Orchestration

**Problem:** Each tool (eCourts, drafting, TalkDoc, calendar, Brain) works standalone.
There is no agent that can chain them together automatically.

**Need:** A set of focused agents, each owning a specific lifecycle trigger, that call the
existing services in sequence and return structured output the UI can display or act on.
See Section 6 for architecture.

---

### 4.7 Client-Facing Portal

**Problem:** The client has an account but can only use the drafting/document-chat pages.
They cannot see their case status, the documents their lawyer shared, hearing dates, or
updates.

**Need:** A restricted client view of their case — status, shared documents, upcoming
hearings, and notes marked `shared` by the lawyer. Uses the same case data; just filtered
by visibility rules.

---

## 5. Data Model Additions

### 5.1 `cases` Collection

```json
{
  "_id": "<uuid>",
  "case_ref":        "matter/internal reference string",
  "title":           "Client Name vs Respondent",
  "case_type":       "Civil / Criminal / Family / Labour / ...",
  "court":           { "state": "...", "district": "...", "court": "..." },
  "cnr":             "MHAU0500012024",        // linked eCourts CNR (optional)
  "lawyer_id":       "<supabase_user_id>",
  "client_ids":      ["<user_id>", ...],
  "paralegal_ids":   ["<user_id>", ...],
  "status":          "Active | Settled | Disposed | Appeal | Archived",
  "stage":           "Filing | Pleadings | Evidence | Arguments | Judgment | Closed",
  "filing_date":     "ISO date",
  "next_hearing":    "ISO date",
  "tags":            ["property", "injunction"],
  "brief":           "Short description of the matter (auto-generated or manual)",
  "created_at":      "ISO datetime",
  "updated_at":      "ISO datetime"
}
```

### 5.2 `hearing_notes` Collection

```json
{
  "_id": "<uuid>",
  "case_id":         "<cases._id>",
  "lawyer_id":       "<supabase_user_id>",
  "hearing_date":    "ISO date",
  "calendar_event_id": "<calendar event _id>",   // optional link
  "type":            "prep | outcome",
  "content":         "Free-form text or structured JSON",
  "ai_brief":        { ... },    // Hearing Prep Agent output (stored on generation)
  "purpose":         "Arguments on injunction application",
  "outcome":         "Hearing adjourned. Next date: ...",
  "next_date":       "ISO date",
  "tasks_generated": ["<task_id>", ...],
  "created_at":      "ISO datetime"
}
```

### 5.3 `case_notes` Collection

```json
{
  "_id": "<uuid>",
  "case_id":    "<cases._id>",
  "author_id":  "<supabase_user_id>",
  "author_role": "Lawyer | Paralegal | Client",
  "visibility": "internal | shared",
  "content":    "Markdown or plain text",
  "attachments": ["<rag_document_id>", ...],
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime"
}
```

### 5.4 `case_tasks` Collection

```json
{
  "_id": "<uuid>",
  "case_id":      "<cases._id>",
  "title":        "File reply to counter-affidavit",
  "description":  "...",
  "due_date":     "ISO date",
  "assigned_to":  "<supabase_user_id>",
  "created_by":   "<supabase_user_id>",
  "status":       "Pending | InProgress | Done | Cancelled",
  "priority":     "High | Medium | Low",
  "source":       "manual | agent",   // 'agent' if auto-created by Post-Hearing Agent
  "created_at":   "ISO datetime"
}
```

---

## 6. Agentic Flow Architecture

All agents are Python classes in a new `Legalv1/agents/` Django app.
They call existing services — they do NOT reimplement them.
Each agent returns a structured JSON result plus a `next_suggested_action`.

```
Legalv1/agents/
├── __init__.py
├── apps.py
├── urls.py           → /api/agents/
├── views.py          → HTTP entry points for each agent
├── base_agent.py     → BaseAgent class (shared logging, error handling)
├── case_intake.py    → CaseIntakeAgent
├── document_intel.py → DocumentIntelligenceAgent
├── hearing_prep.py   → HearingPrepAgent
├── post_hearing.py   → PostHearingAgent
├── draft_context.py  → DraftContextAgent
└── case_closure.py   → CaseClosureAgent
```

### 6.1 CaseIntakeAgent

**Trigger:** Lawyer finishes onboarding a client and creates a new case.

**Steps:**
1. Accept: `client_id`, `cnr` (optional), `case_description`, `court` details
2. If CNR provided → call `ecourt_scrapped` to fetch eCourts case data
3. Extract: `case_type`, `parties`, `acts_and_sections`, `next_hearing_date` from eCourts
4. Call `brain:t1` LLM to classify case type + suggest `stage` from description
5. Create `cases` document in MongoDB
6. Return: case record + `next_suggested_action: "upload_documents"`

**API:** `POST /api/agents/case-intake/`

---

### 6.2 DocumentIntelligenceAgent

**Trigger:** Documents uploaded to a case (or existing TalkDoc session linked to a case).

**Steps:**
1. Accept: `case_id`, `document_ids` (rag_documents IDs already uploaded)
2. For each document, run `talkdoc` KNN search on summary queries ("parties", "key dates",
   "applicable law", "relief sought")
3. Call `brain:t2` LLM with assembled snippets → extract structured facts:
   - parties, key dates, acts/sections, prayer/relief
4. Update `cases.brief` if empty, or append new facts
5. Return: extracted facts + `next_suggested_action: "create_hearing_prep"` or `"start_draft"`

**API:** `POST /api/agents/document-intel/`

---

### 6.3 HearingPrepAgent

**Trigger:** Lawyer opens a hearing event in the calendar (or manually invokes from case page).

**Steps:**
1. Accept: `case_id`, `hearing_date`, `purpose` (arguments / interim order / evidence)
2. Pull eCourts history (via `ecourt_scrapped` CNR if linked)
3. Pull last 3 `hearing_notes.outcome` for this case
4. Run TalkDoc KNN search on case documents for `purpose`-relevant chunks (top-8)
5. Call `mamla_brain` Case Companion endpoint with assembled context
6. Structure result:
   - `applicable_law`: relevant sections
   - `arguments_for`: points to raise
   - `watch_points`: opposing arguments to anticipate
   - `suggested_questions`: questions to put to witnesses/opposite party
   - `checklist`: documents to bring, procedural steps
7. Store result in `hearing_notes` as type `prep`
8. Return structured brief + `next_suggested_action: "create_draft"` or `"record_outcome"`

**API:** `POST /api/agents/hearing-prep/`

---

### 6.4 PostHearingAgent

**Trigger:** Lawyer marks a hearing event complete and records the outcome.

**Steps:**
1. Accept: `case_id`, `hearing_notes_id`, `outcome_text`, `next_date` (optional)
2. Update `hearing_notes` record with `outcome` and `next_date`
3. Update `cases.next_hearing` and `cases.stage` if appropriate
4. Call `brain:t1` LLM on `outcome_text` → extract: status (adjourned/decided/partial order),
   tasks implied (file document, pay court fees, serve notice)
5. Auto-create `case_tasks` for each implied task with `source: "agent"`
6. If next_date provided, suggest creating a calendar event
7. Return: updated case summary + task list + `next_suggested_action: "schedule_next_hearing"`

**API:** `POST /api/agents/post-hearing/`

---

### 6.5 DraftContextAgent

**Trigger:** Lawyer initiates a draft from within a case (rather than standalone drafting).

**Steps:**
1. Accept: `case_id`, `draft_type` (petition / written statement / application / reply)
2. Pull `cases` record → extract court, parties, case_type, stage
3. Pull last `hearing_notes` outcome if any
4. Run TalkDoc search on case documents for key facts relevant to `draft_type`
5. Build enriched `draft_context` JSON:
   - `draft_for`: case + client IDs (pre-populated)
   - `location`: court, district, state from case record
   - `context_summary`: auto-generated paragraph from facts
   - `suggested_sections`: section names appropriate for draft_type + case_type
6. Return context → frontend passes this directly into `DraftingWorkspace` pre-fill

**API:** `POST /api/agents/draft-context/`

---

### 6.6 CaseClosureAgent

**Trigger:** Lawyer marks case as `Settled`, `Disposed`, or `Archived`.

**Steps:**
1. Accept: `case_id`, `resolution_type`, `resolution_summary`
2. Fetch all: hearing notes, tasks (completed/pending), drafts, case notes
3. Call `brain:t3` LLM → generate structured case summary:
   - timeline of key events, final outcome, parties, applicable law used
4. Update `cases.status` = `Archived`; update `cases.stage` = `Closed`
5. Mark all pending tasks as `Cancelled` (or prompt lawyer to review)
6. Create a final `case_notes` entry (visibility `shared`) summarising the outcome for the client
7. Return: full case summary document + `next_suggested_action: "send_closure_email"`

**API:** `POST /api/agents/case-closure/`

---

## 7. New Django App: `cases`

This is the first app to build. It provides the case registry that agents + frontend depend on.

```
Legalv1/cases/
├── __init__.py
├── apps.py
├── urls.py
├── views.py
└── routes/
    ├── case_crud.py      → create, list, get, update, close
    ├── hearing_notes.py  → create/list/get hearing prep + outcomes
    ├── case_notes.py     → threaded notes with visibility
    └── case_tasks.py     → task CRUD per case
```

**URL prefix:** `/api/cases/`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/cases/create/` | Create internal case |
| GET | `/api/cases/list/` | Lawyer's case list |
| GET | `/api/cases/<id>/` | Full case detail |
| PUT | `/api/cases/<id>/update/` | Update status, stage, CNR, brief |
| POST | `/api/cases/<id>/close/` | Close/archive case |
| GET | `/api/cases/<id>/timeline/` | Full timeline (hearings + notes + tasks) |
| POST | `/api/cases/<id>/hearing-notes/` | Create hearing note (prep or outcome) |
| GET | `/api/cases/<id>/hearing-notes/` | List hearing notes |
| POST | `/api/cases/<id>/notes/` | Add case note |
| GET | `/api/cases/<id>/notes/` | List notes (filtered by visibility) |
| POST | `/api/cases/<id>/tasks/` | Create task |
| GET | `/api/cases/<id>/tasks/` | List tasks |
| PUT | `/api/cases/<id>/tasks/<task_id>/` | Update task status |

All endpoints: `@supabase_required`. Lawyer sees all their cases; paralegal sees assigned;
client sees their case(s) with only `shared` notes and no `internal` data.

---

## 8. New Frontend Routes & Components

All routes go into `mamlaAI_ground_zero/frontend/src/AppContent.js`.

| Route | Component | Auth | Notes |
|-------|-----------|------|-------|
| `/cases` | `CaseRegistry` | Lawyer | List of all cases with status filters |
| `/cases/:caseId` | `CaseHub` | Lawyer + Paralegal + Client | Central case page |
| `/cases/:caseId/hearings/:hearingId` | `HearingWorkspace` | Lawyer | Prep brief + recording |
| `/cases/:caseId/documents` | `CaseDocuments` | Lawyer + Paralegal + Client | Scoped TalkDoc |
| `/cases/:caseId/drafts` | `CaseDrafts` | Lawyer | Drafts for this case |

### 8.1 CaseHub (core new page)

The `CaseHub` is the lawyer's cockpit for a single case. Layout:

```
┌─────────────────────────────────────────────────────────┐
│  Case Header: title · status badge · stage · court      │
│  [Prep Hearing]  [New Draft]  [Add Note]  [Add Task]    │
├─────────────┬───────────────────────────────────────────┤
│  Timeline   │   Active Panel (tabs)                     │
│  (left)     │   ┌── Hearings ─────────────────────────┐ │
│  Vertical   │   │  upcoming → past                    │ │
│  scroll of: │   │  each: date, purpose, AI brief, note│ │
│  - Hearings │   └─────────────────────────────────────┘ │
│  - Notes    │   ┌── Documents ────────────────────────┐ │
│  - Drafts   │   │  uploaded docs linked to case       │ │
│  - Tasks    │   │  Chat-with-docs scoped to case      │ │
│             │   └─────────────────────────────────────┘ │
│             │   ┌── Drafts ───────────────────────────┐ │
│             │   │  drafts for this case               │ │
│             │   └─────────────────────────────────────┘ │
│             │   ┌── Notes ────────────────────────────┐ │
│             │   │  threaded notes, visibility toggle  │ │
│             │   └─────────────────────────────────────┘ │
│             │   ┌── Tasks ────────────────────────────┐ │
│             │   │  kanban or list, assign, due dates  │ │
│             │   └─────────────────────────────────────┘ │
└─────────────┴───────────────────────────────────────────┘
```

### 8.2 HearingWorkspace

```
┌────────────────────────────────────────────────────────┐
│  Hearing: [date] · [purpose] · Case: [title]           │
│  [Generate AI Brief]  [Record Outcome]                 │
├────────────────────────────────────────────────────────┤
│  AI BRIEF (collapsible)                                │
│  ┌─ Applicable Law ──────────────────────────────────┐ │
│  │  IPC s.420 — Cheating and dishonestly inducing... │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌─ Arguments to Raise ──────────────────────────────┐ │
│  │  1. The contract signed on [date] clearly...      │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌─ Watch Points ────────────────────────────────────┐ │
│  │  Respondent may argue limitation period...        │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌─ Checklist ───────────────────────────────────────┐ │
│  │  ☐ Certified copy of sale deed                   │ │
│  │  ☐ Bank statement Jan–Mar 2023                   │ │
│  └────────────────────────────────────────────────────┘ │
│                                                        │
│  OUTCOME NOTES (post-hearing recording)               │
│  [textarea: what happened today]                      │
│  Next date: [date picker]                             │
│  [Save Outcome + Generate Tasks]                      │
└────────────────────────────────────────────────────────┘
```

---

## 9. How the Dots Connect (Integration Map)

```
ClientOnboarding  ──(creates)──►  CaseIntakeAgent
                                      │
                                      ▼
                              cases (MongoDB)
                                  │       │
                  ┌───────────────┘       └──────────────────┐
                  ▼                                           ▼
         DocumentIntelAgent                         CalendarPage (hearings)
           (after upload)                                    │
                  │                                          ▼
                  └─► updates cases.brief          HearingPrepAgent
                                                            │
                                                            ▼
                                                  hearing_notes (prep)
                                                            │
                                                   [Lawyer in court]
                                                            │
                                                            ▼
                                                  PostHearingAgent
                                                    │         │
                                                    ▼         ▼
                                              case_tasks    cases.stage
                                                            updated

DraftingWorkspace ◄──(pre-fill)── DraftContextAgent
                                        ▲
                                        │ pulls
                                  cases + hearing_notes
                                  + TalkDoc documents

CaseClosureAgent  ──(on close)──►  cases.status = Archived
                                   Brain T3 → closure report
                                   case_notes (shared) → client sees it
```

---

## 10. What "Agentic" Means Here (Architecture Decision)

We are **not** using a general autonomous agent loop (no LangChain, no AutoGen, no tool-calling
loops). The reasons:

1. **Determinism**: Each agent has a fixed, predictable flow with no open-ended tool selection.
2. **Cost control**: Each agent makes at most 2–3 LLM calls via `chat_complete()` with tight
   `max_tokens`. No runaway loops.
3. **Latency**: Fixed-step pipelines return in 5–15 seconds vs unpredictable agent loops.
4. **Reliability**: The lawyer needs to trust the output; deterministic pipelines are easier
   to test and debug.

Each agent is a Python class with a `.run(inputs)` method that returns a structured dict.
The HTTP views in `agents/views.py` are thin wrappers that call `.run()` and return JSON.

Future upgrade path: if open-ended reasoning is needed (e.g. "research this legal point
and find relevant precedents"), that goes into Mamla Brain Case Companion which already
has the T1→retrieve→T3 multi-step reasoning architecture.

---

## 11. Phased Execution Plan

### Phase 1 — Case Registry & Hub (Foundation)

> **Goal:** Give the lawyer a place to create, view, and manage cases before agents exist.

- [x] **P1-1** Create `Legalv1/cases/` Django app; register in `INSTALLED_APPS` + `urls.py`
- [x] **P1-2** Implement case CRUD endpoints (create, list, get, update, close)
- [x] **P1-3** Implement `case_notes` endpoints (create, list with visibility filter)
- [x] **P1-4** Implement `case_tasks` endpoints (CRUD + status update)
- [x] **P1-5** Implement `hearing_notes` endpoints (create prep, create outcome, list)
- [x] **P1-6** Build `CaseRegistry` frontend page (`/cases`) — list view with status filter
- [x] **P1-7** Build `CaseHub` frontend page (`/cases/:caseId`) — full case detail with tabs (Hearings, Notes, Tasks)
- [x] **P1-8** Add `/cases` to Sidebar nav and update AppContent routes
- [x] **P1-9** Build `HearingWorkspace` frontend page (`/cases/:caseId/hearings/:hearingId`) — prep + outcome recording
- [x] **P1-10** Update `docs/00-agent-quickref.md`, `docs/04-api-reference.md`, `docs/02-backend-legalv1.md`

---

### Phase 2 — Agents App (AI Layer)

> **Goal:** Wire AI intelligence into the case lifecycle.

- [x] **P2-1** Create `Legalv1/agents/` Django app; register in `INSTALLED_APPS` + `urls.py`
- [x] **P2-2** Build `BaseAgent` class with shared logging and error handling
- [x] **P2-3** Implement `CaseIntakeAgent` + `POST /api/agents/case-intake/`
- [x] **P2-4** Implement `DocumentIntelligenceAgent` + `POST /api/agents/document-intel/`
- [x] **P2-5** Implement `HearingPrepAgent` + `POST /api/agents/hearing-prep/`
- [x] **P2-6** Implement `PostHearingAgent` + `POST /api/agents/post-hearing/`
- [x] **P2-7** Implement `DraftContextAgent` + `POST /api/agents/draft-context/`
- [x] **P2-8** Implement `CaseClosureAgent` + `POST /api/agents/case-closure/`

---

### Phase 3 — Hearing Workspace

> **Goal:** Give the lawyer a dedicated page to prepare for and record hearing outcomes.

- [x] **P3-1** Build `HearingWorkspace` frontend page (`/cases/:caseId/hearings/:hearingId`)
- [x] **P3-2** Wire `HearingPrepAgent` call to "Generate AI Brief" button
- [x] **P3-3** Wire `PostHearingAgent` call to "Save Outcome" button
- [x] **P3-4** Auto-create calendar event suggestion when next date is set

---

### Phase 4 — Context-Aware Drafting

> **Goal:** Drafting launched from a case automatically gets case context.

- [x] **P4-1** Add "Start Draft from Case" button on `CaseHub` drafts tab
- [x] **P4-2** Wire `DraftContextAgent` call to pre-fill `DraftingWorkspace`
- [x] **P4-3** Build `CaseDrafts` page scoped to a case (`/cases/:caseId/drafts`)
- [x] **P4-4** Update `DraftingWorkspace` to accept pre-fill context from agent

---

### Phase 5 — Client Portal

> **Goal:** Clients can log in and see their case — status, shared docs, hearing dates, updates.

- [x] **P5-1** Add `/my-case` route for client role (shows their case(s))
- [x] **P5-2** Filter `case_notes` to `visibility: shared` for client view
- [x] **P5-3** Show upcoming hearings from calendar events
- [x] **P5-4** Show shared documents (TalkDoc docs where lawyer explicitly shared)

---

### Phase 6 — Closure & Archiving

> **Goal:** Clean closure workflow with a final AI-generated case summary.

- [x] **P6-1** Build case close modal on `CaseHub` (select resolution type, enter summary)
- [x] **P6-2** Wire `CaseClosureAgent` on close action
- [x] **P6-3** Archive view on `CaseRegistry` (filter: `status=Archived`)

---

## 12. New Things to Introduce (Not Currently in the Platform)

| Feature | Priority | Rationale |
|---------|----------|-----------|
| Internal case registry (`cases` collection) | **P0** | Everything else depends on it |
| Hearing notes (prep + outcome) | **P0** | Core gap in current workflow |
| AI hearing brief (Hearing Prep Agent) | **P1** | High-value, differentiating feature |
| Case tasks | **P1** | Workflow continuity between hearings |
| Case discussion thread | **P1** | Reduces out-of-band communication |
| Client portal (restricted case view) | **P2** | Client retention and trust |
| Case closure / archiving | **P2** | Lifecycle completeness |
| Notification layer (hearing reminders, task deadlines) | **P2** | Celery beat already exists |
| Billing/time tracking per case | **P3** | Out of scope for now, design hook in `cases` schema |

---

## 13. MongoDB Index Plan

Add these indexes in `core/init_clients.py → ensure_indexes()`:

```python
# cases
db["cases"].create_index([("lawyer_id", 1), ("status", 1)])
db["cases"].create_index([("client_ids", 1)])
db["cases"].create_index([("cnr", 1)])

# hearing_notes
db["hearing_notes"].create_index([("case_id", 1), ("hearing_date", -1)])

# case_notes
db["case_notes"].create_index([("case_id", 1), ("created_at", -1)])
db["case_notes"].create_index([("case_id", 1), ("visibility", 1)])

# case_tasks
db["case_tasks"].create_index([("case_id", 1), ("status", 1)])
db["case_tasks"].create_index([("assigned_to", 1), ("due_date", 1)])
```

---

## 14. Open Questions (Resolve Before Execution)

| # | Question | Impact |
|---|----------|--------|
| 1 | Should `cases` be the primary CNR authority, or should we continue allowing case IDs without eCourts linkage? | Schema decision for `cnr` field (nullable or required) |
| 2 | Should clients have direct message access in the discussion thread, or is it read-only notes only? | Security + notification complexity |
| 3 | Should `HearingPrepAgent` be triggered automatically when a hearing calendar event is created, or only on manual request? | UX flow + Celery async vs on-demand |
| 4 | Do we store the full AI brief in `hearing_notes.ai_brief`, or just a summary? Full storage has token cost implications. | Storage cost |
| 5 | Phase 5 client portal — should clients have a separate app shell/sidebar, or just a filtered version of the same UI? | Frontend complexity |
| 6 | Billing/time tracking — should the `cases` schema include a `billing_rate` field now for future use? | Schema forward-compatibility |

---

## 15. Doc Maintenance After Execution

When each phase is executed, update these docs:

| After phase | Update |
|-------------|--------|
| Phase 1 | `04-api-reference.md` (cases endpoints), `02-backend-legalv1.md` (cases app), `00-agent-quickref.md` (routes + collections), `05-changelog-and-improvements.md` |
| Phase 2 | `04-api-reference.md` (agents endpoints), `02-backend-legalv1.md` (agents app), `00-agent-quickref.md` |
| Phases 3–6 | `03-frontend-webpack.md` (new routes), `00-agent-quickref.md` (routes), `05-changelog-and-improvements.md` |
