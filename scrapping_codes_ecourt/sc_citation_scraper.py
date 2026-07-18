"""
sc_citation_scraper.py — Supreme Court citation lookup, mounted at /sc.

Live Indian Supreme Court citation lookup against e-SCR (scr.sci.gov.in).
Scope: SC only — neutral citations (INSC), SCR citations, and equivalent-
reporter citations (SCC / AIR / JT / Scale), all resolved through the same
e-SCR portal since it stores equivalent citations per case.

Mounted by main.py as a sibling to /dc and /hc:
    from sc_citation_scraper import app as sc_app
    app.mount("/sc", sc_app)

--------------------------------------------------------------------------
GROUNDING / WHAT'S VERIFIED VS. INFERRED
--------------------------------------------------------------------------
CONFIRMED against a real captured live browser trace against
https://scr.sci.gov.in/scrsearch/ (2026, DevTools capture of a genuine
"landlord" / year=2026 search — both request AND response bodies seen):
  - checkCaptcha: POST to `?p=pdf_search/checkCaptcha` (no trailing
    slash). Field names confirmed: captcha, search_text, search_opt,
    escr_flag, proximity, sel_lang, neu_cit_year, neu_no, ncn,
    citation_vol, citation_year (note: "citation_year", NOT "citation_yr"
    — that's the /home/ step's key), citation_supl, citation_page,
    ajax_req, app_token.
  - Search: POST to `?p=pdf_search/home/` (WITH trailing slash — this
    differs from the checkCaptcha path). The live UI sends the FULL
    DataTables field set every time regardless of search mode (see the
    `form` dict in `ESCRClient.search()`), including literal values like
    `dist_code=null` (string) and `sort_flg=undefined` (string) — copied
    verbatim rather than guessed, in case the server validates their
    presence.
  - Search RESPONSE shape: `{"reportrow": {"sEcho", "iTotalRecords",
    "iTotalDisplayRecords", "sSearch", "aaData": [[row_num, html], ...]}}`
    — rows are nested under `reportrow.aaData`, NOT top-level `aaData` or
    `data` as originally guessed.
  - Result-row HTML: `<strong>` for case title (first `<strong>` in the
    row — a second `<strong>` later holds the Coram/judges, don't match
    that one), `<span class="ncDisplay">`, `<span class="escrText">`,
    `<input id="cnr" value=... >` (value is UNQUOTED in the live HTML;
    BeautifulSoup's html.parser handles that fine), and
    `onclick=javascript:open_pdf('0' ,'2026' ,'2026_6_328_353' ,'2026INSC496' );`
    — note the space BEFORE each comma, which the original regex
    (`'(\\d+)','(\\d+)'` with no whitespace tolerance) would have failed
    to match. Fixed to tolerate whitespace around commas.
  - Homepage captcha widget: `<img id="captcha_image" src="/scrsearch/vendor/
    securimage/securimage_show.php?...">` (root-relative src, no query
    key=value, just a bare random token) and `<input id="captcha" name="captcha"
    maxlength="6">` for the text field — confirms `_bootstrap_session()`'s
    FIRST selector (`img#captcha_image`) was already correct; the other two
    fallback selectors are now dead code but harmless to leave in.
  - `app_token` is genuinely EMPTY (`value=""`) on a fresh homepage load,
    and real captured POSTs also send it empty — this is normal, not a
    failure. The original code raised `ESCRError` on any empty token,
    which would have hard-failed every single request. Fixed to only
    error when the `<input name="app_token">` element is missing entirely.
  - `search_opt` default is "PHRASE" (confirmed via the homepage radio's
    `checked` attribute) — an earlier trace showing "ANY" was a manual UI
    selection, not the true default. Reverted the assumed base default
    from "ANY" back to "PHRASE" in both checkCaptcha and search().
  - checkCaptcha FAILURE response, confirmed live:
    `{"errormsg":"Invalid Captcha..!!!","captcha_status":"N"}` — critically,
    there is NO `"error"` key on failure. The original success check
    (`not result.get("error")`) would have treated this exact failure
    response as SUCCESS and proceeded with a rejected captcha. Fixed to
    key off `captcha_status` explicitly.
  - checkCaptcha SUCCESS response, confirmed live: exactly
    `{"captcha_status":"Y"}`. The assumed success value ("Y") was correct.
  - openpdfcaptcha: confirmed live — request path has NO trailing slash
    (`?p=pdf_search/openpdfcaptcha`), and the response's PDF-path field is
    `outputfile` (the first guess in the fallback chain was right, no
    change needed), e.g.:
    `{"outputfile":"/scrsearch/tmp/<hash>.pdf","message":"","html_file":null,...}`
  - THE CAPTCHA-SOLVING ACCURACY PROBLEM (this was the actual production
    blocker, not a request-shape bug): scr.sci.gov.in's captcha is
    case-sensitive, and CapSolver's ImageToTextTask "common" module always
    normalizes output to lowercase — confirmed by an A/B test against a
    known captcha image (ground truth "5mGKPf"): passing an undocumented
    `case: true` field produced IDENTICAL lowercase output to omitting it.
    Fixed by fusing CapSolver's character sequence with a local EasyOCR
    pass's case pattern (see `fuse_captcha_case()` below) — EasyOCR
    preserves case correctly but confuses similar digit/letter glyphs
    (4↔a, 5↔S), so the two engines' errors are complementary. Verified
    against two known-ground-truth images (exact match both times) and
    against a full live search + PDF resolution for "2026 INSC 496"
    (Marietta D'Silva v. Rudolf Clothan Lacerda), which succeeded end to
    end on the first captcha attempt.

Every request/response shape and the captcha-accuracy blocker have now
been confirmed against live traffic — this module is no longer
best-effort/unverified.
--------------------------------------------------------------------------
"""

import re
import json
import time
import secrets
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Literal

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ecourts_fastapi_scrapper_cnr_and_causelist_casestatus_and_courtstatus import (
    solve_captcha as _capsolver_solve_captcha,
)

logger = logging.getLogger("citation_lookup")

# ============================================================================
# 1. CITATION CLASSIFICATION
# ============================================================================

CitationTarget = Literal["SC_NEUTRAL", "SC_SCR", "SC_REPORTER", "TEXT_FALLBACK"]

NEUTRAL_SC_PATTERN = re.compile(r"(\d{4})\s*INSC\s*(\d+)", re.IGNORECASE)
SCR_PATTERN = re.compile(r"\[?(\d{4})\]?\s*(\d+)?\s*S\.?\s?C\.?\s?R\.?\s*(\d+)", re.IGNORECASE)
REPORTER_PATTERN = re.compile(
    r"\(?(\d{4})\)?\s*(\d+)?\s*(SCC|JT|SCALE)\s*(?:SC)?\s*(\d+)",
    re.IGNORECASE,
)
# AIR has its own word order: "AIR 2020 SC 123" (reporter name first, no volume)
AIR_PATTERN = re.compile(r"AIR\s*(\d{4})\s*SC\s*(\d+)", re.IGNORECASE)


@dataclass
class ParsedCitation:
    target: CitationTarget
    raw: str
    year: Optional[str] = None
    index: Optional[str] = None      # INSC number
    volume: Optional[str] = None     # SCR / reporter volume
    page: Optional[str] = None       # SCR / reporter page
    reporter: Optional[str] = None   # SCC / AIR / JT / SCALE


def classify_citation(citation_str: str) -> ParsedCitation:
    """
    Order matters: check neutral citation first (most specific / least
    ambiguous), then reporter citations, then SCR, then give up to free text.
    Free text also covers party-name / case-title searches (e.g.
    "State of UP v. Ram Prakash Singh") — e-SCR's search_txt1 field does a
    text/party-name match against the portal, not just structured citations.
    """
    raw = citation_str.strip()

    if m := NEUTRAL_SC_PATTERN.search(raw):
        return ParsedCitation(target="SC_NEUTRAL", raw=raw, year=m.group(1), index=m.group(2))

    if m := AIR_PATTERN.search(raw):
        return ParsedCitation(
            target="SC_REPORTER", raw=raw, year=m.group(1),
            volume="1", reporter="AIR", page=m.group(2),
        )

    if m := REPORTER_PATTERN.search(raw):
        return ParsedCitation(
            target="SC_REPORTER",
            raw=raw,
            year=m.group(1),
            volume=m.group(2) or "1",
            reporter=m.group(3).upper(),
            page=m.group(4),
        )

    if m := SCR_PATTERN.search(raw):
        return ParsedCitation(
            target="SC_SCR",
            raw=raw,
            year=m.group(1),
            volume=m.group(2) or "1",
            page=m.group(3),
        )

    return ParsedCitation(target="TEXT_FALLBACK", raw=raw)


# ============================================================================
# 2. CAPTCHA SOLVER — CapSolver characters fused with EasyOCR case
# ============================================================================
#
# scr.sci.gov.in's securimage captcha is case-sensitive (confirmed live:
# checkCaptcha rejects a correctly-spelled-but-wrong-case answer with
# {"errormsg":"Invalid Captcha..!!!","captcha_status":"N"}).
#
# CapSolver's ImageToTextTask "common" module always normalizes to
# lowercase — confirmed by direct A/B test against a known captcha image
# (ground truth "5mGKPf"): passing an undocumented `case: true` field
# produced IDENTICAL output ("5mgkpf") to omitting it. That field is not
# real for this task type; do not rely on it.
#
# EasyOCR, run locally against the same two ground-truth images, preserved
# case correctly in both cases ("VwabNU;" for "Vw4bNU", "SmGKPf" for
# "5mGKPf") but confused visually-similar digit/letter pairs (4→a, 5→S).
# The two engines' errors are complementary, so fuse them: keep CapSolver's
# character at each position (it's more reliable on the actual glyph/digit
# identity), but take EasyOCR's case whenever the two agree
# case-insensitively at that position. Verified against both ground-truth
# images to reproduce them exactly before wiring this in.

_easyocr_reader = None  # module-level singleton — EasyOCR init loads model weights, slow


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr  # heavy optional dependency — only imported when actually used
        _easyocr_reader = easyocr.Reader(["en"], gpu=False)
    return _easyocr_reader


def _easyocr_read(image_bytes: bytes) -> str:
    reader = _get_easyocr_reader()
    pieces = reader.readtext(image_bytes, detail=0, paragraph=False)
    return "".join(pieces).strip()


def fuse_captcha_case(capsolver_text: str, easyocr_text: str) -> str:
    """
    Combine CapSolver's character sequence with EasyOCR's case pattern.
    Falls back to capsolver_text unchanged if EasyOCR found nothing or the
    lengths don't line up (after stripping EasyOCR's stray punctuation) —
    a same-length alignment is required for confident position-by-position
    fusion; a mismatched length means one of the two misread the character
    *count*, not just case, and guessing further isn't safe.
    """
    clean_easy = re.sub(r"[^A-Za-z0-9]", "", easyocr_text or "")
    if not clean_easy or len(clean_easy) != len(capsolver_text):
        return capsolver_text
    fused = []
    for c_ch, e_ch in zip(capsolver_text, clean_easy):
        if c_ch.isalpha() and e_ch.isalpha() and c_ch.lower() == e_ch.lower():
            fused.append(e_ch)  # trust EasyOCR's case
        else:
            fused.append(c_ch)  # trust CapSolver's character (incl. digits)
    return "".join(fused)


class CaptchaSolver:
    """
    Runs CapSolver (character accuracy) and local EasyOCR (case accuracy)
    concurrently, then fuses the results. If EasyOCR fails or isn't
    installed, falls back to CapSolver's raw (lowercase) answer rather than
    failing the whole request — degraded accuracy beats no answer.
    """

    async def solve(self, image_bytes: bytes, home_url: str) -> str:
        import base64
        import asyncio

        b64 = base64.b64encode(image_bytes).decode()

        async def _capsolver() -> str:
            # solve_captcha() is sync (uses `requests`) — run off the event loop.
            return await asyncio.to_thread(_capsolver_solve_captcha, b64, home_url)

        async def _easyocr() -> str:
            try:
                return await asyncio.to_thread(_easyocr_read, image_bytes)
            except Exception as e:
                logger.warning("EasyOCR case-fusion pass failed, falling back to CapSolver-only: %s", e)
                return ""

        capsolver_text, easyocr_text = await asyncio.gather(_capsolver(), _easyocr())
        return fuse_captcha_case(capsolver_text, easyocr_text)


captcha_solver = CaptchaSolver()


# ============================================================================
# 3. e-SCR LIVE CLIENT (scr.sci.gov.in)
# ============================================================================

ESCR_BASE = "https://scr.sci.gov.in"
ESCR_SEARCH_PATH = "/scrsearch/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
COMMON_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": ESCR_BASE + ESCR_SEARCH_PATH,
    "Origin": ESCR_BASE,
}


class ESCRError(Exception):
    pass


class ESCRClient:
    """
    Reproduces the real e-SCR search flow captured in
    vanga/indian-supreme-court-judgments/sc-requests.md:

      1. GET  /scrsearch/                    -> app_token + captcha image + cookies
      2. POST ?p=pdf_search/checkCaptcha     -> validate solved captcha
      3. POST ?p=pdf_search/home             -> actual search
      4. POST ?p=pdf_search/openpdfcaptcha   -> resolve real PDF tmp url (captcha again)
    """

    def __init__(self, captcha_solver: CaptchaSolver, timeout: float = 15.0):
        self.captcha_solver = captcha_solver
        self.client = httpx.AsyncClient(
            base_url=ESCR_BASE,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            follow_redirects=True,
        )
        self.app_token: Optional[str] = None
        # Set True after the first successful captcha-verified search on
        # this instance. A live-captured browser trace of scr.sci.gov.in's
        # own pagination request to ?p=pdf_search/home/ contains NO
        # `captcha` field at all — the portal validates the captcha once
        # (checkCaptcha) and relies on the session cookie afterward. So
        # once verified, this instance can be reused for follow-up
        # search_structured() page requests without re-solving.
        self._session_verified = False

    async def _bootstrap_session(self) -> bytes:
        """Load the search page, extract app_token + captcha image bytes."""
        resp = await self.client.get(ESCR_SEARCH_PATH)
        soup = BeautifulSoup(resp.text, "html.parser")

        # VERIFIED against a real page load: `<input type="hidden"
        # name="app_token" id="app_token" value="">` is EMPTY on a fresh
        # page load, and the real captured POST requests also sent
        # `app_token=` empty. So an empty token is normal, expected
        # behavior here — not a failure. Only a missing input entirely
        # means the page structure changed.
        token_input = soup.find("input", {"name": "app_token"})
        if token_input is None:
            raise ESCRError(
                "Could not find app_token input on e-SCR homepage — "
                "page structure may have changed, inspect live HTML"
            )
        self.app_token = token_input.get("value", "")

        # VERIFIED against a real page load: `<img id="captcha_image" ...>`.
        captcha_img = (
            soup.find("img", {"id": "captcha_image"})
            or soup.find("img", {"id": "captcha-img"})
            or soup.find("img", {"class": "captcha"})
        )
        if not captcha_img or not captcha_img.get("src"):
            raise ESCRError(
                "Could not find captcha image on e-SCR homepage — "
                "inspect live HTML and patch the selector"
            )

        captcha_url = captcha_img["src"]
        if captcha_url.startswith("/"):
            captcha_resp = await self.client.get(captcha_url)
        else:
            captcha_resp = await self.client.get(captcha_url, headers={"Referer": ESCR_BASE})
        return captcha_resp.content

    async def _solve_and_verify_captcha(self) -> str:
        """Solve captcha and confirm it via checkCaptcha before using it in a real request."""
        last_error: Optional[str] = None
        for attempt in range(3):
            captcha_bytes = await self._bootstrap_session()
            solved = await self.captcha_solver.solve(captcha_bytes, ESCR_BASE + ESCR_SEARCH_PATH)

            # Field NAMES here are verified against a real captured request to
            # ?p=pdf_search/checkCaptcha (note: "citation_year" here, vs.
            # "citation_yr" on the /home/ search step — genuinely different
            # key names between the two endpoints, both confirmed live).
            # search_opt default "PHRASE" matches the homepage form's actual
            # default radio selection (`<input ... value="PHRASE" checked>`
            # confirmed on a fresh page load — a separate trace showing
            # "ANY" was just a manual UI selection, not the true default).
            # NOT fully verified: the live UI populates search_text/
            # neu_cit_year/citation_year with the SAME values as the search
            # that's about to run (not blank) — if checkCaptcha validation
            # ever turns out to be context-sensitive, mirror `parsed`'s
            # target fields into this payload the same way search() does.
            check_resp = await self.client.post(
                ESCR_SEARCH_PATH,
                params={"p": "pdf_search/checkCaptcha"},
                data={
                    "captcha": solved, "search_text": "", "search_opt": "PHRASE",
                    "escr_flag": "", "proximity": "", "sel_lang": "",
                    "neu_cit_year": "", "neu_no": "", "ncn": "",
                    "citation_vol": "", "citation_year": "", "citation_supl": "",
                    "citation_page": "", "ajax_req": "true", "app_token": self.app_token,
                },
                headers=COMMON_HEADERS,
            )
            try:
                result = check_resp.json()
            except json.JSONDecodeError:
                result = None

            # VERIFIED against a real failure response:
            # {"errormsg":"Invalid Captcha..!!!","captcha_status":"N"}
            # — there is NO "error" key on failure, so the original
            # `not result.get("error")` check would have treated this
            # exact failure response as a SUCCESS and proceeded with a
            # rejected captcha. Fixed to key off captcha_status explicitly;
            # anything other than "Y" is treated as failure (the success
            # value itself is still unconfirmed — "Y" is the DC scraper's
            # convention for the equivalent field, used here as the most
            # likely counterpart, but confirm on the next live success).
            if (
                result is not None
                and check_resp.status_code == 200
                and result.get("captcha_status") == "Y"
            ):
                return solved

            last_error = (
                f"attempt {attempt + 1}: status={check_resp.status_code} "
                f"captcha_status={result.get('captcha_status') if result else None!r} "
                f"errormsg={result.get('errormsg') if result else None!r} "
                f"body={check_resp.text[:200]}"
            )
            logger.info("e-SCR captcha check failed — %s", last_error)

        raise ESCRError(f"Failed to solve/verify e-SCR captcha after 3 attempts ({last_error})")

    def _build_base_form(self) -> dict:
        """
        Field set and literal defaults (dist_code="null" as a string,
        sort_flg="undefined", etc.) are copied verbatim from a real captured
        browser request against https://scr.sci.gov.in/scrsearch/?p=pdf_search/home/
        — the portal's UI always sends the full DataTables field set
        regardless of search mode, so we do too rather than sending a
        minimal subset that might get flagged or rejected server-side.
        Callers overlay pagination, target-specific, and filter fields on
        top of this (and add "captcha" only when a fresh solve is needed).
        """
        return {
            "sEcho": "1", "iColumns": "2", "sColumns": ",",
            "iDisplayStart": "0", "iDisplayLength": "10",
            "mDataProp_0": "0", "sSearch_0": "", "bRegex_0": "false",
            "bSearchable_0": "true", "bSortable_0": "true",
            "mDataProp_1": "1", "sSearch_1": "", "bRegex_1": "false",
            "bSearchable_1": "true", "bSortable_1": "true",
            "sSearch": "", "bRegex": "false",
            "iSortCol_0": "0", "sSortDir_0": "asc", "iSortingCols": "1",
            "search_txt1": "", "search_txt2": "", "search_txt3": "",
            "search_txt4": "", "search_txt5": "",
            "pet_res": "", "state_code": "", "state_code_li": "", "dist_code": "null",
            "case_no": "", "case_year": "", "from_date": "", "to_date": "",
            "judge_name": "", "reg_year": "", "fulltext_case_type": "", "act": "",
            "judge_txt": "", "act_txt": "", "section_txt": "", "judge_val": "",
            "act_val": "", "year_val": "", "judge_arr": "", "flag": "", "disp_nature": "",
            "search_opt": "PHRASE", "date_val": "ALL", "fcourt_type": "3",
            "citation_yr": "", "citation_vol": "", "citation_supl": "", "citation_page": "",
            "case_no1": "", "case_year1": "", "pet_res1": "", "fulltext_case_type1": "",
            "citation_keyword": "", "sel_lang": "", "proximity": "",
            "neu_cit_year": "", "neu_no": "", "ncn": "", "bool_opt": "", "sort_flg": "undefined",
            "ajax_req": "true", "app_token": self.app_token,
        }

    async def _post_search(self, form: dict) -> tuple[list, int, int]:
        resp = await self.client.post(
            ESCR_SEARCH_PATH,
            params={"p": "pdf_search/home/"},
            data=form,
            headers=COMMON_HEADERS,
        )
        try:
            payload = resp.json()
        except json.JSONDecodeError:
            raise ESCRError(
                "e-SCR search returned non-JSON — likely a captcha "
                "rejection or an expired session"
            )

        # VERIFIED against a real response: rows are wrapped under
        # payload["reportrow"]["aaData"], not top-level aaData/data.
        reportrow = payload.get("reportrow") or {}
        rows = reportrow.get("aaData") or []
        total_records = int(reportrow.get("iTotalRecords") or 0)
        total_display_records = int(reportrow.get("iTotalDisplayRecords") or 0)
        return rows, total_records, total_display_records

    async def search(self, parsed: ParsedCitation) -> list[dict]:
        """Run a single-citation verification search and parse the results table."""
        form = self._build_base_form()
        form["captcha"] = await self._solve_and_verify_captcha()

        if parsed.target == "SC_NEUTRAL":
            form["neu_cit_year"] = parsed.year
            form["neu_no"] = parsed.index
        elif parsed.target == "SC_SCR":
            form["citation_yr"] = parsed.year
            form["citation_vol"] = parsed.volume
            form["citation_page"] = parsed.page
        elif parsed.target == "SC_REPORTER":
            # e-SCR stores equivalent citations (SCC/AIR/JT/Scale) per case;
            # citation_keyword does a phrase match against that index.
            form["citation_keyword"] = f"{parsed.year} {parsed.volume} {parsed.reporter} {parsed.page}"
        else:
            # Party-name / case-title / free-text search. search_opt stays
            # at the form default "PHRASE" (exact-phrase matching) — we're
            # verifying a specific case, not browsing broad results.
            form["search_txt1"] = parsed.raw

        rows, _total_records, _total_display_records = await self._post_search(form)
        self._session_verified = True
        return self._parse_rows(rows)

    async def search_structured(
        self, filters: dict, iDisplayStart: int = 0, iDisplayLength: int = 10
    ) -> tuple[list[dict], int, int]:
        """
        General filter-driven search for the "Search Case Law" mode — as
        opposed to `search()`, which resolves one already-known citation.

        Returns (parsed_rows, total_records, total_display_records).

        CAPTCHA is only solved once per instance (see `_session_verified`
        on __init__): reuse this same ESCRClient across page requests of
        one logical search to avoid a paid captcha solve on every page
        turn, matching the real portal's own observed pagination behavior.
        """
        form = self._build_base_form()
        form["iDisplayStart"] = str(iDisplayStart)
        form["iDisplayLength"] = str(iDisplayLength)
        if not self._session_verified:
            form["captcha"] = await self._solve_and_verify_captcha()
            # Re-read app_token: _solve_and_verify_captcha() bootstraps a
            # fresh session (new GET) which may rotate it.
            form["app_token"] = self.app_token

        for key, value in filters.items():
            if value not in (None, ""):
                form[key] = str(value)

        rows, total_records, total_display_records = await self._post_search(form)
        self._session_verified = True
        return self._parse_rows(rows), total_records, total_display_records

    def _parse_rows(self, rows: list) -> list[dict]:
        """
        Parsing here IS verified against a real captured row from a live
        search (2026), e.g.:
        <button ... onclick=javascript:open_pdf('0' ,'2026' ,'2026_6_328_353' ,'2026INSC496' );>
          <strong>MARIETTA D'SILVA<span class='fst-italic'>versus</span>RUDOLF CLOTHAN LACERDA & ORS.</strong>
          - <span class='escrText'>[2026] 6 S.C.R. 328</span>
          <span class='ncDisplay'>2026 INSC 496</span>
          <input type='hidden' id='cnr' value=ESCR010001712026>
        </button>

        Three things the original assumption got wrong, fixed here:
        - each row is `[row_number, html]`, not `[id, html]` — row_number is
          a 1-based sequence, unused, confirmed harmless either way since we
          only read index 1.
        - the real onclick has a space before each comma
          (`open_pdf('0' ,'2026' ,...)`), not `open_pdf('0','2026',...)` —
          the regex below tolerates optional whitespace around commas.
        - onclick is an UNQUOTED HTML attribute (`onclick=javascript:open_pdf(...)`,
          no surrounding quotes). Per the HTML spec, an unquoted attribute
          value ends at the first whitespace — so BeautifulSoup only ever
          sees `onclick="javascript:open_pdf('0'"` and silently invents
          bogus extra attributes (e.g. `,'2026'`) out of what follows.
          Confirmed by direct test against the live markup. Fix: regex the
          RAW row HTML for `open_pdf(...)` instead of trusting the parsed
          attribute — this also works fine since the title's open_pdf call
          and the later "PDF" button's open_pdf call share identical first
          4 args, so matching whichever appears first in the string is safe.
        Also: cnr's `value=` attribute is unquoted in the live HTML too;
        BeautifulSoup's html.parser handles THAT fine since there's no
        internal whitespace in a CNR value to trip the same bug.
        """
        results = []
        for row in rows:
            row_html = row[1] if isinstance(row, list) and len(row) > 1 else str(row)
            soup = BeautifulSoup(row_html, "html.parser")

            title_el = soup.find("strong")
            case_title = title_el.get_text(" ", strip=True) if title_el else None

            nc_el = soup.find("span", class_="ncDisplay")
            nc_display = nc_el.get_text(strip=True) if nc_el else None

            escr_el = soup.find("span", class_="escrText")
            scr_citation = escr_el.get_text(strip=True) if escr_el else None

            cnr_el = soup.find("input", {"id": "cnr"})
            cnr = cnr_el.get("value") if cnr_el else None

            path, year, val = None, None, None
            # verified argument order: open_pdf(val, year, path, nc_display)
            # — matched against the RAW row HTML, not a parsed attribute
            # (see docstring above for why the attribute itself is unreliable).
            m = re.search(
                r"open_pdf\(\s*'(\d+)'\s*,\s*'(\d+)'\s*,\s*'([\w_]+)'\s*,\s*'(\w+)'",
                row_html,
            )
            if m:
                val, year, path, nc_display = m.groups()

            results.append({
                "case_title": case_title,
                "nc_display": nc_display,
                "scr_citation": scr_citation,
                "cnr": cnr,
                "_path": path,
                "_year": year,
                "_val": val,
            })
        return results

    async def resolve_pdf_url(self, path: str, year: str, val: str, nc_display: str) -> Optional[str]:
        """
        Resolve the real tmp PDF URL for one result row. Like
        `search_structured()`, this only solves a fresh captcha if the
        instance isn't already session-verified — resolving a result within
        an already-verified search session (e.g. a user clicking a specific
        row after paging through results) shouldn't cost another solve.
        """
        data = {
            "val": val, "lang_flg": "undefined", "path": path,
            "citation_year": year, "fcourt_type": "3", "nc_display": nc_display,
            "ajax_req": "true", "app_token": self.app_token,
        }
        if not self._session_verified:
            data["captcha"] = await self._solve_and_verify_captcha()
            data["app_token"] = self.app_token

        resp = await self.client.post(
            ESCR_SEARCH_PATH,
            params={"p": "pdf_search/openpdfcaptcha"},
            data=data,
            headers=COMMON_HEADERS,
        )
        try:
            payload = resp.json()
        except json.JSONDecodeError:
            return None

        self._session_verified = True

        # NOT VERIFIED: guessed output-field name — patch after one live run.
        pdf_path = payload.get("outputfile") or payload.get("pdf_path") or payload.get("path")
        if not pdf_path:
            return None
        return pdf_path if pdf_path.startswith("http") else f"{ESCR_BASE}{pdf_path}"

    async def close(self):
        await self.client.aclose()


# ============================================================================
# 4. CACHE — cheap in-process dedupe only.
#
# This is NOT the system of record: it's a single-worker, in-memory dedupe
# to avoid re-solving a captcha twice for concurrent identical requests.
# Persistent 30-day caching lives on the Django side (citation_search app),
# mirroring how Legalv1/ecourt_scrapped/services/scraper_client.py is a
# dumb proxy and Django owns caching for the DC/HC scrapers too.
# ============================================================================

class CitationCache:
    def __init__(self, ttl_seconds: int = 60 * 10):
        self._store: dict[str, dict] = {}
        self.ttl = ttl_seconds

    async def get(self, key: str) -> Optional[dict]:
        return self._store.get(key)

    async def set(self, key: str, value: dict) -> None:
        self._store[key] = value


cache = CitationCache()


# ============================================================================
# 4b. CASE-SEARCH SESSION STORE
#
# Keeps one ESCRClient's cookies + solved-captcha state alive across
# paginated "Search Case Law" requests, so paging through results doesn't
# re-solve a paid captcha on every page (see `search_structured()` above
# and the module docstring's evidence that scr.sci.gov.in's own pagination
# requests to ?p=pdf_search/home/ omit the captcha field entirely once a
# session is validated).
#
# In-process only — assumes this FastAPI service runs as a single worker.
# If deployed with multiple workers/replicas, a session created on worker A
# won't be visible to a "next page" request routed to worker B; that would
# need sticky routing or moving session state to Redis. Verify deployment
# topology before relying on this in production.
# ============================================================================

_SEARCH_SESSION_TTL_SECONDS = 60 * 10
_search_sessions: dict[str, dict] = {}


def _prune_expired_search_sessions() -> None:
    now = time.monotonic()
    expired = [sid for sid, entry in _search_sessions.items() if entry["expires_at"] < now]
    for sid in expired:
        entry = _search_sessions.pop(sid, None)
        if entry:
            asyncio.create_task(entry["client"].close())


def _new_search_session(client: "ESCRClient", filters: dict) -> str:
    _prune_expired_search_sessions()
    session_id = secrets.token_urlsafe(16)
    _search_sessions[session_id] = {
        "client": client,
        "filters": filters,
        "expires_at": time.monotonic() + _SEARCH_SESSION_TTL_SECONDS,
    }
    return session_id


def _get_search_session(session_id: str) -> Optional[dict]:
    entry = _search_sessions.get(session_id)
    if not entry:
        return None
    if entry["expires_at"] < time.monotonic():
        _search_sessions.pop(session_id, None)
        asyncio.create_task(entry["client"].close())
        return None
    entry["expires_at"] = time.monotonic() + _SEARCH_SESSION_TTL_SECONDS
    return entry


# ============================================================================
# 5. FASTAPI ROUTER + APP
# ============================================================================

router = APIRouter(prefix="/api/ecourts/v2/citations", tags=["citations"])


class CitationLookupRequest(BaseModel):
    citation: str = Field(
        ...,
        examples=["2024 INSC 45", "[1951] 1 SCR 525", "(2022) 4 SCC 12"],
    )


class CitationLookupResponse(BaseModel):
    query: str
    resolved_target: CitationTarget
    case_title: Optional[str] = None
    nc_display: Optional[str] = None
    scr_citation: Optional[str] = None
    cnr: Optional[str] = None
    pdf_url: Optional[str] = None
    cached: bool = False
    match_count: int = 0


def _cache_key(citation: str) -> str:
    return "citation:" + re.sub(r"\s+", "", citation).upper()


@router.post("/lookup", response_model=CitationLookupResponse)
async def lookup_citation(payload: CitationLookupRequest):
    key = _cache_key(payload.citation)

    cached = await cache.get(key)
    if cached:
        return CitationLookupResponse(**cached, cached=True)

    parsed = classify_citation(payload.citation)
    escr = ESCRClient(captcha_solver=captcha_solver)

    try:
        results = await escr.search(parsed)
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No Supreme Court judgment found for citation '{payload.citation}'",
            )

        top = results[0]
        pdf_url = None
        if top.get("_path") and top.get("_year") and top.get("_val") is not None:
            pdf_url = await escr.resolve_pdf_url(
                top["_path"], top["_year"], top["_val"], top.get("nc_display") or ""
            )

        response_data = {
            "query": payload.citation,
            "resolved_target": parsed.target,
            "case_title": top.get("case_title"),
            "nc_display": top.get("nc_display"),
            "scr_citation": top.get("scr_citation"),
            "cnr": top.get("cnr"),
            "pdf_url": pdf_url,
            "match_count": len(results),
        }
        await cache.set(key, response_data)
        return CitationLookupResponse(**response_data, cached=False)

    except ESCRError as e:
        logger.exception("e-SCR lookup failed for %s", payload.citation)
        raise HTTPException(status_code=502, detail=f"e-SCR portal error: {e}")
    finally:
        await escr.close()


# ============================================================================
# 5b. CASE-SEARCH ROUTES — filtered, paginated multi-result search ("Search
# Case Law" mode), distinct from /lookup's single-best-match citation
# verification above.
# ============================================================================

class CaseSearchFilters(BaseModel):
    keyword: str = ""
    search_opt: Literal["PHRASE", "ANY", "ALL"] = "PHRASE"
    pet_res: str = ""
    pet_res1: str = ""
    from_date: str = ""
    to_date: str = ""
    judge_name: str = ""
    act: str = ""
    section_txt: str = ""
    case_no: str = ""
    case_year: str = ""
    citation_yr: str = ""
    citation_vol: str = ""
    citation_supl: str = ""
    citation_page: str = ""
    neu_cit_year: str = ""
    neu_no: str = ""

    def to_form_filters(self) -> dict:
        return {
            "search_txt1": self.keyword,
            "search_opt": self.search_opt,
            "pet_res": self.pet_res,
            "pet_res1": self.pet_res1,
            "from_date": self.from_date,
            "to_date": self.to_date,
            "judge_name": self.judge_name,
            "judge_txt": self.judge_name,
            "act": self.act,
            "act_txt": self.act,
            "section_txt": self.section_txt,
            "case_no": self.case_no,
            "case_year": self.case_year,
            "citation_yr": self.citation_yr,
            "citation_vol": self.citation_vol,
            "citation_supl": self.citation_supl,
            "citation_page": self.citation_page,
            "neu_cit_year": self.neu_cit_year,
            "neu_no": self.neu_no,
        }


class CaseSearchRequest(BaseModel):
    filters: CaseSearchFilters
    page: int = 1
    page_size: int = 10


class CaseSearchPageRequest(BaseModel):
    session_id: str
    page: int = 1
    page_size: int = 10


class CaseSearchResult(BaseModel):
    case_title: Optional[str] = None
    nc_display: Optional[str] = None
    scr_citation: Optional[str] = None
    cnr: Optional[str] = None
    # Opaque reference fields for resolving this row's PDF on demand via
    # /case-search/resolve — mirrors the real portal's own click-to-resolve
    # PDF/Split/HTML/Flip view buttons (not preloaded for every row).
    pdf_ref_path: Optional[str] = None
    pdf_ref_year: Optional[str] = None
    pdf_ref_val: Optional[str] = None


class CaseSearchResolveRequest(BaseModel):
    session_id: str
    path: str
    year: str
    val: str
    nc_display: str = ""


class CaseSearchResolveResponse(BaseModel):
    pdf_url: Optional[str] = None


class CaseSearchResponse(BaseModel):
    session_id: str
    results: list[CaseSearchResult]
    total_records: int
    total_display_records: int
    page: int
    page_size: int


def _rows_to_case_results(rows: list[dict]) -> list[CaseSearchResult]:
    return [
        CaseSearchResult(
            case_title=row.get("case_title"),
            nc_display=row.get("nc_display"),
            scr_citation=row.get("scr_citation"),
            cnr=row.get("cnr"),
            pdf_ref_path=row.get("_path"),
            pdf_ref_year=row.get("_year"),
            pdf_ref_val=row.get("_val"),
        )
        for row in rows
    ]


def _clamp_page_args(page: int, page_size: int) -> tuple[int, int]:
    return max(page, 1), max(min(page_size, 50), 1)


@router.post("/case-search/search", response_model=CaseSearchResponse)
async def case_search(payload: CaseSearchRequest):
    """First page of a new filtered search — solves a captcha once and opens a session."""
    page, page_size = _clamp_page_args(payload.page, payload.page_size)
    filters = payload.filters.to_form_filters()

    escr = ESCRClient(captcha_solver=captcha_solver)
    try:
        rows, total_records, total_display_records = await escr.search_structured(
            filters, iDisplayStart=(page - 1) * page_size, iDisplayLength=page_size
        )
    except ESCRError as e:
        logger.exception("e-SCR case search failed")
        await escr.close()
        raise HTTPException(status_code=502, detail=f"e-SCR portal error: {e}")

    session_id = _new_search_session(escr, filters)
    return CaseSearchResponse(
        session_id=session_id,
        results=_rows_to_case_results(rows),
        total_records=total_records,
        total_display_records=total_display_records,
        page=page,
        page_size=page_size,
    )


@router.post("/case-search/page", response_model=CaseSearchResponse)
async def case_search_page(payload: CaseSearchPageRequest):
    """Follow-up page of an existing search session — reuses cookies, no captcha re-solve."""
    entry = _get_search_session(payload.session_id)
    if entry is None:
        raise HTTPException(
            status_code=410,
            detail="Search session expired — run a new search to get a fresh session_id.",
        )

    page, page_size = _clamp_page_args(payload.page, payload.page_size)
    escr: ESCRClient = entry["client"]
    try:
        rows, total_records, total_display_records = await escr.search_structured(
            entry["filters"], iDisplayStart=(page - 1) * page_size, iDisplayLength=page_size
        )
    except ESCRError as e:
        logger.exception("e-SCR case search page fetch failed")
        _search_sessions.pop(payload.session_id, None)
        await escr.close()
        raise HTTPException(status_code=502, detail=f"e-SCR portal error: {e}")

    return CaseSearchResponse(
        session_id=payload.session_id,
        results=_rows_to_case_results(rows),
        total_records=total_records,
        total_display_records=total_display_records,
        page=page,
        page_size=page_size,
    )


@router.post("/case-search/resolve", response_model=CaseSearchResolveResponse)
async def case_search_resolve(payload: CaseSearchResolveRequest):
    """
    Resolve one result row's PDF link on demand — mirrors the real portal's
    click-to-resolve PDF button. Reuses the existing search session, so this
    doesn't cost a fresh captcha solve in the common case (see
    `ESCRClient.resolve_pdf_url`).
    """
    entry = _get_search_session(payload.session_id)
    if entry is None:
        raise HTTPException(
            status_code=410,
            detail="Search session expired — run a new search to get a fresh session_id.",
        )

    escr: ESCRClient = entry["client"]
    try:
        pdf_url = await escr.resolve_pdf_url(payload.path, payload.year, payload.val, payload.nc_display)
    except ESCRError as e:
        logger.exception("e-SCR case search PDF resolve failed")
        _search_sessions.pop(payload.session_id, None)
        await escr.close()
        raise HTTPException(status_code=502, detail=f"e-SCR portal error: {e}")

    return CaseSearchResolveResponse(pdf_url=pdf_url)


app = FastAPI(
    title="Mamla.AI — Supreme Court Citation Lookup",
    description=(
        "Resolves Indian Supreme Court citations (neutral/INSC, SCR, "
        "SCC/AIR/JT/Scale) and party-name searches against the live e-SCR "
        "portal (scr.sci.gov.in). Mounted at /sc by the unified scraper "
        "entry point — see main.py."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "cache_size": len(cache._store)}
