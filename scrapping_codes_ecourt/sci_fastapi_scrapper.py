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
from urllib.parse import urljoin

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
    "cnr_no": "case-status-cnr-number",
    "case_status_court": "case-status-court",
    "cause_list": "cause-list",
    "daily_order_case_no": "daily-order-case-no",
    "daily_order_diary_no": "daily-order-diary-no",
    "daily_order_rop_date": "daily-order-rop-date",
    "daily_order_free_text": "free-text-orders",
    "judgements_case_no": "judgements-case-no",
    "judgements_diary_no": "judgements-diary-no",
    "judgements_judge": "judgements-judge",
    "judgements_judgement_date": "judgements-judgement-date",
    "judgements_free_text": "free-text-judgements",
    "office_report_case_no": "office-report-case-no",
    "office_report_diary_no": "office-report-diary-no",
}

_ACTION = {
    "case_no": "get_case_status_case_no",
    "diary_no": "get_case_status_diary_no",
    "party_name": "get_case_status_party_name",
    "aor_code": "get_case_status_aor_code",
    "cnr_no": "get_case_status_cnr_no",
    "case_status_court": "get_case_status_court",
    "cause_list": "get_causes",
    "daily_order_case_no": "get_daily_order_case_no",
    "daily_order_diary_no": "get_daily_order_diary_no",
    "daily_order_rop_date": "get_daily_order_rop_date",
    "daily_order_free_text": "get_daily_order_free_text",
    "judgements_case_no": "get_judgements_case_no",
    "judgements_diary_no": "get_judgements_diary_no",
    "judgements_judge": "get_judgements_judge",
    "judgements_judgement_date": "get_judgements_judgement_date",
    "judgements_free_text": "get_judgements_free_text",
    "office_report_case_no": "get_office_report_case_no",
    "office_report_diary_no": "get_office_report_diary_no",
}

# Cascade actions for the Case Status "Court" mode — GET admin-ajax.php calls
# returning a raw <option> HTML fragment, not the captcha-gated POST flow.
_COURT_CASCADE_ACTION = {
    "states": "list_case_status_states",
    "benches": "list_case_status_bench",
    "case_types": "list_case_status_case_type",
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

# Scraped live from the /judgements-judge/ page's `<select id="judge">`.
JUDGES = [
    {"value": "271", "label": "HON'BLE THE CHIEF JUSTICE"},
    {"value": "279", "label": "HON'BLE MR. JUSTICE VIKRAM NATH"},
    {"value": "282", "label": "HON'BLE MRS. JUSTICE B.V. NAGARATHNA"},
    {"value": "284", "label": "HON'BLE MR. JUSTICE M.M. SUNDRESH"},
    {"value": "286", "label": "HON'BLE MR. JUSTICE PAMIDIGHANTAM SRI NARASIMHA"},
    {"value": "288", "label": "HON'BLE MR. JUSTICE J.B. PARDIWALA"},
    {"value": "289", "label": "HON'BLE MR. JUSTICE DIPANKAR DATTA"},
    {"value": "291", "label": "HON'BLE MR. JUSTICE SANJAY KAROL"},
    {"value": "292", "label": "HON'BLE MR. JUSTICE SANJAY KUMAR"},
    {"value": "293", "label": "HON'BLE MR. JUSTICE AHSANUDDIN AMANULLAH"},
    {"value": "294", "label": "HON'BLE MR. JUSTICE MANOJ MISRA"},
    {"value": "296", "label": "HON'BLE MR. JUSTICE ARAVIND KUMAR"},
    {"value": "297", "label": "HON'BLE MR. JUSTICE PRASHANT KUMAR MISHRA"},
    {"value": "298", "label": "HON'BLE MR. JUSTICE K.V. VISWANATHAN"},
    {"value": "299", "label": "HON'BLE MR. JUSTICE UJJAL BHUYAN"},
    {"value": "300", "label": "HON'BLE MR. JUSTICE S.V.N. BHATTI"},
    {"value": "301", "label": "HON'BLE MR. JUSTICE SATISH CHANDRA SHARMA"},
    {"value": "302", "label": "HON'BLE MR. JUSTICE AUGUSTINE GEORGE MASIH"},
    {"value": "303", "label": "HON'BLE MR. JUSTICE SANDEEP MEHTA"},
    {"value": "304", "label": "HON'BLE  MR. JUSTICE PRASANNA B. VARALE"},
    {"value": "305", "label": "HON'BLE MR. JUSTICE NONGMEIKAPAM KOTISWAR SINGH"},
    {"value": "306", "label": "HON'BLE MR. JUSTICE R. MAHADEVAN"},
    {"value": "307", "label": "HON'BLE MR. JUSTICE MANMOHAN"},
    {"value": "308", "label": "HON'BLE MR. JUSTICE K. VINOD CHANDRAN"},
    {"value": "309", "label": "HON'BLE MR. JUSTICE JOYMALYA BAGCHI"},
    {"value": "311", "label": "HON'BLE MR. JUSTICE N.V. ANJARIA"},
    {"value": "312", "label": "HON'BLE MR. JUSTICE VIJAY BISHNOI"},
    {"value": "313", "label": "HON'BLE MR. JUSTICE ATUL S. CHANDURKAR"},
    {"value": "314", "label": "HON'BLE MR. JUSTICE ALOK ARADHE"},
    {"value": "315", "label": "HON'BLE MR. JUSTICE VIPUL M. PANCHOLI"},
    {"value": "316", "label": "HON'BLE MR. JUSTICE SHEEL  NAGU"},
    {"value": "317", "label": "HON'BLE MR. JUSTICE SHREE CHANDRASHEKHAR"},
    {"value": "318", "label": "HON'BLE MR. JUSTICE SANJEEV SACHDEVA"},
    {"value": "319", "label": "HON'BLE MR. JUSTICE ARUN PALLI"},
    {"value": "320", "label": "HON'BLE MRS. JUSTICE V. MOHANA"},
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

_DIGIT_PAIR_RE = re.compile(r"(\d+)\D+(\d+)")


def _ocr_digit_pair(session: cffi_requests.Session, scid: str) -> tuple:
    """
    Fetch the captcha image and OCR it down to its two operand numbers.

    CapSolver reliably reads the two digit groups on this font but
    frequently garbles the operator glyph between them into noise (e.g.
    "10s5", "1oz5", "10=" for images live inspection confirmed show a clean
    "10 + 5" or "10 - 5") — so this deliberately does not try to identify
    +/-/x here. _submit instead tries all three candidate answers against
    this same fetched image; live testing confirmed the portal evaluates
    each submitted answer independently without invalidating the captcha
    after a wrong guess, so brute-forcing the 3 operators is both reliable
    and cheap (no extra image fetch per guess).
    """
    img_url = f"{BASE}/?_siwp_captcha&id={scid}"
    resp = session.get(img_url, timeout=20)
    resp.raise_for_status()
    b64 = base64.b64encode(resp.content).decode()
    expr_text = _capsolver_solve_captcha(b64, BASE)
    cleaned = expr_text.replace("—", "-").replace("–", "-")
    m = _DIGIT_PAIR_RE.search(cleaned)
    if not m:
        raise SCIError(f"Could not read two operands from captcha text: {expr_text!r}")
    return int(m.group(1)), int(m.group(2))


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


def _fetch_option_list(session: cffi_requests.Session, page_slug: str, action: str, params: dict) -> list:
    """
    Case Status "Court" mode's cascading dropdowns (Court -> State -> Bench ->
    Case Type) are GET admin-ajax.php calls, not the captcha-gated POST submit
    flow — confirmed live: e.g. GET ?action=list_case_status_states returns
    {"success": true, "data": "<option value=490506>Delhi</option>"}, a raw
    HTML fragment meant to replace the next <select>'s contents client-side.
    """
    hidden = _bootstrap(session, page_slug)
    payload = {**hidden, "action": action, **params}
    headers = {**AJAX_HEADERS, "Referer": f"{BASE}/{page_slug}/"}
    resp = session.get(AJAX_URL, params=payload, headers=headers, timeout=20)
    resp.raise_for_status()
    envelope = resp.json()
    if not envelope.get("success"):
        raise SCIError("Could not fetch option list")
    frag = BeautifulSoup(envelope.get("data") or "", "html.parser")
    return [
        {"value": o.get("value", ""), "label": o.get_text(strip=True)}
        for o in frag.find_all("option") if o.get("value")
    ]


def _case_status_states(session: cffi_requests.Session, court: str) -> list:
    return _fetch_option_list(session, _PAGE["case_status_court"], _COURT_CASCADE_ACTION["states"],
                               {"case_status_court": court})


def _case_status_benches(session: cffi_requests.Session, court: str, state: str) -> list:
    return _fetch_option_list(session, _PAGE["case_status_court"], _COURT_CASCADE_ACTION["benches"],
                               {"case_status_court": court, "case_status_state": state})


def _case_status_case_types(session: cffi_requests.Session, court: str, state: str, bench: str) -> list:
    return _fetch_option_list(session, _PAGE["case_status_court"], _COURT_CASCADE_ACTION["case_types"],
                               {"case_status_court": court, "case_status_state": state, "case_status_bench": bench})


_MAX_CAPTCHA_ATTEMPTS = 5


def _post_with_captcha_guess(session, page_slug, action, fields, hidden, guess) -> dict:
    payload = dict(hidden)
    payload.update({k: v for k, v in fields.items() if v not in (None, "")})
    payload["action"] = action
    payload["language"] = "en"
    payload["siwp_captcha_value"] = str(guess)

    headers = dict(AJAX_HEADERS)
    headers["Referer"] = f"{BASE}/{page_slug}/"

    resp = session.post(AJAX_URL, data=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:
        raise SCIError("SCI upstream returned a non-JSON response")


def _envelope_message(envelope: dict) -> str:
    detail = envelope.get("data")
    message = None
    if isinstance(detail, str):
        try:
            message = json.loads(detail).get("message")
        except Exception:
            message = detail
    return message or "SCI search failed"


def _submit(session: cffi_requests.Session, page_slug: str, action: str, fields: dict) -> str:
    """
    Bootstrap the page, solve its captcha, POST to admin-ajax.php, and
    return the raw HTML results fragment on success. Raises SCIError with
    the portal's own message on failure (e.g. no records).

    Since OCR can read the two operand numbers but not reliably which of
    +/-/x separates them, each bootstrap attempt tries all 3 arithmetic
    results as the captcha answer before giving up on that image. Only if
    every guess is rejected as a captcha error (meaning the digits themselves
    were probably misread) does it re-bootstrap for a fresh image, up to
    _MAX_CAPTCHA_ATTEMPTS times — matching the retry convention used by the
    DC/HC/SC scrapers in this same package.
    """
    last_error: Optional[Exception] = None
    for attempt in range(1, _MAX_CAPTCHA_ATTEMPTS + 1):
        try:
            hidden = _bootstrap(session, page_slug)
            a, b = _ocr_digit_pair(session, hidden["scid"])
        except SCIError as e:
            log.warning("SCI captcha OCR misread (attempt %d): %s", attempt, e)
            last_error = e
            continue

        candidates = []
        for val in (a + b, a - b, a * b):
            if val not in candidates:
                candidates.append(val)

        for guess in candidates:
            log.debug("SCI POST %s action=%s fields=%s attempt=%d guess=%s", AJAX_URL, action, fields, attempt, guess)
            envelope = _post_with_captcha_guess(session, page_slug, action, fields, hidden, guess)

            if envelope.get("success"):
                data = envelope.get("data")
                if isinstance(data, dict):
                    return data.get("resultsHtml") or data.get("html") or ""
                return data or ""

            message = _envelope_message(envelope)
            if "captcha" not in message.lower():
                raise SCIError(message)
            last_error = SCIError(message)

        log.warning("SCI captcha rejected all %d candidate answers (attempt %d)", len(candidates), attempt)

    raise last_error or SCIError("SCI captcha solve failed after retries")


# ============================================================================
# RESULTS HTML → STRUCTURED ROWS
# ============================================================================

# header text (lowercased, substring match) -> normalized key.
# Order matters: more specific patterns first (e.g. "diary" before generic "no").
# Order matters: more specific needles must precede more general ones a
# header might also contain — e.g. Cause List's "Petitioner/Respondent
# Advocate" column contains the substring "petitioner", so "advocate" must be
# checked first or that column's value clobbers the real petitioner value
# (confirmed live: without this ordering, the advocate's name ended up in
# the "petitioner" field).
_HEADER_MAP = [
    (("diary no", "diary number"), "diary_no"),
    (("diary year",), "diary_year"),
    (("case no", "case number"), "case_no"),
    (("case year",), "case_year"),
    (("case type",), "case_type"),
    (("advocate",), "advocate"),
    (("petitioner",), "petitioner"),
    (("respondent",), "respondent"),
    (("status",), "status"),
    (("next date", "next hearing", "listing date"), "next_hearing"),
    (("filing date",), "filing_date"),
    (("judge",), "judge"),
    (("bench",), "bench"),
]


def _slugify_header(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_") or "value"


def _normalized_key(header: str) -> str:
    header_l = header.lower()
    for needles, key in _HEADER_MAP:
        if any(n in header_l for n in needles):
            return key
    return _slugify_header(header)


_VERSUS_RE = re.compile(r"\s+versus\s+", re.IGNORECASE)


def _normalize_row(raw: dict) -> dict:
    """Map raw {header_text: cell_text} into the flat schema the Django
    proxy / React frontend already expect (see SCICaseStatusTerminal.jsx's
    CaseCard / SCICaseDetailPage.jsx)."""
    out = {}
    for header, value in raw.items():
        out[_normalized_key(header)] = value
    # Cause List's "Petitioner / Respondent" column combines both parties into
    # one "X Versus Y" cell (confirmed live) rather than separate columns —
    # split it so the frontend's CaseCard "vs {respondent}" line still works.
    if "petitioner" in out and "respondent" not in out:
        parts = _VERSUS_RE.split(out["petitioner"], maxsplit=1)
        if len(parts) == 2:
            out["petitioner"], out["respondent"] = parts[0].strip(), parts[1].strip()
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
        # Section dividers (e.g. "[BAIL MATTERS]") and IA-description
        # continuation rows both use this class and a single colspan'd <td> —
        # confirmed live on Cause List results — skip them, they're not cases.
        if "sci-table-headtext" in (tr.get("class") or []):
            continue
        cells = tr.find_all("td")
        if not cells:
            continue
        raw = {}
        links = {}
        for i, cell in enumerate(cells):
            header = headers[i] if i < len(headers) else f"col_{i}"
            # separator=" " keeps <br>-joined text (e.g. multiple advocate
            # names, or a case label followed by its bench code on the next
            # line) from being smashed together with no space between them.
            text = cell.get_text(separator=" ", strip=True)
            raw[header] = re.sub(r"\s+", " ", text).strip()
            # Some result tables (e.g. Cause List's "Serial Number"/"File"
            # distribution-list shape) carry the useful payload as a link
            # href rather than cell text — e.g. a direct PDF URL on
            # api.sci.gov.in. Capture it as "<key>_url" alongside the cell's
            # visible text so the frontend can render it as an actual link
            # instead of silently dropping it (confirmed live: without this,
            # "View Main Cause List" rendered as inert text with no URL).
            anchor = cell.find("a", href=True)
            if anchor and anchor["href"]:
                links[_normalized_key(header)] = urljoin(BASE, anchor["href"])
        row = _normalize_row(raw)
        for key, href in links.items():
            row[f"{key}_url"] = href
        if tr.get("data-diary-no"):
            row["diary_no"] = tr["data-diary-no"]
        if tr.get("data-diary-year"):
            row["diary_year"] = tr["data-diary-year"]
        results.append(row)
    return results


# ============================================================================
# CASE DETAILS DRILL-DOWN (get_case_details)
# ============================================================================
#
# Confirmed live: unlike every search-mode page, this is a plain GET to
# admin-ajax.php with no captcha, no bootstrap, and no hidden form fields at
# all — just diary_no/diary_year/tab_name. tab_name="" (or "case_details")
# returns the main Case Details table; the site's own JS shows 5 other lazy
# tabs, keyed by these exact tab_name values: argument_transcripts, indexing,
# earlier_court_details, tagged_matters, listing_dates.

_CASE_DETAIL_LIST_LABELS = {
    "petitioner(s)": "petitioners",
    "respondent(s)": "respondents",
    "petitioner advocate(s)": "petitioner_advocates",
    "respondent advocate(s)": "respondent_advocates",
}

_CASE_DETAIL_FIELD_MAP = {
    "diary number": "diary_number_detail",
    "case number": "case_number_detail",
    "cnr number": "cnr_no",
    "present/last listed on": "present_last_listed_on",
    "status/stage": "status_stage",
    "category": "category",
}

_LEADING_INDEX_RE = re.compile(r"^\d+\s+")


def _parse_case_details_html(html: str) -> dict:
    """
    Parse the key/value "Case Details" table (the tab_name="" / "case_details"
    response) into a flat dict. Unlike _parse_result_rows (built for list-style
    result tables), this table is 2 columns per row: a label <td> and a value
    <td>, so it needs its own parser rather than reusing the header-map one.
    """
    if not html:
        return {}
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="caseDetailsTable")
    if not table:
        return {}

    out = {}
    status_badge = table.find(class_=re.compile(r"\bcaseStatus\b"))
    if status_badge:
        out["status"] = status_badge.get_text(strip=True)

    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) != 2:
            continue
        label = cells[0].get_text(strip=True).lower()
        value_cell = cells[1]

        if label in _CASE_DETAIL_LIST_LABELS:
            text = value_cell.get_text(separator="\n", strip=True)
            items = [_LEADING_INDEX_RE.sub("", line).strip() for line in text.split("\n") if line.strip()]
            out[_CASE_DETAIL_LIST_LABELS[label]] = items
            continue

        # Strip the status badge's own text back out of the Diary Number
        # row's value (it's nested inside that cell) so it isn't duplicated.
        for badge in value_cell.find_all(class_=re.compile(r"\bcaseStatus\b")):
            badge.extract()
        text = re.sub(r"\s+", " ", value_cell.get_text(separator=" ", strip=True)).strip()

        key = _CASE_DETAIL_FIELD_MAP.get(label)
        if key is None and "tentatively" in label:
            key = "tentative_listing_date"
        out[key or _slugify_header(label)] = text

    return out


def _get_case_details(session: cffi_requests.Session, diary_no: str, diary_year: str, tab_name: str = "") -> str:
    params = {
        "diary_no": diary_no,
        "diary_year": diary_year,
        "tab_name": tab_name,
        "action": "get_case_details",
        "es_ajax_request": "1",
        "language": "en",
    }
    resp = session.get(AJAX_URL, params=params, headers=AJAX_HEADERS, timeout=20)
    resp.raise_for_status()
    envelope = resp.json()
    if not envelope.get("success"):
        raise SCIError("Could not fetch case details")
    return envelope.get("data") or ""


# ============================================================================
# SCI CLIENT
# ============================================================================


class SCIClient:
    def __init__(self):
        self.session = get_session()

    def case_types(self) -> dict:
        return {"case_types": CASE_TYPES}

    def judges(self) -> dict:
        return {"judges": JUDGES}

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

    def case_by_party(self, party_name: str, year: str, party_type: str = "any", party_status: str = "P") -> dict:
        # Confirmed live from /case-status-party-name/'s own form: year,
        # party_type (Any/Petitioner[P]/Respondent[R]) and party_status
        # (Pending[P]/Disposed[D]) are ALL marked required (redStar) there —
        # the portal's own AJAX handler rejects the request server-side if
        # they're missing ("Year is required." / "Status is required."),
        # confirmed live. Previously year was treated as optional and
        # party_status wasn't sent at all, so every party-name search that
        # didn't happen to include a year failed outright.
        fields = {
            "party_name": party_name, "year": year,
            "party_type": party_type, "party_status": party_status,
        }
        html = _submit(self.session, _PAGE["party_name"], _ACTION["party_name"], fields)
        return {"cases": _parse_result_rows(html)}

    def case_by_aor(self, aor_code: str, year: Optional[str] = None) -> dict:
        html = _submit(self.session, _PAGE["aor_code"], _ACTION["aor_code"], {
            "aor_code": aor_code, "year": year, "party_type": "any", "case_status": "P",
        })
        return {"cases": _parse_result_rows(html)}

    def case_by_cnr(self, cnr_no: str) -> dict:
        html = _submit(self.session, _PAGE["cnr_no"], _ACTION["cnr_no"], {"cnr_no": cnr_no})
        return {"cases": _parse_result_rows(html)}

    # ── Case Status — Court cascade (Court -> State -> Bench -> Case Type) ──

    def case_status_states(self, court: str) -> dict:
        return {"states": _case_status_states(self.session, court)}

    def case_status_benches(self, court: str, state: str) -> dict:
        return {"benches": _case_status_benches(self.session, court, state)}

    def case_status_case_types(self, court: str, state: str, bench: str) -> dict:
        return {"case_types": _case_status_case_types(self.session, court, state, bench)}

    def case_by_court(self, court: str, state: str, bench: str, case_type: str, case_no: str,
                       year: str, listing_date: Optional[str] = None) -> dict:
        fields = {
            "case_status_court": court, "case_status_state": state,
            "case_status_bench": bench, "case_status_case_type": case_type,
            "case_no": case_no, "year": year,
        }
        if listing_date:
            fields["listing_date"] = listing_date
        html = _submit(self.session, _PAGE["case_status_court"], _ACTION["case_status_court"], fields)
        return {"cases": _parse_result_rows(html)}

    # ── Cause List ───────────────────────────────────────────────────────

    def _causelist(self, list_type: str, listing_date: Optional[str] = None, *, search_by: str = "all_courts",
                    court: Optional[str] = None, judge: Optional[str] = None, aor_code: Optional[str] = None,
                    party_name: Optional[str] = None, causelist_type: str = "all",
                    listing_date_from: Optional[str] = None, listing_date_to: Optional[str] = None,
                    msb: str = "main") -> dict:
        fields = {"list_type": list_type, "search_by": search_by, "causelist_type": causelist_type, "msb": msb}
        if listing_date:
            fields["listing_date"] = listing_date
        if listing_date_from:
            fields["listing_date_from"] = listing_date_from
        if listing_date_to:
            fields["listing_date_to"] = listing_date_to
        if court:
            fields["court"] = court
        if judge:
            fields["judge"] = judge
        if aor_code:
            fields["aor_code"] = aor_code
        if party_name:
            fields["party_name"] = party_name
        html = _submit(self.session, _PAGE["cause_list"], _ACTION["cause_list"], fields)
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

    def causelist_search(self, list_type: str, search_by: str = "all_courts", court: Optional[str] = None,
                          judge: Optional[str] = None, aor_code: Optional[str] = None,
                          party_name: Optional[str] = None, causelist_type: str = "all",
                          listing_date: Optional[str] = None, listing_date_from: Optional[str] = None,
                          listing_date_to: Optional[str] = None, msb: str = "main") -> dict:
        return self._causelist(
            list_type, listing_date, search_by=search_by, court=court, judge=judge, aor_code=aor_code,
            party_name=party_name, causelist_type=causelist_type, listing_date_from=listing_date_from,
            listing_date_to=listing_date_to, msb=msb,
        )

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

    def orders_by_rop_date(self, from_date: str, to_date: str) -> dict:
        html = _submit(self.session, _PAGE["daily_order_rop_date"], _ACTION["daily_order_rop_date"], {
            "from_date": from_date, "to_date": to_date,
        })
        return {"orders": _parse_result_rows(html)}

    def orders_free_text(self, search_text: str, from_date: str, to_date: str) -> dict:
        html = _submit(self.session, _PAGE["daily_order_free_text"], _ACTION["daily_order_free_text"], {
            "search_text": search_text, "from_date": from_date, "to_date": to_date,
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
            "judgments search (only case number, diary number, judge, "
            "judgement date, or free text). Try Case Status search instead."
        )

    def judgments_by_date(self, from_date: str, to_date: str) -> dict:
        html = _submit(self.session, _PAGE["judgements_judgement_date"], _ACTION["judgements_judgement_date"], {
            "from_date": from_date, "to_date": to_date,
        })
        return {"judgments": _parse_result_rows(html)}

    def judgments_by_diary(self, diary_no: str, year: str) -> dict:
        html = _submit(self.session, _PAGE["judgements_diary_no"], _ACTION["judgements_diary_no"], {
            "diary_no": diary_no, "year": year,
        })
        return {"judgments": _parse_result_rows(html)}

    def judgments_by_judge(self, judge: str, from_date: str, to_date: str) -> dict:
        html = _submit(self.session, _PAGE["judgements_judge"], _ACTION["judgements_judge"], {
            "judge": judge, "from_date": from_date, "to_date": to_date,
        })
        return {"judgments": _parse_result_rows(html)}

    def judgments_free_text(self, search_text: str, from_date: str, to_date: str) -> dict:
        html = _submit(self.session, _PAGE["judgements_free_text"], _ACTION["judgements_free_text"], {
            "search_text": search_text, "from_date": from_date, "to_date": to_date,
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

    # ── Case Details drill-down ──────────────────────────────────────────

    def case_details(self, diary_no: str, diary_year: str, tab_name: str = "") -> dict:
        html = _get_case_details(self.session, diary_no, diary_year, tab_name)
        details = _parse_case_details_html(html)
        details["diary_no"] = diary_no
        details["diary_year"] = diary_year
        return details

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


@app.get("/judges", tags=["Metadata"])
def judges():
    return _wrap(_get_client().judges)


# ─── Case Status ────────────────────────────────────────────────────────────

class CaseByNumberRequest(BaseModel):
    case_type: str = Field(..., description="SCI case-type code, from /case-types")
    case_no: str
    case_year: str


class CaseByDiaryRequest(BaseModel):
    diary_no: str
    diary_year: str


# party_name-only, year optional — kept solely for /judgments/by-party, whose
# handler always raises a clear "no longer supported" error regardless of
# fields (see judgments_by_party); does NOT reflect the real Case Status
# party-name form's requirements, see CaseStatusByPartyRequest below for that.
class CaseByPartyRequest(BaseModel):
    party_name: str
    year: Optional[str] = None


# Mirrors /case-status-party-name/'s real form, where year, party_type, and
# party_status are all marked required (confirmed live — omitting any of
# them gets rejected server-side with "X is required.").
class CaseStatusByPartyRequest(BaseModel):
    party_name: str
    year: str
    party_type: str = Field("any", description="any | P (Petitioner) | R (Respondent)")
    party_status: str = Field(..., description="P (Pending) | D (Disposed) — required by the portal")


class CaseByAorRequest(BaseModel):
    aor_code: str
    year: Optional[str] = None


class CaseByCnrRequest(BaseModel):
    cnr_no: str


class CaseByCourtRequest(BaseModel):
    court: str = Field(..., description="case_status_court value, from /case-status-court/states")
    state: str = Field(..., description="case_status_state value, from /case-status-court/states response")
    bench: str = Field(..., description="case_status_bench value, from /case-status-court/benches")
    case_type: str = Field(..., description="case_status_case_type value, from /case-status-court/case-types")
    case_no: str
    year: str
    listing_date: Optional[str] = None


@app.post("/case/by-number", tags=["Case Status"])
def case_by_number(payload: CaseByNumberRequest):
    return _wrap(_get_client().case_by_number, payload.case_type, payload.case_no, payload.case_year)


@app.post("/case/by-diary", tags=["Case Status"])
def case_by_diary(payload: CaseByDiaryRequest):
    return _wrap(_get_client().case_by_diary, payload.diary_no, payload.diary_year)


@app.post("/case/by-party", tags=["Case Status"])
def case_by_party(payload: CaseStatusByPartyRequest):
    return _wrap(_get_client().case_by_party, payload.party_name, payload.year, payload.party_type, payload.party_status)


@app.post("/case/by-aor", tags=["Case Status"])
def case_by_aor(payload: CaseByAorRequest):
    return _wrap(_get_client().case_by_aor, payload.aor_code, payload.year)


@app.post("/case/by-cnr", tags=["Case Status"])
def case_by_cnr(payload: CaseByCnrRequest):
    return _wrap(_get_client().case_by_cnr, payload.cnr_no)


@app.get("/case-status-court/states", tags=["Case Status"])
def case_status_court_states(court: str):
    return _wrap(_get_client().case_status_states, court)


@app.get("/case-status-court/benches", tags=["Case Status"])
def case_status_court_benches(court: str, state: str):
    return _wrap(_get_client().case_status_benches, court, state)


@app.get("/case-status-court/case-types", tags=["Case Status"])
def case_status_court_case_types(court: str, state: str, bench: str):
    return _wrap(_get_client().case_status_case_types, court, state, bench)


@app.post("/case/by-court", tags=["Case Status"])
def case_by_court(payload: CaseByCourtRequest):
    return _wrap(_get_client().case_by_court, payload.court, payload.state, payload.bench,
                 payload.case_type, payload.case_no, payload.year, payload.listing_date)


# ─── Cause List ─────────────────────────────────────────────────────────────

class CauseListByDateRequest(BaseModel):
    date: str = Field(..., description="DD-MM-YYYY")


class CauseListSearchRequest(BaseModel):
    list_type: str = Field(..., description="'daily' or 'other'")
    search_by: str = Field("all_courts", description="all_courts | court | judge | aor_code | party_name")
    court: Optional[str] = None
    judge: Optional[str] = None
    aor_code: Optional[str] = None
    party_name: Optional[str] = None
    causelist_type: str = "all"
    listing_date: Optional[str] = Field(None, description="DD-MM-YYYY, used unless causelist_type=weekly")
    listing_date_from: Optional[str] = Field(None, description="DD-MM-YYYY, used when causelist_type=weekly")
    listing_date_to: Optional[str] = Field(None, description="DD-MM-YYYY, used when causelist_type=weekly")
    msb: str = Field("main", description="main | suppli | both")


@app.get("/causelist/today", tags=["Cause List"])
def causelist_today():
    return _wrap(_get_client().causelist_today)


@app.get("/causelist/tomorrow", tags=["Cause List"])
def causelist_tomorrow():
    return _wrap(_get_client().causelist_tomorrow)


@app.post("/causelist/by-date", tags=["Cause List"])
def causelist_by_date(payload: CauseListByDateRequest):
    return _wrap(_get_client().causelist_by_date, payload.date)


@app.post("/causelist/search", tags=["Cause List"])
def causelist_search(payload: CauseListSearchRequest):
    return _wrap(
        _get_client().causelist_search, payload.list_type, payload.search_by, payload.court, payload.judge,
        payload.aor_code, payload.party_name, payload.causelist_type, payload.listing_date,
        payload.listing_date_from, payload.listing_date_to, payload.msb,
    )


# ─── Daily Orders ───────────────────────────────────────────────────────────

class OrdersByRopDateRequest(BaseModel):
    from_date: str = Field(..., description="DD-MM-YYYY")
    to_date: str = Field(..., description="DD-MM-YYYY")


class OrdersFreeTextRequest(BaseModel):
    search_text: str
    from_date: str = Field(..., description="DD-MM-YYYY")
    to_date: str = Field(..., description="DD-MM-YYYY")


@app.post("/orders/by-case", tags=["Daily Orders"])
def orders_by_case(payload: CaseByNumberRequest):
    return _wrap(_get_client().orders_by_case, payload.case_type, payload.case_no, payload.case_year)


@app.post("/orders/by-diary", tags=["Daily Orders"])
def orders_by_diary(payload: CaseByDiaryRequest):
    return _wrap(_get_client().orders_by_diary, payload.diary_no, payload.diary_year)


@app.post("/orders/by-rop-date", tags=["Daily Orders"])
def orders_by_rop_date(payload: OrdersByRopDateRequest):
    return _wrap(_get_client().orders_by_rop_date, payload.from_date, payload.to_date)


@app.post("/orders/free-text", tags=["Daily Orders"])
def orders_free_text(payload: OrdersFreeTextRequest):
    return _wrap(_get_client().orders_free_text, payload.search_text, payload.from_date, payload.to_date)


# ─── Judgments ──────────────────────────────────────────────────────────────

class JudgmentsByDateRequest(BaseModel):
    from_date: str = Field(..., description="DD-MM-YYYY")
    to_date: str = Field(..., description="DD-MM-YYYY")


class JudgmentsByDiaryRequest(BaseModel):
    diary_no: str
    year: str


class JudgmentsByJudgeRequest(BaseModel):
    judge: str = Field(..., description="Judge id, from /judges")
    from_date: str = Field(..., description="DD-MM-YYYY")
    to_date: str = Field(..., description="DD-MM-YYYY")


class JudgmentsFreeTextRequest(BaseModel):
    search_text: str
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


@app.post("/judgments/by-diary", tags=["Judgments"])
def judgments_by_diary(payload: JudgmentsByDiaryRequest):
    return _wrap(_get_client().judgments_by_diary, payload.diary_no, payload.year)


@app.post("/judgments/by-judge", tags=["Judgments"])
def judgments_by_judge(payload: JudgmentsByJudgeRequest):
    return _wrap(_get_client().judgments_by_judge, payload.judge, payload.from_date, payload.to_date)


@app.post("/judgments/free-text", tags=["Judgments"])
def judgments_free_text(payload: JudgmentsFreeTextRequest):
    return _wrap(_get_client().judgments_free_text, payload.search_text, payload.from_date, payload.to_date)


# ─── Office Reports ─────────────────────────────────────────────────────────

@app.post("/office-report/by-case", tags=["Office Reports"])
def office_report_by_case(payload: CaseByNumberRequest):
    return _wrap(_get_client().office_report_by_case, payload.case_type, payload.case_no, payload.case_year)


@app.post("/office-report/by-diary", tags=["Office Reports"])
def office_report_by_diary(payload: CaseByDiaryRequest):
    return _wrap(_get_client().office_report_by_diary, payload.diary_no, payload.diary_year)


# ─── Case Details ───────────────────────────────────────────────────────────

@app.get("/case/details", tags=["Case Status"])
def case_details(diary_no: str, diary_year: str, tab_name: str = ""):
    """
    No captcha required — confirmed live. tab_name defaults to the main
    Case Details tab; other known values: argument_transcripts, indexing,
    earlier_court_details, tagged_matters, listing_dates.
    """
    return _wrap(_get_client().case_details, diary_no, diary_year, tab_name)


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
