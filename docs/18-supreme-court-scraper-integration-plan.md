# 18 — Supreme Court of India (SCI) Scraper Integration Plan

> Integrate a broad Supreme Court service into the existing eCourts stack, mirroring how District
> Court (DC) and High Court (HC) are wired. See also [`06-ecourts-scraper.md`](06-ecourts-scraper.md).

## Context

The app already exposes **District Court (DC)** and **High Court (HC)** case-search inside a single
"eCourts" surface, plus a narrow **Supreme Court e-SCR *citation* lookup** (`/sc`). We now want a
**broad SCI service** — Case Status, Cause List, Daily Orders, Judgments, Office Reports — wired the
exact same way DC/HC are: a FastAPI scraper mounted alongside `/dc`, `/hc`, `/sc`, Django proxy views,
and a frontend reachable via a toggle chip in the eCourts hub.

This is a **third repetition of an established 3-layer pattern**. HC (added after DC) is the closest
template — copy it. Everything is additive; nothing existing is modified destructively.

**Decisions:** build all 3 layers into the existing dirs (`scrapping_codes_ecourt/`,
`Legalv1/ecourt_scrapped/`, `new_frontend/`); cover **all 5 flows / 18 endpoints**; navigation via a
**toggle chip in the eCourts hub** (mirrors HC, no new sidebar item).

**Naming — avoid the `/sc` collision:** the existing `/sc` mount = e-SCR *citation* lookup and stays
untouched. The new broad service mounts at **`/sci`**, Django prefix **`/api/ecourts/v2/sci/`**,
frontend BASE **`ecourts/v2/sci`**, routes under **`/ecourts/sci/*`**.

> **Key risk / first milestone:** the SCI backend API request-payload field names and response JSON
> keys (`webapi.sci.gov.in/api/...`) are **unconfirmed** in the source spec — they must be verified
> live via Chrome DevTools before the scraper parser is trusted (exactly how `sc_citation_scraper.py`
> was hardened; see its module docstring). Build the scraper with debug logging and treat the
> field/key mapping as best-effort until a live trace confirms it. The Django + frontend layers are
> not blocked by this — their contract is our own `/sci/...` shape.

---

## Layer 1 — FastAPI scraper (`scrapping_codes_ecourt/`)

**New file `scrapping_codes_ecourt/sci_fastapi_scrapper.py`** exposing module-level `app = FastAPI(...)`,
following the conventions in `sc_citation_scraper.py` and the DC scraper:

- **Session:** single module-global `_sci_session = cffi_requests.Session(impersonate="chrome110")`,
  primed by a GET to the SCI home/case-status page (no session pool — one domain).
- **CAPTCHA:** SCI uses a **math** captcha ("7 _ 3" → 7−3). Implement `solve_sci_captcha(session, img_url)`:
  fetch image → read digits (local OCR or reuse the DC scraper's CapSolver `ImageToTextTask` via
  `from ecourts_fastapi_scrapper_cnr_and_causelist_casestatus_and_courtstatus import solve_captcha`,
  the same import trick `sc_citation_scraper.py:109` uses) → subtract. No new required env key
  (CapSolver key already loaded by `main.py`).
- **18 endpoints** per the spec, under this sub-app's own root (main.py strips the `/sci` prefix):
  `GET /health`, `GET /case-types`, `POST /case/by-number|by-diary|by-party|by-aor`,
  `GET /causelist/today|tomorrow` + `POST /causelist/by-date`, `POST /orders/by-case|by-diary`,
  `POST /judgments/by-case|by-party|by-date`, `POST /office-report/by-case|by-diary`,
  `POST /document/pdf`.
- **PDF terminal:** fetch bytes server-side with the same session and return
  `StreamingResponse(io.BytesIO(...), media_type="application/pdf")` — never expose the raw
  session-bound URL (same rule as DC `/case/order-pdf`).
- Add `CORSMiddleware(allow_origins=["*"])` like the siblings (listener is localhost-only).

**Wire into `scrapping_codes_ecourt/main.py`:** add `from sci_fastapi_scrapper import app as sci_app`
(after line 110), `app.mount("/sci", sci_app)` (after line 150), and add an `"sci"` entry to both the
`index()` map (`main.py:160-179`) and the aggregated `health()` gather (`main.py:200-221`). Update the
mount-map table in the module docstring.

**Deps:** if using local OCR, add `pytesseract`+`Pillow` to the `py312` conda env (scraper deps are
installed ad-hoc there, *not* in `requirements.txt`). If CapSolver-only, no new deps. No launch-script
change needed — `start_scrapper.sh` runs the unified `main:app` (dev :8003 / prod :8002).

## Layer 2 — Django proxy (`Legalv1/ecourt_scrapped/`)

- **Env:** append to `Legalv1/legalenv` (after line 62) — and to `legalenv.dev` —
  `SCI_SCRAPER_BASE_URL=http://localhost:8003/sci` (dev) / `:8002` (prod), matching the existing
  `SC_CITATION_SCRAPER_BASE_URL` line format.
- **New `services/sci_scraper_client.py`** — verbatim copy of `services/scraper_client.py`, only
  swapping the env var to `SCI_SCRAPER_BASE_URL` (keep `get/post/post_pdf/health_check`).
- **New `sci_views.py`** — ~18 `@api_view(["GET"|"POST"]) @supabase_required` proxy functions, one per
  endpoint, each validating input then calling `sci_scraper_client.post(...)`/`.get(...)`. Reuse the
  existing helpers `from ecourt_scrapped.views import _parse_body, _error, _scraper_error_response`.
  The PDF view returns `HttpResponse(pdf_bytes, content_type="application/pdf")` (pattern at
  `views.py:321-341`). Optionally cache `case-types` in Django's cache (24h) like `citation_views.py`
  caches results — it's a near-static list.
- **New `sci_urls.py`** — `path(...)`→view map mirroring `urls.py` structure (health, case-types,
  case/*, causelist/*, orders/*, judgments/*, office-report/*, pdf/).
- **Register:** add `path('sci/', include('ecourt_scrapped.sci_urls'))` in
  `ecourt_scrapped/urls.py` next to the `hc/` include (line 59). Yields `/api/ecourts/v2/sci/...`.
- No Django ORM models (the app has none — DC/HC lookups are passthrough); SCI is passthrough too.

## Layer 3 — Frontend (`new_frontend/src/`)

Copy the HC component set in `src/components/ecourt_scrapper/` (Tailwind + `index.css` classes
`input-base`/`btn-primary`/`card`, Material Symbols icons, local `useState`, `uiSlice`
`beginBlocking`/`stopBlocking` overlay — no new redux slice):

- **`apiSCI.js`** — copy `apiHC.js`, `const BASE = 'ecourts/v2/sci'`, one fn per endpoint incl.
  `getSCICaseTypes()`, the 4 case-status searches, 3 cause-list calls, orders/judgments/office-report
  searches, and `downloadSCIPdf(...)` with `responseType:'blob'`.
- **New screens** (copy the matching HC file):
  `SCITerminal.jsx` (hub — copy `HCTerminal.jsx`; module cards for the 5 flows + toggle chips back to
  District/High Court), `SCICaseStatusTerminal.jsx` (4 mode tabs: case-number / diary / party / AOR —
  copy `HCCaseStatusTerminal.jsx`, use a case-type `<select>` populated by `getSCICaseTypes()` instead
  of `LocationCascade`), `SCICauseListTerminal.jsx` (today/tomorrow/by-date), `SCIDailyOrdersTerminal.jsx`,
  `SCIJudgmentsTerminal.jsx`, `SCIOfficeReportsTerminal.jsx`, `SCICaseDetailPage.jsx`. SCI has **no
  location cascade** — case-type dropdown + text fields only.
- **Routes** in `src/AppContent.js`: ~7 `lazy(() => import(...))` imports (after line 58) + a
  `/ecourts/sci/*` `<Route>` block after line 229 (`/ecourts/sci`, `.../case-status`, `.../cause-list`,
  `.../daily-orders`, `.../judgments`, `.../office-reports`, `.../case/:id`).
- **Navigation:** add a `Supreme Court →` toggle chip in `EcourtsTerminal.jsx:138-149` (the same
  flex row that holds the District/High Court chips → `navigate('/ecourts/sci')`), and add the
  reciprocal chip in `HCTerminal.jsx` (~line 96-107). No `Sidebar.jsx` change.

---

## Files at a glance

**New:** `scrapping_codes_ecourt/sci_fastapi_scrapper.py`;
`Legalv1/ecourt_scrapped/{services/sci_scraper_client.py, sci_views.py, sci_urls.py}`;
`new_frontend/src/components/ecourt_scrapper/{apiSCI.js, SCITerminal.jsx, SCICaseStatusTerminal.jsx,
SCICauseListTerminal.jsx, SCIDailyOrdersTerminal.jsx, SCIJudgmentsTerminal.jsx,
SCIOfficeReportsTerminal.jsx, SCICaseDetailPage.jsx}`.

**Edited:** `scrapping_codes_ecourt/main.py` (mount + index/health); `Legalv1/legalenv`(+`legalenv.dev`);
`Legalv1/ecourt_scrapped/urls.py` (include); `new_frontend/src/AppContent.js` (imports+routes);
`new_frontend/src/components/ecourt_scrapper/{EcourtsTerminal.jsx, HCTerminal.jsx}` (toggle chips).

## Verification (end-to-end)

1. **Scraper live-trace first (the risk):** open DevTools on the real SCI site, capture one
   `getCaseStatus` request+response, and reconcile the scraper's payload field names / response keys +
   captcha flow against it before trusting the parser (mirror the `sc_citation_scraper.py` hardening).
2. **Scraper up:** run `start_scrapper.sh` (dev, :8003) → `GET /sci/health`, `/sci/docs` load;
   `GET /sci/case-types` returns the type list (validates session, no captcha); then
   `POST /sci/case/by-number` with a known case validates captcha + parser; `POST /sci/document/pdf`
   streams a PDF.
3. **Django:** `python manage.py check` clean; with an auth cookie hit
   `/api/ecourts/v2/sci/health/` and `/api/ecourts/v2/sci/case-types/` (200 passthrough), and one
   `case/by-number/` POST.
4. **Frontend:** `webpack --config webpack.dev.js` compiles; `npm start`, open `/ecourts` → click
   **Supreme Court →** → run a case-number search end to end, open a judgment/order PDF.
