"""
Central Administrative Tribunal (CAT) — Unified FastAPI Scraper
All 19 benches covered via single CIS system: cis.cgat.gov.in/catlive/

Mounted inside the unified scraper process (see main.py) at the /cat prefix —
this module is not run standalone. Its own routes below are root-relative
(e.g. "/benches", "/case/by-number") because Starlette strips the "/cat"
mount prefix before dispatching to this sub-app; externally they resolve to
/cat/benches, /cat/case/by-number, etc.

Swagger UI (mounted): http://localhost:8003/cat/docs

--------------------------------------------------------------------------
REWRITE NOTE (live-crawled and verified): the previous version of this
module was built from guessed PHP form field names and was silently
non-functional end-to-end — proven by reproducing its exact logic against a
case confirmed to exist live (Delhi bench, O.A./1/2024) and getting "No case
found or bench not selected." Root cause and fixes, all confirmed against
the live site:

  - Bench activation hit `misdetailreport123.php?no=<bench_b64>`, which does
    nothing of the sort (it's actually the case-detail drilldown URL, keyed
    by a per-case token, not a bench code). The real activation call is
    `GET home1.php?no=<bench_b64>` — only after that, with the *same*
    session's cookies preserved, does the site's `bench_code1..4` hidden
    fields (and therefore any subsequent search) reflect the selected bench.
  - Case Status never POSTs to `case_status.php` — that page is just the
    form shell. Each of its 4 tabs fires an AJAX `GET` to `partyDetail.php`
    with its own field names and a `id=<mode>` marker:
      by case no.  -> caseNo, benchCode1, caseType, year,      id=casetypewise
      by diary no. -> dairy_no, benchCode2, dairy_year,        id=dairynowise1
      by party     -> nameParty, benchCode3, partyType,        id=partynamewise
      by advocate  -> nameAdv, benchCode4, AdvocateType,       id=advnamewise
    None of these match the old `selCaseType`/`txtCaseNo`/`txtDiaryNo`/
    `selPartyType`/`txtPartyName`/`selAdvocateType`/`txtAdvocateName` fields.
  - `case_type` codes are numeric 1-8 on the live `<select>`, not the letter
    codes (OA/TA/MA/...) previously hardcoded.
  - `partyType`/`AdvocateType` codes were also wrong: real is
    both=1/petitioner=2/respondent=3 for party (both=3/1/2 was coded), and
    petitioner=2/respondent=3 for advocate (no "both" option at all; 1/2 was
    coded).
  - Search results are a *thin* summary row (Diary No./Location/Case
    Type/Case No./Date of Filing/Applicant/Respondent) with a "MORE DETAIL"
    link (`javascript:popsurety_detailreport('<token>')`) — the previous
    parser expected the rich case-details/hearing-history/orders tables to
    already be present in this same response, which they never are. Full
    detail now requires a second call (see `/case/detail` below), to
    `Misdetailreport123.php?no=<token>`.
  - Daily/Final Orders never POST to `daily_order.php`/`final_order.php`
    either — same page-shell situation. The real AJAX targets are
    `order_detail.php` (daily, 5 modes) and `fiorder_detail.php` (final, 4
    modes), each keyed by its own `id=` value, mirroring the Case Status
    pattern above (case/diary/party/date-range/judge). Confirmed live with
    real order rows including direct PDF links — no separate order-detail
    drilldown is needed, unlike Case Status.
  - Cause List's `internal/public_causelist_save.php?filing_no=base64(...)`
    URL pattern was already correct (confirmed live, real data) — it only
    had a parser bug: real rows are `sr_no, case_number, parties, advocate,
    (blank)`, but the parser labeled column 4 "purpose" (a field that
    doesn't exist in this data) and shifted advocate into the wrong slot.
  - Judgments (`catjudgements.nic.in`) could not be re-verified — that host
    times out from this environment (likely a `.nic.in` network restriction
    here, not necessarily down for real users) — left unchanged/unverified.

Key differences from district eCourts / SCI (still true post-rewrite):
  - NO CAPTCHA on any public page
  - NO session pool in the DC/HC/SC sense — a fresh session is created per
    bench request and bench-activated via `home1.php`, then reused for the
    AJAX search + any drilldown call within that same request
  - Bench selection via base64-encoded numeric ID (hardcoded below)
  - Cause list URL: base64(YYYY-MM-DD#bench_slug) pattern
  - PHP backend, not JSON API — responses are HTML fragments, parsed with BeautifulSoup
  - Case identifier: bench + case_type + case_no + year (no CNR)
  - Order PDF links returned inline are direct/stable URLs — no streaming proxy needed
"""

import base64
import re
from datetime import date as dt
from typing import Optional
from urllib.parse import urljoin

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from curl_cffi.requests.exceptions import RequestException as CffiRequestException
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
# CASE TYPES — Confirmed live from case_status.php's <select id="case_type">.
# Codes are numeric (1-8), NOT the OA/TA/MA-style letter codes used elsewhere
# on this site's own case-number formatting — that distinction is real: the
# *search* dropdown uses these numeric codes, but a found case's own "Case
# Type"/"Case No." display text still reads "O.A." etc. (see parse_summary_table).
# ─────────────────────────────────────────────────────────────────────────────
CAT_CASE_TYPES = [
    {"code": "1", "name": "Original Application"},
    {"code": "2", "name": "Transfer Application"},
    {"code": "3", "name": "Misc Application"},
    {"code": "4", "name": "Contempt Petition"},
    {"code": "5", "name": "Petition for Transfer"},
    {"code": "6", "name": "Review Application"},
    {"code": "7", "name": "Criminal Contempt Petition"},
    {"code": "8", "name": "OA Objection"},
]

# Confirmed live: both=1/petitioner=2/respondent=3 (case-status party search
# AND orders party search share this exact mapping).
_PARTY_TYPE_MAP = {"both": "1", "petitioner": "2", "respondent": "3"}
# Confirmed live: case-status advocate search has NO "both" option.
_ADVOCATE_TYPE_MAP = {"petitioner": "2", "respondent": "3"}

_judges_cache: Optional[list] = None


# ─────────────────────────────────────────────────────────────────────────────
# SESSION — fresh session per bench request, activated via home1.php
# ─────────────────────────────────────────────────────────────────────────────
def make_session(bench_code: str) -> cffi_requests.Session:
    """
    Create a session scoped to a specific CAT bench. Confirmed live: the
    bench is activated by GETting home1.php?no=<base64(bench_code)> — after
    that call, this *same* session's subsequent requests see bench_code1..4
    populated site-side. (misdetailreport123.php, used here previously, does
    not do this — it's the case-detail drilldown URL for a different flow.)
    """
    s = cffi_requests.Session(impersonate=IMPERSONATE)
    bench_b64 = base64.b64encode(bench_code.encode()).decode()
    s.get(f"{CAT_BASE}/home1.php?no={bench_b64}", headers=BASE_HEADERS, timeout=20)
    return s


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def clean(el) -> str:
    return el.get_text(" ", strip=True) if el else ""

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_") or "value"

def get_bench(bench_slug: str) -> dict:
    bench = _bench_by_slug.get(bench_slug.lower())
    if not bench:
        valid = [b["slug"] for b in CAT_BENCHES]
        raise HTTPException(400, f"Unknown bench '{bench_slug}'. Valid: {valid}")
    return bench

def to_slash_date(dmy: str) -> str:
    """dd-mm-yyyy (this API's convention, matches DC/HC/SCI) -> dd/mm/yyyy
    (what the live CAT forms actually take for from_date/to_date)."""
    d, m, y = dmy.split("-")
    return f"{d}/{m}/{y}"

def party_type_code(value: str) -> str:
    return _PARTY_TYPE_MAP.get((value or "").strip().lower(), "1")

def advocate_type_code(value: str) -> str:
    return _ADVOCATE_TYPE_MAP.get((value or "").strip().lower(), "2")

def causelist_filing_no(date_str: str, bench_slug: str) -> str:
    """
    Build the base64-encoded filing_no for the causelist URL.
    Pattern confirmed live: filing_no = base64("YYYY-MM-DD#bench_slug")
    date_str: "dd-mm-yyyy" — converted to "YYYY-MM-DD" internally
    """
    d, m, y = date_str.split("-")
    iso_date = f"{y}-{m}-{d}"
    raw = f"{iso_date}#{bench_slug}"
    return base64.b64encode(raw.encode()).decode()


def get_judges() -> list:
    """
    The ~200-entry judge/member list used by the orders-by-judge modes is
    embedded directly in daily_order.php's <select id="member_wise"> (no
    separate AJAX endpoint) — fetched once and cached in-process, mirroring
    how the site itself treats it as a static reference list shared across
    all benches.
    """
    global _judges_cache
    if _judges_cache is not None:
        return _judges_cache
    session = cffi_requests.Session(impersonate=IMPERSONATE)
    r = session.get(f"{CAT_BASE}/daily_order.php", headers=BASE_HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")
    select = soup.find("select", id="member_wise")
    judges = []
    if select:
        for opt in select.find_all("option"):
            val = (opt.get("value") or "").strip()
            if val:
                judges.append({"code": val, "name": clean(opt)})
    # The live site intermittently 500s and serves a degraded page with only
    # the placeholder option (confirmed live) — don't let a transient bad
    # response permanently poison the cache; only cache a plausible full list.
    if len(judges) > 10:
        _judges_cache = judges
    return judges


# ─────────────────────────────────────────────────────────────────────────────
# PARSERS
# ─────────────────────────────────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"popsurety_detailreport\('([^']+)'\)")

# Case Status search-result columns -> normalized keys. "Other Details" is
# dropped (it's just the literal text "MORE DETAIL" — the useful part is the
# link itself, captured separately as detail_token).
_SUMMARY_HEADER_MAP = {
    "diary no.": "diary_no",
    "location": "location",
    "case type": "case_type",
    "case no.": "case_no",
    "date of filing": "filing_date",
    "applicant": "applicant",
    "respondent": "respondent",
}


def parse_summary_table(html: str) -> list:
    """
    Parse the thin AJAX result table shared by partyDetail.php's 4 Case
    Status modes into row dicts, normalizing headers and pulling a
    `detail_token` out of each row's "MORE DETAIL" link
    (javascript:popsurety_detailreport('<token>')) for the /case/detail
    drilldown. Returns [] for a "No Record Found" response.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []
    rows = table.find_all("tr")
    if not rows:
        return []
    headers = [clean(c) for c in rows[0].find_all(["th"])]
    body_rows = rows[1:] if headers else rows

    results = []
    for tr in body_rows:
        cells = tr.find_all("td")
        if not cells:
            continue
        texts = [clean(c) for c in cells]
        if len(cells) == 1 and ("no record" in texts[0].lower() or not texts[0]):
            continue
        raw = {}
        for i, cell in enumerate(cells):
            header = headers[i] if i < len(headers) else f"col_{i}"
            key = _SUMMARY_HEADER_MAP.get(header.strip().lower())
            if key:
                raw[key] = clean(cell)
            elif header.strip().lower() != "other details":
                raw[slugify(header)] = clean(cell)
        m = _TOKEN_RE.search(str(tr))
        if m:
            raw["detail_token"] = m.group(1)
        if any(raw.values()):
            results.append(raw)
    return results


# Section headers inside the single case-detail table -> the list field they
# introduce (confirmed live: everything below "CASE STATUS" through
# "DOCUMENT FILING DETAILS" is ONE <table>, not separate ones).
_DETAIL_LIST_LABELS = {
    "petitioner(s)": "petitioners",
    "respondent(s)": "respondents",
    "petitoner advocate(s)": "petitioner_advocates",   # sic — matches the site's own typo
    "respondent advocate(s)": "respondent_advocates",
}
_DETAIL_FIELD_MAP = {
    "petitioner(s) address": "petitioner_address",
    "respondent(s) address": "respondent_address",
}
_VS_RE = re.compile(r"\s+Vs\s+", re.IGNORECASE)
_WINDOW_OPEN_RE = re.compile(r"window\.open\('([^']+)'")


def _extract_action_url(row):
    """Pull the real target out of a row's `onclick="...window.open('<url>'...)"`
    popup link (its href is just "#") — used by the reference/connected case
    sub-tables' "Daily Order"/"View" cell."""
    for a in row.find_all("a"):
        m = _WINDOW_OPEN_RE.search(a.get("onclick") or "")
        if m:
            return urljoin(f"{CAT_BASE}/", m.group(1))
    return None


def parse_case_detail_html(html: str) -> dict:
    """
    Parse the "MORE DETAIL" drilldown (Misdetailreport123.php) into a flat
    dict. Best-effort: the real markup mixes single-cell section-header rows,
    2-cell key/value rows, and 3 mini result tables (Reference/Connected
    cases, Document Filing) inside one big <table>, distinguished only by
    section-header text — there's no class/id structure to key off of.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return {}

    out: dict = {}
    mode = None
    sub_headers: dict = {}
    reference_cases, connected_cases, filings = [], [], []

    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        texts = [clean(c) for c in cells]
        if not any(texts):
            continue

        if len(cells) == 1:
            label = texts[0].strip()
            up = label.upper()
            if "REFERANCE CASE" in up or "REFERENCE CASE" in up:
                mode = "reference"
            elif "CONNECT CASE" in up:
                mode = "connect"
            elif "DOCUMENT FILING" in up:
                mode = "filing"
            elif up == "CASE STATUS":
                pass
            elif label.lower().startswith("diary no"):
                out["diary_no"] = label.split("-", 1)[-1].strip()
            elif _VS_RE.search(label):
                applicant, respondent = _VS_RE.split(label, maxsplit=1)
                out["applicant"] = applicant.strip()
                out["respondent"] = respondent.strip()
            elif label.lower().startswith("filing date"):
                out["filing_date"] = label.split(":", 1)[-1].strip()
            continue

        if mode in ("reference", "connect", "filing"):
            first = texts[0].strip().lower()
            if first in ("diary no", "party type"):
                sub_headers[mode] = texts
                continue
            bucket = {"reference": reference_cases, "connect": connected_cases, "filing": filings}[mode]
            cols = sub_headers.get(mode) or [f"col_{i}" for i in range(len(texts))]
            entry = {cols[i] if i < len(cols) else f"col_{i}": t for i, t in enumerate(texts)}
            # The "Daily Order"/"View" cell isn't a real link (href="#") — its
            # target is a popup URL embedded in onclick="...window.open('<url>'...)".
            # Confirmed live: ref_order.php?diary_no=<token> is directly
            # fetchable with no session/cookie needed, same as order pdf_urls
            # elsewhere in this API, so expose it as a normal link.
            action_url = _extract_action_url(row)
            if action_url:
                entry["daily_order_url"] = action_url
            bucket.append(entry)
            continue

        # main key/value rows (2+ cells, not inside a sub-section)
        label = texts[0].rstrip(":").strip()
        label_l = label.lower()
        if label_l in _DETAIL_LIST_LABELS:
            value = texts[1] if len(texts) > 1 else ""
            items = [x.strip() for x in value.split(",") if x.strip() and x.strip() != "-"]
            out[_DETAIL_LIST_LABELS[label_l]] = items
        elif label_l == "court fee" and len(texts) >= 4:
            out["court_fee"] = texts[1]
            out["group"] = texts[3]
        elif len(texts) >= 2:
            out[_DETAIL_FIELD_MAP.get(label_l) or slugify(label)] = texts[1]

    if reference_cases:
        out["reference_cases"] = reference_cases
    if connected_cases:
        out["connected_cases"] = connected_cases
    if filings:
        out["document_filings"] = filings
    return out


def parse_order_list_html(html: str) -> list:
    """Parse a daily/final order result table (order_detail.php /
    fiorder_detail.php) — real headers are Sr. No./Case No./Party
    Details/Order Date with a direct PDF link per row."""
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
            texts = [clean(c) for c in cells]
            if len(cells) == 1 and "no record" in texts[0].lower():
                continue
            entry: dict = {}
            for i, cell in enumerate(cells):
                col = headers[i] if i < len(headers) else f"col_{i}"
                entry[col] = clean(cell)
                a = cell.find("a", href=True)
                if a:
                    entry["pdf_url"] = urljoin(f"{CAT_BASE}/", a["href"])
            if any(v for v in entry.values()):
                orders.append(entry)
    return orders


def parse_causelist_html(html: str, bench_name: str, date: str) -> dict:
    """Parse the CAT cause list HTML into structured bench/case data.
    Real per-case rows are: sr_no, case_number, "X Vs Y" parties, advocate,
    (blank 5th column) — previously mislabeled column 4 as "purpose" (a field
    that doesn't exist here), which pushed advocate into the wrong slot."""
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
                    "advocate": clean(cells[3]) if len(cells) > 3 else "",
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
        result["pdf_url"] = urljoin(f"{CAT_BASE}/", pdf_links[0])

    return result


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

## Flow A — Case Status Search

```
GET /benches              -> pick bench_slug (e.g. "delhi")
GET /case-types           -> pick case_type (numeric code, e.g. "1" = Original Application)
POST /case/by-number      -> { bench, case_type, case_no, year }
POST /case/by-diary       -> { bench, diary_no, year }
POST /case/by-party       -> { bench, party_name, party_type }   party_type: Both|Petitioner|Respondent
POST /case/by-advocate    -> { bench, advocate_name, advocate_type }  advocate_type: Petitioner|Respondent
POST /case/detail         -> { token }   token = a result row's detail_token
```

---

## Flow B — Cause List

```
GET  /benches             -> pick bench_slug
POST /causelist            -> { bench, date }   date: dd-mm-yyyy
```

---

## Flow C — Orders

```
GET  /judges                    -> judge/member code list (for the by-judge modes)
POST /orders/daily/by-case      -> { bench, case_type, case_no, year }
POST /orders/daily/by-diary     -> { bench, diary_no, year }
POST /orders/daily/by-party     -> { bench, party_name, party_type }
POST /orders/daily/by-date      -> { bench, from_date, to_date }   dd-mm-yyyy
POST /orders/daily/by-judge     -> { bench, judge_code }
POST /orders/final/by-case      -> { bench, case_type, case_no, year }
POST /orders/final/by-diary     -> { bench, diary_no, year }
POST /orders/final/by-date      -> { bench, from_date, to_date }   dd-mm-yyyy
POST /orders/final/by-judge     -> { bench, judge_code }
```

---

## Flow D — Judgments (unverified — catjudgements.nic.in unreachable at rewrite time)

```
POST /judgments/search    -> { bench, query, from_year, to_year }
```
""",
    version="2.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(CffiRequestException)
async def cat_upstream_error_handler(request: Request, exc: CffiRequestException):
    # The live CAT portal is confirmed intermittently slow/unresponsive under
    # load (500s and timeouts observed live, independent of request
    # correctness) — surface that as a clean 504 instead of an opaque 500.
    return JSONResponse(status_code=504, content={"error": f"CAT portal did not respond: {exc}"})


# ── Pydantic Models ──────────────────────────────────────────────────────────

class CATCaseByNumberRequest(BaseModel):
    bench:      str = Field(..., example="delhi")
    case_type:  str = Field(..., example="1", description="Numeric code from GET /case-types")
    case_no:    str = Field(..., example="1265")
    year:       str = Field(..., example="2024")


class CATCaseByDiaryRequest(BaseModel):
    bench:      str = Field(..., example="delhi")
    diary_no:   str = Field(..., example="123456")
    year:       str = Field(..., example="2024")


class CATCaseByPartyRequest(BaseModel):
    bench:       str = Field(..., example="delhi")
    party_name:  str = Field(..., example="Ram Kumar Singh")
    party_type:  str = Field("Both", example="Both", description="'Both', 'Petitioner', or 'Respondent'")


class CATCaseByAdvocateRequest(BaseModel):
    bench:          str = Field(..., example="delhi")
    advocate_name:  str = Field(..., example="Sharma")
    advocate_type:  str = Field("Petitioner", example="Petitioner", description="'Petitioner' or 'Respondent'")


class CATCaseDetailRequest(BaseModel):
    token: str = Field(..., description="detail_token from a Case Status search result row")


class CATCauseListRequest(BaseModel):
    bench:  str = Field(..., example="delhi")
    date:   str = Field(..., example="04-04-2026", description="Date in dd-mm-yyyy format")


class CATOrdersByCaseRequest(BaseModel):
    bench:      str = Field(..., example="delhi")
    case_type:  str = Field(..., example="1")
    case_no:    str = Field(..., example="1265")
    year:       str = Field(..., example="2024")


class CATOrdersByDiaryRequest(BaseModel):
    bench:      str = Field(..., example="delhi")
    diary_no:   str = Field(..., example="123456")
    year:       str = Field(..., example="2024")


class CATOrdersByPartyRequest(BaseModel):
    bench:       str = Field(..., example="delhi")
    party_name:  str = Field(..., example="Ram Kumar Singh")
    party_type:  str = Field("Both", example="Both")


class CATOrdersByDateRequest(BaseModel):
    bench:      str = Field(..., example="delhi")
    from_date:  str = Field(..., example="01-07-2026", description="dd-mm-yyyy")
    to_date:    str = Field(..., example="17-07-2026", description="dd-mm-yyyy")


class CATOrdersByJudgeRequest(BaseModel):
    bench:       str = Field(..., example="delhi")
    judge_code:  str = Field(..., description="Numeric code from GET /judges")


class CATJudgmentSearchRequest(BaseModel):
    bench:      str = Field("delhi", example="delhi", description="bench_slug or 'all' for all benches")
    query:      str = Field(..., example="departmental promotion")
    from_year:  str = Field("2020", example="2020")
    to_year:    str = Field("", example="2026", description="Leave empty for current year")


# ── System ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "tribunal": "CAT", "benches": len(CAT_BENCHES)}


# ── Reference Data ───────────────────────────────────────────────────────────

@app.get("/benches", tags=["Reference"])
def cat_benches():
    return CAT_BENCHES


@app.get("/case-types", tags=["Reference"])
def cat_case_types():
    return CAT_CASE_TYPES


@app.get("/judges", tags=["Reference"],
         summary="Get the judge/member code list used by orders-by-judge modes")
def cat_judges():
    return get_judges()


# ── Case Status ──────────────────────────────────────────────────────────────

@app.post("/case/by-number", tags=["Case Status"])
def cat_case_by_number(body: CATCaseByNumberRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])
    params = {"caseNo": body.case_no, "benchCode1": bench["code"], "caseType": body.case_type, "year": body.year}
    r = session.get(f"{CAT_BASE}/partyDetail.php", params={**params, "id": "casetypewise"},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    return {"success": True, "bench": bench["name"], "cases": parse_summary_table(r.text)}


@app.post("/case/by-diary", tags=["Case Status"])
def cat_case_by_diary(body: CATCaseByDiaryRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])
    params = {"dairy_no": body.diary_no, "benchCode2": bench["code"], "dairy_year": body.year}
    r = session.get(f"{CAT_BASE}/partyDetail.php", params={**params, "id": "dairynowise1"},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    return {"success": True, "bench": bench["name"], "cases": parse_summary_table(r.text)}


@app.post("/case/by-party", tags=["Case Status"])
def cat_case_by_party(body: CATCaseByPartyRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])
    params = {"nameParty": body.party_name, "benchCode3": bench["code"], "partyType": party_type_code(body.party_type)}
    r = session.get(f"{CAT_BASE}/partyDetail.php", params={**params, "id": "partynamewise"},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    return {"success": True, "bench": bench["name"], "cases": parse_summary_table(r.text)}


@app.post("/case/by-advocate", tags=["Case Status"])
def cat_case_by_advocate(body: CATCaseByAdvocateRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])
    params = {"nameAdv": body.advocate_name, "benchCode4": bench["code"], "AdvocateType": advocate_type_code(body.advocate_type)}
    r = session.get(f"{CAT_BASE}/partyDetail.php", params={**params, "id": "advnamewise"},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    return {"success": True, "bench": bench["name"], "cases": parse_summary_table(r.text)}


@app.post("/case/detail", tags=["Case Status"],
          summary="Full case detail drilldown from a search result's detail_token")
def cat_case_detail(body: CATCaseDetailRequest):
    session = cffi_requests.Session(impersonate=IMPERSONATE)
    r = session.get(f"{CAT_BASE}/Misdetailreport123.php", params={"no": body.token},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    detail = parse_case_detail_html(r.text)
    if not detail:
        raise HTTPException(404, "No case detail found for this token.")
    return {"success": True, "case_details": detail}


# ── Cause List ───────────────────────────────────────────────────────────────

@app.post("/causelist", tags=["Cause List"])
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


# ── Orders — Daily ───────────────────────────────────────────────────────────

@app.post("/orders/daily/by-case", tags=["Orders"])
def cat_orders_daily_by_case(body: CATOrdersByCaseRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])
    params = {"caseNo": body.case_no, "benchCode1": bench["code"], "caseType": body.case_type, "year": body.year}
    r = session.get(f"{CAT_BASE}/order_detail.php", params={**params, "id": "casetypewise"},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    orders = parse_order_list_html(r.text)
    return {"success": True, "bench": bench["name"], "orders": orders, "total": len(orders)}


@app.post("/orders/daily/by-diary", tags=["Orders"])
def cat_orders_daily_by_diary(body: CATOrdersByDiaryRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])
    params = {"dairy_no": body.diary_no, "benchCode2": bench["code"], "dairy_year": body.year}
    r = session.get(f"{CAT_BASE}/order_detail.php", params={**params, "id": "dairynowise1"},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    orders = parse_order_list_html(r.text)
    return {"success": True, "bench": bench["name"], "orders": orders, "total": len(orders)}


@app.post("/orders/daily/by-party", tags=["Orders"])
def cat_orders_daily_by_party(body: CATOrdersByPartyRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])
    # Confirmed live: this mode's own bench-scope slot is benchCode5, distinct
    # from case-status's party mode (benchCode3) despite the identical shape.
    params = {"nameParty": body.party_name, "benchCode5": bench["code"], "partyType": party_type_code(body.party_type)}
    r = session.get(f"{CAT_BASE}/order_detail.php", params={**params, "id": "partynamewise1"},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    orders = parse_order_list_html(r.text)
    return {"success": True, "bench": bench["name"], "orders": orders, "total": len(orders)}


@app.post("/orders/daily/by-date", tags=["Orders"])
def cat_orders_daily_by_date(body: CATOrdersByDateRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])
    params = {
        "benchCode3": bench["code"],
        "from_date": to_slash_date(body.from_date),
        "to_date": to_slash_date(body.to_date),
    }
    r = session.get(f"{CAT_BASE}/order_detail.php", params={**params, "id": "partynamewise"},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    orders = parse_order_list_html(r.text)
    return {"success": True, "bench": bench["name"], "orders": orders, "total": len(orders)}


@app.post("/orders/daily/by-judge", tags=["Orders"])
def cat_orders_daily_by_judge(body: CATOrdersByJudgeRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])
    params = {"benchCode4": bench["code"], "member_wise": body.judge_code}
    r = session.get(f"{CAT_BASE}/order_detail.php", params={**params, "id": "membernamewsie"},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    orders = parse_order_list_html(r.text)
    return {"success": True, "bench": bench["name"], "orders": orders, "total": len(orders)}


# ── Orders — Final / Oral ────────────────────────────────────────────────────

@app.post("/orders/final/by-case", tags=["Orders"])
def cat_orders_final_by_case(body: CATOrdersByCaseRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])
    params = {"caseNo": body.case_no, "benchCode1": bench["code"], "caseType": body.case_type, "year": body.year}
    r = session.get(f"{CAT_BASE}/fiorder_detail.php", params={**params, "id": "casetypewise"},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    orders = parse_order_list_html(r.text)
    return {"success": True, "bench": bench["name"], "orders": orders, "total": len(orders)}


@app.post("/orders/final/by-diary", tags=["Orders"])
def cat_orders_final_by_diary(body: CATOrdersByDiaryRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])
    params = {"dairy_no": body.diary_no, "benchCode2": bench["code"], "dairy_year": body.year}
    r = session.get(f"{CAT_BASE}/fiorder_detail.php", params={**params, "id": "dairynowise1"},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    orders = parse_order_list_html(r.text)
    return {"success": True, "bench": bench["name"], "orders": orders, "total": len(orders)}


@app.post("/orders/final/by-date", tags=["Orders"])
def cat_orders_final_by_date(body: CATOrdersByDateRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])
    params = {
        "benchCode3": bench["code"],
        "from_date": to_slash_date(body.from_date),
        "to_date": to_slash_date(body.to_date),
    }
    r = session.get(f"{CAT_BASE}/fiorder_detail.php", params={**params, "id": "partynamewise"},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    orders = parse_order_list_html(r.text)
    return {"success": True, "bench": bench["name"], "orders": orders, "total": len(orders)}


@app.post("/orders/final/by-judge", tags=["Orders"])
def cat_orders_final_by_judge(body: CATOrdersByJudgeRequest):
    bench = get_bench(body.bench)
    session = make_session(bench["code"])
    params = {"judge_code": body.judge_code, "benchCode4": bench["code"]}
    r = session.get(f"{CAT_BASE}/fiorder_detail.php", params={**params, "id": "membernamewsie"},
                     headers=BASE_HEADERS, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"CAT returned HTTP {r.status_code}")
    orders = parse_order_list_html(r.text)
    return {"success": True, "bench": bench["name"], "orders": orders, "total": len(orders)}


# ── Judgments ────────────────────────────────────────────────────────────────

@app.post("/judgments/search", tags=["Judgments"],
          description="UNVERIFIED at rewrite time — catjudgements.nic.in was unreachable "
                       "from the environment this was crawled from (connection timeout on "
                       "port 443). Left unchanged from the prior implementation.")
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
                entry["pdf_url"] = urljoin(f"{JUDGMENT_BASE}/", href)
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
