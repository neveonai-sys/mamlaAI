"""
sci_fastapi_scrapper.py — Supreme Court of India (SCI) broad case-search scraper.

Mounted by main.py as a sibling to /dc, /hc, /sc:
    from sci_fastapi_scrapper import app as sci_app
    app.mount("/sci", sci_app)

Scope: Case Status (case-number / diary-number / party-name / AOR-code),
Cause List (today / tomorrow / by-date), Daily Orders, Judgments, Office
Reports — against www.sci.gov.in.

--------------------------------------------------------------------------
REBUILT 2026-07 — legacy domains retired, live-traced against the real site
--------------------------------------------------------------------------
The original version of this module targeted `main.sci.gov.in` (session
priming) / `webapi.sci.gov.in` (JSON REST API). Both are now dead ends:
`main.sci.gov.in` no longer resolves at all (NXDOMAIN, confirmed against
public DNS), and `webapi.sci.gov.in`, while it still resolves, timed out on
every connection attempt from this environment. The Supreme Court's entire
public site has since been rebuilt on WordPress at `www.sci.gov.in`, with a
custom `sci-api` mu-plugin replacing the old REST backend.

CONFIRMED LIVE (via direct HTTP trace against www.sci.gov.in, 2026-07-16):
  - Each search mode is its own WordPress page (e.g. /case-status-case-no/,
    /case-status-diary-no/, /daily-order-case-no/, /judgements-judge/ ...),
    each embedding a `<form id="sciapi-services-...">` with hidden fields
    `scid`, a dynamically-named `tok_<hash>` field, `sci_form_nonce`,
    `_wp_http_referer`, `_form_time`, `_form_signature`, `es_ajax_request`.
  - Captcha is Securimage-WP: image at `{BASE}/?_siwp_captcha&id=<scid>`.
    Despite the different widget, the image itself is still a **math**
    expression (e.g. "9 + 5") — confirmed by fetching and viewing a live
    captcha image — so the existing math-eval + CapSolver OCR approach
    carries over unchanged.
  - All searches submit via a single shared endpoint:
    `POST {BASE}/wp-admin/admin-ajax.php` as a classic WordPress AJAX call
    (form-urlencoded body, NOT JSON), with `action=<mode-specific action>`,
    `language=en`, `siwp_captcha_value=<solved answer>`, all the harvested
    hidden fields, and the mode's own visible fields. Response envelope is
    `{"success": bool, "data": ...}` — confirmed live with a deliberately
    wrong captcha answer, which returned
    `{"success": false, "data": "{\\"message\\": \\"The captcha code entered
    was incorrect.\\"}"}` (a JSON *string* inside `data`, matching the site's
    own `$.parseJSON(response.data)` client-side handling).
  - On success, `data` carries an HTML fragment (`resultsHtml` or the string
    itself) meant to be injected into the DOM — there is no structured JSON
    result shape anymore. This module parses that HTML back into the flat
    dict shape the Django proxy / React frontend already expect (see
    `_normalize_row`), so no changes are needed downstream of this file.

UNVERIFIED — could not be completed from this environment (no CapSolver key
configured here, so no live captcha could actually be solved end-to-end):
  - The exact results-table column headers/markup on a genuine *successful*
    search. `_normalize_row` maps by keyword-matching header text, which is
    robust to minor label variation but unverified against real data.
  - The multi-tab case-detail drill-down (`action=get_case_details`, seen
    wired to `.viewCnrDetails`/`.caseDetailsTabHeading` clicks client-side)
    that the live site uses to lazily fetch hearing-history/orders sub-tabs.
    The `tab_name` values it expects were not discoverable without a solved
    captcha to reach that UI state, so `hearing_history`/`orders` are
    returned as empty lists rather than guessed at.
  - `judgments/by-party` — the new site has no party-name judgments page
    (only case-no / diary-no / judge / judgement-date). The endpoint is
    kept for API-surface compatibility but returns a clear 502 explaining
    the portal no longer offers this search rather than fabricating data.

Treat every parsed field as provisional until reconciled against a live,
captcha-solved trace (set CAPSOLVER_API_KEY and re-run against a known real
case). Debug logging is left on deliberately for that reconciliation pass.
--------------------------------------------------------------------------
"""

import base64
import io
import json
import logging
import re
from typing import Optional

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ecourts_fastapi_scrapper_cnr_and_causelist_casestatus_and_courtstatus import (
    solve_captcha as _capsolver_solve_captcha,
)

log = logging.getLogger("sci_scraper")

# ============================================================================
# CONFIG
# ============================================================================

BASE = "https://www.sci.gov.in"
AJAX_URL = f"{BASE}/wp-admin/admin-ajax.php"
IMPERSONATE = "chrome110"

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}
AJAX_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE,
}

# page slug (under BASE) that bootstraps each search mode's hidden
# fields + captcha, and the admin-ajax.php `action` it submits to —
# both confirmed via a live HTTP trace, see module docstring.
_PAGE = {
    "case_no": "case-status-case-no",
    "diary_no": "case-status-diary-no",
    "party_name": "case-status-party-name",
    "aor_code": "case-status-aor-code",
    "cause_list": "cause-list",
    "daily_order_case_no": "daily-order-case-no",
    "daily_order_diary_no": "daily-order-diary-no",
    "judgements_case_no": "judgements-case-no",
    "judgements_judgement_date": "judgements-judgement-date",
    "office_report_case_no": "office-report-case-no",
    "office_report_diary_no": "office-report-diary-no",
}

_ACTION = {
    "case_no": "get_case_status_case_no",
    "diary_no": "get_case_status_diary_no",
    "party_name": "get_case_status_party_name",
    "aor_code": "get_case_status_aor_code",
    "cause_list": "get_causes",
    "daily_order_case_no": "get_daily_order_case_no",
    "daily_order_diary_no": "get_daily_order_diary_no",
    "judgements_case_no": "get_judgements_case_no",
    "judgements_judgement_date": "get_judgements_judgement_date",
    "office_report_case_no": "get_office_report_case_no",
    "office_report_diary_no": "get_office_report_diary_no",
}

# Scraped live from the /case-status-case-no/ page's `<select id="case_type">`.
CASE_TYPES = [
    {"code": "1", "label": "SPECIAL LEAVE PETITION (CIVIL)"},
    {"code": "2", "label": "SPECIAL LEAVE PETITION (CRIMINAL)"},
    {"code": "3", "label": "CIVIL APPEAL"},
    {"code": "4", "label": "CRIMINAL APPEAL"},
    {"code": "5", "label": "WRIT PETITION (CIVIL)"},
    {"code": "6", "label": "WRIT PETITION(CRIMINAL)"},
    {"code": "7", "label": "TRANSFER PETITION (CIVIL)"},
    {"code": "8", "label": "TRANSFER PETITION (CRIMINAL)"},
    {"code": "9", "label": "REVIEW PETITION (CIVIL)"},
    {"code": "10", "label": "REVIEW PETITION (CRIMINAL)"},
    {"code": "11", "label": "TRANSFERRED CASE (CIVIL)"},
    {"code": "12", "label": "TRANSFERRED CASE (CRIMINAL)"},
    {"code": "13", "label": "SPECIAL LEAVE TO PETITION (CIVIL)..."},
    {"code": "14", "label": "SPECIAL LEAVE TO PETITION (CRIMINAL)..."},
    {"code": "15", "label": "WRIT TO PETITION (CIVIL)..."},
    {"code": "16", "label": "WRIT TO PETITION (CRIMINAL)..."},
    {"code": "17", "label": "ORIGINAL SUIT"},
    {"code": "18", "label": "DEATH REFERENCE CASE"},
    {"code": "19", "label": "CONTEMPT PETITION (CIVIL)"},
    {"code": "20", "label": "CONTEMPT PETITION (CRIMINAL)"},
    {"code": "21", "label": "TAX REFERENCE CASE"},
    {"code": "22", "label": "SPECIAL REFERENCE CASE"},
    {"code": "23", "label": "ELECTION PETITION (CIVIL)"},
    {"code": "24", "label": "ARBITRATION PETITION"},
    {"code": "25", "label": "CURATIVE PETITION(CIVIL)"},
    {"code": "26", "label": "CURATIVE PETITION(CRL)"},
    {"code": "27", "label": "REF. U/A 317(1)"},
    {"code": "28", "label": "MOTION(CRL)"},
    {"code": "31", "label": "DIARYNO AND DIARYYR"},
    {"code": "32", "label": "SUO MOTO WRIT PETITION(CIVIL)"},
    {"code": "33", "label": "SUO MOTO WRIT PETITION(CRIMINAL)"},
    {"code": "34", "label": "SUO MOTO CONTEMPT PETITION(CIVIL)"},
    {"code": "35", "label": "SUO MOTO CONTEMPT PETITION(CRIMINAL)"},
    {"code": "37", "label": "REF. U/S 14 RTI"},
    {"code": "38", "label": "REF. U/S 17 RTI"},
    {"code": "39", "label": "MISCELLANEOUS APPLICATION"},
    {"code": "40", "label": "SUO MOTO TRANSFER PETITION(CIVIL)"},
    {"code": "41", "label": "SUO MOTO TRANSFER PETITION(CRIMINAL)"},
    {"code": "9999", "label": "Unknown"},
]

# Single shared session — SCI is one domain, no cascading state like DC's
# state→district→complex→establishment hierarchy, so (unlike the DC scraper's
# per-home-url session pool) one module-global session is enough.
_sci_session: Optional[cffi_requests.Session] = None


def get_session() -> cffi_requests.Session:
    global _sci_session
    if _sci_session is None:
        _sci_session = cffi_requests.Session(impersonate=IMPERSONATE)
        _sci_session.headers.update(BASE_HEADERS)
    return _sci_session


class SCIError(Exception):
    pass


# ============================================================================
# MATH CAPTCHA SOLVER (Securimage-WP image, arithmetic expression)
# ============================================================================

_MATH_EXPR_RE = re.compile(r"(\d+)\s*([+\-xX*])\s*(\d+)")


def _evaluate_math_captcha(expr_text: str) -> str:
    """
    Turn OCR'd text like "7 - 3" or "4 x 2" into the numeric answer string.
    Raises SCIError if the expression can't be parsed — caller should retry
    with a fresh captcha image rather than guess.
    """
    m = _MATH_EXPR_RE.search(expr_text.replace("—", "-").replace("–", "-"))
    if not m:
        raise SCIError(f"Could not parse math captcha text: {expr_text!r}")
    a, op, b = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    if op == "+":
        return str(a + b)
    if op == "-":
        return str(a - b)
    return str(a * b)  # 'x' or '*'


def _solve_captcha(session: cffi_requests.Session, scid: str) -> str:
    img_url = f"{BASE}/?_siwp_captcha&id={scid}"
    resp = session.get(img_url, timeout=20)
    resp.raise_for_status()
    b64 = base64.b64encode(resp.content).decode()
    expr_text = _capsolver_solve_captcha(b64, BASE)
    return _evaluate_math_captcha(expr_text)


# ============================================================================
# BOOTSTRAP + SUBMIT — shared by every search mode
# ============================================================================


def _bootstrap(session: cffi_requests.Session, page_slug: str) -> dict:
    """
    Load a search-mode's page and harvest every hidden field its form
    submits (scid, the dynamically-named tok_<hash> field, sci_form_nonce,
    _wp_http_referer, _form_time, _form_signature, es_ajax_request).
    Raises SCIError if the sciapi-services form isn't found — the page
    structure has changed and this needs a fresh live-trace.
    """
    resp = session.get(f"{BASE}/{page_slug}/", timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form", id=re.compile(r"^sciapi-services"))
    if not form:
        raise SCIError(
            f"Could not find the sciapi-services form on /{page_slug}/ — "
            "page structure may have changed, inspect live HTML"
        )
    hidden = {}
    for inp in form.find_all("input", {"type": "hidden"}):
        name = inp.get("name")
        if name:
            hidden[name] = inp.get("value", "")
    if "scid" not in hidden:
        raise SCIError(f"No captcha field found on /{page_slug}/ — cannot solve captcha")
    return hidden


def _submit(session: cffi_requests.Session, page_slug: str, action: str, fields: dict) -> str:
    """
    Bootstrap the page, solve its captcha, POST to admin-ajax.php, and
    return the raw HTML results fragment on success. Raises SCIError with
    the portal's own message on failure (e.g. wrong captcha, no records).
    """
    hidden = _bootstrap(session, page_slug)
    answer = _solve_captcha(session, hidden["scid"])

    payload = dict(hidden)
    payload.update({k: v for k, v in fields.items() if v not in (None, "")})
    payload["action"] = action
    payload["language"] = "en"
    payload["siwp_captcha_value"] = answer

    headers = dict(AJAX_HEADERS)
    headers["Referer"] = f"{BASE}/{page_slug}/"

    log.debug("SCI POST %s action=%s fields=%s", AJAX_URL, action, fields)
    resp = session.post(AJAX_URL, data=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    try:
        envelope = resp.json()
    except Exception:
        raise SCIError("SCI upstream returned a non-JSON response")

    if not envelope.get("success"):
        detail = envelope.get("data")
        message = None
        if isinstance(detail, str):
            try:
                message = json.loads(detail).get("message")
            except Exception:
                message = detail
        raise SCIError(message or "SCI search failed")

    data = envelope.get("data")
    if isinstance(data, dict):
        return data.get("resultsHtml") or data.get("html") or ""
    return data or ""


# ============================================================================
# RESULTS HTML → STRUCTURED ROWS
# ============================================================================

# header text (lowercased, substring match) -> normalized key.
# Order matters: more specific patterns first (e.g. "diary" before generic "no").
_HEADER_MAP = [
    (("diary no", "diary number"), "diary_no"),
    (("diary year",), "diary_year"),
    (("case no", "case number"), "case_no"),
    (("case year",), "case_year"),
    (("case type",), "case_type"),
    (("petitioner",), "petitioner"),
    (("respondent",), "respondent"),
    (("status",), "status"),
    (("next date", "next hearing", "listing date"), "next_hearing"),
    (("filing date",), "filing_date"),
    (("advocate",), "advocate"),
    (("judge",), "judge"),
    (("bench",), "bench"),
]


def _slugify_header(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_") or "value"


def _normalize_row(raw: dict) -> dict:
    """Map raw {header_text: cell_text} into the flat schema the Django
    proxy / React frontend already expect (see SCICaseStatusTerminal.jsx's
    CaseCard / SCICaseDetailPage.jsx)."""
    out = {}
    for header, value in raw.items():
        header_l = header.lower()
        matched_key = None
        for needles, key in _HEADER_MAP:
            if any(n in header_l for n in needles):
                matched_key = key
                break
        out[matched_key or _slugify_header(header)] = value
    out.setdefault("hearing_history", [])
    out.setdefault("orders", [])
    return out


def _parse_result_rows(html: str) -> list[dict]:
    """
    Parse the HTML fragment returned in a successful admin-ajax.php response
    into a list of normalized case/order/judgment row dicts. Best-effort:
    looks for the first <table>, builds headers from <th> (or the first
    row's <td> if there's no distinct header row), and also captures
    row-level data-diary-no/data-diary-year attributes (present on
    case-status result rows per the site's own click-through JS) so
    diary_no/diary_year survive even if the visible column text differs.

    UNVERIFIED against a genuine successful response — see module
    docstring. Returns [] rather than raising if no table is found, since
    "Nothing Found" is a normal, valid outcome.
    """
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []

    rows = table.find_all("tr")
    if not rows:
        return []

    header_cells = rows[0].find_all(["th"])
    body_rows = rows[1:] if header_cells else rows
    if not header_cells:
        header_cells = rows[0].find_all(["td", "th"])
        body_rows = rows[1:]
    headers = [c.get_text(strip=True) for c in header_cells]

    results = []
    for tr in body_rows:
        cells = tr.find_all("td")
        if not cells:
            continue
        raw = {}
        for i, cell in enumerate(cells):
            header = headers[i] if i < len(headers) else f"col_{i}"
            raw[header] = cell.get_text(strip=True)
        row = _normalize_row(raw)
        if tr.get("data-diary-no"):
            row["diary_no"] = tr["data-diary-no"]
        if tr.get("data-diary-year"):
            row["diary_year"] = tr["data-diary-year"]
        results.append(row)
    return results


# ============================================================================
# SCI CLIENT
# ============================================================================


class SCIClient:
    def __init__(self):
        self.session = get_session()

    def case_types(self) -> dict:
        return {"case_types": CASE_TYPES}

    # ── Case Status ─────────────────────────────────────────────────────

    def case_by_number(self, case_type: str, case_no: str, case_year: str) -> dict:
        html = _submit(self.session, _PAGE["case_no"], _ACTION["case_no"], {
            "case_no": case_no, "case_type": case_type, "year": case_year,
        })
        return {"cases": _parse_result_rows(html)}

    def case_by_diary(self, diary_no: str, diary_year: str) -> dict:
        html = _submit(self.session, _PAGE["diary_no"], _ACTION["diary_no"], {
            "diary_no": diary_no, "year": diary_year,
        })
        return {"cases": _parse_result_rows(html)}

    def case_by_party(self, party_name: str, year: Optional[str] = None) -> dict:
        html = _submit(self.session, _PAGE["party_name"], _ACTION["party_name"], {
            "party_name": party_name, "year": year, "party_type": "any",
        })
        return {"cases": _parse_result_rows(html)}

    def case_by_aor(self, aor_code: str, year: Optional[str] = None) -> dict:
        html = _submit(self.session, _PAGE["aor_code"], _ACTION["aor_code"], {
            "aor_code": aor_code, "year": year, "party_type": "any", "case_status": "P",
        })
        return {"cases": _parse_result_rows(html)}

    # ── Cause List ───────────────────────────────────────────────────────

    def _causelist(self, list_type: str, listing_date: str) -> dict:
        html = _submit(self.session, _PAGE["cause_list"], _ACTION["cause_list"], {
            "list_type": list_type,
            "listing_date": listing_date,
            "search_by": "all_courts",
            "causelist_type": "all",
            "msb": "main",
        })
        return {"cases": _parse_result_rows(html), "date": listing_date}

    def causelist_today(self) -> dict:
        import datetime
        today = datetime.date.today().strftime("%d-%m-%Y")
        return self._causelist("daily", today)

    def causelist_tomorrow(self) -> dict:
        import datetime
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%d-%m-%Y")
        return self._causelist("other", tomorrow)

    def causelist_by_date(self, list_date: str) -> dict:
        return self._causelist("other", list_date)

    # ── Daily Orders ─────────────────────────────────────────────────────

    def orders_by_case(self, case_type: str, case_no: str, case_year: str) -> dict:
        html = _submit(self.session, _PAGE["daily_order_case_no"], _ACTION["daily_order_case_no"], {
            "case_no": case_no, "case_type": case_type, "year": case_year,
        })
        return {"orders": _parse_result_rows(html)}

    def orders_by_diary(self, diary_no: str, diary_year: str) -> dict:
        html = _submit(self.session, _PAGE["daily_order_diary_no"], _ACTION["daily_order_diary_no"], {
            "diary_no": diary_no, "year": diary_year,
        })
        return {"orders": _parse_result_rows(html)}

    # ── Judgments ────────────────────────────────────────────────────────

    def judgments_by_case(self, case_type: str, case_no: str, case_year: str) -> dict:
        html = _submit(self.session, _PAGE["judgements_case_no"], _ACTION["judgements_case_no"], {
            "case_no": case_no, "case_type": case_type, "year": case_year,
        })
        return {"judgments": _parse_result_rows(html)}

    def judgments_by_party(self, party_name: str) -> dict:
        raise SCIError(
            "The live Supreme Court portal no longer offers a party-name "
            "judgments search (only case number, diary number, judge, or "
            "judgement date). Try Case Status search instead."
        )

    def judgments_by_date(self, from_date: str, to_date: str) -> dict:
        html = _submit(self.session, _PAGE["judgements_judgement_date"], _ACTION["judgements_judgement_date"], {
            "from_date": from_date, "to_date": to_date,
        })
        return {"judgments": _parse_result_rows(html)}

    # ── Office Reports ───────────────────────────────────────────────────

    def office_report_by_case(self, case_type: str, case_no: str, case_year: str) -> dict:
        html = _submit(self.session, _PAGE["office_report_case_no"], _ACTION["office_report_case_no"], {
            "case_no": case_no, "case_type": case_type, "year": case_year,
        })
        return {"reports": _parse_result_rows(html)}

    def office_report_by_diary(self, diary_no: str, diary_year: str) -> dict:
        html = _submit(self.session, _PAGE["office_report_diary_no"], _ACTION["office_report_diary_no"], {
            "diary_no": diary_no, "year": diary_year,
        })
        return {"reports": _parse_result_rows(html)}

    # ── Document / PDF ───────────────────────────────────────────────────

    def document_bytes(self, doc_url: str) -> bytes:
        resp = self.session.get(doc_url, headers={"Referer": BASE}, timeout=60)
        resp.raise_for_status()
        return resp.content


def _get_client() -> SCIClient:
    return SCIClient()


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Mamla.AI — Supreme Court of India (SCI) Case Search",
    description=(
        "Case Status, Cause List, Daily Orders, Judgments, and Office Reports "
        "against www.sci.gov.in. Mounted at /sci by the unified scraper entry "
        "point — see main.py. Rebuilt 2026-07 after main.sci.gov.in/"
        "webapi.sci.gov.in were retired; see module docstring for what's "
        "confirmed live vs. still unverified."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except SCIError as e:
        log.exception("SCI upstream error")
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "sci"}


@app.get("/case-types", tags=["Metadata"])
def case_types():
    return _wrap(_get_client().case_types)


# ─── Case Status ────────────────────────────────────────────────────────────

class CaseByNumberRequest(BaseModel):
    case_type: str = Field(..., description="SCI case-type code, from /case-types")
    case_no: str
    case_year: str


class CaseByDiaryRequest(BaseModel):
    diary_no: str
    diary_year: str


class CaseByPartyRequest(BaseModel):
    party_name: str
    year: Optional[str] = None


class CaseByAorRequest(BaseModel):
    aor_code: str
    year: Optional[str] = None


@app.post("/case/by-number", tags=["Case Status"])
def case_by_number(payload: CaseByNumberRequest):
    return _wrap(_get_client().case_by_number, payload.case_type, payload.case_no, payload.case_year)


@app.post("/case/by-diary", tags=["Case Status"])
def case_by_diary(payload: CaseByDiaryRequest):
    return _wrap(_get_client().case_by_diary, payload.diary_no, payload.diary_year)


@app.post("/case/by-party", tags=["Case Status"])
def case_by_party(payload: CaseByPartyRequest):
    return _wrap(_get_client().case_by_party, payload.party_name, payload.year)


@app.post("/case/by-aor", tags=["Case Status"])
def case_by_aor(payload: CaseByAorRequest):
    return _wrap(_get_client().case_by_aor, payload.aor_code, payload.year)


# ─── Cause List ─────────────────────────────────────────────────────────────

class CauseListByDateRequest(BaseModel):
    date: str = Field(..., description="DD-MM-YYYY")


@app.get("/causelist/today", tags=["Cause List"])
def causelist_today():
    return _wrap(_get_client().causelist_today)


@app.get("/causelist/tomorrow", tags=["Cause List"])
def causelist_tomorrow():
    return _wrap(_get_client().causelist_tomorrow)


@app.post("/causelist/by-date", tags=["Cause List"])
def causelist_by_date(payload: CauseListByDateRequest):
    return _wrap(_get_client().causelist_by_date, payload.date)


# ─── Daily Orders ───────────────────────────────────────────────────────────

@app.post("/orders/by-case", tags=["Daily Orders"])
def orders_by_case(payload: CaseByNumberRequest):
    return _wrap(_get_client().orders_by_case, payload.case_type, payload.case_no, payload.case_year)


@app.post("/orders/by-diary", tags=["Daily Orders"])
def orders_by_diary(payload: CaseByDiaryRequest):
    return _wrap(_get_client().orders_by_diary, payload.diary_no, payload.diary_year)


# ─── Judgments ──────────────────────────────────────────────────────────────

class JudgmentsByDateRequest(BaseModel):
    from_date: str = Field(..., description="DD-MM-YYYY")
    to_date: str = Field(..., description="DD-MM-YYYY")


@app.post("/judgments/by-case", tags=["Judgments"])
def judgments_by_case(payload: CaseByNumberRequest):
    return _wrap(_get_client().judgments_by_case, payload.case_type, payload.case_no, payload.case_year)


@app.post("/judgments/by-party", tags=["Judgments"])
def judgments_by_party(payload: CaseByPartyRequest):
    return _wrap(_get_client().judgments_by_party, payload.party_name)


@app.post("/judgments/by-date", tags=["Judgments"])
def judgments_by_date(payload: JudgmentsByDateRequest):
    return _wrap(_get_client().judgments_by_date, payload.from_date, payload.to_date)


# ─── Office Reports ─────────────────────────────────────────────────────────

@app.post("/office-report/by-case", tags=["Office Reports"])
def office_report_by_case(payload: CaseByNumberRequest):
    return _wrap(_get_client().office_report_by_case, payload.case_type, payload.case_no, payload.case_year)


@app.post("/office-report/by-diary", tags=["Office Reports"])
def office_report_by_diary(payload: CaseByDiaryRequest):
    return _wrap(_get_client().office_report_by_diary, payload.diary_no, payload.diary_year)


# ─── Document / PDF ─────────────────────────────────────────────────────────

class DocumentPdfRequest(BaseModel):
    doc_url: str = Field(..., description="Absolute SCI document URL resolved from a search result")


@app.post("/document/pdf", tags=["Documents"])
def document_pdf(payload: DocumentPdfRequest):
    try:
        pdf_bytes = _get_client().document_bytes(payload.doc_url)
    except SCIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf")
