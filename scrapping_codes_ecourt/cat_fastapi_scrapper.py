"""
Central Administrative Tribunal (CAT) — Unified FastAPI Scraper
All 19 benches covered via single CIS system: cis.cgat.gov.in/catlive/

Mounted inside the unified scraper process (see main.py) at the /cat prefix —
this module is not run standalone. Its own routes below are root-relative
(e.g. "/benches", "/case/by-number") because Starlette strips the "/cat"
mount prefix before dispatching to this sub-app; externally they resolve to
/cat/benches, /cat/case/by-number, etc.

Swagger UI (mounted): http://localhost:8003/cat/docs

Endpoints:
  GET  /benches                    → list of all 19 benches with codes
  GET  /case-types                 → OA, MA, TA, RA, CP, CCP, PT (static)

  Case Status (4 search modes)
  POST /case/by-number             → by bench + case_type + case_no + year
  POST /case/by-diary              → by bench + diary_no + year
  POST /case/by-party              → by bench + party_name + party_type
  POST /case/by-advocate           → by bench + advocate_name + advocate_type

  Cause List
  POST /causelist                  → cause list for bench + date (dd-mm-yyyy)

  Orders
  POST /orders/daily               → daily orders for bench + date
  POST /orders/final               → oral/final orders by bench + case

  Judgments
  POST /judgments/search           → full-text judgment search (catjudgements.nic.in)

Key differences from district eCourts / SCI:
  - NO CAPTCHA on any public page
  - NO session pool — fresh session per bench request (make_session() is
    called at the top of every endpoint handler, not cached)
  - Bench selection via base64-encoded numeric ID (hardcoded below)
  - Cause list URL: base64(YYYY-MM-DD#bench_slug) pattern
  - PHP backend, not JSON API — responses are HTML pages, parsed with BeautifulSoup
  - Case identifier: bench + case_type + case_no + year (no CNR)
  - PDF links returned inline are direct/stable URLs — no streaming proxy needed

Field-name caveat: the PHP form field names below (selCaseType, txtCaseNo,
txtDiaryNo, ...) are based on the visible HTML form structure and are
unverified against a live network trace. Confirm against the real portal
before trusting parser output in production (same posture as sc_citation_scraper.py
and sci_fastapi_scrapper.py were hardened/flagged).
"""

import base64
from datetime import date as dt

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
CAT_BASE      = "https://cis.cgat.gov.in/catlive"
CAT_HOME_URL  = f"{CAT_BASE}/case_status.php"
JUDGMENT_BASE = "https://catjudgements.nic.in"
IMPERSONATE   = "chrome110"

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}
FORM_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": CAT_HOME_URL,
    "Origin": "https://cis.cgat.gov.in",
}

# ─────────────────────────────────────────────────────────────────────────────
# BENCH REGISTRY — Confirmed from live page JS (popsurety_detailreport1 calls)
# bench_code = base64.b64decode(js_arg) decoded to numeric string
# bench_slug = lowercase bench name used in causelist URL construction
# ─────────────────────────────────────────────────────────────────────────────
CAT_BENCHES = [
    {"name": "Delhi (Principal)",  "code": "100", "slug": "delhi"},
    {"name": "Ahmedabad",          "code": "120", "slug": "ahmedabad"},
    {"name": "Allahabad",          "code": "330", "slug": "allahabad"},
    {"name": "Bangalore",          "code": "103", "slug": "bangalore"},
    {"name": "Chandigarh",         "code": "60",  "slug": "chandigarh"},
    {"name": "Chennai",            "code": "310", "slug": "chennai"},
    {"name": "Cuttack",            "code": "260", "slug": "cuttack"},
    {"name": "Ernakulam",          "code": "180", "slug": "ernakulam"},
    {"name": "Guwahati",           "code": "40",  "slug": "guwahati"},
    {"name": "Hyderabad",          "code": "21",  "slug": "hyderabad"},
    {"name": "Jabalpur",           "code": "200", "slug": "jabalpur"},
    {"name": "Jaipur",             "code": "291", "slug": "jaipur"},
    {"name": "Jammu",              "code": "117", "slug": "jammu"},
    {"name": "Jodhpur",            "code": "111", "slug": "jodhpur"},
    {"name": "Kolkata",            "code": "350", "slug": "kolkata"},
    {"name": "Lucknow",            "code": "332", "slug": "lucknow"},
    {"name": "Mumbai",             "code": "210", "slug": "mumbai"},
    {"name": "Patna",              "code": "116", "slug": "patna"},
    {"name": "Srinagar",           "code": "119", "slug": "srinagar"},
]

_bench_by_slug = {b["slug"]: b for b in CAT_BENCHES}

# ─────────────────────────────────────────────────────────────────────────────
# CASE TYPES — Static, from live dropdown
# ─────────────────────────────────────────────────────────────────────────────
CAT_CASE_TYPES = [
    {"code": "OA",  "name": "Original Application"},          # Most common
    {"code": "TA",  "name": "Transfer Application"},
    {"code": "MA",  "name": "Misc Application"},
    {"code": "CP",  "name": "Contempt Petition"},
    {"code": "PT",  "name": "Petition for Transfer"},
    {"code": "RA",  "name": "Review Application"},
    {"code": "CCP", "name": "Criminal Contempt Petition"},
    {"code": "OAO", "name": "OA Objection"},
]


# ─────────────────────────────────────────────────────────────────────────────
# SESSION — No pool needed; CAT has no per-page cookie dependency
# ─────────────────────────────────────────────────────────────────────────────
def make_session(bench_code: str) -> cffi_requests.Session:
    """
    Create a fresh session scoped to a specific CAT bench.
    The bench is activated by calling the bench-select URL which
    sets a server-side session cookie binding requests to that bench.
    """
    s = cffi_requests.Session(impersonate=IMPERSONATE)
    s.get(CAT_HOME_URL, headers=BASE_HEADERS, timeout=20)
    # Activate the bench — the JS call popsurety_detailreport1('MTAw')
    # passes the base64-encoded bench_code to a server-side handler
    bench_b64 = base64.b64encode(bench_code.encode()).decode()
    s.get(
        f"{CAT_BASE}/misdetailreport123.php?no={bench_b64}",
        headers=BASE_HEADERS, timeout=20
    )
    return s


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def clean(el) -> str:
    return el.get_text(" ", strip=True) if el else ""

def get_bench(bench_slug: str) -> dict:
    bench = _bench_by_slug.get(bench_slug.lower())
    if not bench:
        valid = [b["slug"] for b in CAT_BENCHES]
        raise HTTPException(400, f"Unknown bench '{bench_slug}'. Valid: {valid}")
    return bench

def causelist_filing_no(date_str: str, bench_slug: str) -> str:
    """
    Build the base64-encoded filing_no for the causelist URL.
    Pattern confirmed from live URLs:
      filing_no = base64("YYYY-MM-DD#bench_slug")
    date_str: "dd-mm-yyyy" — converted to "YYYY-MM-DD" internally
    """
    d, m, y = date_str.split("-")
    iso_date = f"{y}-{m}-{d}"
    raw = f"{iso_date}#{bench_slug}"
    return base64.b64encode(raw.encode()).decode()

def parse_case_status_html(html: str) -> dict:
    """
    Parse the CAT case status HTML page into structured data.
    CAT uses PHP-generated HTML tables — no JSON API.
    """
    soup = BeautifulSoup(html, "html.parser")
    out: dict = {"success": False}

    body_text = soup.get_text(" ", strip=True).lower()
    if any(k in body_text for k in ["no record", "not found", "please select bench",
                                     "invalid", "no case"]):
        out["error"] = "No case found or bench not selected."
        return out

    tables = soup.find_all("table")
    if not tables:
        out["error"] = "No table in response — unexpected HTML structure."
        out["raw_text"] = body_text[:500]
        return out

    details: dict = {}
    hearings: list = []
    orders: list = []

    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue

        headers = [clean(c) for c in rows[0].find_all(["th", "td"])]
        header_str = " ".join(headers).lower()

        if "case no" in header_str or "case type" in header_str or "filing" in header_str:
            for row in rows[1:]:
                cells = row.find_all("td")
                for i in range(0, len(cells) - 1, 2):
                    k = clean(cells[i]).rstrip(":")
                    v = clean(cells[i + 1])
                    if k and len(k) < 80:
                        details[k] = v

        elif "date of hearing" in header_str or "next date" in header_str or "purpose" in header_str:
            for row in rows[1:]:
                cells = row.find_all("td")
                if not cells:
                    continue
                entry = {}
                for i, cell in enumerate(cells):
                    col = headers[i] if i < len(headers) else f"col_{i}"
                    entry[col] = clean(cell)
                    a = cell.find("a", href=True)
                    if a and (".pdf" in a["href"].lower() or "order" in a["href"].lower()):
                        entry["order_pdf_url"] = (
                            a["href"] if a["href"].startswith("http")
                            else f"{CAT_BASE}/{a['href'].lstrip('/')}"
                        )
                if any(v for v in entry.values() if v):
                    hearings.append(entry)

        elif "order" in header_str or "judgment" in header_str:
            for row in rows[1:]:
                cells = row.find_all("td")
                if not cells:
                    continue
                entry = {}
                for i, cell in enumerate(cells):
                    col = headers[i] if i < len(headers) else f"col_{i}"
                    entry[col] = clean(cell)
                    a = cell.find("a", href=True)
                    if a:
                        href = a["href"]
                        entry["pdf_url"] = (
                            href if href.startswith("http")
                            else f"{CAT_BASE}/{href.lstrip('/')}"
                        )
                if any(v for v in entry.values() if v):
                    orders.append(entry)

    if details:
        out["case_details"] = details
    if hearings:
        out["case_history"] = hearings
    if orders:
        out["orders"] = orders

    out["success"] = True
    return out


def parse_causelist_html(html: str, bench_name: str, date: str) -> dict:
    """Parse the CAT cause list HTML into structured bench/case data."""
    soup = BeautifulSoup(html, "html.parser")
    result = {
        "success": True,
        "bench": bench_name,
        "date": date,
        "total_cases": 0,
    }

    current_court = ""
    all_cases = []

    for element in soup.find_all(["h3", "h4", "b", "strong", "tr"]):
        text = clean(element).strip()
        if any(kw in text.upper() for kw in ["HON'BLE", "MEMBER", "COURT NO", "BENCH"]):
            if len(text) > 10:
                current_court = text

        if element.name == "tr":
            cells = element.find_all("td")
            if len(cells) >= 3:
                entry = {
                    "court": current_court,
                    "sr_no": clean(cells[0]),
                    "case_number": clean(cells[1]),
                    "parties": clean(cells[2]) if len(cells) > 2 else "",
                    "purpose": clean(cells[3]) if len(cells) > 3 else "",
                    "advocate": clean(cells[4]) if len(cells) > 4 else "",
                }
                if entry["case_number"] and entry["case_number"].lower() not in (
                        "sl no", "case no", "s.no", "sno"):
                    all_cases.append(entry)

    result["cases"] = all_cases
    result["total_cases"] = len(all_cases)

    pdf_links = [
        a["href"] for a in soup.find_all("a", href=True)
        if ".pdf" in a["href"].lower()
    ]
    if pdf_links:
        result["pdf_url"] = pdf_links[0] if pdf_links[0].startswith("http") \
            else f"{CAT_BASE}/{pdf_links[0].lstrip('/')}"

    return result


def parse_order_list_html(html: str) -> list:
    """Parse daily order or final order list HTML."""
    soup = BeautifulSoup(html, "html.parser")
    orders = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [clean(c) for c in rows[0].find_all(["th", "td"])]
        for row in rows[1:]:
            cells = row.find_all("td")
            if not cells:
                continue
            entry: dict = {}
            for i, cell in enumerate(cells):
                col = headers[i] if i < len(headers) else f"col_{i}"
                entry[col] = clean(cell)
                a = cell.find("a", href=True)
                if a:
                    href = a["href"]
                    entry["pdf_url"] = (
                        href if href.startswith("http")
                        else f"{CAT_BASE}/{href.lstrip('/')}"
                    )
            if any(v for v in entry.values() if v):
                orders.append(entry)
    return orders


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CAT India — Central Administrative Tribunal API",
    description="""
# Central Administrative Tribunal (CAT) — Unified API

Covers all 19 CAT benches via the single CIS system at `cis.cgat.gov.in/catlive/`.

**No CAPTCHA** — public pages are open access.

---

## Key Differences from District eCourts / SCI

| Aspect | District eCourts | SCI | CAT |
|---|---|---|---|
| Location hierarchy | State→District→Complex→Est→Court | None | **Bench only (1 step)** |
| Case identifier | `cino` (16-char CNR) | diary/case + year | `bench + case_type + case_no + year` |
| CAPTCHA | Yes (CapSolver) | Math (local OCR) | **No CAPTCHA** |
| Backend | AJAX JSON API | JSON API | **PHP form POST → HTML** |
| Sessions | Pool per home URL | Single shared session | **Fresh session per bench request** |
| PDF delivery | Encrypted token → stream | Session-bound → stream | **Direct URL in response** |

---

## Flow A — Case Status Search

```
GET /benches              → pick bench_slug (e.g. "delhi")
GET /case-types           → pick case_type (e.g. "OA")
POST /case/by-number      → { bench, case_type, case_no, year }
POST /case/by-diary       → { bench, diary_no, year }
POST /case/by-party       → { bench, party_name, party_type }
POST /case/by-advocate    → { bench, advocate_name, advocate_type }
```

---

## Flow B — Cause List

```
GET  /benches             → pick bench_slug
POST /causelist           → { bench, date }   date: dd-mm-yyyy
```

---

## Flow C — Orders

```
POST /orders/daily        → { bench, date }
POST /orders/final        → { bench, case_type, case_no, year }
```

---

## Flow D — Judgments

```
POST /judgments/search    → { bench, query, from_year, to_year }
```
""",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


# ── Pydantic Models ──────────────────────────────────────────────────────────

class CATCaseByNumberRequest(BaseModel):
    bench:      str = Field(..., example="delhi",
                            description="bench_slug from GET /benches (e.g. 'delhi', 'mumbai')")
    case_type:  str = Field(..., example="OA",
                            description="Case type from GET /case-types (OA, MA, TA, RA, CP...)")
    case_no:    str = Field(..., example="1265",
                            description="Case number only (no prefix, no year)")
    year:       str = Field(..., example="2024", description="4-digit year")


class CATCaseByDiaryRequest(BaseModel):
    bench:      str = Field(..., example="delhi")
    diary_no:   str = Field(..., example="123456")
    year:       str = Field(..., example="2024")


class CATCaseByPartyRequest(BaseModel):
    bench:       str = Field(..., example="delhi")
    party_name:  str = Field(..., example="Ram Kumar Singh",
                             description="Partial match supported")
    party_type:  str = Field("Both", example="Both",
                             description="'Both', 'Petitioner', or 'Respondent'")


class CATCaseByAdvocateRequest(BaseModel):
    bench:          str = Field(..., example="delhi")
    advocate_name:  str = Field(..., example="Sharma",
                                description="Partial match supported")
    advocate_type:  str = Field("Petitioner", example="Petitioner",
                                description="'Petitioner' or 'Respondent'")


class CATCauseListRequest(BaseModel):
    bench:  str = Field(..., example="delhi",
                        description="bench_slug from GET /benches")
    date:   str = Field(..., example="04-04-2026",
                        description="Date in dd-mm-yyyy format")


class CATOrdersDailyRequest(BaseModel):
    bench:  str = Field(..., example="delhi")
    date:   str = Field(..., example="04-04-2026", description="dd-mm-yyyy")


class CATOrdersFinalRequest(BaseModel):
    bench:      str = Field(..., example="delhi")
    case_type:  str = Field(..., example="OA")
    case_no:    str = Field(..., example="1265")
    year:       str = Field(..., example="2024")


class CATJudgmentSearchRequest(BaseModel):
    bench:      str = Field("delhi", example="delhi",
                            description="bench_slug or 'all' for all benches")
    query:      str = Field(..., example="departmental promotion",
                            description="Keywords to search in judgment text")
    from_year:  str = Field("2020", example="2020")
    to_year:    str = Field("", example="2026",
                            description="Leave empty for current year")


# ── System ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "tribunal": "CAT", "benches": len(CAT_BENCHES)}


# ── Reference Data ───────────────────────────────────────────────────────────

@app.get("/benches", tags=["Reference"],
         summary="Get all 19 CAT benches with slug codes",
         description="Static list — cache for 24h. Use `slug` as `bench` param in all other endpoints.")
def cat_benches():
    return CAT_BENCHES


@app.get("/case-types", tags=["Reference"],
         summary="Get all CAT case types",
         description="Static. OA (Original Application) is the most common.")
def cat_case_types():
    return CAT_CASE_TYPES


# ── Case Status ──────────────────────────────────────────────────────────────

@app.post("/case/by-number", tags=["Case Status"],
          summary="Search case by case type, number, and year",
          description="""
**Most common search mode.** Requires bench + case_type + case_no + year.

Case number format: `OA-1265/2024` → pass `case_type="OA"`, `case_no="1265"`, `year="2024"`.

No CAPTCHA. Returns case details, hearing history, and any available order PDF links.
""")
def cat_case_by_number(body: CATCaseByNumberRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])

    payload = {
        "selCaseType": body.case_type.upper(),   # OA, MA, TA, RA, CP, CCP, PT
        "txtCaseNo":   body.case_no,
        "txtCaseYear": body.year,
        "Submit":      "Get Status",
    }

    r = session.post(
        f"{CAT_BASE}/case_status.php",
        data=payload,
        headers=FORM_HEADERS,
        timeout=30,
    )
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")

    result = parse_case_status_html(r.text)
    result["bench"]     = bench["name"]
    result["case_type"] = body.case_type.upper()
    result["case_no"]   = body.case_no
    result["year"]      = body.year
    return result


@app.post("/case/by-diary", tags=["Case Status"],
          summary="Search case by diary number and year",
          description="Use when case is newly filed and not yet registered. Diary number is assigned at filing.")
def cat_case_by_diary(body: CATCaseByDiaryRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])

    payload = {
        "txtDiaryNo":   body.diary_no,
        "txtDiaryYear": body.year,
        "Submit":       "Get Status",
    }

    r = session.post(
        f"{CAT_BASE}/case_status.php",
        data=payload,
        headers=FORM_HEADERS,
        timeout=30,
    )
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")

    result = parse_case_status_html(r.text)
    result["bench"]    = bench["name"]
    result["diary_no"] = body.diary_no
    result["year"]     = body.year
    return result


@app.post("/case/by-party", tags=["Case Status"],
          summary="Search cases by party name",
          description="""
Search by petitioner or respondent name. Partial match supported (minimum 3 characters).
Returns list of matching cases for the selected bench.
""")
def cat_case_by_party(body: CATCaseByPartyRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])

    party_map = {"both": "3", "petitioner": "1", "respondent": "2"}
    party_code = party_map.get(body.party_type.lower(), "3")

    payload = {
        "selPartyType": party_code,
        "txtPartyName": body.party_name,
        "Submit":       "Get Status",
    }

    r = session.post(
        f"{CAT_BASE}/case_status.php",
        data=payload,
        headers=FORM_HEADERS,
        timeout=30,
    )
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")

    result = parse_case_status_html(r.text)
    result["bench"]      = bench["name"]
    result["party_name"] = body.party_name
    result["party_type"] = body.party_type
    return result


@app.post("/case/by-advocate", tags=["Case Status"],
          summary="Search cases by advocate name",
          description="Search by petitioner's or respondent's advocate name. Partial match supported.")
def cat_case_by_advocate(body: CATCaseByAdvocateRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])

    adv_map = {"petitioner": "1", "respondent": "2"}
    adv_code = adv_map.get(body.advocate_type.lower(), "1")

    payload = {
        "selAdvocateType": adv_code,
        "txtAdvocateName": body.advocate_name,
        "Submit":          "Get Status",
    }

    r = session.post(
        f"{CAT_BASE}/case_status.php",
        data=payload,
        headers=FORM_HEADERS,
        timeout=30,
    )
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")

    result = parse_case_status_html(r.text)
    result["bench"]         = bench["name"]
    result["advocate_name"] = body.advocate_name
    result["advocate_type"] = body.advocate_type
    return result


# ── Cause List ───────────────────────────────────────────────────────────────

@app.post("/causelist", tags=["Cause List"],
          summary="Get cause list for a bench on a specific date",
          description="""
Returns all cases listed for the given bench on the given date.

**URL pattern:** `cis.cgat.gov.in/catlive/internal/public_causelist_save.php?filing_no=<base64(YYYY-MM-DD#bench_slug)>`

The `filing_no` encoding is handled internally — just pass `bench` and `date`.

Date format: `dd-mm-yyyy`
""")
def cat_causelist(body: CATCauseListRequest):
    bench = get_bench(body.bench)

    filing_no = causelist_filing_no(body.date, bench["slug"])
    url = f"{CAT_BASE}/internal/public_causelist_save.php?filing_no={filing_no}"

    session = make_session(bench["code"])
    r = session.get(url, headers=BASE_HEADERS, timeout=30)

    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")

    body_text = r.text.lower()
    if "no record" in body_text or "not found" in body_text or len(r.text.strip()) < 100:
        return {
            "success": True,
            "bench": bench["name"],
            "date": body.date,
            "cases": [],
            "total_cases": 0,
            "message": "No cause list found for this bench and date.",
        }

    return parse_causelist_html(r.text, bench["name"], body.date)


# ── Orders ───────────────────────────────────────────────────────────────────

@app.post("/orders/daily", tags=["Orders"],
          summary="Get daily orders for a bench on a specific date",
          description="""
Returns all orders passed by the bench on the given date.
Each order entry contains a direct `pdf_url` for download.

Date format: `dd-mm-yyyy`
""")
def cat_orders_daily(body: CATOrdersDailyRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])

    d, m, y = body.date.split("-")
    cat_date = f"{m}/{d}/{y}"

    payload = {
        "txtListingDate": cat_date,
        "Submit":         "Get Orders",
    }

    r = session.post(
        f"{CAT_BASE}/daily_order.php",
        data=payload,
        headers=FORM_HEADERS,
        timeout=30,
    )
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")

    orders = parse_order_list_html(r.text)
    return {
        "success": True,
        "bench":   bench["name"],
        "date":    body.date,
        "orders":  orders,
        "total":   len(orders),
    }


@app.post("/orders/final", tags=["Orders"],
          summary="Get oral/final orders for a specific case",
          description="""
Returns final/oral orders (judgments) for a specific case.
Each entry contains a direct `pdf_url` for download.
""")
def cat_orders_final(body: CATOrdersFinalRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])

    payload = {
        "selCaseType": body.case_type.upper(),
        "txtCaseNo":   body.case_no,
        "txtCaseYear": body.year,
        "Submit":      "Get Orders",
    }

    r = session.post(
        f"{CAT_BASE}/final_order.php",
        data=payload,
        headers=FORM_HEADERS,
        timeout=30,
    )
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")

    orders = parse_order_list_html(r.text)
    return {
        "success":   True,
        "bench":     bench["name"],
        "case_type": body.case_type.upper(),
        "case_no":   body.case_no,
        "year":      body.year,
        "orders":    orders,
        "total":     len(orders),
    }


# ── Judgments ────────────────────────────────────────────────────────────────

@app.post("/judgments/search", tags=["Judgments"],
          summary="Search CAT judgments by keyword",
          description="""
Searches the CAT judgment database at `catjudgements.nic.in`.

- `bench`: bench_slug or `"all"` for all benches
- `query`: keyword(s) in judgment text
- `from_year` / `to_year`: year range

Returns list of matching judgments with direct PDF URLs.
""")
def cat_judgments_search(body: CATJudgmentSearchRequest):
    session = cffi_requests.Session(impersonate=IMPERSONATE)
    session.get(f"{JUDGMENT_BASE}/", headers=BASE_HEADERS, timeout=20)

    to_year = body.to_year or str(dt.today().year)

    payload = {
        "bench":    body.bench if body.bench != "all" else "",
        "keyword":  body.query,
        "fromyear": body.from_year,
        "toyear":   to_year,
        "Submit":   "Search",
    }

    r = session.post(
        f"{JUDGMENT_BASE}/search.php",
        data=payload,
        headers={**FORM_HEADERS, "Referer": f"{JUDGMENT_BASE}/"},
        timeout=30,
    )
    if r.status_code != 200:
        raise HTTPException(502, f"CAT Judgments returned HTTP {r.status_code}")

    soup = BeautifulSoup(r.text, "html.parser")
    judgments = []

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        entry: dict = {}
        for i, cell in enumerate(cells):
            entry[f"col_{i}"] = clean(cell)
            a = cell.find("a", href=True)
            if a:
                href = a["href"]
                entry["pdf_url"] = (
                    href if href.startswith("http")
                    else f"{JUDGMENT_BASE}/{href.lstrip('/')}"
                )
                entry["title"] = clean(a)
        if any(v for v in entry.values() if v):
            judgments.append(entry)

    return {
        "success":   True,
        "bench":     body.bench,
        "query":     body.query,
        "from_year": body.from_year,
        "to_year":   to_year,
        "judgments": judgments,
        "total":     len(judgments),
    }
