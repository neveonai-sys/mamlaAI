# HC Scraper — Backend + Frontend Integration Plan

> **Scope:** Wire the existing HC FastAPI scraper (port 8001) into the Django backend
> and React frontend. Mirrors the district-court `ecourt_scrapped` app pattern — no
> new Django app, no new URL mount in `Legalv1/urls.py`.

---

## Architecture at a Glance

```
Frontend (React)                Django (ecourt_scrapped)          HC FastAPI (port 8001)
─────────────────────           ────────────────────────          ──────────────────────
/ecourts/hc/**  →  apiHC.js  →  POST /api/ecourts/v2/hc/**  →  GET /case/* / /orders/* etc.
```

**Key differences from district court:**

| | District Court | High Court |
|---|---|---|
| FastAPI port | 3000 | 8001 |
| HC identifier | `state_code + dist_code + court_complex_code + est_code` | `hc` slug + `bench` slug |
| FastAPI method | POST | GET (params) |
| Location picker | `LocationCascade` (4-level cascade) | `HCCourtSelector` (2-level: HC + bench) |
| Master data | MongoDB-cached + seed jobs | Static dict in FastAPI (no seed needed) |
| Date formats | `DD-MM-YYYY` everywhere | Mixed — see endpoint table |

---

## Phase 1 — Backend

### 1.1 New: `Legalv1/ecourt_scrapped/services/hc_scraper_client.py`

Mirrors `services/scraper_client.py`. Key difference: `get()` accepts query `params: dict`.

```python
HC_SCRAPER_BASE = os.environ.get("HC_SCRAPER_BASE_URL", "http://localhost:8001")

def get(path: str, params: dict = None) -> dict | list:
    r = requests.get(_url(path), params=params, timeout=HC_SCRAPER_TIMEOUT)
    r.raise_for_status()
    return r.json()

def health_check() -> dict: ...
```

---

### 1.2 New: `Legalv1/ecourt_scrapped/hc_views.py`

All views use `@supabase_required`. Pattern: parse JSON body → forward to HC FastAPI as GET query params.

| View function | Django URL | HC FastAPI endpoint | Auth |
|---|---|---|---|
| `hc_courts` | `GET hc/courts/` | `GET /courts` | ✅ required |
| `hc_health` | `GET hc/health/` | `GET /health` | ✅ required |
| `hc_meta_police_stations` | `GET hc/meta/police-stations/` | `GET /meta/police_stations?hc=&bench=` | ✅ required |
| `hc_meta_court_numbers` | `GET hc/meta/court-numbers/` | `GET /meta/court_numbers?hc=&bench=` | ✅ required |
| `hc_cnr_search` | `GET hc/case/cnr/<str:cino>/` | `GET /case/cnr/{cino}` | ✅ required |
| `hc_case_party` | `POST hc/case/party/` | `GET /case/party` | ✅ required |
| `hc_case_advocate` | `POST hc/case/advocate/` | `GET /case/advocate` | ✅ required |
| `hc_case_bar_code` | `POST hc/case/bar-code/` | `GET /case/bar-code` | ✅ required |
| `hc_case_filing` | `POST hc/case/filing/` | `GET /case/filing` | ✅ required |
| `hc_case_fir` | `POST hc/case/fir/` | `GET /case/fir` | ✅ required |
| `hc_orders_search` | `POST hc/orders/search/` | `GET /orders/search` | ✅ required |
| `hc_orders_by_court` | `POST hc/orders/by-court/` | `GET /orders/by-court` | ✅ required |
| `hc_orders_by_date` | `POST hc/orders/by-date/` | `GET /orders/by-date` | ✅ required |
| `hc_causelist` | `POST hc/causelist/` | `GET /causelist` | ✅ required |

**Request/response mapping per endpoint:**

```
hc_case_party     body: { hc, bench, name, year, status }           → GET /case/party?hc=&bench=&name=&year=&status=
hc_case_advocate  body: { hc, bench, query, status }                → GET /case/advocate?hc=&bench=&query=&status=
hc_case_bar_code  body: { hc, bench, bar_code, status }             → GET /case/bar-code?hc=&bench=&bar_code=&status=
hc_case_filing    body: { hc, bench, filing_number, year }          → GET /case/filing?hc=&bench=&filing_number=&year=
hc_case_fir       body: { hc, bench, police_station, fir_number,    → GET /case/fir?...
                          fir_year, status }
hc_orders_search  body: { hc, bench, name, year }                   → GET /orders/search?...
hc_orders_by_court body: { hc, bench, judge_code, date_from,        → GET /orders/by-court?...
                           date_to }   (YYYY-MM-DD)
hc_orders_by_date  body: { hc, bench, date_from, date_to }          → GET /orders/by-date?...
                          (DD-MM-YYYY — different format!)
hc_causelist       body: { hc, bench, list_date }                   → GET /causelist?...
```

---

### 1.3 New: `Legalv1/ecourt_scrapped/hc_urls.py`

```python
from django.urls import path
from ecourt_scrapped import hc_views as views

urlpatterns = [
    path('health/',                        views.hc_health),
    path('courts/',                        views.hc_courts),
    path('meta/police-stations/',          views.hc_meta_police_stations),
    path('meta/court-numbers/',            views.hc_meta_court_numbers),
    path('case/cnr/<str:cino>/',           views.hc_cnr_search),
    path('case/party/',                    views.hc_case_party),
    path('case/advocate/',                 views.hc_case_advocate),
    path('case/bar-code/',                 views.hc_case_bar_code),
    path('case/filing/',                   views.hc_case_filing),
    path('case/fir/',                      views.hc_case_fir),
    path('orders/search/',                 views.hc_orders_search),
    path('orders/by-court/',               views.hc_orders_by_court),
    path('orders/by-date/',                views.hc_orders_by_date),
    path('causelist/',                     views.hc_causelist),
]
```

---

### 1.4 Modify: `Legalv1/ecourt_scrapped/urls.py`

Add one line at the bottom (before the closing `]`):

```python
path('hc/', include('ecourt_scrapped.hc_urls')),
```

This exposes everything under `/api/ecourts/v2/hc/`.

---

### 1.5 Excluded HC Endpoints (DORMANT — do not proxy)

| HC FastAPI endpoint | Reason |
|---|---|
| `GET /case/number` | Marked 🔲 not tested in `HC_SCRAPER_STATUS.md` |
| `GET /case/act` | 💤 DORMANT |
| `GET /case/type` | 💤 DORMANT |
| `GET /orders/{cino}` | 💤 DORMANT |

---

## Phase 2 — Frontend

### New Files (all in `frontend/src/components/ecourt_scrapper/`)

| File | Purpose |
|---|---|
| `apiHC.js` | All HC API calls via `apiClient` |
| `HCCourtSelector.jsx` | 2-level HC + bench dropdown |
| `HCTerminal.jsx` | Landing page at `/ecourts/hc` |
| `HCCaseStatusTerminal.jsx` | Case search — 6 tabs |
| `HCCourtOrdersTerminal.jsx` | Orders search — 3 tabs |
| `HCCauseListTerminal.jsx` | Cause list |
| `HCCaseDetailPage.jsx` | Full case detail display |

### Modified Existing Files

| File | Change |
|---|---|
| `EcourtsTerminal.jsx` | Add District / High Court toggle button row |
| `AppContent.js` | Add 5 new HC routes |

---

### 2.1 `apiHC.js`

```js
// Base: /api/ecourts/v2/hc/
// Uses apiClient from services/api.js (Axios, Supabase auth attached)

fetchHCCourts()                              // GET hc/courts/
fetchHCHealth()                             // GET hc/health/
fetchHCPoliceStations(hc, bench)            // GET hc/meta/police-stations/?hc=&bench=
fetchHCCourtNumbers(hc, bench)              // GET hc/meta/court-numbers/?hc=&bench=

searchHCCnr(cino)                           // GET hc/case/cnr/{cino}/
searchHCParty(payload)                      // POST hc/case/party/
searchHCAdvocate(payload)                   // POST hc/case/advocate/
searchHCBarCode(payload)                    // POST hc/case/bar-code/
searchHCFiling(payload)                     // POST hc/case/filing/
searchHCFir(payload)                        // POST hc/case/fir/

searchHCOrdersByParty(payload)              // POST hc/orders/search/
searchHCOrdersByCourt(payload)              // POST hc/orders/by-court/
searchHCOrdersByDate(payload)               // POST hc/orders/by-date/

fetchHCCauseList(payload)                   // POST hc/causelist/
```

---

### 2.2 `HCCourtSelector.jsx`

Props: `onChange({ hc, bench, hcLabel, benchLabel, isComplete })`, `initialValues`, `disabled`

Behaviour:
- On mount: call `fetchHCCourts()` → populate HC select
- On HC change: derive bench options from the response (no extra API call needed — bench list is in `/courts` response)
- When both are selected: `isComplete = true`, calls `onChange`

---

### 2.3 `HCTerminal.jsx` — Landing at `/ecourts/hc`

Three navigation cards:
- **Case Search** → `/ecourts/hc/case-status`
- **Court Orders** → `/ecourts/hc/court-orders`
- **Cause List** → `/ecourts/hc/cause-list`

Plus a **CNR quick-lookup** text input at the top (bypasses full search — direct to `/ecourts/hc/case/:cino`).

---

### 2.4 `HCCaseStatusTerminal.jsx`

6 tabs:

| Tab | Fields | API call |
|---|---|---|
| **CNR** | 16-char CNR input | `searchHCCnr(cino)` → navigate to `/ecourts/hc/case/:cino` |
| **Party** | `HCCourtSelector` + name + year + status | `searchHCParty(payload)` |
| **Advocate** | `HCCourtSelector` + advocate name + status | `searchHCAdvocate(payload)` |
| **Bar Code** | `HCCourtSelector` + bar code + status | `searchHCBarCode(payload)` |
| **Filing** | `HCCourtSelector` + filing number + year | `searchHCFiling(payload)` |
| **FIR** | `HCCourtSelector` + PS dropdown + FIR no + year + status | `searchHCFir(payload)` |

Results render inline below the form (list of case cards). Each case card has a detail link to `/ecourts/hc/case/:cino`.

---

### 2.5 `HCCourtOrdersTerminal.jsx`

3 tabs:

| Tab | Fields | Note |
|---|---|---|
| **By Party** | `HCCourtSelector` + name + optional year | |
| **By Court** | `HCCourtSelector` + court-number dropdown + date_from + date_to | Dates: `YYYY-MM-DD` |
| **By Date** | `HCCourtSelector` + date_from + date_to | Dates: `DD-MM-YYYY` ⚠️ |

Results: order cards with PDF link (`pdf_url` field), case number, order date, judge.

---

### 2.6 `HCCauseListTerminal.jsx`

Fields: `HCCourtSelector` + date picker (default today, formatted to `DD-MM-YYYY`).

Results: cause list items as cards — serial, bench name, list type, PDF button.

---

### 2.7 `HCCaseDetailPage.jsx`

Route: `/ecourts/hc/case/:cino`

On mount: calls `searchHCCnr(cino)` (proxy: `GET /hc/case/cnr/:cino/`).

Sections rendered:

| Section | Fields displayed |
|---|---|
| Case Header | `cino`, `high_court`, `bench`, `case_type_name / case_no / case_year`, `status` pill, `filing_date` |
| Parties | `petitioner` + `petitioner_advocate`, `respondent` + `respondent_advocate` |
| Status | `stage_of_case`, `coram`, `next_hearing`, `last_hearing`, `subject` |
| Acts | Chip list from `acts[]` |
| Hearing History | Table: date, judge, purpose, next_date |
| Orders | Table: date, order_number, judge + PDF link |
| Linked Cases | Table: `filing_number`, `case_number`, `is_main`, `status` |
| IA Details | Table: `ia_number`, `classification`, `party`, `filing_date`, `status` |
| Subordinate Court | `court_number_and_name`, `case_number_and_year`, `case_decision_date` |

---

### 2.8 Modify `EcourtsTerminal.jsx`

Add a **District / High Court** toggle at the top of the page:

```jsx
<div className="flex gap-2 mb-6">
  <button className="btn btn-active">District Court</button>
  <button className="btn" onClick={() => navigate('/ecourts/hc')}>High Court</button>
</div>
```

Similarly: `HCTerminal.jsx` has the reverse toggle pointing back to `/ecourts`.

Also: make the existing CNR quick-lookup auto-detect HC CNR prefixes. The first 4 chars of a valid HC CNR are 2 letters + `HC` (e.g. `UPHC`, `DLHC`, `MHHC`). If the entered CNR matches that pattern, navigate to `/ecourts/hc/case/:cino` instead of the DC route.

---

### 2.9 Modify `AppContent.js`

Add 5 new lazy-loaded routes in the `/ecourts/*` section:

```jsx
<Route path="/ecourts/hc"               element={<HCTerminal />} />
<Route path="/ecourts/hc/case-status"   element={<HCCaseStatusTerminal />} />
<Route path="/ecourts/hc/court-orders"  element={<HCCourtOrdersTerminal />} />
<Route path="/ecourts/hc/cause-list"    element={<HCCauseListTerminal />} />
<Route path="/ecourts/hc/case/:cino"    element={<HCCaseDetailPage />} />
```

---

## Phase 3 — Docs to Update

| Doc | What to add |
|---|---|
| `docs/04-api-reference.md` | HC API section: all 14 endpoints with params |
| `docs/03-frontend-webpack.md` | 5 new HC routes in route table |
| `docs/06-ecourts-scraper.md` | HC service section, env var, new pattern |
| `docs/05-changelog-and-improvements.md` | Entry for this integration |

---

## Env Vars (new)

| Var | Default | Purpose |
|---|---|---|
| `HC_SCRAPER_BASE_URL` | `http://localhost:8001` | HC FastAPI service URL |
| `HC_SCRAPER_TIMEOUT` | `120` | Request timeout in seconds |

---

## Date Format Reference (HC-specific)

| Endpoint | `date_from` / `date_to` format |
|---|---|
| `POST hc/orders/by-court/` | `YYYY-MM-DD` |
| `POST hc/orders/by-date/` | `DD-MM-YYYY` |
| `POST hc/causelist/` (`list_date`) | `DD-MM-YYYY` |
| All response date fields | `DD-MM-YYYY` |

The `apiHC.js` layer handles format conversion internally so the UI always works with a standard date picker value.

---

## Verification Checklist

- [ ] `HC_SCRAPER_BASE_URL=http://localhost:8001` set in env, HC FastAPI running
- [ ] `curl localhost:8000/api/ecourts/v2/hc/courts/` → returns all HC slugs
- [ ] `curl localhost:8000/api/ecourts/v2/hc/health/` → `{"status": "ok"}`
- [ ] Navigate to `/ecourts` → "High Court" toggle button visible
- [ ] Navigate to `/ecourts/hc` → landing page with 3 nav cards
- [ ] HC CNR (e.g. `UPHC010551112017`) in quick-lookup → routes to `/ecourts/hc/case/:cino`
- [ ] DC CNR in quick-lookup → still routes to `/ecourts/case/:cnr` (existing behaviour preserved)
- [ ] Party search: select `allahabad` / `allahabad` bench, enter name, submit → results list renders
- [ ] FIR tab: after selecting HC + bench, police station dropdown populates
- [ ] Orders → By Court: court-number dropdown populates after HC + bench selected
- [ ] Cause list: date defaults to today, PDF links in results are valid `https://hcservices.ecourts.gov.in/...` URLs
- [ ] No 4xx / 5xx in browser console
- [ ] No undefined prop errors in React
