"""
eCourts India — Unified FastAPI
Swagger UI: http://localhost:8000/docs

Endpoints:
  CNR Search
    POST /cnr/search                  → full case details by CNR number

  Cause List
    GET  /causelist/states            → list of all states with codes
    POST /causelist/districts         → districts for a state
    POST /causelist/complexes         → court complexes for a district
    POST /causelist/establishments    → establishments for a complex
    POST /causelist/courts            → court names for an establishment
    POST /causelist/fetch             → fetch civil/criminal cause list

  Case History (from cause list "View" button)
    POST /case/history                → full case details by case_no + cino + court codes
    POST /case/from-url               → same, but pass the view_history_url directly
    POST /case/order-pdf              → resolve encrypted PDF params → direct PDF URL

Install:
    pip install fastapi uvicorn curl_cffi beautifulsoup4 requests

Run:
    export CAPSOLVER_API_KEY=CAP-xxx
    uvicorn ecourts_api:app --host 0.0.0.0 --port 8000 --reload
"""

import os, re, time, base64, json
from datetime import date as dt
from typing import Optional
from urllib.parse import urlparse, parse_qs

import requests as std_requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
CAPSOLVER_API_KEY = os.environ.get("CAPSOLVER_API_KEY", "")
if not CAPSOLVER_API_KEY:
    raise RuntimeError("Set env var: export CAPSOLVER_API_KEY=CAP-xxx")

BASE_URL        = "https://services.ecourts.gov.in/ecourtindia_v6"
CNR_HOME_URL    = f"{BASE_URL}/?p=home/index"
CL_HOME_URL     = f"{BASE_URL}/?p=cause_list/index"
CAPTCHA_URL     = f"{BASE_URL}/vendor/securimage/securimage_show.php"
IMPERSONATE     = "chrome110"

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}
AJAX_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://services.ecourts.gov.in",
}

# Confirmed state codes from live eCourts page HTML
STATES = [
    {"name": "Andaman and Nicobar",                          "code": "28"},
    {"name": "Andhra Pradesh",                               "code": "2"},
    {"name": "Arunachal Pradesh",                            "code": "36"},
    {"name": "Assam",                                        "code": "6"},
    {"name": "Bihar",                                        "code": "8"},
    {"name": "Chandigarh",                                   "code": "27"},
    {"name": "Chhattisgarh",                                 "code": "18"},
    {"name": "Delhi",                                        "code": "26"},
    {"name": "Goa",                                          "code": "30"},
    {"name": "Gujarat",                                      "code": "17"},
    {"name": "Haryana",                                      "code": "14"},
    {"name": "Himachal Pradesh",                             "code": "5"},
    {"name": "Jammu and Kashmir",                            "code": "12"},
    {"name": "Jharkhand",                                    "code": "7"},
    {"name": "Karnataka",                                    "code": "3"},
    {"name": "Kerala",                                       "code": "4"},
    {"name": "Ladakh",                                       "code": "33"},
    {"name": "Lakshadweep",                                  "code": "37"},
    {"name": "Madhya Pradesh",                               "code": "23"},
    {"name": "Maharashtra",                                  "code": "1"},
    {"name": "Manipur",                                      "code": "25"},
    {"name": "Meghalaya",                                    "code": "21"},
    {"name": "Mizoram",                                      "code": "19"},
    {"name": "Nagaland",                                     "code": "34"},
    {"name": "Odisha",                                       "code": "11"},
    {"name": "Puducherry",                                   "code": "35"},
    {"name": "Punjab",                                       "code": "22"},
    {"name": "Rajasthan",                                    "code": "9"},
    {"name": "Sikkim",                                       "code": "24"},
    {"name": "Tamil Nadu",                                   "code": "10"},
    {"name": "Telangana",                                    "code": "29"},
    {"name": "The Dadra And Nagar Haveli And Daman And Diu", "code": "38"},
    {"name": "Tripura",                                      "code": "20"},
    {"name": "Uttarakhand",                                  "code": "15"},
    {"name": "Uttar Pradesh",                                "code": "13"},
    {"name": "West Bengal",                                  "code": "16"},
]


# ──────────────────────────────────────────────────────────────────────────────
# SESSION POOL  (one per home URL to keep cookies separate)
# ──────────────────────────────────────────────────────────────────────────────
_sessions: dict[str, cffi_requests.Session] = {}

def get_session(home_url: str) -> cffi_requests.Session:
    if home_url not in _sessions:
        s = cffi_requests.Session(impersonate=IMPERSONATE)
        resp = s.get(home_url, headers=BASE_HEADERS, timeout=20)
        if resp.status_code != 200:
            raise HTTPException(502, f"Could not reach eCourts: HTTP {resp.status_code}")
        _sessions[home_url] = s
        print(f"[✓] New session for {home_url.split('?p=')[1]}  cookies={dict(s.cookies)}")
    return _sessions[home_url]

def reset_session(home_url: str):
    _sessions.pop(home_url, None)

def ajax_post(home_url: str, p: str, payload: dict) -> dict:
    session = get_session(home_url)
    headers = {**AJAX_HEADERS, "Referer": home_url}
    try:
        r = session.post(f"{BASE_URL}/?p={p}", data=payload,
                         headers=headers, timeout=30)
        print(f"[ajax_post] {p} → HTTP {r.status_code}  "
              f"Content-Type={r.headers.get('Content-Type','?')}  "
              f"len={len(r.content)}  preview={r.text[:80]!r}")
        if r.status_code != 200:
            return {"_error": f"HTTP {r.status_code}"}
        if not r.text.strip():
            # Empty body — session may have expired
            reset_session(home_url)
            return {"_raw": ""}
        try:
            return r.json()
        except Exception:
            return {"_raw": r.text}
    except Exception as e:
        reset_session(home_url)
        raise HTTPException(502, f"Request to eCourts failed: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# CAPTCHA
# ──────────────────────────────────────────────────────────────────────────────
def fetch_captcha_b64(home_url: str, src: str = "") -> str:
    session = get_session(home_url)
    if not src: src = CAPTCHA_URL
    if src.startswith("/"): src = f"https://services.ecourts.gov.in{src}"
    url = f"{src}{'&' if '?' in src else '?'}cb={int(time.time())}"
    r = session.get(url, headers=BASE_HEADERS, timeout=20)
    if r.status_code != 200 or len(r.content) < 100:
        raise HTTPException(502, f"CAPTCHA fetch failed: HTTP {r.status_code}")
    return base64.b64encode(r.content).decode().replace("\n", "")

def solve_captcha(b64: str, home_url: str) -> str:
    r = std_requests.post(
        "https://api.capsolver.com/createTask",
        json={"clientKey": CAPSOLVER_API_KEY,
              "task": {"type": "ImageToTextTask", "websiteURL": home_url,
                       "module": "common", "body": b64}},
        timeout=30,
    )
    if r.status_code != 200:
        raise HTTPException(502, f"CapSolver HTTP {r.status_code}: {r.text[:200]}")
    d = r.json()
    if d.get("errorId") != 0:
        raise HTTPException(502, f"CapSolver {d.get('errorCode')}: {d.get('errorDescription')}")
    text = d.get("solution", {}).get("text", "").strip()
    if not text:
        raise HTTPException(502, "CapSolver returned empty solution")
    print(f"[CapSolver] Solved: '{text}'")
    return text

def extract_captcha_src(div_html: str) -> str:
    soup = BeautifulSoup(div_html, "html.parser")
    img  = (soup.find("img", id="captcha_image") or
            soup.find("img", attrs={"src": re.compile(r"securimage_show", re.I)}))
    return img["src"] if img and img.get("src") else ""

def is_captcha_bad(resp: dict) -> bool:
    msg = resp.get("errormsg","")
    # Only treat as captcha failure if errormsg explicitly says captcha/invalid
    # Do NOT block on status=0 alone — some endpoints return status=0 with valid data
    if msg and re.search(r"captcha|invalid\s+captcha", msg, re.I):
        return True
    if resp.get("status") == "N":
        return True
    # status=0 is captcha-bad ONLY if there is no usable HTML content
    if resp.get("status") == 0:
        has_content = any(
            resp.get(k) for k in (
                "case_list","casetype_list","party_list",
                "case_data","data_list","casetype_list",
                "searchresult","result",
            )
        )
        return not has_content
    return False


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def clean(el) -> str:
    return el.get_text(" ", strip=True) if el else ""

def abs_url(href: str) -> str:
    if not href or href == "#": return ""
    if href.startswith("http"): return href
    if href.startswith("/"): return f"https://services.ecourts.gov.in{href}"
    return f"{BASE_URL}/{href.lstrip('/')}"

def parse_options(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    skip = {"select district","select court complex","select establishment",
            "select court","select court name",""}
    return [{"code": o.get("value","").strip(), "name": o.get_text(strip=True)}
            for o in soup.find_all("option")
            if o.get("value","").strip() not in ("0","-1","")
            and o.get_text(strip=True).lower() not in skip]

def selprevdays(date_str: str) -> str:
    try:
        d, m, y = date_str.split("-")
        return "1" if (dt.today() - dt(int(y), int(m), int(d))).days >= 1 else "0"
    except Exception:
        return "0"

def parse_viewbusiness_onclick(onclick: str) -> dict:
    args = re.findall(r"'([^']*)'", onclick)
    if len(args) >= 11:
        return {"court_code": args[0], "dist_code": args[1], "nextdate1": args[2],
                "case_number1": args[3], "state_code": args[4], "disposal_flag": args[5],
                "businessDate": args[6], "court_no": args[7],
                "national_court_code": args[8], "search_by": args[9], "srno": args[10]}
    return {}


# ──────────────────────────────────────────────────────────────────────────────
# CASE HTML PARSER  (shared by CNR search + viewHistory)
# ──────────────────────────────────────────────────────────────────────────────
def parse_case_html(html: str, cino: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out: dict = {"cino": cino, "success": False}

    body_text = soup.get_text(" ", strip=True).lower()
    if any(k in body_text for k in ["no record","does not exist","case not found","invalid cnr"]):
        out["error"] = "No case found."
        return out

    h2 = soup.find("h2")
    if h2: out["court_name"] = clean(h2).strip()

    def next_table(heading_pattern):
        h = soup.find(string=re.compile(heading_pattern, re.I))
        return next(iter(h.find_all_next("table")), None) if h else None

    def parse_kv(table) -> dict:
        result = {}
        for row in table.find_all("tr"):
            # Handle rows with th+td (label+value) OR all-td rows
            ths = row.find_all("th")
            tds = row.find_all("td")
            if ths and tds:
                # th=label, td=value — may repeat across row
                all_cells = row.find_all(["th","td"])
                i = 0
                while i < len(all_cells) - 1:
                    if all_cells[i].name == "th":
                        k = clean(all_cells[i]).rstrip(":")
                        # find next td
                        j = i + 1
                        while j < len(all_cells) and all_cells[j].name == "th":
                            j += 1
                        if j < len(all_cells):
                            v = clean(all_cells[j])
                            if k and len(k) < 80: result[k] = v
                            i = j + 1
                        else:
                            i += 1
                    else:
                        i += 1
            elif tds and len(tds) >= 2:
                for i in range(0, len(tds) - 1, 2):
                    k = clean(tds[i]).rstrip(":")
                    v = clean(tds[i+1])
                    if k and len(k) < 80: result[k] = v
        return result

    # Case Details
    cd_t = (soup.find("table", class_=re.compile(r"case_details", re.I))
            or next_table(r"^Case Details$"))
    if cd_t:
        cd = parse_kv(cd_t)
        qr_a = cd_t.find("a", string=re.compile(r"QR|Cause Title", re.I))
        if qr_a: cd["qr_url"] = abs_url(qr_a.get("href",""))
        out["case_details"] = cd

    # Case Status
    st_t = next_table(r"^Case Status$")
    if st_t: out["case_status"] = parse_kv(st_t)

    # Parties - use class-based selectors to avoid picking up Acts table
    pet_table = soup.find(["ul","table"], class_=re.compile(r"petitioner", re.I))
    if pet_table:
        items = [li.get_text(" ", strip=True) for li in pet_table.find_all("li")]
        if not items:
            items = [t for t in pet_table.get_text("\n", strip=True).split("\n") if t.strip()]
        if items: out["petitioner_and_advocate"] = items

    res_table = soup.find(["ul","table"], class_=re.compile(r"respondent", re.I))
    if res_table:
        items = [li.get_text(" ", strip=True) for li in res_table.find_all("li")]
        if not items:
            items = [t for t in res_table.get_text("\n", strip=True).split("\n") if t.strip()]
        if items: out["respondent_and_advocate"] = items

    # Acts
    acts_t = next_table(r"^Acts$")
    if acts_t:
        rows = acts_t.find_all("tr")
        hdrs = [clean(c) for c in rows[0].find_all(["th","td"])] if rows else []
        out["acts"] = [dict(zip(hdrs,[clean(c) for c in r.find_all("td")]))
                       for r in rows[1:] if r.find_all("td")]

    # FIR Details
    fir_t = next_table(r"FIR Details")
    if fir_t:
        fir = {}
        for row in fir_t.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                k = clean(cells[0]).rstrip(":")
                v = clean(cells[1])
                if k and k.lower() not in ("field","details"): fir[k] = v
        out["fir_details"] = fir

    # Case History
    hist_t = next_table(r"^Case History$")
    if hist_t:
        rows = hist_t.find_all("tr")
        # Header row uses <th> elements
        header_row = rows[0] if rows else None
        hdrs = [clean(c) for c in header_row.find_all(["th","td"])] if header_row else []
        # Clean empty headers
        hdrs = [h if h else f"col_{i}" for i, h in enumerate(hdrs)]
        hearings = []
        for row in rows[1:]:
            cells = row.find_all("td")
            if not cells: continue
            entry: dict = {}
            for i, cell in enumerate(cells):
                col = hdrs[i] if i < len(hdrs) else f"col_{i}"
                entry[col] = clean(cell)
                a = cell.find("a")
                if a:
                    onclick = a.get("onclick","")
                    if "viewBusiness" in onclick:
                        entry["business_params"] = parse_viewbusiness_onclick(onclick)
            if any(v for k,v in entry.items() if v and k != "business_params"):
                hearings.append(entry)
        out["case_history"] = hearings

    # Interim Orders + PDF links
    orders_t = (
        next_table(r"Final Orders / Judgements")
        or next_table(r"Final Orders")
        or next_table(r"Interim Orders")
        or next_table(r"Judgements")
        or next_table(r"^Orders$")
    )
    if orders_t:
        rows = orders_t.find_all("tr")
        hdrs = [clean(c) for c in rows[0].find_all(["th","td"])] if rows else []
        orders = []
        for row in rows[1:]:
            cells = row.find_all("td")
            if not cells: continue
            entry: dict = {}
            for i, cell in enumerate(cells):
                col = hdrs[i] if i < len(hdrs) else f"col_{i}"
                entry[col] = clean(cell)
                a = cell.find("a")
                if a:
                    onclick = a.get("onclick","") or ""
                    if "display_pdf" in onclick or "displayPdf" in onclick:
                        args = re.findall(r"'([^']*)'", onclick)
                        if len(args) >= 4:
                            entry["pdf_params"] = {
                                "normal_v": args[0], "case_val": args[1],
                                "court_code": args[2], "filename": args[3],
                            }
                            entry["pdf_endpoint"] = "POST /case/order-pdf"
                    # Capture plain href (e.g. direct PDF link on "Order" anchor)
                    href = a.get("href", "") or ""
                    if href and href != "#":
                        entry[f"{col}_url"] = abs_url(href)
                    elif href == "#" and onclick and "display_pdf" not in onclick and "displayPdf" not in onclick:
                        entry[f"{col}_onclick"] = onclick
            orders.append(entry)
        if orders: out["interim_orders"] = orders

    # Case Transfer Details
    tr_t = next_table(r"Case Transfer Details")
    if tr_t:
        rows = tr_t.find_all("tr")
        hdrs = [clean(c) for c in rows[0].find_all(["th","td"])] if rows else []
        out["case_transfer_details"] = [
            dict(zip(hdrs,[clean(c) for c in r.find_all("td")]))
            for r in rows[1:] if r.find_all("td")
        ]

    out["success"] = True
    return out


# ──────────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="eCourts India API",
    description="""
# eCourts India — Unified Scraping API

Everything is driven by the output of the previous step. No hardcoded values.

---

## 🔵 Flow A — CNR Number Search

```
POST /cnr/search   { "cnr_number": "BRAU010000972020" }
```
→ Returns full case: details, status, parties, acts, FIR, case history, interim orders  
→ Each `interim_orders[]` entry has `pdf_params` → pass to `POST /case/order-pdf`

---

## 🟢 Flow B — Cause List (step by step, copy output → next input)

### Step 1 — States
```
GET /causelist/states
```
→ Copy `code` for your state (e.g. Bihar = `"8"`)

### Step 2 — Districts
```
POST /causelist/districts   { "state_code": "8" }
```
→ Copy `code` for your district (e.g. Buxar = `"26"`)

### Step 3 — Court Complexes
```
POST /causelist/complexes   { "state_code": "8", "dist_code": "26" }
```
→ Copy `code` for your complex (e.g. `"1080063@4@Y"`)

### Step 4 — Establishments
```
POST /causelist/establishments   { "state_code": "8", "dist_code": "26", "court_complex_code": "1080063@4@Y" }
```
→ Copy `code` for your establishment (e.g. `"4"`)

### Step 5 — Courts
```
POST /causelist/courts   { "state_code": "8", "dist_code": "26", "court_complex_code": "1080063@4@Y", "est_code": "4" }
```
→ Copy `code` for your court (e.g. `"4^2"`) and `name`

### Step 6 — Fetch Cause List
```
POST /causelist/fetch   { all above codes + "court_no": "4^2", "court_name": "...", "date": "22-03-2025", "list_type": "civil" }
```
→ Returns `cases[]` — each row has `view_history_url`, `case_no`, `cino`

---

## 🟡 Flow C — Case Detail from Cause List Row

### Option 1 — Easiest (paste the URL)
```
POST /case/from-url   { "view_history_url": "<paste view_history_url from cause list row>" }
```

### Option 2 — With individual fields
```
POST /case/history   { case_no, cino, court_code, state_code, dist_code, court_complex_code }
```
→ Returns full case details + `interim_orders[]` with `pdf_params`

---

## 🔴 Flow D — Download Court Order PDF

```
POST /case/order-pdf   { paste the entire pdf_params object from an interim_orders entry }
```
→ Returns `{ "pdf_url": "https://...reports/abc.pdf" }` — direct download link
""",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


# ── Pydantic Models ──────────────────────────────────────────────────────────
class CNRRequest(BaseModel):
    cnr_number: str = Field(..., example="BRAU010000972020",
                            description="16-digit alphanumeric CNR number")

class StateRequest(BaseModel):
    state_code: str = Field(..., example="8", description="State code from /causelist/states")

class DistrictRequest(BaseModel):
    state_code: str = Field(..., example="8")
    dist_code:  str = Field(..., example="26")

class ComplexRequest(BaseModel):
    state_code:         str = Field(..., example="8")
    dist_code:          str = Field(..., example="26")
    court_complex_code: str = Field(..., example="1080063@4@Y",
                                    description="Full complex code including @est@flag suffix")

class CourtRequest(BaseModel):
    state_code:         str = Field(..., example="8")
    dist_code:          str = Field(..., example="26")
    court_complex_code: str = Field(..., example="1080063@4@Y")
    est_code:           str = Field(..., example="4")

class CauseListRequest(BaseModel):
    state_code:         str = Field(..., example="8")
    dist_code:          str = Field(..., example="26")
    court_complex_code: str = Field(..., example="1080063@4@Y")
    est_code:           str = Field(..., example="4")
    court_no:           str = Field(..., example="4^2",
                                    description="Court code from /causelist/courts")
    court_name:         str = Field(..., example="2-Sri Vinit Kumar Singh-Civil Judge (Sr. Div.)-II")
    date:               str = Field(..., example="22-03-2025",
                                    description="Date in dd-mm-yyyy format")
    list_type:          str = Field("civil", example="civil",
                                    description="'civil' or 'criminal'")

class CaseHistoryRequest(BaseModel):
    case_no:             str = Field(..., example="203300000941999")
    cino:                str = Field(..., example="BRBU220000181999")
    court_code:          str = Field(..., example="4")
    state_code:          str = Field(..., example="8")
    dist_code:           str = Field(..., example="26")
    court_complex_code:  str = Field(..., example="1080063")

class CaseFromURLRequest(BaseModel):
    view_history_url: str = Field(
        ...,
        example="https://services.ecourts.gov.in/ecourtindia_v6/?p=home/viewHistory&court_code=4&state_code=8&dist_code=26&court_complex_code=1080063&case_no=203300000941999&cino=BRBU220000181999&search_flag=CLcauselist&search_by=CauseList",
        description="Copy the view_history_url directly from a cause list case row"
    )

class OrderPDFRequest(BaseModel):
    normal_v:   str = Field(..., description="Encrypted param from pdf_params in interim_orders")
    case_val:   str = Field(..., description="Encrypted param from pdf_params")
    court_code: str = Field(..., description="Encrypted param from pdf_params")
    filename:   str = Field(..., description="Encrypted param from pdf_params")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "active_sessions": list(_sessions.keys())}


# ────────────────────────────────────────────────────────────────────────────
# CNR SEARCH
# ────────────────────────────────────────────────────────────────────────────
@app.post("/cnr/search", tags=["CNR Search"],
          summary="Search case by CNR number",
          description="Solves CAPTCHA automatically. Returns full case details including history, parties, acts, FIR, interim orders.")
def cnr_search(body: CNRRequest):
    cnr = body.cnr_number.strip().upper()
    if len(cnr) != 16 or not cnr.isalnum():
        raise HTTPException(400, "CNR must be exactly 16 alphanumeric characters")

    captcha_src = ""
    token       = ""
    for attempt in range(1, 5):
        b64     = fetch_captcha_b64(CNR_HOME_URL, captcha_src)
        captcha = solve_captcha(b64, CNR_HOME_URL)
        resp    = ajax_post(CNR_HOME_URL, "cnr_status/searchByCNR",
                            {"cino": cnr, "fcaptcha_code": captcha,
                             "ajax_req": "true", "app_token": token})
        if is_captcha_bad(resp):
            new_src = extract_captcha_src(resp.get("div_captcha",""))
            if new_src: captcha_src = new_src
            if resp.get("app_token"): token = resp["app_token"]
            continue
        html = resp.get("casetype_list","") or resp.get("_raw","")
        if not html:
            raise HTTPException(422, "Empty response from eCourts server")
        result = parse_case_html(html, cnr)
        if resp.get("app_token"): token = resp["app_token"]
        return result
    raise HTTPException(422, "CAPTCHA rejected 4 times — check CapSolver balance")


# ────────────────────────────────────────────────────────────────────────────
# CAUSE LIST — CASCADE
# ────────────────────────────────────────────────────────────────────────────
@app.get("/causelist/states", tags=["Cause List"],
         summary="Get all states with their codes")
def causelist_states():
    return STATES


@app.post("/causelist/districts", tags=["Cause List"],
          summary="Get districts for a state")
def causelist_districts(body: StateRequest):
    resp = ajax_post(CL_HOME_URL, "casestatus/fillDistrict",
                     {"state_code": body.state_code, "ajax_req": "true", "app_token": ""})
    districts = parse_options(resp.get("dist_list",""))
    if not districts:
        raise HTTPException(404, f"No districts found for state_code={body.state_code}")
    return districts


@app.post("/causelist/complexes", tags=["Cause List"],
          summary="Get court complexes for a district")
def causelist_complexes(body: DistrictRequest):
    resp = ajax_post(CL_HOME_URL, "casestatus/fillcomplex",
                     {"state_code": body.state_code, "dist_code": body.dist_code,
                      "ajax_req": "true", "app_token": ""})
    complexes = parse_options(resp.get("complex_list",""))
    if not complexes:
        raise HTTPException(404, "No court complexes found")
    return complexes


@app.post("/causelist/establishments", tags=["Cause List"],
          summary="Get establishments for a court complex")
def causelist_establishments(body: ComplexRequest):
    complex_code = body.court_complex_code.split("@")[0]
    resp = ajax_post(CL_HOME_URL, "casestatus/fillCourtEstablishment",
                     {"state_code": body.state_code, "dist_code": body.dist_code,
                      "court_complex_code": complex_code,
                      "ajax_req": "true", "app_token": ""})
    ests = parse_options(resp.get("establishment_list",""))
    if not ests:
        raise HTTPException(404, "No establishments found")
    return ests


@app.post("/causelist/courts", tags=["Cause List"],
          summary="Get court names for an establishment")
def causelist_courts(body: CourtRequest):
    complex_code = body.court_complex_code.split("@")[0]
    resp = ajax_post(CL_HOME_URL, "cause_list/fillCauseList",
                     {"state_code": body.state_code, "dist_code": body.dist_code,
                      "court_complex_code": complex_code, "est_code": body.est_code,
                      "ajax_req": "true", "app_token": ""})
    courts = parse_options(resp.get("courtnumber_list") or resp.get("cause_list") or "")
    if not courts:
        raise HTTPException(404, "No courts found")
    return courts


@app.post("/causelist/fetch", tags=["Cause List"],
          summary="Fetch civil or criminal cause list",
          description="Solves CAPTCHA automatically. Returns list of cases, each with a `view_history_url` you can pass to POST /case/from-url.")
def causelist_fetch(body: CauseListRequest):
    cicri        = "civ" if body.list_type.lower() == "civil" else "cri"
    complex_code = body.court_complex_code.split("@")[0]
    prev_days    = selprevdays(body.date)
    captcha_src  = ""

    for attempt in range(1, 6):
        b64     = fetch_captcha_b64(CL_HOME_URL, captcha_src)
        captcha = solve_captcha(b64, CL_HOME_URL)
        payload = {
            "sess_state_code":         body.state_code,
            "sess_dist_code":          body.dist_code,
            "court_complex_code":      complex_code,
            "court_est_code":          body.est_code,
            "CL_court_no":             body.court_no,
            "causelist_date":          body.date,
            "fcaptcha_code":           captcha,
            "cause_list_captcha_code": captcha,
            "court_name_txt":          body.court_name,
            "state_code":              body.state_code,
            "dist_code":               body.dist_code,
            "est_code":                body.est_code,
            "cicri":                   cicri,
            "selprevdays":             prev_days,
            "ajax_req":                "true",
            "app_token":               "",
        }
        resp = ajax_post(CL_HOME_URL, "cause_list/submitCauseList", payload)
        print(f"[causelist/fetch] attempt={attempt} status={resp.get('status')} "
              f"keys={list(resp.keys())} raw_preview={str(resp.get('_raw',''))[:100]!r}")

        # Empty response = session expired or redirect — reset and retry
        if resp.get("_raw") == "" or resp.get("_error"):
            print(f"    [!] Empty/error response — resetting session and retrying")
            reset_session(CL_HOME_URL)
            captcha_src = ""
            continue

        if is_captcha_bad(resp):
            new_src = extract_captcha_src(resp.get("div_captcha",""))
            if new_src: captcha_src = new_src
            continue

        if resp.get("status") == 1:
            case_data = resp.get("case_data","")
            if not case_data:
                # No cases for this date/court — return empty result
                return {
                    "date": body.date, "type": body.list_type,
                    "court_name": body.court_name,
                    "cases": [], "total_cases": 0,
                    "message": "No cases found for this court and date."
                }
            return _parse_causelist_html(case_data, body, complex_code)

        # Some courts return status=0 with case_data (no captcha error, just no data)
        if resp.get("case_data") is not None:
            return _parse_causelist_html(resp.get("case_data",""), body, complex_code)

        raise HTTPException(422, f"Unexpected response status={resp.get('status')}: {str(resp)[:300]}")

    raise HTTPException(422, "CAPTCHA rejected / session failed after 5 attempts")


def _parse_causelist_html(html: str, body: CauseListRequest,
                           complex_code: str) -> dict:
    if not html:
        raise HTTPException(422, "Empty cause list HTML")
    soup = BeautifulSoup(html, "html.parser")
    result = {
        "date": body.date, "type": body.list_type,
        "court_name": body.court_name, "cases": [],
    }

    h = soup.find(["h2","h3","h4"])
    if h: result["heading"] = clean(h)

    pdfs = [{"text": clean(a), "url": a["href"]}
            for a in soup.find_all("a", href=re.compile(r"\.pdf", re.I))]
    if pdfs: result["pdf_links"] = pdfs

    table = soup.find("table")
    if not table:
        result["raw_text"] = soup.get_text(" ",strip=True)[:3000]
        return result

    rows    = table.find_all("tr")
    headers = [clean(c) for c in rows[0].find_all(["th","td"])] if rows else []
    current_section = ""
    cases = []

    for row in rows[1:]:
        cells = row.find_all("td")
        if not cells: continue
        if len(cells) == 1 and cells[0].get("colspan"):
            current_section = clean(cells[0])
            continue

        entry: dict = {"section": current_section}
        for i, cell in enumerate(cells):
            col = headers[i] if i < len(headers) else f"col_{i}"
            entry[col] = clean(cell)
            # Search full cell HTML for viewHistory — works on any element type
            cell_html = str(cell)
            vh_match  = re.search(r"viewHistory\s*\(([^)]+)\)", cell_html)
            if vh_match:
                # Confirmed format: viewHistory('case_no','cino',court_code,'','flag',state,dist,complex,'search_by')
                all_args = [a.strip().strip(chr(39)).strip(chr(34)) for a in vh_match.group(1).split(",")]
                if len(all_args) >= 3:
                    entry["case_no"]           = all_args[0]
                    entry["cino"]              = all_args[1]
                    entry["court_code_history"] = all_args[2]
                    entry["view_history_url"]  = (
                        f"{BASE_URL}/?p=home/viewHistory"
                        f"&court_code={all_args[2]}"
                        f"&state_code={body.state_code}"
                        f"&dist_code={body.dist_code}"
                        f"&court_complex_code={complex_code}"
                        f"&case_no={all_args[0]}&cino={all_args[1]}"
                        f"&search_flag=CLcauselist&search_by=CauseList"
                    )

        if any(v for k,v in entry.items()
               if v and k not in ("section","view_history_url","case_no",
                                   "cino","court_code_history")):
            cases.append(entry)

    result["cases"]       = cases
    result["total_cases"] = len(cases)
    return result


# ────────────────────────────────────────────────────────────────────────────
# CASE HISTORY  (from cause list "View" button)
# ────────────────────────────────────────────────────────────────────────────
def _do_view_history(case_no: str, cino: str, court_code: str,
                      state_code: str, dist_code: str,
                      court_complex_code: str) -> dict:
    payload = {
        "court_code":          court_code,
        "state_code":          state_code,
        "dist_code":           dist_code,
        "court_complex_code":  court_complex_code,
        "case_no":             case_no,
        "cino":                cino,
        "hideparty":           "",
        "search_flag":         "CLcauselist",
        "search_by":           "CauseList",
        "ajax_req":            "true",
        "app_token":           "",
    }
    resp = ajax_post(CNR_HOME_URL, "home/viewHistory", payload)
    if resp.get("status") != 1:
        raise HTTPException(422,
            f"viewHistory returned status={resp.get('status')} — {str(resp)[:200]}")
    html = resp.get("data_list","")
    if not html:
        raise HTTPException(422, "Empty data_list from viewHistory")
    return parse_case_html(html, cino)


@app.post("/case/history", tags=["Case History"],
          summary="Get full case details using case_no + cino + court codes",
          description="No CAPTCHA needed. Copy values from a cause list case row.")
def case_history(body: CaseHistoryRequest):
    return _do_view_history(
        body.case_no, body.cino, body.court_code,
        body.state_code, body.dist_code, body.court_complex_code)


@app.post("/case/from-url", tags=["Case History"],
          summary="Get full case details by pasting the view_history_url",
          description="Easiest option — just copy the `view_history_url` from a cause list case row and paste it here.")
def case_from_url(body: CaseFromURLRequest):
    parsed = urlparse(body.view_history_url)
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    required = ["case_no","cino","court_code","state_code","dist_code","court_complex_code"]
    missing  = [f for f in required if not params.get(f)]
    if missing:
        raise HTTPException(400, f"URL missing params: {missing}")
    return _do_view_history(
        params["case_no"], params["cino"], params["court_code"],
        params["state_code"], params["dist_code"], params["court_complex_code"])


@app.post("/case/order-pdf", tags=["Case History"],
          summary="Download court order PDF",
          description="Copy `pdf_params` from an `interim_orders` entry. Returns the PDF file directly — the resolved URL is a one-time token that expires immediately, so bytes are fetched server-side.")
def case_order_pdf(body: OrderPDFRequest):
    from fastapi.responses import StreamingResponse
    import io

    payload = {
        "normal_v":   body.normal_v,
        "case_val":   body.case_val,
        "court_code": body.court_code,
        "filename":   body.filename,
        "appFlag":    "",
        "ajax_req":   "true",
        "app_token":  "",
    }
    resp = ajax_post(CNR_HOME_URL, "home/display_pdf", payload)
    pdf_path = resp.get("order","").strip()
    if not pdf_path:
        raise HTTPException(422, f"No PDF path returned: {str(resp)[:200]}")

    pdf_url = f"{BASE_URL}/{pdf_path}"
    print(f"[order-pdf] Resolved URL: {pdf_url} — fetching bytes now")

    # Must use the same session that resolved the token
    session = get_session(CNR_HOME_URL)
    pdf_resp = session.get(
        pdf_url,
        headers={**BASE_HEADERS, "Referer": CNR_HOME_URL},
        timeout=30,
    )

    print(f"[order-pdf] PDF fetch → HTTP {pdf_resp.status_code}  "
          f"Content-Type={pdf_resp.headers.get('Content-Type','?')}  "
          f"len={len(pdf_resp.content)}")

    if pdf_resp.status_code != 200:
        raise HTTPException(502, f"PDF fetch failed: HTTP {pdf_resp.status_code}")

    content_type = pdf_resp.headers.get("Content-Type", "application/pdf")
    if "html" in content_type.lower() or len(pdf_resp.content) < 100:
        raise HTTPException(422, f"PDF response looks invalid — got HTML or empty body. "
                                 f"Content-Type={content_type} len={len(pdf_resp.content)}")

    filename = pdf_path.split("/")[-1]
    return StreamingResponse(
        io.BytesIO(pdf_resp.content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Bonus: fetch by CINO only (no case_no needed) ────────────────────────────
class CinoCaseRequest(BaseModel):
    cino: str = Field(
        ..., example="BRAU110008762020",
        description="Copy the `cino` field directly from a cause list case row. Works exactly like CNR search — CAPTCHA solved automatically."
    )

@app.post("/case/by-cino", tags=["Case History"],
          summary="Get full case details using only the cino from a cause list row",
          description="Simplest option — just copy `cino` from any cause list row. Solves CAPTCHA automatically via CapSolver. Returns identical result to /cnr/search.")
def case_by_cino(body: CinoCaseRequest):
    """
    cino IS the CNR number — they're the same thing.
    This endpoint is an alias for /cnr/search that accepts
    the field name as returned by /causelist/fetch rows.
    """
    cino = body.cino.strip().upper()
    if not cino:
        raise HTTPException(400, "cino is required")

    captcha_src = ""
    token       = ""
    for attempt in range(1, 5):
        b64     = fetch_captcha_b64(CNR_HOME_URL, captcha_src)
        captcha = solve_captcha(b64, CNR_HOME_URL)
        resp    = ajax_post(CNR_HOME_URL, "cnr_status/searchByCNR",
                            {"cino": cino, "fcaptcha_code": captcha,
                             "ajax_req": "true", "app_token": token})
        if is_captcha_bad(resp):
            new_src = extract_captcha_src(resp.get("div_captcha",""))
            if new_src: captcha_src = new_src
            if resp.get("app_token"): token = resp["app_token"]
            continue
        html = resp.get("casetype_list","") or resp.get("_raw","")
        if not html:
            raise HTTPException(422, "Empty response from eCourts")
        result = parse_case_html(html, cino)
        if resp.get("app_token"): token = resp["app_token"]
        return result
"""
eCourts India — Phase 2: Case Status Search
Append this block to ecourts_fastapi_scrapper_v2.py

New endpoints:
  Case Status Search (all require state→district→complex→establishment cascade first)
    POST /casestatus/police-stations     → police stations for a complex (FIR search only)
    POST /casestatus/by-party            → search by petitioner/respondent name
    POST /casestatus/by-filing           → search by filing number + year
    POST /casestatus/by-advocate         → search by advocate name / bar code / date case list
    POST /casestatus/by-fir              → search by FIR number + police station + year

  Each returns a list of matching cases, each with a view_history_url
  passable to POST /case/from-url (already exists in Phase 1)
"""

# ──────────────────────────────────────────────────────────────────────────────
# PHASE 2 CONFIG
# ──────────────────────────────────────────────────────────────────────────────
CS_HOME_URL = f"{BASE_URL}/?p=casestatus/index"


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 2 — Pydantic Models
# ──────────────────────────────────────────────────────────────────────────────

class CaseStatusBase(BaseModel):
    """
    Common location fields required by every case status search.
    Use the same cascade as Phase 1 (states → districts → complexes → establishments).
    Pass the BARE complex code here (strip @ suffix).
    """
    state_code:         str = Field(..., example="8",
                                    description="From GET /causelist/states")
    dist_code:          str = Field(..., example="1",
                                    description="From POST /causelist/districts")
    court_complex_code: str = Field(..., example="1080001",
                                    description="Bare complex code — strip @ suffix from /causelist/complexes")
    est_code:           str = Field(..., example="4",
                                    description="From POST /causelist/establishments")


class PoliceStationRequest(CaseStatusBase):
    pass


class PartyNameRequest(CaseStatusBase):
    party_name:        str = Field(..., example="MEGMA FINE CO LTD",
                                   description="Petitioner or respondent name (partial match supported)")
    registration_year: str = Field(..., example="2017",
                                   description="4-digit registration year")
    case_status:       str = Field("Pending", example="Pending",
                                   description="'Pending', 'Disposed', or 'Both'")


class FilingNumberRequest(CaseStatusBase):
    filing_number: str = Field(..., example="16",
                               description="Filing number (numeric)")
    filing_year:   str = Field(..., example="2017",
                               description="4-digit filing year")


class AdvocateRequest(BaseModel):
    """
    Three search modes — set search_by to select which one:

    ┌─────────────────┬──────────────────────────────────────────────────────┐
    │ search_by       │ Required fields                                      │
    ├─────────────────┼──────────────────────────────────────────────────────┤
    │ "name"          │ advocate_name + case_status                          │
    │ "code"          │ advocate_code + advocate_year + case_status          │
    │ "date_caselist" │ advocate_code + advocate_year + caselist_date        │
    └─────────────────┴──────────────────────────────────────────────────────┘

    All modes also require the 4 location fields (state/dist/complex/est).
    """
    # ── location (same cascade as Phase 1) ───────────────────────────────────
    state_code:         str = Field(..., example="8")
    dist_code:          str = Field(..., example="1")
    court_complex_code: str = Field(..., example="1080001",
                                    description="Bare complex code — strip @ suffix")
    est_code:           str = Field(..., example="4")

    # ── mode selector ────────────────────────────────────────────────────────
    search_by: str = Field(
        "name",
        example="name",
        description=(
            "'name'          → search by advocate name (+ case_status)\n"
            "'code'          → search by bar code + year (+ case_status)\n"
            "'date_caselist' → search by bar code + year + caselist_date"
        ),
    )

    # ── mode: name ───────────────────────────────────────────────────────────
    advocate_name: str = Field(
        "",
        example="Sharma",
        description="[name mode] Advocate name — partial match supported",
    )

    # ── mode: code / date_caselist ───────────────────────────────────────────
    advocate_state_code: str = Field(
        "",
        example="BR",
        description="[code / date_caselist mode] State portion of bar code (e.g. 'BR')",
    )
    advocate_code: str = Field(
        "",
        example="1234",
        description="[code / date_caselist mode] Bar code number",
    )
    advocate_year: str = Field(
        "",
        example="2010",
        description="[code / date_caselist mode] Bar code registration year",
    )

    # ── mode: date_caselist only ─────────────────────────────────────────────
    caselist_date: str = Field(
        "",
        example="20-03-2026",
        description="[date_caselist mode] Case list date in dd-mm-yyyy format",
    )

    # ── mode: name / code (not used by date_caselist) ────────────────────────
    case_status: str = Field(
        "Pending",
        example="Pending",
        description="[name / code mode] 'Pending', 'Disposed', or 'Both'",
    )


class FIRRequest(CaseStatusBase):
    police_station_code: str = Field(..., example="29-5137032",
                                     description="Full code from POST /casestatus/police-stations in format 'statepart-uniformcode'")
    ps_state_code:       str = Field("",  example="29",
                                     description="Numeric state part of police station code (before the dash). Auto-extracted from police_station_code if not provided.")
    ps_uniform_code:     str = Field("",  example="5137032",
                                     description="Uniform code part (after the dash). Auto-extracted from police_station_code if not provided.")
    fir_number:          str = Field("",  example="123",
                                     description="FIR number (can be empty to list all cases for a police station)")
    fir_year:            str = Field("",  example="2018",
                                     description="4-digit FIR year (can be empty)")
    case_status:         str = Field("Both", example="Both",
                                     description="'Pending', 'Disposed', or 'Both'")


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _case_status_flag(case_status: str) -> str:
    """Convert human-readable status to eCourts flag value."""
    return {"pending": "Pending", "disposed": "Disposed", "both": "Both"}.get(
        case_status.lower(), "Pending"
    )


def _parse_casestatus_html(html: str,
                            state_code: str,
                            dist_code: str,
                            court_complex_code: str) -> list[dict]:
    """
    Parse the case list table returned by all case status searches.
    Returns a list of case rows, each with a view_history_url.
    """
    soup  = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []

    rows = table.find_all("tr")
    if not rows:
        return []

    headers = [clean(c) for c in rows[0].find_all(["th", "td"])]
    cases   = []

    for row in rows[1:]:
        cells = row.find_all("td")
        if not cells:
            continue

        entry: dict = {}
        for i, cell in enumerate(cells):
            col        = headers[i] if i < len(headers) else f"col_{i}"
            entry[col] = clean(cell)

            cell_html = str(cell)
            vh_match  = re.search(r"viewHistory\s*\(([^)]+)\)", cell_html)
            if vh_match:
                raw_args = re.findall(r"'([^']*)'|(\d+)", vh_match.group(1))
                args     = [a or b for a, b in raw_args]
                if len(args) >= 2:
                    case_no    = args[0]
                    cino       = args[1]
                    court_code = args[2] if len(args) > 2 else ""
                    entry["case_no"]            = case_no
                    entry["cino"]               = cino
                    entry["court_code_history"] = court_code
                    entry["view_history_url"]   = (
                        f"{BASE_URL}/?p=home/viewHistory"
                        f"&court_code={court_code}"
                        f"&state_code={state_code}"
                        f"&dist_code={dist_code}"
                        f"&court_complex_code={court_complex_code}"
                        f"&case_no={case_no}&cino={cino}"
                        f"&search_flag=CaseSearch&search_by=CaseStatus"
                    )

        if any(v for k, v in entry.items()
               if v and k not in ("view_history_url", "case_no",
                                  "cino", "court_code_history")):
            cases.append(entry)

    return cases


def _run_casestatus_search(endpoint: str,
                            payload: dict,
                            state_code: str,
                            dist_code: str,
                            court_complex_code: str,
                            captcha_field: str = "fcaptcha_code",
                            html_key: str | None = None) -> dict:
    """
    Shared execution wrapper for all case status search types.
    Handles CAPTCHA retry, parses result HTML, returns structured response.

    captcha_field: name of the captcha POST field (varies per search type)
      party search    → "fcaptcha_code"
      advocate search → "adv_captcha_code"
      filing search   → TBC
      FIR search      → TBC

    html_key: response JSON key containing the case list HTML (varies per type)
      party search    → "party_data"
      advocate search → "adv_data"
      filing search   → TBC
      FIR search      → TBC
    """
    # Always use bare complex code (strip @est@flag suffix if caller forgot)
    bare_complex = court_complex_code.split("@")[0]
    payload["court_complex_code"] = bare_complex
    captcha_src = ""

    for attempt in range(1, 6):
        b64     = fetch_captcha_b64(CS_HOME_URL, captcha_src)
        captcha = solve_captcha(b64, CS_HOME_URL)

        full_payload = {
            **payload,
            captcha_field: captcha,   # use correct captcha field name per search type
            "ajax_req":    "true",
            "app_token":   "",
        }

        resp = ajax_post(CS_HOME_URL, endpoint, full_payload)

        print(f"[casestatus] {endpoint} attempt={attempt} "
              f"status={resp.get('status')} keys={list(resp.keys())}")

        if resp.get("_raw") == "" or resp.get("_error"):
            reset_session(CS_HOME_URL)
            captcha_src = ""
            continue

        if is_captcha_bad(resp):
            new_src = extract_captcha_src(resp.get("div_captcha", ""))
            if new_src:
                captcha_src = new_src
            continue

        # Log all keys so we can identify the correct one during testing
        print(f"[casestatus] response keys={list(resp.keys())} "
              f"status={resp.get('status')}")
        for k, v in resp.items():
            if isinstance(v, str) and len(v) > 50 and k not in ("div_captcha",):
                print(f"  [casestatus] candidate key='{k}' preview={v[:120]!r}")

        # Use caller-specified key first, then fall back to known variants
        html = ""
        if html_key:
            html = resp.get(html_key, "")
        if not html:
            # Confirmed keys: party_data, adv_data
            # TBC keys for filing + FIR — update after network tab inspection
            html = (resp.get("party_data")
                    or resp.get("adv_data")
                    or resp.get("filing_data")
                    or resp.get("fir_data")
                    or resp.get("case_list")
                    or resp.get("casetype_list")
                    or resp.get("case_data")
                    or resp.get("data_list")
                    or resp.get("_raw")
                    or "")

        if not html:
            return {"cases": [], "total_cases": 0,
                    "message": "No cases found."}

        cases = _parse_casestatus_html(
            html, state_code, dist_code, court_complex_code
        )
        return {"cases": cases, "total_cases": len(cases)}

    raise HTTPException(422, "CAPTCHA rejected after 5 attempts")


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 2 — Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/casestatus/police-stations", tags=["Case Status Search"],
          summary="Get police stations for a court complex (required for FIR search)",
          description="""
Returns list of police stations for the given court complex.
Each entry has `code` and `name`.

The `code` is in format `'statepart-uniformcode'` e.g. `'29-5137032'`.
Pass it directly as `police_station_code` to `POST /casestatus/by-fir`.
""")
def casestatus_police_stations(body: PoliceStationRequest):
    bare_complex = body.court_complex_code.split("@")[0]

    resp = ajax_post(
        CS_HOME_URL,
        "casestatus/fillPoliceStation",
        {
            "state_code":         body.state_code,
            "dist_code":          body.dist_code,
            "court_complex_code": bare_complex,
            "est_code":           body.est_code,
            "ajax_req":           "true",
            "app_token":          "",
        },
    )
    print(f"[police-stations] keys={list(resp.keys())}")
    for k, v in resp.items():
        if isinstance(v, str) and len(v) > 20:
            print(f"  [police-stations] [{k}] preview={v[:200]!r}")

    raw_html = (
        resp.get("police_data")
        or resp.get("police_station_list")
        or resp.get("policestation_list")
        or resp.get("police_list")
        or resp.get("_raw")
        or ""
    )

    # parse_options gets code+name from <option> tags
    stations = parse_options(raw_html)

    if not stations:
        raise HTTPException(404,
            f"No police stations found. "
            f"Response keys={list(resp.keys())} "
            f"raw preview={raw_html[:150]!r}")

    # Each station code from eCourts is "statepart-uniformcode" e.g. "29-5137032"
    # Enrich each entry with the split parts for convenience
    enriched = []
    for s in stations:
        parts = s["code"].split("-", 1)
        enriched.append({
            "code":         s["code"],          # full "29-5137032" → pass to by-fir
            "name":         s["name"],
            "ps_state_code":  parts[0] if len(parts) >= 2 else s["code"],
            "ps_uniform_code": parts[1] if len(parts) >= 2 else "",
        })
    return enriched


@app.post("/casestatus/by-party", tags=["Case Status Search"],
          summary="Search cases by party name (petitioner or respondent)",
          description="""
Requires state→district→complex→establishment codes from the Phase 1 cascade.

- `party_name`: partial name match supported
- `registration_year`: 4-digit year e.g. `"2017"`
- `case_status`: `"Pending"`, `"Disposed"`, or `"Both"`

Returns list of matching cases each with `view_history_url` →
pass to `POST /case/from-url` to get full case details.
""")
def casestatus_by_party(body: PartyNameRequest):
    payload = {
        "state_code":         body.state_code,
        "dist_code":          body.dist_code,
        "court_complex_code": body.court_complex_code.split("@")[0],
        "est_code":           body.est_code,
        "petres_name":        body.party_name,    # confirmed field name from network tab
        "rgyearP":            body.registration_year,  # confirmed field name
        "case_status":        _case_status_flag(body.case_status),  # confirmed field name
    }
    return _run_casestatus_search(
        "casestatus/submitPartyName",
        payload,
        body.state_code, body.dist_code, body.court_complex_code,
    )


@app.post("/casestatus/by-filing", tags=["Case Status Search"],
          summary="Search cases by filing number and year",
          description="""
Requires state→district→complex→establishment codes from the Phase 1 cascade.

- `filing_number`: numeric filing number e.g. `"16"`
- `filing_year`: 4-digit year e.g. `"2017"`

Returns list of matching cases each with `view_history_url`.
""")
def casestatus_by_filing(body: FilingNumberRequest):
    bare_complex = body.court_complex_code.split("@")[0]
    payload = {
        "state_code":         body.state_code,
        "dist_code":          body.dist_code,
        "court_complex_code": bare_complex,
        "est_code":           body.est_code,
        "case_type":          "",          # always empty
        "filing_no":          body.filing_number,   # confirmed field name
        "filyear":            body.filing_year,     # confirmed field name
    }
    return _run_casestatus_search(
        "casestatus/submitFillingNo",
        payload,
        body.state_code, body.dist_code, bare_complex,
        captcha_field="file_captcha_code",   # confirmed captcha field name
        html_key="filing_data",              # confirmed response key
    )


@app.post("/casestatus/by-advocate", tags=["Case Status Search"],
          summary="Search cases by advocate — name, bar code, or date case list",
          description="""
Three modes controlled by `search_by`:

| `search_by`      | What to provide                                        |
|------------------|--------------------------------------------------------|
| `"name"`         | `advocate_name` + `case_status`                        |
| `"code"`         | `advocate_state_code` + `advocate_code` + `advocate_year` + `case_status` |
| `"date_caselist"`| `advocate_state_code` + `advocate_code` + `advocate_year` + `caselist_date` (dd-mm-yyyy) |

All modes require the 4 location fields from the Phase 1 cascade.
Returns list of matching cases each with `view_history_url`.
""")
def casestatus_by_advocate(body: AdvocateRequest):

    bare_complex = body.court_complex_code.split("@")[0]

    # ── mode: name (radAdvt=1) ────────────────────────────────────────────────
    if body.search_by == "name":
        if not body.advocate_name:
            raise HTTPException(400, "advocate_name is required when search_by='name'")
        payload = {
            "state_code":         body.state_code,
            "dist_code":          body.dist_code,
            "court_complex_code": bare_complex,
            "est_code":           body.est_code,
            "radAdvt":            "1",               # radio: Advocate Name
            "advocate_name":      body.advocate_name,
            "adv_bar_state":      "",
            "adv_bar_code":       "",
            "adv_bar_year":       "",
            "case_status":        _case_status_flag(body.case_status),
            "caselist_date":      "",
            "case_type":          "",
        }
        return _run_casestatus_search(
            "casestatus/submitAdvName",
            payload,
            body.state_code, body.dist_code, bare_complex,
            captcha_field="adv_captcha_code",
            html_key="adv_data",
        )

    # ── mode: code (radAdvt=2) ────────────────────────────────────────────────
    elif body.search_by == "code":
        if not body.advocate_code:
            raise HTTPException(400, "advocate_code is required when search_by='code'")
        payload = {
            "state_code":         body.state_code,
            "dist_code":          body.dist_code,
            "court_complex_code": bare_complex,
            "est_code":           body.est_code,
            "radAdvt":            "2",               # radio: Bar Code
            "advocate_name":      "",
            "adv_bar_state":      body.advocate_state_code,
            "adv_bar_code":       body.advocate_code,
            "adv_bar_year":       body.advocate_year,
            "case_status":        _case_status_flag(body.case_status),
            "caselist_date":      "",
            "case_type":          "",
        }
        return _run_casestatus_search(
            "casestatus/submitAdvName",
            payload,
            body.state_code, body.dist_code, bare_complex,
            captcha_field="adv_captcha_code",
            html_key="adv_data",
        )

    # ── mode: date_caselist (radAdvt=3) ──────────────────────────────────────
    elif body.search_by == "date_caselist":
        if not body.advocate_code:
            raise HTTPException(400, "advocate_code is required when search_by='date_caselist'")
        if not body.caselist_date:
            raise HTTPException(400, "caselist_date is required (format: dd-mm-yyyy)")
        payload = {
            "state_code":         body.state_code,
            "dist_code":          body.dist_code,
            "court_complex_code": bare_complex,
            "est_code":           body.est_code,
            "radAdvt":            "3",               # radio: Date Case List
            "advocate_name":      "",
            "adv_bar_state":      body.advocate_state_code,
            "adv_bar_code":       body.advocate_code,
            "adv_bar_year":       body.advocate_year,
            "case_status":        "",
            "caselist_date":      body.caselist_date,  # dd-mm-yyyy
            "case_type":          "",
        }
        return _run_casestatus_search(
            "casestatus/submitAdvName",
            payload,
            body.state_code, body.dist_code, bare_complex,
            captcha_field="adv_captcha_code",
            html_key="adv_data",
        )

    else:
        raise HTTPException(
            400,
            f"Invalid search_by='{body.search_by}'. "
            "Must be 'name', 'code', or 'date_caselist'."
        )


@app.post("/casestatus/by-fir", tags=["Case Status Search"],
          summary="Search cases by FIR number, police station, and year",
          description="""
Requires state→district→complex→establishment codes from the Phase 1 cascade.
Also requires `police_station_code` from `POST /casestatus/police-stations`.

- `fir_number`: FIR number e.g. `"123"`
- `fir_year`: 4-digit year e.g. `"2017"`
- `case_status`: `"Pending"`, `"Disposed"`, or `"Both"`

Returns list of matching cases each with `view_history_url`.
""")
def casestatus_by_fir(body: FIRRequest):
    bare_complex = body.court_complex_code.split("@")[0]

    # Split police_station_code "29-5137032" into parts
    # OR use explicitly provided ps_state_code + ps_uniform_code
    if body.ps_state_code and body.ps_uniform_code:
        ps_state     = body.ps_state_code
        uniform_code = body.ps_uniform_code
    else:
        ps_parts     = body.police_station_code.split("-", 1)
        ps_state     = ps_parts[0] if len(ps_parts) >= 2 else body.police_station_code
        uniform_code = ps_parts[1] if len(ps_parts) >= 2 else ""

    print(f"[by-fir] police_st_code={ps_state!r} uniform_code={uniform_code!r} "
          f"fir_no={body.fir_number!r} firyear={body.fir_year!r}")

    payload = {
        "state_code":         body.state_code,
        "dist_code":          body.dist_code,
        "court_complex_code": bare_complex,
        "est_code":           body.est_code,
        "police_st_code":     ps_state,       # numeric only e.g. "29"
        "uniform_code":       uniform_code,    # e.g. "5137032"
        "fir_no":             body.fir_number,
        "firyear":            body.fir_year,
        "case_status":        _case_status_flag(body.case_status),
    }
    return _run_casestatus_search(
        "casestatus/submitFirNo",
        payload,
        body.state_code, body.dist_code, bare_complex,
        captcha_field="fir_captcha_code",
        html_key="case_data",
    )
