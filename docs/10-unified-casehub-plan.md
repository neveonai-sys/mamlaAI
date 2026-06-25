# 10 — Unified Case Hub + Context-Aware Workflow Plan

> **Status:** ✅ COMPLETE — All 18 items implemented on 2026-04-04.
> Implementation verified: 0 editor errors across all changed files.

---

## Implementation Summary (2026-04-04)

| # | Item | File(s) | Status |
|---|------|---------|--------|
| 1 | Auto-generate `case_ref` (`MC-{YYYY}-{6-char}`) on case creation; remove user-editable field | `cases/routes/case_crud.py` | ✅ |
| 2 | Unique MongoDB index on `cases.case_ref` | `core/init_clients.py` | ✅ |
| 3 | Remove "Internal Ref" input from `CreateCaseModal` | `CaseRegistry.jsx` | ✅ |
| 4 | Always-visible `case_ref` copy-chip in CaseHub header | `CaseHub.jsx` | ✅ |
| 5 | `GET /api/aidrafts/list/` — add `?case_id=` filter | `ai_draft/views.py` | ✅ |
| 6 | `GET /api/calendar/events/` — add `?case_id=` filter | `calendar_management/views.py` | ✅ |
| 7 | `GET /api/users/clients/` — add `?search=` filter | `users/supabase_views.py` | ✅ |
| 8 | CaseHub **Documents tab** — fetches `talkdoc/documents/?caseid=` | `CaseHub.jsx` | ✅ |
| 9 | CaseHub **Calendar tab** — fetches `calendar/events/?case_id=` | `CaseHub.jsx` | ✅ |
| 10 | CaseHub **eCourts tab** — CNR branch + `ecourts_params` form branch | `CaseHub.jsx` | ✅ |
| 11 | `DraftingWorkspace` — `?case_id=` URL param pre-fills case + stage→type map | `DraftingWorkspace.jsx` | ✅ |
| 12 | `CalendarPage` — `?case_id=` URL param opens editor pre-filled as Court Hearing | `CalendarPage.jsx` | ✅ |
| 13 | `CreateCaseModal` — collapsible "Link Client" section (search + inline invite) | `CaseRegistry.jsx` | ✅ |
| 14 | New `ClientProfile.jsx` — contact card + linked cases list | `clients/ClientProfile.jsx` (new) | ✅ |
| 15 | Route `/clients/:clientId` → `<ClientProfile>` | `AppContent.js` | ✅ |
| 16 | `ClientOnboarding` rows navigate to `/clients/:clientId` | `ClientOnboarding.jsx` | ✅ |
| 17 | `listCalendarEventsByCase()` service wrapper | `services/casesApi.js` | ✅ |
| 18 | CaseHub **Drafts tab** — switched to backend `aidrafts/list/?case_id=` filter | `CaseHub.jsx` | ✅ |

### Key implementation notes

- `ecourts_params` was missing from `UPDATABLE_FIELDS` — added proactively
- `draft_for.caseid` uses lowercase `caseid` key (dot-notation filter in MongoDB)
- Calendar events store `caseId` (camelCase) — `?case_id=` filter applied after sort
- `ensure_indexes()` remains commented out at boot — run manually to build the new `case_ref` unique index on existing data before enabling
- `onboard-client/` returns `signup_link` not `client_id`; inline invite uses a phone-based lookup afterwards to resolve the client id
- `listCases()` response key is `cases` (not `results`)

---

## Vision

The **Case** is the single command centre for a lawyer's work. From one CaseHub page a lawyer can see and act on every draft, document, calendar event, and eCourts status tied to that case — without re-entering court location or client details they've already set up.

Client creation is merged into the case creation modal so there's no separate "add client" step. A lightweight client profile page (/clients/:clientId) shows their linked cases.

---

## What Does NOT Change

Every existing route, component, and API endpoint continues to work identically without the new params. All new fields and query params are optional. Lawyers who ignore the new tabs or deep-links lose nothing.

| Existing feature | Route / endpoint | Status |
|-----------------|-----------------|--------|
| Case list + create | `/cases` → CaseRegistry | Unchanged |
| Case detail (overview, hearings, notes, tasks) | `/cases/:caseId` → CaseHub | Extended (new tabs added) |
| Standalone drafting | `/drafting`, `/drafting/:id` | Unchanged; `?case_id=` is purely optional |
| Document upload + chat | `/documents`, `/documents/:id` | Unchanged; `?case=` was already supported |
| Calendar | `/calendar` | Unchanged; `?case_id=` is optional |
| eCourts terminal | `/ecourts/*` | Unchanged |
| Client roster | `/clients` → ClientOnboarding | Unchanged |
| Client case portal | `/my-case` | Unchanged |

---

## Phase 1 — Backend Additions (unblock the new tabs)

All changes are backwards-compatible additive fields / optional query params.

### 1A — `ai_draft` — store + filter by case_id

**File:** `Legalv1/ai_draft/views.py`

- `start_session` view: accept optional `case_id` in POST body; store on the `aidrafts_complete_data` document.
- Saved-drafts list endpoint (`get_user_saved_drafts` or a new `list/`): add optional `?case_id=` filter — only return drafts where `case_id` matches when the param is present.

### 1B — Calendar — add case_id filter

**File:** `Legalv1/calendar_management/views.py`

- `GET /api/calendar/events/` already accepts `start_date`, `end_date`, `search`, `upcoming`.
- Add optional `?case_id=` filter: return only events where the event document's `caseId` field matches.
- **Pre-check:** Verify the REST calendar events are storing `caseId` in MongoDB. If not, update the `POST /api/calendar/events/` write path to persist `caseId` first.

### 1C — Cases — store eCourts search params

**File:** `Legalv1/cases/views.py` (or routes/)

- `PATCH /api/cases/<case_id>/update/` already exists and accepts any updatable field.
- Add `ecourts_params` to the accepted fields:
  ```json
  {
    "ecourts_params": {
      "search_type": "cnr | party | filing | advocate | fir",
      "cnr": "...",
      "party_name": "...",
      "filing_number": "...",
      "registration_year": "...",
      "advocate_name": "...",
      "police_station_code": "...",
      "fir_year": "...",
      "fir_number": "..."
    }
  }
  ```
- No new endpoint needed.

---

## Phase 2 — CaseHub: 4 New Tabs

**File:** `mamlaAI_ground_zero/frontend/src/components/cases/CaseHub.jsx`

The existing four tabs (Overview, Hearings, Notes, Tasks) stay. Four new tabs are appended.

### Tab 5 — Drafts

- Fetch: `GET /api/aidrafts/list/?case_id={caseId}` (Phase 1A)
- Show: title, draft_type, updated_at, status badge
- "New Draft" button → navigate to `/drafting?case_id={caseId}`
- Row click → `/drafting/{session_id}?case_id={caseId}`

### Tab 6 — Documents

- Fetch: `GET /api/talkdoc/documents/?caseid={caseId}` — **already supported, zero new backend work**
- Show: filename, indexed status badge, uploaded_at
- "Upload / Chat" button → `/documents?case={caseId}`
- Row click → `/documents?case={caseId}` with that doc's ID passed so DocumentWorkspace can pre-select it

### Tab 7 — Calendar

- Fetch: `GET /api/calendar/events/?case_id={caseId}&upcoming=true` (Phase 1B)
- Show: upcoming events list — date, time, title, eventType badge
- Past events in a collapsible section below
- "Add Event" button → `/calendar?case_id={caseId}` (Phase 3C)

### Tab 8 — eCourts

**If `case.cnr` is present:**
- Inline "Check Status" section with CNR, last-checked timestamp, manual "Refresh" button
- Refresh calls `POST /api/ecourts/v2/cnr/search/` on demand (not auto, to avoid rate limiting)
- "Open Full Detail" link → `/ecourts/case/{case.cnr}`

**If no CNR:**
- Editable form with `search_type` toggle (CNR / Party / Filing / Advocate / FIR) + matching input fields (same controls as the eCourts CaseSearch page)
- "Save to Case" button → calls `PATCH /api/cases/{caseId}/update/` with `ecourts_params` (Phase 1C)
- "Run Search" button → navigates to `/ecourts/case-search?q={savedQuery}&type={savedType}` with pre-filled params

---

## Phase 3 — Context-Aware Deep Links

### 3A — DraftingWorkspace.jsx

**File:** `mamlaAI_ground_zero/frontend/src/components/drafting/DraftingWorkspace.jsx`

On mount, if `?case_id=` is in URL params:
1. Call `getCase(case_id)` (already in casesApi.js)
2. Extract `case.court.state`, `case.court.district`, `case.court.court_name` → pre-fill into the location fields so the state/district/court selection step is skipped
3. Map `case.stage` → suggested `draft_type`:

   | Case stage | Suggested draft type |
   |-----------|---------------------|
   | Filing | Petition / Plaint |
   | Pleadings | Written Statement / Reply |
   | Evidence | Affidavit |
   | Arguments | Written Submissions |
   | Appeal | Memorandum of Appeal |
   | Closed | Application |

4. Show the pre-filled location and suggested draft type — user can still override
5. On session start: include `case_id` in the `start_session` payload (wires the draft back to the case for Tab 5)
6. Keep `case_id` in component state for the full session

### 3B — DocumentWorkspace.jsx

**No code change needed.** DocumentWorkspace already reads `?case` query param and pre-fills `matter.caseid`. All navigation links from CaseHub just need to pass `?case={caseId}`.

### 3C — CalendarPage.jsx

**File:** `mamlaAI_ground_zero/frontend/src/components/calendar/CalendarPage.jsx`

On mount, read `?case_id=` from URL params (or `useLocation().state`):
- Pre-fill the "New Event" form's `caseId` field
- Default `eventType` to 'Court Hearing'
- User can change both before saving

---

## Phase 4 — Unified Matter Creation Modal

**File:** `mamlaAI_ground_zero/frontend/src/components/cases/CaseRegistry.jsx`

Extend the existing `CreateCaseModal`. The case fields (title, type, state/district/court cascade, CNR, dates, tags, brief) don't change.

Add a collapsible **"Add Client (optional)"** section at the bottom — collapsed by default:

1. **Search existing clients:** text input → calls `GET /api/users/clients/` filtered by typed name/email → results shown as selectable chips
2. **Create new client inline:** "Create new client" toggle expands a mini-form (fname, lname, email, phone)
   - On modal save: calls `POST /api/users/onboard-client/` first → gets `client_id` → includes in `case.client_ids`
3. **Existing client selected:** their `user_id` is added to `client_ids` in the `createCase` payload

Any standalone "Add Client" shortcut buttons duplicating this flow can be removed from nav/dashboard.

The `/clients` page (`ClientOnboarding`) stays as the full client roster for bulk management.

---

## Phase 5 — Lightweight Client Profile

### New component: `ClientProfile.jsx`

**File (new):** `mamlaAI_ground_zero/frontend/src/components/clients/ClientProfile.jsx`

- Fetch: `GET /api/users/clients/{clientId}/` — contact info
- Fetch: `GET /api/cases/list/` — backend already filters to accessible cases; frontend further filters to cases containing this client in `client_ids`
- Show:
  - Avatar/initials, full name, phone, email, status badge
  - List of linked cases as CaseCard components (reuse from CaseRegistry)
  - Clicking a case → `/cases/{caseId}` (CaseHub)
- No sub-tabs: documents, drafts, and calendar events are all visible per-case from CaseHub

**Route:**

**File:** `mamlaAI_ground_zero/frontend/src/AppContent.js`
- Add `/clients/:clientId` → `<ClientProfile>`
- Existing `/clients` → `<ClientOnboarding>` stays unchanged

**Make client rows in ClientOnboarding clickable:** navigate to `/clients/:clientId` on click.

---

## Relevant Files

| File | Change |
|------|--------|
| `Legalv1/ai_draft/views.py` | Phase 1A: case_id storage + filter |
| `Legalv1/calendar_management/views.py` | Phase 1B: case_id filter + caseId write |
| `Legalv1/cases/views.py` (or routes/) | Phase 1C: ecourts_params in update |
| `frontend/src/components/cases/CaseHub.jsx` | Phase 2: 4 new tabs |
| `frontend/src/components/cases/CaseRegistry.jsx` | Phase 4: extend CreateCaseModal |
| `frontend/src/components/drafting/DraftingWorkspace.jsx` | Phase 3A: case_id param, pre-fill, stage→type map |
| `frontend/src/components/calendar/CalendarPage.jsx` | Phase 3C: accept caseId on mount |
| `frontend/src/AppContent.js` | Phase 5: add /clients/:clientId route |
| `frontend/src/components/clients/ClientProfile.jsx` (NEW) | Phase 5: lightweight client profile |
| `frontend/src/services/casesApi.js` | New wrappers: listDraftsByCase, listCalendarEventsByCase |

---

## Verification Checklist

1. Create case from CaseRegistry → attach existing client inline → case arrives with `client_ids` populated
2. Create case + create new client inline in the same modal → client onboarded + linked in one submit
3. CaseHub → Drafts tab → only this case's drafts shown; "New Draft" opens DraftingWorkspace with location pre-filled + draft type suggested from stage
4. Save a draft from that pre-filled session → return to CaseHub Drafts tab → draft appears
5. CaseHub → Documents tab → only docs tagged to this case; "Upload / Chat" opens DocumentWorkspace with case pre-selected in matter
6. CaseHub → Calendar tab → only events for this case; "Add Event" opens CalendarPage with caseId + Court Hearing type pre-filled
7. CaseHub → eCourts tab (no CNR) → fill search params → "Save to Case" → verify `ecourts_params` stored in case record; "Run Search" navigates to eCourts with pre-filled form
8. CaseHub → eCourts tab (with CNR) → manual "Refresh" fetches latest eCourts status
9. `/clients` → click a client row → lightweight profile shows contact + linked cases as cards; clicking a case goes to CaseHub
10. All standalone flows (drafting without case, doc upload, client onboarding) work exactly as before

---

## Decisions Log

| Decision | Choice | Reason |
|---------|--------|--------|
| Client Hub depth | Lightweight profile only — no tabs | Full per-case context lives in CaseHub; no need to duplicate |
| Drafting pre-population | Location auto-filled + draft type suggested from stage | User-selected: saves the location step, suggests but doesn't force type |
| eCourts search persistence | Save `ecourts_params` to case record via existing PATCH | Saves re-entry; no new endpoint needed |
| eCourts CNR refresh | Manual on-demand only | Avoid scraper rate limits; show last-checked timestamp |
| Creation UX | Single-form modal, collapsible client section | User-selected; least disruptive to existing flow |
| Documents tab | Zero new backend work | TalkDoc already supports `?caseid=` filter |
| Backward compat | All new fields/params optional | Existing standalone flows unaffected |
