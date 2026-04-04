# HC Scraper — Status & Freeze Registry

> **HARD RULE:** Any endpoint/function marked ✅ is **frozen**. Do NOT modify the code
> behind it unless explicitly requested. If a supporting function is shared with an
> unfrozen endpoint, create a separate copy for the new endpoint rather than changing
> the existing one.

**File:** `hcecourt_fastapi_complete_scrapper.py`
**Portal:** `https://hcservices.ecourts.gov.in/hcservices/`

---

## Search Endpoints — Status

| # | Endpoint | Handler | Search type / action_code | Status |
|---|----------|---------|---------------------------|--------|
| 1 | `GET /case/cnr/{cino}` | `search_cnr` → `_hc.search_cnr` → `_get_cnr` | `SEARCH_CNR` | ✅ **FROZEN** |
| 2 | `GET /case/detail/{cino}` | `get_case_detail` → `_hc.get_case_detail` | uses `_get_cnr` + `_parse_cnr_html` | ✅ **FROZEN** |
| 3 | `GET /case/party` | `search_party` → `_hc.search_party` | `partywise` | ✅ **FROZEN** |
| 4 | `GET /case/number` | `search_case_number` → `_hc.search_case_number` | `case_no` | 🔲 not tested |
| 5 | `GET /case/advocate` | `search_advocate` → `_hc.search_advocate_name` | `advocate_name` | ✅ **FROZEN** |
| 6 | `GET /case/bar-code` | `search_bar_code` → `_hc.search_bar_code` | `advocate_code` | ✅ **FROZEN** (supports /case/advocate) |
| 7 | `GET /case/filing` | `search_filing` → `_hc.search_filing_number` | `filing_no` | ✅ **FROZEN** |
| 8 | `GET /case/fir` | `search_fir` → `_hc.search_fir` | `FIR_no` | ✅ **FROZEN** |
| 9 | `GET /case/act` | `search_act` → `_hc.search_act` | `act_type` | 💤 **DORMANT** (not included for now, do not remove code) |
| 10 | `GET /case/type` | `search_case_type` → `_hc.search_case_type` | `case_type` | 💤 **DORMANT** (not included for now, do not remove code) |
| 11 | `GET /orders/search` | `search_orders_by_party` → `_hc.search_orders_by_party` | `COpartyName` | ✅ **FROZEN** |
| 12 | `GET /orders/by-court` | `search_orders_by_court` → `_hc.search_orders_by_court` | `court_number` | ✅ **FROZEN** |
| 13 | `GET /orders/by-date` | `search_orders_by_date` → `_hc.search_orders_by_date` | `showRecords` | ✅ **FROZEN** |
| 14 | `GET /orders/{cino}` | `get_orders` → `_hc.get_orders` | uses `_parse_cnr_html` | 💤 **DORMANT** (not included for now, do not remove code) |
| 15 | `GET /causelist` | `get_cause_list` → `_hc.get_cause_list` | cause list API | ✅ **FROZEN** |
| 16 | `GET /meta/police_stations` | `get_police_stations` | metadata | ✅ **FROZEN** (supports /case/fir) |
| 17 | `GET /meta/court_numbers` | `get_court_numbers` | metadata | ✅ **FROZEN** (supports /orders/by-court) |

---

## Frozen Code Map — CNR Search (✅)

The following functions/classes are part of the CNR search pipeline and **must not be modified**:

### 1. `HIGH_COURTS` dict (lines ~130–335)
Static registry of all supported High Courts and their benches.
Each entry has:
- `state_code` — portal state code (e.g. `"9"` for Allahabad, `"16"` for Calcutta)
- `nat_code` — 4-char national court code used in CNR prefix (e.g. `"UPHC"`, `"WBHC"`)
- `name` — display name
- `benches` — dict of bench keys, each with:
  - `dist_code` — portal bench/dist code (string integer, e.g. `"1"`, `"2"`)
  - `label` — display label (e.g. `"Principal Bench"`, `"Circuit Bench At Jalpaiguri"`)
  - `cnr_prefix` *(optional)* — override prefix string or list of strings when
    the portal-assigned prefix differs from `nat_code + dist_code.zfill(2)`

**Verified bench data corrections applied:**

| HC | Correction |
|----|-----------|
| Calcutta | `state_code "28" → "16"`, all 4 benches with correct dist_codes |
| Calcutta / Jalpaiguri | `cnr_prefix: "WBCHCJ"` |
| Calcutta / Port Blair | `cnr_prefix: ["WBCHCO", "WBCHCP"]` (dual prefix) |
| Bombay | All 7 benches: 1=Appellate, 2=Original, 3=Aurangabad, 4=Nagpur, 5=Goa, 6=TORTS, 7=Kolhapur |
| Rajasthan | Swapped: 1=Jaipur, 2=Jodhpur |
| Madhya Pradesh | Swapped: 1=Jabalpur, 2=Indore, 3=Gwalior |
| Jammu & Kashmir | Swapped: 1=Jammu, 2=Srinagar |

---

### 2. `_build_cnr_map()` (line ~345)
Builds `CNR_PREFIX_MAP: dict[str, dict]` at startup — maps 6-char CNR prefix → `{hc_key, bench_key, hc_meta, bench_meta}`.

Supports `cnr_prefix` as **string or list**. Each prefix gets its own map entry independently.

---

### 3. `resolve_cnr(cino)` (line ~368)
Thin wrapper: slices `cino[:6]`, looks up `CNR_PREFIX_MAP`, raises `422` if not found.

---

### 4. `_get_cnr(cino, hc, bench)` — inside `HCSession` (line ~1318)
POST to `cases_qry/index_qry.php` with:
```
state_code, dist_code, court_code=dist_code,
caseStatusSearchType=SEARCH_CNR ("cino"),
cino, national_court_code=cino[:6]
```
Returns raw `HCCaseItem` list (usually 1 item).

---

### 5. `_parse_cnr_html(html, cino, hc_key, bench_key)` (line ~905)
Full HTML parser for `o_civil_case_history.php` response.

Sections parsed (in order):

| # | HTML element | Fields populated |
|---|-------------|-----------------|
| 1 | `table.case_details_table` | `filing_no`, `reg_no`, `filing_date`, `reg_date` |
| 2 | `table.table_r` | `next_hearing`, `first_hearing`, `stage_of_case`, `coram`, `judicial_branch`, `bench_type`, `state`, `district`, `not_before_me` |
| 3 | `span.Petitioner_Advocate_table` | `petitioner`, `petitioner_advocate` |
| 4 | `span.Respondent_Advocate_table` | `respondent`, `respondent_advocate` |
| 5 | `table#subject_table` | `subject` (category) |
| 6 | Derive from reg_no | `case_type`, `case_no`, `year` (regex supports `W.P.(C)` format) |
| 7 | Status derivation | `status` (Pending / Disposed) |
| 8 | `table.history_table` | `hearing_history` list of `CaseDetailHearing` |
| 9 | Acts table (`id=act_table` / `class=Acts_table`) | `acts` list |
| 10 | `span.Lower_court_table` | `subordinate_court` (`SubordinateCourt` model) |
| 11 | `table.linkedCase` | `linked_cases` list of `LinkedCase` |
| 12 | `table.IAheading` | `ia_details` list of `IADetail` |
| 13 | `table.order_table` | `orders` list of `CaseDetailOrder` |
| 14 | Max-date of history + orders | `last_hearing` |

---

### 6. Data Models (all frozen as part of CNR pipeline)

| Model | Purpose |
|-------|---------|
| `HCCaseDetail` | Full case detail response model |
| `CaseDetailHearing` | Single row from history_table |
| `CaseDetailOrder` | Single row from order_table — includes `judge`, `document_url` |
| `SubordinateCourt` | Lower court details |
| `IADetail` | IA (Interlocutory Application) row |
| `LinkedCase` | Row from linkedCase table — `filing_number`, `case_number`, `is_main`, `status` |

---

### 7. Session / HTTP flow (frozen — shared with other endpoints)

```
GET main.php?t=<ms>          → sets PHPSESSID cookie
GET securimage_show.php?<rnd> → captcha image bytes
Capsolver → captcha text
POST cases_qry/index_qry.php → search result JSON  (base_params + search params)
GET  cases_qry/o_civil_case_history.php?cino=...  → case detail HTML
```

`HCSession.base_params()` always includes:
```
court_code, state_code, court_complex_code, captcha, appFlag=web
```

Cookie jar iterated via `client.cookies.jar` (`c.name` / `c.value`) to extract PHPSESSID for logging.

---

### 8. Known tricky portals quirks (do not "fix" these — they're intentional)

- `appFlag=web` must be sent — portal behaves differently without it
- `court_code` and `court_complex_code` are both set to `bench["dist_code"]` (not `"1"`)
- `national_court_code` is `cino[:6]` — NOT derived from `nat_code + dist_code`; this is the only correct approach for multi-prefix benches
- `con` response field can be `"No Record(s) Found"` (string) — always check `startswith("[")` before JSON parsing
- `history_table` `<a>` tags inside cells must be replaced with their text (lxml parse artefact)
- Advocate parsing has two formats:
  - Standard: `"Advocate- NAME"` label inside span
  - Delhi HC / some benches: next `&nbsp;&nbsp;&nbsp;&nbsp;` indented line after party name

---

## Potentially wrong (not yet verified)

- `meghalaya` has `state_code: "16"` — same as Calcutta, likely wrong; not tested yet
- Any other HC state_codes not yet hit live

---

## Changelog

| Date | What changed |
|------|-------------|
| Session 1–2 | Initial scraper, session flow, captcha, all search endpoints skeleton |
| Session 3 | `action_code="showRecords"` fixed in `search_orders_by_date` |
| Session 3 | `bench["label"]` fix in `get_cause_list` (was `bench["name"]`) |
| Session 3 | Cookie jar iteration for PHPSESSID logging |
| Session 3 | `con` JSON robustness: `startswith("[")` check |
| Session 3 | Calcutta state_code `"28"` → `"16"`, all bench dist_codes corrected |
| Session 3 | `cnr_prefix` support for Jalpaiguri (`"WBCHCJ"`) |
| Session 3 | `cnr_prefix` list support + Port Blair dual prefixes `["WBCHCO","WBCHCP"]` |
| Session 3 | `_build_cnr_map` now handles string or list `cnr_prefix` |
| Session 3 | `court_code` in `_get_cnr` → `bench["dist_code"]` (was hardcoded `"1"`) |
| Session 3 | `national_court_code` → `cino[:6]` (most correct for all benches) |
| Session 3 | `case_type` regex `[A-Z0-9]+` → `.+?` (handles `W.P.(C)`) |
| Session 3 | Advocate parsing: Delhi HC indent fallback |
| Session 3 | Orders table parser (`order_table` class), `judge` field added |
| Session 3 | `last_hearing` from max of history + order dates |
| Session 3 | `next_hearing`/`first_hearing` cleaned via `_clean_date_val()` |
| Session 3 | Acts table parser (finds "Under Act(s)" header) |
| Session 3 | `SubordinateCourt`, `IADetail` models + parsers |
| Session 3 | `HCCaseDetail` + `filing_date`, `bench_type`, `judicial_branch`, `state`, `district`, `not_before_me`, `subordinate_court`, `ia_details` |
| Session 3 | Bombay all 7 benches corrected |
| Session 3 | Rajasthan/MP/J&K bench codes corrected (were swapped) |
| Session 3 | Double-space normalization in party/advocate names |
| Session 4 | `LinkedCase` model + `linked_cases` field + `table.linkedCase` parser (sections renumbered: was 11=IA, now 11=Linked, 12=IA) |
| Session 5 | `GET /case/party` confirmed working in live test — frozen |
| Session 6 | `GET /case/advocate`, `GET /case/bar-code`, `GET /case/filing`, `GET /case/fir`, `GET /meta/police_stations` confirmed working — frozen |
| Session 6 | `GET /case/act` and `GET /case/type` marked 💤 DORMANT — code kept, not exposed for now |
| Session 7 | `GET /orders/search`, `GET /orders/by-court`, `GET /orders/by-date`, `GET /meta/court_numbers` confirmed working — frozen |
| Session 7 | `GET /orders/{cino}` marked 💤 DORMANT — code kept, not exposed for now |
| Session 8 | `GET /causelist` confirmed working — frozen |
| Session 9 | Full API Reference section added to this doc |

---

## API Reference — Active / Frozen Endpoints

> **Base URL:** `http://<host>:8001`
> All parameters are query-string unless noted as path parameter `{param}`.
> `hc` and `bench` keys are lowercase snake_case (e.g. `allahabad`, `calcutta`, `port_blair`).
> Use `GET /courts` to enumerate all valid `hc` / `bench` key pairs.

---

### `GET /courts`
Returns all supported High Courts and their bench keys.

**No parameters.**

**Response** — JSON object keyed by HC slug:
```json
{
  "allahabad": {
    "name": "Allahabad High Court",
    "benches": {
      "allahabad": "Principal Bench",
      "lucknow":   "Lucknow Bench"
    }
  },
  ...
}
```

---

### `GET /health`
Portal reachability check.

**No parameters.**

**Response:**
```json
{ "status": "ok", "portal": "https://hcservices.ecourts.gov.in/hcservices/" }
```

---

### `GET /case/cnr/{cino}` ✅
Full case detail from a CNR number. HC and bench are auto-detected from the CNR prefix — no hc/bench params needed.

**Path parameter:**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `cino` | string | ✅ | 16-char CNR e.g. `UPHC010551112017`, `WBCHCP0001102020` |

**Response** — `HCCaseDetail`:
```json
{
  "cino":               "WBCHCP0001102020",
  "high_court":         "Calcutta High Court",
  "bench":              "Circuit Bench At Port Blair",
  "case_type_name":     "CPAN",
  "case_no":            "12",
  "case_year":          2020,
  "filing_date":        "21-09-2020",
  "petitioner":         "GAUTAM HALDER",
  "respondent":         "SUNIL KUMAR SINGH",
  "extra_party":        null,
  "date_of_decision":   null,
  "status":             "Pending",
  "registration_date":  "21-09-2020",
  "next_hearing":       "06-03-2026",
  "last_hearing":       "20-02-2026",
  "stage_of_case":      "APPLICATION",
  "coram":              "HON'BLE JUSTICE JAY SENGUPTA , HON'BLE JUSTICE MD. SHABBAR RASHIDI",
  "bench_type":         null,
  "judicial_branch":    "Judicial Section",
  "state":              null,
  "district":           null,
  "not_before_me":      null,
  "subject":            "GROUP A (WRIT MATTERS) ( 1 )",
  "acts":               ["Contempt of Courts Act ,1971"],
  "subordinate_court":  null,
  "ia_details":         [],
  "linked_cases": [
    { "filing_number": "CPAN/12/2020", "case_number": "CPAN/12/2020", "is_main": true,  "status": null },
    { "filing_number": "MA/23/2019",   "case_number": "MA/23/2019",   "is_main": false, "status": "Disposed" }
  ],
  "hearing_history": [
    { "date": "31-01-2025", "judge": "HON'BLE JUSTICE JAY SENGUPTA ...", "purpose": "APPLICATION", "next_date": null }
  ],
  "orders": [
    { "date": "31-01-2025", "order_number": "1", "judge": "HON'BLE JUSTICE JAY SENGUPTA,...", "document_url": "https://hcservices.ecourts.gov.in/..." }
  ],
  "petitioner_advocate": "GOPALA BINNU KUMAR",
  "respondent_advocate": null,
  "data_source":  "hcservices.ecourts.gov.in",
  "fetched_at":   "2026-04-03T10:00:00"
}
```

---

### `GET /case/detail/{cino}` ✅
Identical response to `/case/cnr/{cino}`. Same path param, same `HCCaseDetail` response. (Different internal route — kept for backwards compatibility.)

---

### `GET /case/party` ✅
Search cases by petitioner or respondent name.

**Query parameters:**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `hc` | string | ✅ | e.g. `allahabad` |
| `bench` | string | ✅ | e.g. `allahabad` |
| `name` | string | ✅ | min 3 chars, partial match OK |
| `year` | string | ✅ | 4-digit registration year e.g. `2017` |
| `status` | string | ❌ | `Pending` / `Disposed` / `Both` (default: `Both`) |

**Response** — `SearchResponse`:
```json
{
  "query_type": "party_name",
  "high_court": "Allahabad High Court",
  "bench":      "Principal Bench",
  "total":      12,
  "page":       1,
  "cases": [
    {
      "cino":               "UPHC010551112017",
      "case_no":            "588952",
      "case_type_code":     92,
      "case_type_name":     "WPIL",
      "case_year":          2017,
      "petitioner":         "PANKAJ KUMAR",
      "respondent":         "STATE OF U.P.",
      "extra_party":        null,
      "date_of_decision":   null,
      "status":             "Pending",
      "order_url_path":     null,
      "detail_url":         "/case/cnr/UPHC010551112017",
      "petitioner_advocate": null,
      "respondent_advocate": null
    }
  ],
  "fetched_at": "2026-04-03T10:00:00"
}
```

---

### `GET /case/advocate` ✅
Search cases by advocate name (min 3 chars).

**Query parameters:**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `hc` | string | ✅ | |
| `bench` | string | ✅ | |
| `query` | string | ✅ | Advocate name, min 3 chars e.g. `sharma` |
| `status` | string | ❌ | `Pending` / `Disposed` / `Both` (default: `Both`) |

**Response** — `SearchResponse` (same structure as `/case/party`).

---

### `GET /case/bar-code` ✅
Search cases by advocate bar registration number (exact match).

**Query parameters:**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `hc` | string | ✅ | |
| `bench` | string | ✅ | |
| `bar_code` | string | ✅ | e.g. `UP12345`, `MH/1234/2005` |
| `status` | string | ❌ | `Pending` / `Disposed` / `Both` (default: `Both`) |

**Response** — `SearchResponse`.

---

### `GET /case/filing` ✅
Search cases by filing / diary number.

**Query parameters:**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `hc` | string | ✅ | |
| `bench` | string | ✅ | |
| `filing_number` | string | ✅ | e.g. `32226` |
| `year` | string | ✅ | 4-digit year |
| `case_type` | string | ❌ | Case type code or abbreviation (default: `""` = all) |

**Response** — `SearchResponse`.

---

### `GET /case/fir` ✅
Search criminal cases by FIR number.

**Query parameters:**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `hc` | string | ✅ | |
| `bench` | string | ✅ | |
| `police_station` | string | ✅ | Code from `GET /meta/police_stations` |
| `status` | string | ✅ | `Pending` / `Disposed` / `Both` |
| `fir_number` | string | ❌ | FIR number (default: `""`) |
| `year` | string | ❌ | FIR year (default: `""`) |

**Response** — `SearchResponse`.

---

### `GET /meta/police_stations` ✅
Police station list — use before calling `/case/fir`.

**Query parameters:**
| Param | Type | Required |
|-------|------|----------|
| `hc` | string | ✅ |
| `bench` | string | ✅ |

**Response** — `list[PoliceStation]`:
```json
[
  { "code": "4890602", "name": "KOTWALI" },
  { "code": "4890603", "name": "CIVIL LINES" }
]
```

---

### `GET /meta/court_numbers` ✅
Judge / court number list — use before calling `/orders/by-court`.

**Query parameters:**
| Param | Type | Required |
|-------|------|----------|
| `hc` | string | ✅ |
| `bench` | string | ✅ |

**Response** — `list[CourtJudge]`:
```json
[
  {
    "court_code":  "1007",
    "judge_name":  "HON'BLE JUSTICE ARINDAM MUKHERJEE",
    "designation": "JUSTICE",
    "date_from":   "2023-01-10",
    "date_to":     "2026-04-01",
    "bench_label": null
  }
]
```

---

### `GET /orders/search` ✅
Search court orders / judgements by party name — returns PDF URLs.

**Query parameters:**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `hc` | string | ✅ | |
| `bench` | string | ✅ | |
| `name` | string | ✅ | Party name (petitioner or respondent) |
| `year` | string | ❌ | Registration year (default: all years) |

**Response** — `OrderSearchResponse`:
```json
{
  "query_type": "orders_party_name",
  "high_court": "Allahabad High Court",
  "bench":      "Principal Bench",
  "total":      5,
  "orders": [
    {
      "cino":          "UPHC010551112017",
      "case_no":       "588952",
      "case_type_name": "WPIL",
      "reg_year":      2017,
      "reg_no":        1,
      "order_no":      1,
      "order_date":    "2021-03-15",
      "document_name": "Judgement/Order",
      "pdf_url":       "https://hcservices.ecourts.gov.in/hcservices/cases/display_pdf.php?filename=...",
      "detail_url":    "/case/cnr/UPHC010551112017"
    }
  ],
  "fetched_at": "2026-04-03T10:00:00"
}
```

---

### `GET /orders/by-court` ✅
Search court orders by court/judge number and date range.

**Query parameters:**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `hc` | string | ✅ | |
| `bench` | string | ✅ | |
| `judge_code` | string | ✅ | `court_code` from `GET /meta/court_numbers` |
| `date_from` | string | ✅ | Format: `YYYY-MM-DD` |
| `date_to` | string | ✅ | Format: `YYYY-MM-DD` |

**Response** — `OrderSearchResponse` (same structure as `/orders/search`).

---

### `GET /orders/by-date` ✅
Search all court orders issued in a date range.

**Query parameters:**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `hc` | string | ✅ | |
| `bench` | string | ✅ | |
| `date_from` | string | ✅ | Format: `DD-MM-YYYY` (⚠️ different from `/orders/by-court`) |
| `date_to` | string | ✅ | Format: `DD-MM-YYYY` |

**Response** — `OrderSearchResponse`.

---

### `GET /causelist` ✅
Daily bench cause list with PDF links.

**Query parameters:**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `hc` | string | ✅ | |
| `bench` | string | ✅ | |
| `list_date` | string | ❌ | Format: `DD-MM-YYYY`. Defaults to today. |

**Response** — `CauseListResponse`:
```json
{
  "high_court":   "Allahabad High Court",
  "bench":        "Principal Bench",
  "date":         "03-04-2026",
  "total_items":  42,
  "items": [
    {
      "serial":    "1",
      "bench":     "HON'BLE JUSTICE ARINDAM MUKHERJEE",
      "list_type": "Daily List",
      "pdf_url":   "https://hcservices.ecourts.gov.in/..."
    }
  ],
  "fetched_at": "2026-04-03T10:00:00"
}
```

---

## Date Format Summary

| Endpoint | Date param format |
|----------|-------------------|
| `/orders/by-court` `date_from` / `date_to` | `YYYY-MM-DD` |
| `/orders/by-date` `date_from` / `date_to` | `DD-MM-YYYY` |
| `/causelist` `list_date` | `DD-MM-YYYY` |
| All response date fields (`next_hearing`, `last_hearing`, order dates, etc.) | `DD-MM-YYYY` |
| `fetched_at` | ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SS`) |

---

## Error Responses

All endpoints return standard HTTP error codes:

| Code | Meaning |
|------|---------|
| `422 Unprocessable Entity` | Invalid CNR prefix / missing required param |
| `400 Bad Request` | HC or bench key not found |
| `503 Service Unavailable` | Portal unreachable or captcha failure after retries |
| `500 Internal Server Error` | Unexpected parse error |

Error body:
```json
{ "detail": "Unrecognised CNR prefix 'XYZAB1'" }
```
