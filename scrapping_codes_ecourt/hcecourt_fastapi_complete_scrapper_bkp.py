"""
hc_court_app.py
═══════════════════════════════════════════════════════════════════
Mamla.AI — High Court Case Search  (standalone FastAPI, single file)
Source:  https://hcservices.ecourts.gov.in/hcservices/

ARCHITECTURE — HTTP-first, no Playwright for case searches:
  The portal exposes a proper JSON API under /hcservices/cases_qry/
  All search modes call these endpoints directly after obtaining a
  PHP session cookie + solved CAPTCHA.

Verified API endpoints (from browser network tab):
  POST cases_qry/o_civil_case_history.php   ← party name, case number etc.
  GET  cases_qry/o_civil_case_history.php   ← CNR lookup
  POST cases_qry/o_order_list.php           ← court orders
  POST cases_qry/o_causelist.php            ← cause list

Request params (from the actual POST body you shared):
  court_code=1
  state_code=13           (HC state code)
  court_complex_code=1    (bench / dist_code)
  caseStatusSearchType=CSpartyName | CNRNumber | CSCaseNumber | CSadvName |
                          CSFilingNumber | CSFIRNumber | CSActType | CSCaseType
  captcha=lh65y8
  f=Pending | Disposed | Both
  petres_name=pankaj
  rgyear=2017

CNR variant (GET):
  state_code=13&dist_code=1&court_code=1&caseStatusSearchType=CNRNumber
  &cino=UPHC010551112017&national_court_code=UPHC01

JSON response fields:
  con[]          ← array of case objects
  totRecords     ← total result count
  courtNameArr   ← HC name array
  court_code     ← bench code array
  Error          ← error string if any

Each case object:
  cino, case_no, case_no2, case_type, case_year
  pet_name, res_name, extra_party, type_name (case type abbreviation)
  date_of_decision, orderurlpath (for fetching orders)
  orcase: "a"=active "d"=disposed

Install:
  pip install fastapi uvicorn httpx beautifulsoup4 lxml tenacity pytesseract Pillow
  # Optional for better CAPTCHA accuracy:
  # export CAPSOLVER_API_KEY=your_key

Run:
  uvicorn hc_court_app:app --reload --port 8001
  Docs: http://localhost:8001/docs
═══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import random
import re
import time
import urllib.parse
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError

# ─────────────────────────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("hc_court")

# ─────────────────────────────────────────────────────────────────
#  PORTAL CONSTANTS
# ─────────────────────────────────────────────────────────────────

BASE            = "https://hcservices.ecourts.gov.in/hcservices"
MAIN_PHP        = f"{BASE}/main.php"
CAPTCHA_URL     = f"{BASE}/securimage/securimage_show.php"

# JSON API endpoints — these return the actual data
API_SEARCH      = f"{BASE}/cases_qry/index_qry.php"          # POST party/case/advocate searches
API_CASE_QUERY  = f"{BASE}/cases_qry/o_civil_case_history.php"  # GET CNR detail
API_ORDERS      = f"{BASE}/cases_qry/o_order_list.php"
API_CAUSELIST   = f"{BASE}/cases_qry/o_causelist.php"

# caseStatusSearchType values
SEARCH_CNR          = "CNRNumber"
SEARCH_PARTY        = "CSpartyName"
SEARCH_CASE_NUMBER  = "CSCaseNumber"
SEARCH_ADVOCATE     = "CSAdvName"
SEARCH_BAR_CODE     = "CSAdvName"   # same endpoint; search_type param switches name vs bar-code
SEARCH_FILING       = "CSfilingNumber"
SEARCH_FIR          = "CSFIRNumber"
SEARCH_ACT          = "CSActType"
SEARCH_CASE_TYPE    = "CSCaseType"
SEARCH_ORDERS_PARTY = "COpartyName"    # court orders search by party name
SEARCH_ORDERS_COURT = "COcourtNumber"  # court orders search by court/judge number
SEARCH_ORDERS_DATE  = "COorderDate"    # court orders search by order date range

API_FETCH_ORDER = f"{BASE}/cases_qry/o_fetchorder.php"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-IN,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Referer":          MAIN_PHP,
    "Origin":           "https://hcservices.ecourts.gov.in",
}

# ─────────────────────────────────────────────────────────────────
#  HIGH COURT REFERENCE DATA
#  state_code  → the HC's state identifier in the portal
#  dist_code   → bench / court complex code within the HC
#  nat_code    → national court code prefix used in CNR numbers
# ─────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────
#  CAUSELIST SESSION CACHE
#  display_causelist_pdf.php filename tokens are tied to the specific
#  HCSERVICES_SESSID that fetched the cause list HTML. We keep that
#  session alive (TTL = 3 min) so PDF proxying reuses it.
# ─────────────────────────────────────────────────────────────────

CAUSELIST_SESSION_TTL = 180   # seconds — portal sessions expire ~4-5 min
_causelist_sessions: dict[str, tuple["HCSession", float]] = {}
_causelist_session_lock = asyncio.Lock()

HIGH_COURTS: dict[str, dict] = {
    "allahabad": {
        "name": "Allahabad High Court",
        "state_code": "13", "nat_code": "UPHC",
        "benches": {
            "allahabad": {"dist_code": "1", "label": "Allahabad (Principal Bench)"},
            "lucknow":   {"dist_code": "2", "label": "Lucknow Bench"},
        },
    },
    "bombay": {
        "name": "Bombay High Court",
        "state_code": "1", "nat_code": "MHHC",
        "benches": {
            # cnr_prefix lists include alternate prefixes observed in the wild (e.g. HCBM)
            "bombay":        {"dist_code": "1", "label": "Appellate Side, Bombay",     "cnr_prefix": ["MHHC01", "HCBM01"]},
            "original":      {"dist_code": "2", "label": "Original Side, Bombay",     "cnr_prefix": ["MHHC02", "HCBM02"]},
            "aurangabad":    {"dist_code": "3", "label": "Bench at Aurangabad",       "cnr_prefix": ["MHHC03", "HCBM03"]},
            "nagpur":        {"dist_code": "4", "label": "Bench at Nagpur",           "cnr_prefix": ["MHHC04", "HCBM04"]},
            "goa":           {"dist_code": "5", "label": "High Court of Bombay at Goa","cnr_prefix": ["MHHC05", "HCBM05"]},
            "special_torts": {"dist_code": "6", "label": "Special Court (TORTS) Bombay","cnr_prefix": ["MHHC06", "HCBM06"]},
            "kolhapur":      {"dist_code": "7", "label": "Bench at Kolhapur",         "cnr_prefix": ["MHHC07", "HCBM07"]},
        },
    },
    "calcutta": {
        "name": "Calcutta High Court",
        "state_code": "16", "nat_code": "WBHC",
        "benches": {
            "calcutta":   {"dist_code": "1", "label": "Original Side"},
            "jalpaiguri": {"dist_code": "2", "label": "Circuit Bench At Jalpaiguri", "cnr_prefix": "WBCHCJ"},
            "appellate":  {"dist_code": "3", "label": "Appellate Side"},
            "port_blair": {"dist_code": "4", "label": "Circuit Bench At Port Blair", "cnr_prefix": ["WBCHCO", "WBCHCP"]},
        },
    },
    "madras": {
        "name": "Madras High Court",
        "state_code": "10", "nat_code": "TNHC",
        "benches": {
            "madras":  {"dist_code": "1", "label": "Chennai (Principal Bench)"},
            "madurai": {"dist_code": "2", "label": "Madurai Bench"},
        },
    },
    "delhi": {
        "name": "High Court of Delhi",
        "state_code": "3", "nat_code": "DLHC",
        "benches": {
            "delhi": {"dist_code": "1", "label": "Delhi"},
        },
    },
    "karnataka": {
        "name": "High Court of Karnataka",
        "state_code": "3", "nat_code": "KRHC",
        "benches": {
            "bangalore":  {"dist_code": "1", "label": "Bangalore (Principal Bench)"},
            "dharwad":    {"dist_code": "2", "label": "Dharwad Bench"},
            "kalaburagi": {"dist_code": "3", "label": "Kalaburagi Bench"},
        },
    },
    "kerala": {
        "name": "High Court of Kerala",
        "state_code": "4", "nat_code": "KLHC",
        "benches": {
            "ernakulam": {"dist_code": "1", "label": "Ernakulam"},
        },
    },
    "gujarat": {
        "name": "High Court of Gujarat",
        "state_code": "17", "nat_code": "GJHC",
        "benches": {
            "ahmedabad": {"dist_code": "1", "label": "Ahmedabad"},
        },
    },
    "rajasthan": {
        "name": "High Court of Rajasthan",
        "state_code": "9", "nat_code": "RJHC",
        "benches": {
            "jaipur":  {"dist_code": "1", "label": "Jaipur Bench"},
            "jodhpur": {"dist_code": "2", "label": "Jodhpur (Principal Bench)"},
        },
    },
    "madhya_pradesh": {
        "name": "High Court of Madhya Pradesh",
        "state_code": "14", "nat_code": "MPHC",
        "benches": {
            "jabalpur": {"dist_code": "1", "label": "Jabalpur (Principal Bench)"},
            "indore":   {"dist_code": "2", "label": "Indore Bench"},
            "gwalior":  {"dist_code": "3", "label": "Gwalior Bench"},
        },
    },
    "andhra_pradesh": {
        "name": "High Court of Andhra Pradesh",
        "state_code": "2", "nat_code": "APHC",
        "benches": {
            "amaravati": {"dist_code": "1", "label": "Amaravati"},
        },
    },
    "telangana": {
        "name": "High Court for State of Telangana",
        "state_code": "29", "nat_code": "TSHC",
        "benches": {
            "hyderabad": {"dist_code": "1", "label": "Hyderabad"},
        },
    },
    "punjab_haryana": {
        "name": "High Court of Punjab and Haryana",
        "state_code": "20", "nat_code": "PHHC",
        "benches": {
            "chandigarh": {"dist_code": "1", "label": "Chandigarh"},
        },
    },
    "orissa": {
        "name": "High Court of Orissa",
        "state_code": "11", "nat_code": "ORHC",
        "benches": {
            "cuttack": {"dist_code": "1", "label": "High Court of Orissa"},
        },
    },
    "gauhati": {
        "name": "Gauhati High Court",
        "state_code": "6", "nat_code": "AZHC",
        "benches": {
            "guwahati": {"dist_code": "1", "label": "Guwahati (Principal Bench)"},
            "kohima":   {"dist_code": "2", "label": "Kohima Bench (Nagaland)"},
            "aizawl":   {"dist_code": "3", "label": "Aizawl Bench (Mizoram)"},
            "itanagar": {"dist_code": "4", "label": "Itanagar Bench (Arunachal)"},
        },
    },
    "patna": {
        "name": "Patna High Court",
        "state_code": "8", "nat_code": "BRHC",
        "benches": {
            "patna": {"dist_code": "1", "label": "Patna"},
        },
    },
    "jharkhand": {
        "name": "Jharkhand High Court",
        "state_code": "7", "nat_code": "JHHC",
        "benches": {
            "ranchi": {"dist_code": "1", "label": "Ranchi"},
        },
    },
    "chhattisgarh": {
        "name": "High Court of Chhattisgarh",
        "state_code": "18", "nat_code": "CGHC",
        "benches": {
            "bilaspur": {"dist_code": "1", "label": "Bilaspur"},
        },
    },
    "himachal": {
        "name": "High Court of Himachal Pradesh",
        "state_code": "5", "nat_code": "HPHC",
        "benches": {
            "shimla": {"dist_code": "1", "label": "Shimla"},
        },
    },
    "uttarakhand": {
        "name": "High Court of Uttarakhand",
        "state_code": "15", "nat_code": "UKHC",
        "benches": {
            "nainital": {"dist_code": "1", "label": "Nainital"},
        },
    },
    "jammu_kashmir": {
        "name": "High Court of Jammu and Kashmir",
        "state_code": "12", "nat_code": "JKHC",
        "benches": {
            "srinagar": {"dist_code": "1", "label": "Srinagar Wing"},
            "jammu":    {"dist_code": "2", "label": "Jammu Wing"},
        },
    },
    "manipur": {
        "name": "High Court of Manipur",
        "state_code": "25", "nat_code": "MNHC",
        "benches": {
            "imphal": {"dist_code": "1", "label": "Imphal"},
        },
    },
    "meghalaya": {
        "name": "High Court of Meghalaya",
        "state_code": "21", "nat_code": "MLHC",
        "benches": {
            "shillong": {"dist_code": "1", "label": "Shillong"},
        },
    },
    "tripura": {
        "name": "High Court of Tripura",
        "state_code": "20", "nat_code": "TRHC",
        "benches": {
            "agartala": {"dist_code": "1", "label": "Agartala"},
        },
    },
    "sikkim": {
        "name": "High Court of Sikkim",
        "state_code": "24", "nat_code": "SKHC",
        "benches": {
            "gangtok": {"dist_code": "1", "label": "Gangtok"},
        },
    },
}


# ─────────────────────────────────────────────────────────────────
#  CNR PREFIX → HC/BENCH REVERSE LOOKUP
#  CNR = {nat_code}{dist_code_2digit}{seq}{year}
#  e.g. UPHC010551112017 → UPHC+01 = allahabad/allahabad
# ─────────────────────────────────────────────────────────────────

def _build_cnr_map() -> dict:
    m = {}
    for hc_key, meta in HIGH_COURTS.items():
        nat = meta["nat_code"]
        sc  = meta["state_code"]
        for b_key, b_meta in meta["benches"].items():
            dc       = b_meta["dist_code"].zfill(2)
            prefixes = b_meta.get("cnr_prefix") or (nat + dc)
            if isinstance(prefixes, str):
                prefixes = [prefixes]
            entry = {
                "hc_key":     hc_key,
                "bench_key":  b_key,
                "state_code": sc,
                "dist_code":  b_meta["dist_code"],
            }
            for key in prefixes:
                m[key] = entry
    return m

CNR_PREFIX_MAP: dict = _build_cnr_map()


def resolve_cnr(cino: str) -> dict:
    """
    Auto-resolve HC + bench from CNR number.
    Never raises for unknown prefixes — logs a warning and returns best-effort metadata
    so the portal call can still proceed (routing is ultimately done by national_court_code=cino[:6]).
    """
    cino = cino.strip().upper().replace("-", "").replace(" ", "")
    prefix = cino[:6]

    # 1. Exact match in map
    meta = CNR_PREFIX_MAP.get(prefix)
    if meta:
        return meta

    # 2. Unknown prefix — attempt best-effort fallback
    #    Extract dist_code from chars 4-5 of the CNR (always present per CNR spec)
    dist_raw = cino[4:6].lstrip("0") or "1"
    nat4 = cino[:4]  # e.g. 'HCBM', 'DLHC'

    # 2a. Try matching by nat_code last-2 chars (e.g. HCBM → 'BM' ≈ Bombay)
    #     and matching dist_code
    for hc_key, hc_meta in HIGH_COURTS.items():
        nat = hc_meta["nat_code"]  # e.g. 'MHHC'
        if nat[-2:] == nat4[-2:] or nat[:2] == nat4[:2] or nat[2:] == nat4[2:]:
            for bench_key, bench_meta in hc_meta["benches"].items():
                if bench_meta["dist_code"].lstrip("0") == dist_raw:
                    log.warning(
                        "resolve_cnr: unknown prefix %r — guessed %s/%s via nat_code+dist match",
                        prefix, hc_key, bench_key,
                    )
                    return {
                        "hc_key":     hc_key,
                        "bench_key":  bench_key,
                        "state_code": hc_meta["state_code"],
                        "dist_code":  bench_meta["dist_code"],
                    }

    # 2b. Widen: match only by dist_code across all HCs
    for hc_key, hc_meta in HIGH_COURTS.items():
        for bench_key, bench_meta in hc_meta["benches"].items():
            if bench_meta["dist_code"].lstrip("0") == dist_raw:
                log.warning(
                    "resolve_cnr: unknown prefix %r — dist_code-only fallback %s/%s",
                    prefix, hc_key, bench_key,
                )
                return {
                    "hc_key":     hc_key,
                    "bench_key":  bench_key,
                    "state_code": hc_meta["state_code"],
                    "dist_code":  bench_meta["dist_code"],
                }

    # 2c. Last resort: use first HC, but override dist_code with what the CNR says
    first_hc_key = next(iter(HIGH_COURTS))
    first_hc = HIGH_COURTS[first_hc_key]
    first_bench_key = next(iter(first_hc["benches"]))
    log.warning(
        "resolve_cnr: no match at all for prefix %r — last-resort fallback, national_court_code will route correctly",
        prefix,
    )
    return {
        "hc_key":     first_hc_key,
        "bench_key":  first_bench_key,
        "state_code": first_hc["state_code"],
        "dist_code":  dist_raw,
    }


# ─────────────────────────────────────────────────────────────────
#  PYDANTIC MODELS
# ─────────────────────────────────────────────────────────────────

class CaseStatusEnum(str, Enum):
    PENDING   = "Pending"
    DISPOSED  = "Disposed"
    UNKNOWN   = "Unknown"

class SearchStatus(str, Enum):
    PENDING  = "Pending"
    DISPOSED = "Disposed"
    BOTH     = "Both"

# Portal sends  f=Pending / f=Disposed / f=Both
_STATUS_MAP = {
    SearchStatus.PENDING:  "Pending",
    SearchStatus.DISPOSED: "Disposed",
    SearchStatus.BOTH:     "Both",
}


class HCCaseItem(BaseModel):
    """
    Lightweight case item — one entry from a list-type search result.
    Matches the JSON fields returned by cases_qry/o_civil_case_history.php
    """
    cino:              str                        # CNR / case internal number
    case_no:           str                        # formatted case number
    case_type_code:    int
    case_type_name:    str                        # e.g. WPIL, CRLA, A482
    case_year:         int
    petitioner:        str
    respondent:        str
    extra_party:       Optional[str]  = None
    date_of_decision:  Optional[str]  = None
    status:            CaseStatusEnum = CaseStatusEnum.PENDING
    order_url_path:         Optional[str]  = None      # encoded path to fetch orders
    detail_url:             Optional[str]  = None      # relative URL to fetch full case detail via this API
    petitioner_advocate:    Optional[str]  = None
    respondent_advocate:    Optional[str]  = None

    class Config:
        use_enum_values = True


class SearchResponse(BaseModel):
    query_type:   str
    high_court:   str
    bench:        str
    total:        int
    page:         int = 1
    cases:        list[HCCaseItem]
    fetched_at:   datetime = Field(default_factory=datetime.utcnow)


class OrderSearchItem(BaseModel):
    cino:           str
    case_no:        Optional[str]  = None
    case_type_name: Optional[str]  = None
    reg_year:       Optional[int]  = None
    reg_no:         Optional[int]  = None
    fil_no:         Optional[int]  = None   # filing number (used when reg_no is null)
    fil_year:       Optional[int]  = None   # filing year
    order_no:       Optional[int]  = None
    order_date:     Optional[str]  = None   # YYYY-MM-DD as returned by portal
    document_name:  Optional[str]  = None   # e.g. "Judgement/Order"
    pdf_url:        Optional[str]  = None   # direct link to open/download the PDF
    detail_url:     Optional[str]  = None   # relative link to full case detail via this API


class OrderSearchResponse(BaseModel):
    query_type:  str
    high_court:  str
    bench:       str
    total:       int
    orders:      list[OrderSearchItem]
    fetched_at:  datetime = Field(default_factory=datetime.utcnow)


class CaseDetailHearing(BaseModel):
    date:            str
    judge:           Optional[str] = None
    purpose:         Optional[str] = None
    next_date:       Optional[str] = None   # Business On Date (date matter was listed)
    cause_list_type: Optional[str] = None   # e.g. "Daily Main", "Daily List"


class CaseDetailOrder(BaseModel):
    date:         str
    order_number: Optional[str] = None
    judge:        Optional[str] = None
    document_url: Optional[str] = None


class SubordinateCourt(BaseModel):
    court_number_and_name: Optional[str] = None
    case_number_and_year:  Optional[str] = None
    case_decision_date:    Optional[str] = None
    state:                 Optional[str] = None
    district:              Optional[str] = None


class IADetail(BaseModel):
    ia_number:      str
    classification: Optional[str] = None
    party:          Optional[str] = None
    filing_date:    Optional[str] = None
    next_date:      Optional[str] = None
    status:         Optional[str] = None


class LinkedCase(BaseModel):
    filing_number: str
    case_number:   Optional[str] = None
    is_main:       bool = False
    status:        Optional[str] = None   # e.g. "Disposed"


class DocumentDetail(BaseModel):
    sr_no:             str
    document_no:       Optional[str] = None
    date_of_receiving: Optional[str] = None
    filed_by:          Optional[str] = None
    advocate_name:     Optional[str] = None
    document_filed:    Optional[str] = None


class ObjectionDetail(BaseModel):
    sr_no:            str
    scrutiny_date:    Optional[str] = None
    objection:        Optional[str] = None
    compliance_date:  Optional[str] = None
    receipt_date:     Optional[str] = None


class PoliceStation(BaseModel):
    code: str
    name: str


class CourtJudge(BaseModel):
    court_code:   str            # e.g. "1007"
    judge_name:   str            # e.g. "HON'BLE JUSTICE ARINDAM MUKHERJEE"
    designation:  Optional[str] = None   # e.g. "JUSTICE"
    date_from:    Optional[str] = None   # YYYY-MM-DD
    date_to:      Optional[str] = None   # YYYY-MM-DD
    bench_label:  Optional[str] = None   # circuit bench label if present


class HCCaseDetail(BaseModel):
    """
    Full case detail — returned after fetching the individual case page.
    Built from the JSON list item + a secondary detail fetch.
    """
    cino:             str
    high_court:       str
    bench:            str
    case_type_name:   str
    case_no:          str
    case_year:        int
    filing_date:      Optional[str] = None
    petitioner:       str
    respondent:       str
    extra_party:      Optional[str]  = None
    date_of_decision: Optional[str]  = None
    status:           CaseStatusEnum = CaseStatusEnum.PENDING
    # Detail fields (from secondary fetch — may be empty for list-only searches)
    registration_date: Optional[str] = None
    next_hearing:      Optional[str] = None
    last_hearing:      Optional[str] = None
    stage_of_case:     Optional[str] = None
    coram:             Optional[str] = None
    bench_type:        Optional[str] = None
    judicial_branch:   Optional[str] = None
    state:             Optional[str] = None
    district:          Optional[str] = None
    not_before_me:     Optional[str] = None
    subject:           Optional[str] = None
    acts:              list[str]     = Field(default_factory=list)
    subordinate_court: Optional[SubordinateCourt] = None
    ia_details:        list[IADetail]             = Field(default_factory=list)
    linked_cases:      list[LinkedCase]            = Field(default_factory=list)
    hearing_history:   list[CaseDetailHearing]    = Field(default_factory=list)
    orders:            list[CaseDetailOrder]      = Field(default_factory=list)
    documents:         list[DocumentDetail]       = Field(default_factory=list)
    objections:        list[ObjectionDetail]      = Field(default_factory=list)
    main_case_number:  Optional[str] = None   # from "Main Matters" section (e.g. S/656/2017)
    petitioner_advocate:  Optional[str] = None
    respondent_advocate:  Optional[str] = None
    data_source:       str            = "hcservices.ecourts.gov.in"
    fetched_at:        datetime       = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class CauseListItem(BaseModel):
    serial:     str
    bench:      str                  # judge/bench name
    list_type:  Optional[str] = None # e.g. "Daily List"
    pdf_url:    Optional[str] = None # absolute URL to view/download the PDF


class CauseListResponse(BaseModel):
    high_court:   str
    bench:        str
    date:         str
    total_items:  int
    items:        list[CauseListItem]
    fetched_at:   datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────
#  CAPTCHA SOLVER
# ─────────────────────────────────────────────────────────────────

class CaptchaSolver:
    """
    Tier 1 — Tesseract local OCR (free, ~40-60% on securimage)
    Tier 2 — Capsolver API (set CAPSOLVER_API_KEY, ~$0.80/1000)
    """
    _key = os.getenv("CAPSOLVER_API_KEY", "")

    async def solve(self, image_bytes: bytes) -> str:
        # Tier 1 — Capsolver API (better accuracy, ~$0.80/1000)
        if self._key:
            try:
                result = await self._capsolver(image_bytes)
                if result and len(result) >= 4:
                    log.debug("captcha:capsolver → %s", result)
                    return result
            except Exception as e:
                log.warning("capsolver failed: %s", e)

        # Tier 2 — Tesseract local OCR (free, ~40-60% on securimage)
        try:
            result = self._tesseract(image_bytes)
            if result and len(result) >= 4:
                log.debug("captcha:tesseract → %s", result)
                return result
        except Exception as e:
            log.debug("tesseract failed: %s", e)

        log.warning("captcha: all methods failed, returning empty string")
        return ""

    def _tesseract(self, image_bytes: bytes) -> str:
        import pytesseract
        from PIL import Image, ImageOps, ImageFilter

        img = Image.open(io.BytesIO(image_bytes))
        img = img.resize((img.width * 3, img.height * 3), Image.LANCZOS)
        img = img.convert("L")
        img = ImageOps.autocontrast(img, cutoff=5)
        img = img.filter(ImageFilter.SHARPEN)
        img = img.point(lambda x: 255 if x > 130 else 0, "1")
        text = pytesseract.image_to_string(
            img,
            config=(
                "--psm 8 --oem 3 "
                "-c tessedit_char_whitelist="
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
            ),
        )
        return text.strip().replace(" ", "").replace("\n", "")

    async def _capsolver(self, image_bytes: bytes) -> str:
        b64 = base64.b64encode(image_bytes).decode()
        async with httpx.AsyncClient(timeout=90.0) as client:
            r = await client.post(
                "https://api.capsolver.com/createTask",
                json={
                    "clientKey": self._key,
                    "task": {"type": "ImageToTextTask", "body": b64, "case": True},
                },
            )
            data = r.json()
            if data.get("errorId") != 0:
                raise RuntimeError(data.get("errorDescription", "unknown capsolver error"))

            # ImageToTextTask is synchronous — solution may already be in the createTask response
            if data.get("status") == "ready" and data.get("solution", {}).get("text"):
                return data["solution"]["text"]

            # Fallback: poll for result (should rarely be needed for this task type)
            task_id = data.get("taskId")
            if not task_id:
                raise RuntimeError("Capsolver returned no taskId and no immediate solution")
            for _ in range(24):
                await asyncio.sleep(3)
                res = await client.post(
                    "https://api.capsolver.com/getTaskResult",
                    json={"clientKey": self._key, "taskId": task_id},
                )
                if res.status_code != 200:
                    log.debug("capsolver getTaskResult status=%s", res.status_code)
                    continue
                rd = res.json()
                if rd.get("status") == "ready":
                    return rd["solution"]["text"]
        raise RuntimeError("Capsolver timed out")


_solver = CaptchaSolver()

# ─────────────────────────────────────────────────────────────────
#  SESSION MANAGER
#  The portal requires:
#    1. A PHP session cookie (PHPSESSID) from GET main.php
#    2. A solved CAPTCHA value from that session's securimage
#  Both are short-lived (~5 minutes). We refresh per request.
# ─────────────────────────────────────────────────────────────────

class HCSession:
    """
    Holds a live httpx.AsyncClient with valid PHPSESSID + solved captcha.
    Create one per search request via HCSession.create().
    """

    def __init__(self, client: httpx.AsyncClient, captcha: str, state_code: str, dist_code: str, captcha_image: bytes = b""):
        self.client        = client
        self.captcha       = captcha
        self.state_code    = state_code
        self.dist_code     = dist_code
        self.captcha_image = captcha_image  # raw PNG bytes, kept for debug

    @classmethod
    async def create(cls, state_code: str, dist_code: str) -> "HCSession":
        """
        1. GET main.php → receive PHPSESSID cookie
        2. GET securimage with same session → get CAPTCHA image
        3. Solve CAPTCHA
        Returns a ready-to-use HCSession.
        """
        client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=30.0,
            follow_redirects=True,
        )

        # Step 1: Establish session
        ts = int(time.time() * 1000)
        await client.get(f"{MAIN_PHP}?t={ts}")

        # Step 2: Fetch CAPTCHA image (same session → same PHPSESSID cookie)
        # Browser uses Math.random() — a float like "0.259731954053827" — as cache-buster
        captcha_resp = await client.get(
            f"{CAPTCHA_URL}?{random.random()}",
            headers={**DEFAULT_HEADERS, "Accept": "image/avif,image/webp,image/png,image/*,*/*;q=0.8"},
        )

        captcha_text = ""
        if captcha_resp.status_code == 200 and len(captcha_resp.content) > 100:
            captcha_text = await _solver.solve(captcha_resp.content)
            # Log PHPSESSID so we can confirm session cookie is flowing.
            # httpx.Cookies.get() may miss domain-scoped cookies; iterate jar directly.
            all_cookies = {c.name: c.value for c in client.cookies.jar}
            phpsessid = all_cookies.get("PHPSESSID", "<not-set>")
            log.info(
                "session_created state=%s bench=%s captcha=%s phpsessid=%s image_bytes=%d all_cookies=%s",
                state_code, dist_code, captcha_text, phpsessid, len(captcha_resp.content),
                list(all_cookies.keys()),
            )
        else:
            log.warning("captcha image fetch failed: status=%s len=%d",
                        captcha_resp.status_code, len(captcha_resp.content))

        return cls(client, captcha_text, state_code, dist_code, captcha_resp.content)

    @classmethod
    async def create_bare(cls, state_code: str, dist_code: str) -> "HCSession":
        """Lightweight session — just PHPSESSID, no captcha. Used for metadata fetches."""
        client = httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=15.0, follow_redirects=True)
        ts = int(time.time() * 1000)
        await client.get(f"{MAIN_PHP}?t={ts}")
        return cls(client, "", state_code, dist_code)

    async def close(self):
        await self.client.aclose()

    def base_params(self) -> dict:
        """Core params shared by all search types."""
        return {
            "court_code":          self.dist_code,
            "state_code":          self.state_code,
            "court_complex_code":  self.dist_code,
            "captcha":             self.captcha,
            "appFlag":             "web",
        }


# ─────────────────────────────────────────────────────────────────
#  JSON RESPONSE PARSER
# ─────────────────────────────────────────────────────────────────

def _parse_cases(raw: dict, hc_key: str, bench_key: str) -> list[HCCaseItem]:
    """
    Parse the JSON response from cases_qry/o_civil_case_history.php
    into a list of HCCaseItem objects.

    The 'con' field is a JSON string (!) containing the array of cases.
    Example structure verified from the actual API response in the document.
    """
    error_msg = raw.get("Error", "")
    if error_msg and error_msg.strip():
        log.warning("portal error: %s", error_msg)
        return []

    # 'con' is a JSON string wrapping the array
    con_raw = raw.get("con", [])
    if isinstance(con_raw, list) and con_raw:
        con_raw = con_raw[0]  # first element is the JSON string
    if isinstance(con_raw, str):
        stripped = con_raw.strip()
        # Browser confirms valid results always start with '['.
        # Anything else (e.g. "No Record(s) Found", empty string) means zero results.
        if not stripped or not stripped.startswith("["):
            if stripped:
                log.info("portal returned no results — con: %r", stripped[:120])
            return []
        try:
            cases_arr = json.loads(con_raw)
        except json.JSONDecodeError:
            log.warning("could not parse 'con' JSON string — value: %r", con_raw[:300])
            return []
    elif isinstance(con_raw, list):
        cases_arr = con_raw
    else:
        return []

    items: list[HCCaseItem] = []
    for c in cases_arr:
        status = (
            CaseStatusEnum.DISPOSED
            if (c.get("date_of_decision") or c.get("orcase") == "d")
            else CaseStatusEnum.PENDING
        )
        items.append(HCCaseItem(
            cino=c.get("cino", ""),
            case_no=c.get("case_no", ""),
            case_type_code=int(c.get("case_type", 0)),
            case_type_name=c.get("type_name", ""),
            case_year=int(c.get("case_year", 0)),
            petitioner=re.sub(r'\s+', ' ', (c.get("pet_name") or c.get("lpet_name") or "")).strip(),
            respondent=re.sub(r'\s+', ' ', (c.get("res_name") or c.get("lres_name") or "")).strip(),
            extra_party=(c.get("extra_party") or "").strip() or None,
            date_of_decision=c.get("date_of_decision") or None,
            status=status,
            order_url_path=c.get("orderurlpath") or None,
            detail_url=f"/case/cnr/{c.get('cino', '')}" if c.get("cino") else None,
            petitioner_advocate=((c.get("adv_name1") or c.get("ladv_name1") or "").strip()) or None,
            respondent_advocate=((c.get("adv_name2") or c.get("ladv_name2") or "").strip()) or None,
        ))
    return items


def _parse_case_detail_html(html: str, base_item: HCCaseItem, hc_key: str, bench_key: str) -> HCCaseDetail:
    """
    Parse the HTML case detail page into HCCaseDetail.
    The portal renders full case details as HTML after a detail-view click.
    We extract the two-column label/value table + history tables.
    """
    soup = BeautifulSoup(html, "lxml")
    hc_meta    = HIGH_COURTS[hc_key]
    bench_meta = hc_meta["benches"][bench_key]

    def fv(*labels: str) -> str:
        """Find value in label/value table rows."""
        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                cell_text = cells[0].get_text(" ", strip=True).lower()
                for label in labels:
                    if label.lower() in cell_text:
                        return cells[1].get_text(" ", strip=True)
        return ""

    def tbl_rows(tbl) -> list[dict]:
        if not tbl:
            return []
        rows = tbl.find_all("tr")
        if not rows:
            return []
        headers = [th.get_text(" ", strip=True) for th in rows[0].find_all(["th", "td"])]
        result = []
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) == len(headers):
                result.append({headers[i]: cells[i].get_text(" ", strip=True) for i in range(len(headers))})
        return result

    # Hearing history
    hearings: list[CaseDetailHearing] = []
    for tbl in soup.find_all("table"):
        hdr_text = " ".join(th.get_text() for th in tbl.find_all("th")).lower()
        if "business" in hdr_text or "purpose" in hdr_text or "hearing" in hdr_text:
            for row in tbl_rows(tbl):
                d = (row.get("Date") or row.get("Business Date") or row.get("Hearing Date") or "").strip()
                if d:
                    hearings.append(CaseDetailHearing(
                        date=d,
                        purpose=(row.get("Business") or row.get("Purpose") or "").strip() or None,
                        next_date=(row.get("Next Date") or "").strip() or None,
                    ))
            if hearings:
                break

    # Orders
    orders_list: list[CaseDetailOrder] = []
    for tbl in soup.find_all("table"):
        hdr_text = " ".join(th.get_text() for th in tbl.find_all("th")).lower()
        if "order" in hdr_text or "judgment" in hdr_text:
            for row_tag in tbl.find_all("tr")[1:]:
                cells = row_tag.find_all(["td", "th"])
                if not cells:
                    continue
                link_tag = row_tag.find("a", href=True)
                doc_url = None
                if link_tag:
                    href = link_tag["href"]
                    doc_url = href if href.startswith("http") else f"https://hcservices.ecourts.gov.in{href}"
                d = cells[0].get_text(strip=True) if cells else ""
                orders_list.append(CaseDetailOrder(
                    date=d,
                    order_number=cells[1].get_text(strip=True) if len(cells) > 1 else None,
                    document_url=doc_url,
                ))
            if orders_list:
                break

    acts_str = fv("acts", "act", "under section")
    acts     = [a.strip() for a in re.split(r"[,;]", acts_str) if a.strip()] if acts_str else []

    return HCCaseDetail(
        cino=base_item.cino,
        high_court=hc_meta["name"],
        bench=bench_meta["label"],
        case_type_name=base_item.case_type_name,
        case_no=base_item.case_no,
        case_year=base_item.case_year,
        petitioner=base_item.petitioner,
        respondent=base_item.respondent,
        extra_party=base_item.extra_party,
        date_of_decision=base_item.date_of_decision,
        status=base_item.status,
        registration_date=fv("registration date", "date of registration") or None,
        next_hearing=fv("next date", "next hearing") or None,
        last_hearing=fv("last date", "previous hearing") or None,
        subject=fv("subject", "nature of case") or None,
        acts=acts,
        petitioner_advocate=fv("petitioner's advocate", "appellant's advocate") or None,
        respondent_advocate=fv("respondent's advocate", "government pleader") or None,
        hearing_history=hearings[-10:],
        orders=orders_list[-5:],
    )




def _parse_cnr_html(html: str, cino: str, hc_key: str, bench_key: str) -> "HCCaseDetail":
    """
    Parse the HTML returned by the CNR endpoint.
    Written against verified real HTML (Allahabad HC, UPHC010551112017).

    HTML sections:
      case_details_table  → Filing No, Registration No, Filing Date, Registration Date, CNR
      table_r             → Next Hearing Date, Stage, Coram, Bench Type, Judicial Branch
      Petitioner_Advocate_table span  → party name + "Advocate- NAME"
      Respondent_Advocate_table span  → same
      subject_table       → Category, Sub Category
      history_table       → Cause List Type | Judge | Business On Date | Hearing Date | Purpose
      IAheading table     → IA details
    """
    soup = BeautifulSoup(html, "lxml")
    hc_meta    = HIGH_COURTS.get(hc_key, {})
    bench_meta = hc_meta.get("benches", {}).get(bench_key, {})

    # ── Helper: flatten cell text ─────────────────────────────────────
    def ct(cell):
        return cell.get_text(" ", strip=True)

    # ── 1. Case Details Table ─────────────────────────────────────────
    # 4-column rows: label | value | label | value
    filing_no = reg_no = filing_date = reg_date = ""
    dtbl = (soup.find("table", class_="case_details_table") or
            soup.find("table", attrs={"class": lambda c: "case_details" in (c or "")}))
    if dtbl:
        for row in dtbl.find_all("tr"):
            cells = row.find_all("td")
            def kv(c): return ct(c).lower()
            if len(cells) >= 2:
                k0, v1 = kv(cells[0]), ct(cells[1])
                if   "filing number"      in k0: filing_no   = v1
                elif "filing date"        in k0: filing_date = v1
                elif "registration number" in k0: reg_no     = v1
                elif "registration date"  in k0: reg_date    = v1
            if len(cells) >= 4:
                k2, v3 = kv(cells[2]), ct(cells[3])
                if   "filing number"      in k2: filing_no   = v3
                elif "filing date"        in k2: filing_date = v3
                elif "registration number" in k2: reg_no     = v3
                elif "registration date"  in k2: reg_date    = v3

    # ── 2. Case Status Red Box (table.table_r) ────────────────────────
    next_hearing = first_hearing = stage = coram = bench_type = judicial_branch = ""
    state_val = district_val = not_before_me = ""
    stbl = (soup.find("table", class_="table_r") or
            soup.find("table", attrs={"class": lambda c: "table_r" in (c or "")}))
    if stbl:
        for row in stbl.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                lbl = ct(cells[0]).lower()
                val = ct(cells[1])
                if   "first hearing"   in lbl: first_hearing  = val
                elif "next hearing"    in lbl: next_hearing   = val
                elif "stage"           in lbl: stage          = val
                elif "coram"           in lbl: coram          = val
                elif "bench type"      in lbl: bench_type     = val
                elif "judicial branch" in lbl: judicial_branch = val
                elif "not before me"   in lbl: not_before_me = val
                elif lbl.strip() == "state":   state_val     = val
                elif lbl.strip() == "district": district_val = val

    def _clean_date_val(v: str) -> str:
        """Return empty string for portal non-date placeholders like ': -' or '--'."""
        return v if re.search(r'\d', v) else ""

    next_hearing  = _clean_date_val(next_hearing)
    first_hearing = _clean_date_val(first_hearing)

    # ── 3. Party Spans ────────────────────────────────────────────────
    # <span class='Petitioner_Advocate_table'>
    #   1) PARTY NAME<br/>
    #      Advocate- ADVOCATE NAME<br/>
    # </span>
    def parse_party_span(cls):
        span = soup.find("span", class_=cls)
        if not span:
            return "", ""
        # Use stripped_strings to get all text nodes
        # NOTE: strip() only removes ASCII whitespace; U+00A0 (&nbsp;) must be stripped separately
        texts = list(span.stripped_strings)
        party = ""
        advocate = ""
        for t in texts:
            t_clean = re.sub(r'\s+', ' ', t.replace('\u00a0', ' ')).strip()  # strip &nbsp;, collapse spaces
            if not t_clean:
                continue
            t_lower = t_clean.lower()
            if t_lower.startswith("advocate-") or t_lower.startswith("advocate -") or t_lower.startswith("advocate\u2013"):
                # Explicit "Advocate-" prefix format (Allahabad HC and others)
                advocate = re.sub(r"(?i)^advocate\s*[-\u2013]\s*", "", t_clean).strip()
            elif re.match(r"^\d+\)\s*", t_clean):
                # Numbered party entry: "1) PARTY NAME"
                if not party:
                    party = re.sub(r"^\d+\)\s*", "", t_clean).strip()
            elif party and not advocate:
                # Indented line after party name with no "Advocate-" prefix (Delhi HC format)
                advocate = t_clean
        return party, advocate

    petitioner, pet_adv  = parse_party_span("Petitioner_Advocate_table")
    respondent, resp_adv = parse_party_span("Respondent_Advocate_table")

    # ── 4. Category / Subject ─────────────────────────────────────────
    category = sub_category = ""
    stbl2 = soup.find("table", id="subject_table")
    if stbl2:
        for row in stbl2.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                lbl = ct(cells[0]).lower()
                val = ct(cells[1])
                if "sub category" in lbl:   sub_category = val
                elif "category"   in lbl:   category     = val
    subject = sub_category or category or judicial_branch or ""

    # ── 5. Derive case_type + case_no + year ──────────────────────────
    case_no   = reg_no or filing_no
    case_type = ""
    year_str  = ""
    if case_no:
        m = re.match(r"^(.+?)\s*/\s*(\d+)\s*/\s*(\d{4})", case_no)
        if m:
            case_type = m.group(1)
            year_str  = m.group(3)
    if not year_str and len(cino) == 16:
        year_str = cino[-4:]

    # ── 6. Status ─────────────────────────────────────────────────────
    status = CaseStatusEnum.PENDING if (stage or next_hearing or first_hearing) else CaseStatusEnum.UNKNOWN

    # ── 7. Hearing History Table ──────────────────────────────────────
    # class='history_table' — 5 columns:
    # [0] Cause List Type  [1] Judge  [2] Business On Date (link)  [3] Hearing Date  [4] Purpose
    #
    # The portal uses unquoted onclick attributes on the <a> tags inside col[2], e.g.:
    #   onclick=viewBusiness('1' ,'1' ,'20260324' ,...)
    # lxml's HTML parser can misinterpret these and shift cell boundaries, causing rows
    # to be dropped.  Fix: strip all <a> tags from the raw history table HTML before
    # re-parsing so lxml only sees clean <td> cells.
    hearings: list[CaseDetailHearing] = []
    htbl_match = re.search(
        r'<table\b[^>]*class=["\']history_table["\'][^>]*>.*?</table>',
        html, re.DOTALL | re.IGNORECASE
    )
    if htbl_match:
        # Unwrap every <a ...>TEXT</a> — keep the inner text (business date link text),
        # remove the tag and its unquoted onclick attributes which confuse lxml.
        htbl_clean = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', htbl_match.group(0),
                            flags=re.DOTALL | re.IGNORECASE)
        htbl_soup = BeautifulSoup(htbl_clean, "lxml")
        htbl = htbl_soup.find("table")
        if htbl:
            rows = htbl.find_all("tr")[1:]  # skip header row
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue
                cause_list = ct(cells[0]).strip()     # Cause List Type (Daily Main, etc.)
                judge_val    = ct(cells[1]).strip()
                # Business On Date — the date the matter was listed / order uploaded
                listed_date  = ct(cells[2]).strip()
                hearing_date = ct(cells[3]).strip()   # actual hearing date
                purpose      = ct(cells[4]).strip() if len(cells) > 4 else ""

                date_val = hearing_date or listed_date
                if date_val and re.match(r'\d{2}-\d{2}-\d{4}', date_val):
                    # business_date is next_date only when it differs from hearing_date
                    biz_date = listed_date if (listed_date and listed_date != hearing_date
                                               and re.match(r'\d{2}-\d{2}-\d{4}', listed_date)) else None
                    hearings.append(CaseDetailHearing(
                        date=date_val,
                        judge=judge_val or None,
                        purpose=purpose or None,
                        next_date=biz_date,
                        cause_list_type=cause_list or None,
                    ))

    # ── 8. Regex fallbacks for dates that may fail on malformed HTML ───
    # Some rows have unclosed/nested <label> tags; use regex on raw HTML as backstop.
    if not (reg_date or filing_date):
        m = re.search(
            r'(?:Filing|Registration)\s+Date[^>]*>\s*(?:<[^>]+>\s*)*([\d]{2}-[\d]{2}-[\d]{4})',
            html, re.IGNORECASE | re.DOTALL
        )
        if m:
            filing_date = m.group(1)

    # ── 9. Acts Table ─────────────────────────────────────────────────
    # Table with headers "Under Act(s)" / "Under Section(s)"
    acts_parsed: list[str] = []
    for tbl in soup.find_all("table"):
        first_row = tbl.find("tr")
        if not first_row:
            continue
        headers = [ct(c).lower() for c in first_row.find_all(["th", "td"])]
        if any("under act" in h for h in headers):
            for row in tbl.find_all("tr")[1:]:
                cells = row.find_all("td")
                if cells:
                    act_name = ct(cells[0]).strip()
                    if act_name:
                        section = ct(cells[1]).strip() if len(cells) > 1 else ""
                        acts_parsed.append(
                            f"{act_name} — {section}"
                            if section and section.upper() != "NOTKNOWN"
                            else act_name
                        )
            break  # only first matching table

    # ── 12. Subordinate Court Information ──────────────────────────────
    # <span class='Lower_court_table'>  label : value <br/> ... </span>
    sub_court: Optional[SubordinateCourt] = None
    lower_span = soup.find("span", class_="Lower_court_table")
    if lower_span:
        sc: dict[str, str] = {}
        for label_el in lower_span.find_all("span"):
            key = ct(label_el).strip().rstrip(":")
            following = label_el.find_next_sibling("label")
            if following:
                val = ct(following).strip().lstrip(":" + "\u00a0").strip()
                sc[key.lower()] = val
        if sc:
            sub_court = SubordinateCourt(
                court_number_and_name=sc.get("court number and name") or None,
                case_number_and_year=sc.get("case number and year") or None,
                case_decision_date=sc.get("case decision date") or None,
                state=sc.get("state") or None,
                district=sc.get("district") or None,
            )

    # ── 11. Linked Cases ──────────────────────────────────────────────────
    # table.linkedCase — two columns: Filing Number | Case Number
    # Contains separator rows (colspan) with sub-headings like "IA Details" — skip those.
    linked_cases_parsed: list[LinkedCase] = []
    lc_tbl = soup.find("table", class_="linkedCase")
    if lc_tbl:
        for row in lc_tbl.find_all("tr"):
            cells = row.find_all("td")
            if not cells:  # header row (th elements only)
                continue
            # Skip colspan separator rows (section sub-headings)
            if any(c.get("colspan") for c in cells):
                continue
            if len(cells) < 2:
                continue
            filing_raw = re.sub(r"\s+", " ", ct(cells[0])).strip()
            case_raw   = re.sub(r"\s+", " ", ct(cells[1])).strip()
            if not filing_raw:
                continue
            # Extract parenthetical marker: "MA/23/2019 ( Disposed )" → status="Disposed"
            paren_src = case_raw or filing_raw
            status_match = re.search(r"\(\s*(.+?)\s*\)", paren_src)
            is_main   = False
            lc_status = None
            if status_match:
                marker = status_match.group(1).lower()
                if marker == "main":
                    is_main = True
                else:
                    lc_status = status_match.group(1).strip()
            filing_clean = re.sub(r"\s*\(.*?\)", "", filing_raw).strip()
            case_clean   = re.sub(r"\s*\(.*?\)", "", case_raw).strip() or None
            linked_cases_parsed.append(LinkedCase(
                filing_number=filing_clean,
                case_number=case_clean,
                is_main=is_main,
                status=lc_status,
            ))

    # ── 12. IA Details ─────────────────────────────────────────────────
    # table.IAheading  — headers: IA Number | Party | Date of Filing | Next Date | IA Status
    ia_details_parsed: list[IADetail] = []
    ia_tbl = soup.find("table", class_="IAheading")
    if ia_tbl:
        for row in ia_tbl.find_all("tr")[1:]:  # skip header
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            # Cell[0]: IA number + Classification
            ia_cell_text = cells[0].get_text(" ", strip=True)
            ia_num_match = re.match(r"([^\s]+)", ia_cell_text)
            ia_num = ia_num_match.group(1) if ia_num_match else ia_cell_text.split()[0] if ia_cell_text.split() else ""
            classif_match = re.search(r"Classification\s*:\s*(.+)", ia_cell_text, re.IGNORECASE)
            classif = classif_match.group(1).strip() if classif_match else None
            # Cell[1]: Party names (newline-separated)
            party_text = re.sub(r"\s+", " ", ct(cells[1])).strip() or None
            filing_dt  = ct(cells[2]).strip() if len(cells) > 2 else None
            next_dt    = ct(cells[3]).strip() if len(cells) > 3 else None
            ia_status  = ct(cells[4]).strip() if len(cells) > 4 else None
            if ia_num:
                ia_details_parsed.append(IADetail(
                    ia_number=ia_num,
                    classification=classif or None,
                    party=party_text,
                    filing_date=filing_dt or None,
                    next_date=next_dt or None,
                    status=ia_status or None,
                ))
    # [0] Order Number  [1] Order on (case ref)  [2] Judge  [3] Order Date  [4] PDF link
    BASE_HC = "https://hcservices.ecourts.gov.in/hcservices/"
    orders_parsed: list[CaseDetailOrder] = []
    order_dates: list[str] = []
    otbl = soup.find("table", class_="order_table")
    if otbl:
        for row in otbl.find_all("tr")[1:]:  # skip header row
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            order_num  = ct(cells[0]).strip()
            order_judge = re.sub(r'\s+', ' ', ct(cells[2])).strip() if len(cells) > 2 else ""
            order_date = ct(cells[3]).strip()
            doc_url    = None
            if len(cells) > 4:
                a = cells[4].find("a")
                if a and a.get("href"):
                    href = a["href"].strip()
                    doc_url = href if href.startswith("http") else BASE_HC + href.lstrip("/")
            if order_date and re.match(r"\d{2}-\d{2}-\d{4}", order_date):
                order_dates.append(order_date)
                orders_parsed.append(CaseDetailOrder(
                    date=order_date,
                    order_number=order_num or None,
                    judge=order_judge or None,
                    document_url=doc_url,
                ))

    # Most recent hearing date — use history rows first, fall back to latest order date.
    # NOTE: "First Hearing Date" in the status box is the OLDEST not the most recent.
    most_recent_hearing: Optional[str] = None
    all_dated: list[str] = [h.date for h in hearings] + order_dates
    if all_dated:
        try:
            most_recent_hearing = max(all_dated, key=lambda d: datetime.strptime(d, "%d-%m-%Y"))
        except ValueError:
            most_recent_hearing = all_dated[-1]

    # ── 10b. Main Matters section ───────────────────────────────────────────
    # Some HCs (especially Bombay Original Side) show a "Main Matters" section between
    # Acts and Hearing History. It contains a single-row table with "Case Number" label.
    # The table has no standard class; we scan for it by label text.
    main_case_number: Optional[str] = None
    for tbl in soup.find_all("table"):
        rows = tbl.find_all("tr")
        if not rows:
            continue
        cells_0 = rows[0].find_all(["td", "th"])
        row_text = " ".join(ct(c).lower() for c in cells_0)
        if "case number" in row_text and "hearing" not in row_text and "filing" not in row_text:
            # Value is in the same row's second cell or in the next row
            if len(cells_0) >= 2:
                val = ct(cells_0[1]).strip()
                if not val and len(rows) > 1:
                    second_row_cells = rows[1].find_all(["td", "th"])
                    val = ct(second_row_cells[0]).strip() if second_row_cells else ""
            elif len(rows) > 1:
                second_row_cells = rows[1].find_all(["td", "th"])
                val = ct(second_row_cells[0]).strip() if second_row_cells else ""
            else:
                val = ""
            if val and val.upper() not in ("CASE NUMBER", ""):
                main_case_number = val
                break

    # ── 13. Document Details ─────────────────────────────────────────────────
    # Table with header containing "Document Filed" or "Filed by"
    docs_parsed: list[DocumentDetail] = []
    for tbl in soup.find_all("table"):
        first_row = tbl.find("tr")
        if not first_row:
            continue
        hdrs = [ct(c).lower() for c in first_row.find_all(["th", "td"])]
        if any("document filed" in h or "filed by" in h for h in hdrs):
            def _idx(labels):
                for lbl in labels:
                    for i, h in enumerate(hdrs):
                        if lbl in h:
                            return i
                return -1
            sr_i   = 0
            dno_i  = _idx(["document no", "doc no"])
            rcv_i  = _idx(["date of receiving", "date of receipt"])
            fby_i  = _idx(["filed by"])
            adv_i  = _idx(["name of advocate", "advocate"])
            dfl_i  = _idx(["document filed"])
            for row in tbl.find_all("tr")[1:]:
                cells = row.find_all("td")
                if not cells:
                    continue
                def _cv(i): return cells[i].get_text(" ", strip=True) if 0 <= i < len(cells) else None
                docs_parsed.append(DocumentDetail(
                    sr_no=_cv(sr_i) or "",
                    document_no=_cv(dno_i),
                    date_of_receiving=_cv(rcv_i),
                    filed_by=_cv(fby_i),
                    advocate_name=_cv(adv_i),
                    document_filed=_cv(dfl_i),
                ))
            break

    # ── 14. Objection Details ────────────────────────────────────────────────
    # Table with "Scrutiny Date" or "Objection Compliance Date" in header
    objs_parsed: list[ObjectionDetail] = []
    for tbl in soup.find_all("table"):
        first_row = tbl.find("tr")
        if not first_row:
            continue
        hdrs = [ct(c).lower() for c in first_row.find_all(["th", "td"])]
        if any("scrutiny date" in h or "compliance date" in h for h in hdrs):
            for row in tbl.find_all("tr")[1:]:
                cells = row.find_all("td")
                if not cells:
                    continue
                def _cv2(i): return cells[i].get_text(" ", strip=True) if 0 <= i < len(cells) else None
                objs_parsed.append(ObjectionDetail(
                    sr_no=_cv2(0) or "",
                    scrutiny_date=_cv2(1),
                    objection=_cv2(2),
                    compliance_date=_cv2(3),
                    receipt_date=_cv2(4),
                ))
            break

    return HCCaseDetail(
        cino=cino,
        high_court=hc_meta.get("name", hc_key),
        bench=bench_meta.get("label", bench_key),
        case_type_name=bench_type or case_type,
        case_no=case_no,
        case_year=int(year_str) if year_str.isdigit() else 0,
        filing_date=filing_date or None,
        petitioner=petitioner,
        respondent=respondent,
        extra_party=None,
        date_of_decision=None,
        status=status,
        registration_date=reg_date or filing_date or None,
        next_hearing=next_hearing or None,
        last_hearing=most_recent_hearing or None,
        stage_of_case=stage or None,
        coram=coram or None,
        bench_type=bench_type or None,
        judicial_branch=judicial_branch or None,
        state=state_val or None,
        district=district_val or None,
        not_before_me=not_before_me or None,
        subject=subject or None,
        acts=acts_parsed,
        subordinate_court=sub_court,
        ia_details=ia_details_parsed,
        linked_cases=linked_cases_parsed,
        petitioner_advocate=pet_adv or None,
        respondent_advocate=resp_adv or None,
        hearing_history=hearings,
        orders=orders_parsed,
        documents=docs_parsed,
        objections=objs_parsed,
        main_case_number=main_case_number or None,
    )


def _tbl_rows_generic(tbl) -> list[dict]:
    """Convert any HTML table to list of dicts keyed by th headers."""
    rows = tbl.find_all("tr")
    if not rows:
        return []
    headers = [th.get_text(" ", strip=True) for th in rows[0].find_all(["th", "td"])]
    result = []
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if cells:
            result.append({
                headers[i] if i < len(headers) else str(i): cells[i].get_text(" ", strip=True)
                for i in range(len(cells))
            })
    return result


# ─────────────────────────────────────────────────────────────────
#  CORE HC API CLIENT
# ─────────────────────────────────────────────────────────────────

class HCClient:
    """
    Stateless client. Each method creates a fresh session, calls the API,
    returns normalised results, then closes the session.
    """

    def _get_meta(self, hc_key: str, bench_key: str):
        hc = HIGH_COURTS.get(hc_key.lower())
        if not hc:
            raise ValueError(f"Unknown HC '{hc_key}'. Valid: {sorted(HIGH_COURTS)}")
        bench = hc["benches"].get(bench_key.lower())
        if not bench:
            raise ValueError(
                f"Unknown bench '{bench_key}' for {hc['name']}. "
                f"Valid: {sorted(hc['benches'])}"
            )
        return hc, bench

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=12))
    async def _post_query(self, hc_key: str, bench_key: str, extra_params: dict, action_code: str = "showRecords") -> dict:
        """POST to the cases_qry endpoint and return the raw JSON dict."""
        hc, bench = self._get_meta(hc_key, bench_key)
        session = await HCSession.create(hc["state_code"], bench["dist_code"])
        try:
            params = {**session.base_params(), **extra_params}
            log.info("POST %s params=%s", API_SEARCH, {k: v for k, v in params.items() if k != "captcha"})
            resp = await session.client.post(
                API_SEARCH,
                params={"action_code": action_code},
                data=params,
                headers={**DEFAULT_HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            body = resp.text
            log.debug("response status=%s body[:200]=%s", resp.status_code, body[:200])
            try:
                return resp.json()
            except Exception:
                # Portal returns HTML when captcha is wrong or session is invalid.
                from bs4 import BeautifulSoup as _BSTmp
                err_text = _BSTmp(body, "html.parser").get_text(" ", strip=True)[:300]
                # Save the captcha image to /tmp so it can be inspected manually
                if session.captcha_image:
                    import tempfile, pathlib
                    ts_fail = int(time.time() * 1000)
                    fail_path = pathlib.Path(tempfile.gettempdir()) / f"hccaptcha_fail_{ts_fail}.png"
                    fail_path.write_bytes(session.captcha_image)
                    log.warning(
                        "POST non-JSON response — captcha=%r solved=%r content-type=%s\n"
                        "  HTML text: %s\n  captcha image saved → %s",
                        session.captcha, session.captcha,
                        resp.headers.get("content-type", "?"),
                        err_text, fail_path,
                    )
                else:
                    log.warning(
                        "POST non-JSON response — captcha=%r content-type=%s\n  HTML text: %s",
                        session.captcha, resp.headers.get("content-type", "?"), err_text,
                    )
                raise ValueError(f"portal returned HTML (captcha may be wrong): {err_text[:150]}")
        finally:
            await session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=12),
        # 4xx/5xx are NOT transient — never retry them
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _get_cnr(self, hc_key: str, bench_key: str, cino: str) -> str:
        """
        GET request for CNR — returns raw HTML (NOT JSON).

        The CNR endpoint returns the full case detail as an HTML page.
        No CAPTCHA required for CNR lookups on the HC portal.

        Portal returns HTTP 500 when the case is not found (undocumented behaviour).
        We intercept that and raise HTTPException(404) immediately — no retries.
        """
        hc, bench = self._get_meta(hc_key, bench_key)
        session = await HCSession.create(hc["state_code"], bench["dist_code"])
        try:
            params = {
                "state_code":           hc["state_code"],
                "dist_code":            bench["dist_code"],
                "court_code":           bench["dist_code"],
                "caseStatusSearchType": SEARCH_CNR,
                "cino":                 cino,
                "national_court_code":  cino[:6],  # first 6 chars of CNR is always the court prefix
            }
            log.info("CNR GET cino=%s state=%s bench=%s", cino, hc["state_code"], bench["dist_code"])
            resp = await session.client.get(
                API_CASE_QUERY,
                params=params,
                headers={**DEFAULT_HEADERS, "Accept": "text/html,application/xhtml+xml,*/*;q=0.9"},
            )
            # Portal returns 500 when CNR is not found — treat as 404, not a server error
            if resp.status_code == 500:
                log.info("CNR not found (portal 500): cino=%s", cino)
                raise HTTPException(
                    status_code=404,
                    detail=f"Case not found for CNR: {cino}. The portal returned no record."
                )
            resp.raise_for_status()
            body = resp.text
            log.debug("CNR response len=%d content_type=%s first_80=%r",
                      len(body), resp.headers.get("content-type", "?"), body[:80])
            return body
        finally:
            await session.close()

    # ── SEARCH MODE 1: CNR ─────────────────────────────────────────

    async def search_cnr(self, cino: str) -> "HCCaseDetail":
        """
        CNR lookup — auto-resolves HC and bench from the CNR prefix.
        No hc/bench params needed. Just pass the 16-char CNR.

        The CNR endpoint returns HTML directly (not JSON).
        No CAPTCHA required for CNR lookups.

        cino: 16-char e.g. UPHC010551112017
          UPHC = Allahabad HC nat_code
          01   = Principal Bench (dist_code, zero-padded)
        """
        cino = cino.strip().upper().replace("-", "").replace(" ", "")
        if len(cino) != 16 or not cino.isalnum():
            raise ValueError(f"CNR must be 16 alphanumeric characters. Got: {cino!r}")

        # Auto-resolve HC + bench from CNR prefix — user never needs to specify these
        meta = resolve_cnr(cino)

        hc_key    = meta["hc_key"]
        bench_key = meta["bench_key"]
        log.info("CNR resolved: cino=%s hc=%s bench=%s state=%s",
                 cino, hc_key, bench_key, meta["state_code"])

        try:
            html = await self._get_cnr(hc_key, bench_key, cino)
        except HTTPException:
            raise  # already a clean 404 from inside _get_cnr (portal 500 case)
        except (RetryError, httpx.HTTPStatusError) as exc:
            # Retries exhausted or a non-500 HTTP error — surface as a clean error
            cause = getattr(exc, '__cause__', None) or exc
            status_code = getattr(getattr(cause, 'response', None), 'status_code', None)
            if status_code and 400 <= status_code < 500:
                raise HTTPException(status_code=404,
                    detail=f"Case not found for CNR: {cino}.")
            raise HTTPException(status_code=503,
                detail="High Court portal unavailable. Please try again shortly.")

        stripped = html.strip()
        if not stripped:
            raise HTTPException(status_code=404, detail=f"Empty response for CNR: {cino}")

        lhtml = stripped.lower()
        if "no record" in lhtml or ("case" not in lhtml and len(stripped) < 500):
            raise HTTPException(
                status_code=404,
                detail=f"No case found for CNR: {cino}. Check the CNR number."
            )

        return _parse_cnr_html(html, cino, hc_key, bench_key)

    # ── SEARCH MODE 2: PARTY NAME ──────────────────────────────────

    async def search_party(
        self,
        hc_key:    str,
        bench_key: str,
        name:      str,
        year:      str,
        status:    SearchStatus = SearchStatus.BOTH,
    ) -> list[HCCaseItem]:
        """
        Search by petitioner or respondent name.
        Partial names work (min 3 chars). Portal matches both petitioner + respondent.
        """
        if len(name.strip()) < 3:
            raise ValueError("Party name must be at least 3 characters")
        raw = await self._post_query(hc_key, bench_key, {
            "caseStatusSearchType": SEARCH_PARTY,
            "petres_name":          name.strip(),
            "rgyear":               year,
            "f":                    _STATUS_MAP[status],
        })
        return _parse_cases(raw, hc_key, bench_key)

    # ── SEARCH MODE 3: CASE NUMBER ─────────────────────────────────

    async def search_case_number(
        self,
        hc_key:      str,
        bench_key:   str,
        case_type:   str,
        case_number: str,
        year:        str,
    ) -> list[HCCaseItem]:
        """
        Search by case type + registration number + year.
        case_type should be the numeric code (1, 2, 3…) or the abbreviation (WPIL, CRLA…).
        The portal returns a list; use /case/detail/{cino} for full history.
        """
        raw = await self._post_query(hc_key, bench_key, {
            "caseStatusSearchType": SEARCH_CASE_NUMBER,
            "case_type":            case_type,
            "case_no":              case_number,
            "rgyear":               year,
        })
        return _parse_cases(raw, hc_key, bench_key)

    # ── SEARCH MODE 4: ADVOCATE NAME ──────────────────────────────

    async def search_advocate_name(
        self,
        hc_key:    str,
        bench_key: str,
        name:      str,
        status:    SearchStatus = SearchStatus.BOTH,
    ) -> list[HCCaseItem]:
        """Search by advocate's enrolled name (min 3 chars)."""
        if len(name.strip()) < 3:
            raise ValueError("Advocate name must be at least 3 characters")
        raw = await self._post_query(hc_key, bench_key, {
            "caseStatusSearchType": SEARCH_ADVOCATE,
            "advocate_name":        name.strip(),
            "search_type":          "1",
            "f":                    _STATUS_MAP[status],
        })
        return _parse_cases(raw, hc_key, bench_key)

    # ── SEARCH MODE 5: BAR CODE ───────────────────────────────────

    async def search_bar_code(
        self,
        hc_key:    str,
        bench_key: str,
        bar_code:  str,
        status:    SearchStatus = SearchStatus.BOTH,
    ) -> list[HCCaseItem]:
        """
        Search by advocate bar registration number.
        Format varies by HC: e.g. MH/1234/2005  or  DL/0001/1998
        """
        raw = await self._post_query(hc_key, bench_key, {
            "caseStatusSearchType": SEARCH_BAR_CODE,
            "adv_bar_state":        bar_code.strip(),
            "search_type":          "2",
            "f":                    _STATUS_MAP[status],
        })
        return _parse_cases(raw, hc_key, bench_key)

    # ── SEARCH MODE 6: FILING NUMBER ──────────────────────────────

    async def search_filing_number(
        self,
        hc_key:        str,
        bench_key:     str,
        filing_number: str,
        year:          str,
        case_type:     str = "",
    ) -> list[HCCaseItem]:
        """Search by pre-registration filing/diary number."""
        raw = await self._post_query(hc_key, bench_key, {
            "caseStatusSearchType": SEARCH_FILING,
            "case_type":            case_type,
            "case_no":              filing_number.strip(),
            "rgyear":               year,
        })
        return _parse_cases(raw, hc_key, bench_key)

    # ── METADATA: POLICE STATIONS ──────────────────────────────

    async def get_police_stations(self, hc_key: str, bench_key: str) -> list[PoliceStation]:
        """
        Fetch the police station dropdown for FIR search.
        Returns [{code, name}] — pass code as police_station_code in search_fir().
        Response format from portal: "0~Select Police Station#3466153~AABKARI 3466153#..."
        """
        hc, bench = self._get_meta(hc_key, bench_key)
        session = await HCSession.create_bare(hc["state_code"], bench["dist_code"])
        try:
            resp = await session.client.post(
                f"{API_SEARCH}?action_code=fillPoliceSt",
                data={"court_code": "1", "state_code": hc["state_code"]},
            )
            text = resp.text.strip()
            stations: list[PoliceStation] = []
            for entry in text.split("#"):
                if "~" not in entry:
                    continue
                code, name_raw = entry.split("~", 1)
                code = code.strip()
                if code == "0":   # skip the "Select Police Station" placeholder
                    continue
                # portal appends the numeric code again at end of name: "AABKARI 3466153"
                name = re.sub(r"\s+\d+$", "", name_raw.strip())
                stations.append(PoliceStation(code=code, name=name))
            return stations
        finally:
            await session.close()

    # ── METADATA: COURT / JUDGE NUMBERS ────────────────────────────

    async def get_court_numbers(self, hc_key: str, bench_key: str) -> list[CourtJudge]:
        """
        Fetch the court/judge dropdown for court-orders search.
        Portal response format:
          D~--Circuit Bench--#2$1001^2019-03-14^2021-04-11~1001-HON'BLE JUSTICE X-JUSTICE(...)#
        Returns [{court_code, judge_name, designation, date_from, date_to, bench_label}]
        """
        hc, bench = self._get_meta(hc_key, bench_key)
        session = await HCSession.create_bare(hc["state_code"], bench["dist_code"])
        try:
            resp = await session.client.post(
                f"{API_SEARCH}?action_code=showselect",
                data={
                    "court_code":         bench["dist_code"],
                    "state_code":         hc["state_code"],
                    "court_complex_code": bench["dist_code"],
                },
            )
            text = resp.text.strip()
        finally:
            await session.close()

        judges: list[CourtJudge] = []
        current_bench_label: Optional[str] = None

        for entry in text.split("#"):
            entry = entry.strip()
            if not entry:
                continue
            # Bench section header: "D~-----Circuit Bench At Jalpaiguri-----"
            if entry.startswith("D~"):
                current_bench_label = entry[2:].strip("-").strip()
                continue
            # Judge entry: "2$1007^2019-03-14^2021-04-11~1007-HON'BLE JUSTICE X-JUSTICE( dates )"
            if "~" not in entry:
                continue
            left, label = entry.split("~", 1)
            # left = "2$1007^2019-03-14^2021-04-11"
            parts = left.split("$", 1)
            if len(parts) < 2:
                continue
            code_dates = parts[1].split("^")
            court_code = code_dates[0].strip()
            date_from  = code_dates[1].strip() if len(code_dates) > 1 else None
            date_to    = code_dates[2].strip() if len(code_dates) > 2 else None
            # label = "1007-HON'BLE JUSTICE X-JUSTICE( 14-03-2019/11-04-2021 )"
            # strip leading "code-"
            clean = re.sub(r"^\d+-", "", label).strip()
            # remove trailing " ( dates )"
            clean = re.sub(r"\s*\(.*?\)\s*$", "", clean).strip()
            # split name from designation on last " -" before designation token
            desig_match = re.search(r"-([A-Z /]+)$", clean)
            if desig_match:
                designation = desig_match.group(1).strip()
                judge_name  = clean[:desig_match.start()].strip()
            else:
                designation = None
                judge_name  = clean
            if not court_code:
                continue
            judges.append(CourtJudge(
                court_code=court_code,
                judge_name=judge_name,
                designation=designation,
                date_from=date_from,
                date_to=date_to,
                bench_label=current_bench_label,
            ))
        return judges

    # ── SEARCH MODE 8: ORDERS BY COURT NUMBER ─────────────────────

    def _order_pdf_url(self, hc_key: str, bench_key: str, url_path: str) -> str | None:
        """Build a full o_fetchorder.php URL that carries state_code+court_code so
        the PDF proxy can warm up the portal session with the right HC context."""
        if not url_path:
            return None
        hc_meta    = HIGH_COURTS.get(hc_key, {})
        bench_meta = (hc_meta.get("benches") or {}).get(bench_key, {})
        state_code = hc_meta.get("state_code", "1")
        court_code = bench_meta.get("dist_code", "1")
        return (
            f"{API_FETCH_ORDER}?orderurlpath={url_path}"
            f"&state_code={state_code}&court_code={court_code}"
        )

    async def search_orders_by_court(
        self,
        hc_key:     str,
        bench_key:  str,
        judge_code: str,
        date_from:  str,
        date_to:    str,
    ) -> list[OrderSearchItem]:
        """
        Search court orders by court/judge number and date range.
        judge_code: court_code from /meta/court_numbers (e.g. "1007")
        date_from/date_to: YYYY-MM-DD
        """
        raw = await self._post_query(hc_key, bench_key, {
            "caseStatusSearchType": SEARCH_ORDERS_COURT,
            "nnjudgecode":          judge_code.strip(),
            "temp_date1":           date_from.strip(),
            "temp_date2":           date_to.strip(),
        })

        order_data = raw.get("con", [])
        if isinstance(order_data, str):
            try:
                order_data = json.loads(order_data)
            except Exception:
                order_data = []
        elif isinstance(order_data, list) and order_data and isinstance(order_data[0], str):
            try:
                order_data = json.loads(order_data[0])
            except Exception:
                order_data = []

        items: list[OrderSearchItem] = []
        for o in (order_data or []):
            url_path = o.get("orderurlpath") or ""
            pdf_url = self._order_pdf_url(hc_key, bench_key, url_path)
            cino = o.get("cino") or ""
            items.append(OrderSearchItem(
                cino=cino,
                case_no=str(o.get("case_no") or "") or None,
                case_type_name=o.get("type_name") or None,
                reg_year=o.get("reg_year") or None,
                reg_no=o.get("reg_no") or None,
                fil_no=o.get("fil_no") or None,
                fil_year=o.get("fil_year") or None,
                order_no=o.get("order_no") or None,
                order_date=o.get("order_dt") or o.get("date_of_decision") or None,
                document_name=(o.get("docu_name") or "").strip() or None,
                pdf_url=pdf_url,
                detail_url=f"/case/cnr/{cino}" if cino else None,
            ))
        return items

    # ── SEARCH MODE 8b: ORDERS BY DATE RANGE ──────────────────────

    async def search_orders_by_date(
        self,
        hc_key:    str,
        bench_key: str,
        date_from: str,
        date_to:   str,
    ) -> list[OrderSearchItem]:
        """
        Search court orders by order date range (COorderDate).
        date_from / date_to: DD-MM-YYYY (as the portal expects)
        action_code=showRecord (no trailing 's') — different from other searches.
        """
        raw = await self._post_query(
            hc_key, bench_key,
            {
                "caseStatusSearchType": SEARCH_ORDERS_DATE,
                "from_date":            date_from.strip(),
                "to_date":              date_to.strip(),
            },
            action_code="showRecords",
        )

        order_data = raw.get("con", [])
        if isinstance(order_data, str):
            try:
                order_data = json.loads(order_data)
            except Exception:
                order_data = []
        elif isinstance(order_data, list) and order_data and isinstance(order_data[0], str):
            try:
                order_data = json.loads(order_data[0])
            except Exception:
                order_data = []

        items: list[OrderSearchItem] = []
        for o in (order_data or []):
            url_path = o.get("orderurlpath") or ""
            pdf_url = self._order_pdf_url(hc_key, bench_key, url_path)
            cino = o.get("cino") or ""
            items.append(OrderSearchItem(
                cino=cino,
                case_no=str(o.get("case_no") or "").strip() or None,
                case_type_name=o.get("type_name") or None,
                reg_year=o.get("reg_year") or None,
                reg_no=o.get("reg_no") or None,
                order_no=o.get("order_no") or None,
                order_date=o.get("order_dt") or None,
                document_name=(o.get("docu_name") or "").strip() or None,
                pdf_url=pdf_url,
                detail_url=f"/case/cnr/{cino}" if cino else None,
            ))
        return items

    # ── SEARCH MODE 7: FIR NUMBER ─────────────────────────────────

    async def search_fir(
        self,
        hc_key:          str,
        bench_key:       str,
        police_station:  str,
        status:          SearchStatus,
        fir_number:      str = "",
        year:            str = "",
    ) -> list[HCCaseItem]:
        """Search criminal cases by FIR number and/or year. police_station and status are required."""
        params: dict = {
            "caseStatusSearchType": SEARCH_FIR,
            "police_st_code":       police_station.strip(),
            "f":                    _STATUS_MAP[status],
        }
        if fir_number:
            params["fir_no"] = fir_number.strip()
        if year:
            params["firyear"] = year.strip()
        raw = await self._post_query(hc_key, bench_key, params)
        return _parse_cases(raw, hc_key, bench_key)

    # ── SEARCH MODE 7b: ADVOCATE NAME / BAR CODE ─────────────────

    async def search_advocate(
        self,
        hc_key:    str,
        bench_key: str,
        query:     str,
        status:    SearchStatus,
    ) -> list[HCCaseItem]:
        """
        Search by advocate name (search_type=1) or bar registration code (search_type=2).
        Automatically uses bar-code mode when query contains '/' (e.g. A/H0267/2014).
        """
        is_bar_code = "/" in query.strip()
        params: dict = {
            "caseStatusSearchType": SEARCH_ADVOCATE,
            "search_type":          "2" if is_bar_code else "1",
            "f":                    _STATUS_MAP[status],
        }
        if is_bar_code:
            params["adv_bar_state"] = query.strip()
        else:
            params["advocate_name"] = query.strip()
        raw = await self._post_query(hc_key, bench_key, params)
        return _parse_cases(raw, hc_key, bench_key)

    # ── SEARCH MODE 8: ACT / SECTION ──────────────────────────────

    async def search_act(
        self,
        hc_key:   str,
        bench_key: str,
        act_code: str,
        section:  str = "",
        status:   SearchStatus = SearchStatus.PENDING,
    ) -> list[HCCaseItem]:
        """
        Search by Act type code + optional section.
        act_code is the numeric code from the portal's act dropdown.
        Use GET /acts/{hc}/{bench} to retrieve valid act codes for an HC.
        """
        params: dict = {
            "caseStatusSearchType": SEARCH_ACT,
            "act_type":             act_code,
            "f":                    _STATUS_MAP[status],
        }
        if section:
            params["under_section"] = section
        raw = await self._post_query(hc_key, bench_key, params)
        return _parse_cases(raw, hc_key, bench_key)

    # ── SEARCH MODE 9: CASE TYPE ──────────────────────────────────

    async def search_case_type(
        self,
        hc_key:    str,
        bench_key: str,
        case_type: str,
        year:      str,
        status:    SearchStatus = SearchStatus.PENDING,
    ) -> list[HCCaseItem]:
        """List all cases of a given type in a year. Returns large result sets."""
        raw = await self._post_query(hc_key, bench_key, {
            "caseStatusSearchType": SEARCH_CASE_TYPE,
            "case_type":            case_type,
            "rgyear":               year,
            "f":                    _STATUS_MAP[status],
        })
        return _parse_cases(raw, hc_key, bench_key)

    # ── CASE DETAIL (HTML fetch by cino) ──────────────────────────

    async def get_case_detail(self, cino: str) -> HCCaseDetail:
        """
        Fetch full case detail by CINO / CNR.
        HC and bench are auto-resolved from the CNR prefix — same as search_cnr.
        """
        return await self.search_cnr(cino)

    # ── COURT ORDERS SEARCH (by party name) ───────────────────────

    async def search_orders_by_party(
        self,
        hc_key:    str,
        bench_key: str,
        name:      str,
        year:      Optional[str] = None,
    ) -> list[OrderSearchItem]:
        """
        Search court orders by party name (COpartyName).
        Returns order documents with direct PDF URLs.
        """
        params: dict = {
            "caseStatusSearchType": SEARCH_ORDERS_PARTY,
            "partynameOrder":       name,
        }
        if year:
            params["rgyearOrder"] = year

        raw = await self._post_query(hc_key, bench_key, params)

        order_data = raw.get("con", [])
        if isinstance(order_data, list) and order_data and isinstance(order_data[0], str):
            try:
                order_data = json.loads(order_data[0])
            except Exception:
                order_data = []

        items: list[OrderSearchItem] = []
        for o in (order_data or []):
            url_path = o.get("orderurlpath") or ""
            pdf_url = self._order_pdf_url(hc_key, bench_key, url_path)
            cino = o.get("cino") or ""
            items.append(OrderSearchItem(
                cino=cino,
                case_no=str(o.get("case_no") or "") or None,
                case_type_name=o.get("type_name") or None,
                reg_year=o.get("reg_year") or None,
                reg_no=o.get("reg_no") or None,
                fil_no=o.get("fil_no") or None,
                fil_year=o.get("fil_year") or None,
                order_no=o.get("order_no") or None,
                order_date=o.get("order_dt") or None,
                document_name=(o.get("docu_name") or "").strip() or None,
                pdf_url=pdf_url,
                detail_url=f"/case/cnr/{cino}" if cino else None,
            ))
        return items

    # ── COURT ORDERS (by CINO) ─────────────────────────────────────

    async def get_orders(
        self, hc_key: str, bench_key: str, cino: str
    ) -> list[CaseDetailOrder]:
        """
        Fetch orders/judgements for a case by CINO. Returns PDF download URLs.
        Uses index_qry.php with caseStatusSearchType=COcaseCino.
        """
        raw = await self._post_query(hc_key, bench_key, {
            "caseStatusSearchType": "COcaseCino",
            "cino":                 cino.strip(),
        })

        order_data = raw.get("con", raw.get("orders", []))
        if isinstance(order_data, str):
            try:
                order_data = json.loads(order_data)
            except Exception:
                order_data = []
        if isinstance(order_data, list) and order_data and isinstance(order_data[0], str):
            try:
                order_data = json.loads(order_data[0])
            except Exception:
                order_data = []

        orders: list[CaseDetailOrder] = []
        for o in (order_data or []):
            pdf_path = o.get("orderurlpath") or o.get("url") or ""
            pdf_url = self._order_pdf_url(hc_key, bench_key, pdf_path)
            orders.append(CaseDetailOrder(
                date=o.get("order_dt") or o.get("order_date") or o.get("date") or "",
                order_number=str(o.get("order_no") or ""),
                document_url=pdf_url,
            ))
        return orders

    def _parse_orders_html(self, html: str) -> list[CaseDetailOrder]:
        soup = BeautifulSoup(html, "lxml")
        orders: list[CaseDetailOrder] = []
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                link = row.find("a", href=True)
                doc_url = None
                if link:
                    href = link["href"]
                    doc_url = href if href.startswith("http") else f"https://hcservices.ecourts.gov.in{href}"
                orders.append(CaseDetailOrder(
                    date=cells[0].get_text(strip=True),
                    order_number=cells[1].get_text(strip=True) if len(cells) > 1 else None,
                    document_url=doc_url,
                ))
        return orders

    # ── CAUSE LIST ────────────────────────────────────────────────

    async def get_cause_list(
        self,
        hc_key:    str,
        bench_key: str,
        list_date: str,
    ) -> CauseListResponse:
        """
        Fetch the daily cause list index for a given date.
        list_date: DD-MM-YYYY (as the portal uses)
        Returns a list of benches with their PDF cause list URLs.
        """
        hc, bench = self._get_meta(hc_key, bench_key)
        state_code = hc["state_code"]
        court_code = bench["dist_code"]
        session = await HCSession.create(state_code, court_code)
        try:
            resp = await session.client.post(
                API_SEARCH,
                params={"action_code": "showCauseList"},
                data={
                    **session.base_params(),
                    "caseStatusSearchType": "CLcauselist",
                    "causelist_date":       list_date,
                    "flag":                 "",
                    "selprevdays":          "0",
                },
                headers={**DEFAULT_HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
        except Exception:
            await session.close()
            raise

        # Keep the session alive in the cache — PDF filename tokens are tied
        # to this specific HCSERVICES_SESSID and cannot be fetched with a new session.
        cache_key = f"{state_code}:{court_code}"
        async with _causelist_session_lock:
            old = _causelist_sessions.pop(cache_key, None)
            if old:
                asyncio.create_task(old[0].close())
            _causelist_sessions[cache_key] = (session, time.time())

        items = self._parse_causelist_html(resp.text)
        # Embed state_code + court_code into each PDF URL so the proxy
        # knows which cached session to look up.
        for item in items:
            if item.pdf_url:
                sep = "&" if "?" in item.pdf_url else "?"
                item.pdf_url = f"{item.pdf_url}{sep}state_code={state_code}&court_code={court_code}"
        return CauseListResponse(
            high_court=hc["name"],
            bench=bench["label"],
            date=list_date,
            total_items=len(items),
            items=items,
        )

    def _parse_causelist_html(self, html: str) -> list[CauseListItem]:
        """
        Parse the HTML table returned by showCauseList.
        Columns: Sr No | Bench | Cause List Type | View Causelist (link)
        PDF href is relative: cases/display_causelist_pdf.php?filename=...
        """
        soup = BeautifulSoup(html, "lxml")
        items: list[CauseListItem] = []
        table = soup.find("table", class_="causelistTbl") or soup.find("table")
        if not table:
            return items
        for row in table.find_all("tr")[1:]:   # skip header
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            serial    = cells[0].get_text(strip=True)
            bench_txt = cells[1].get_text(strip=True)
            list_type = cells[2].get_text(strip=True) or None
            link = cells[3].find("a", href=True)
            pdf_url = None
            if link:
                href = link["href"].strip()
                if href.startswith("http"):
                    pdf_url = href
                else:
                    pdf_url = f"https://hcservices.ecourts.gov.in/hcservices/{href.lstrip('/')}"
            if bench_txt:
                items.append(CauseListItem(
                    serial=serial,
                    bench=bench_txt,
                    list_type=list_type,
                    pdf_url=pdf_url,
                ))
        return items

    # ── HEALTH CHECK ──────────────────────────────────────────────

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(MAIN_PHP)
                portal_ok = r.status_code == 200
        except Exception as e:
            return {"status": "error", "detail": str(e)}
        return {
            "status":  "ok" if portal_ok else "degraded",
            "portal":  MAIN_PHP,
            "captcha": "capsolver" if os.getenv("CAPSOLVER_API_KEY") else "tesseract-local",
        }


# Module-level singleton
_hc = HCClient()


# ─────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────

def _resolve(hc: str, bench: str):
    """Validate HC + bench, raise 422 if bad."""
    hc = hc.lower()
    bench = bench.lower()
    if hc not in HIGH_COURTS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown high court '{hc}'. Use GET /courts for valid keys.",
        )
    if bench not in HIGH_COURTS[hc]["benches"]:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown bench '{bench}' for {HIGH_COURTS[hc]['name']}. "
                   f"Valid: {sorted(HIGH_COURTS[hc]['benches'])}",
        )
    return hc, bench


def _wrap(results: list[HCCaseItem], hc: str, bench: str, query_type: str) -> SearchResponse:
    meta = HIGH_COURTS[hc]
    return SearchResponse(
        query_type=query_type,
        high_court=meta["name"],
        bench=meta["benches"][bench]["label"],
        total=len(results),
        cases=results,
    )


def _err(e: Exception, label: str):
    log.error("%s failed: %s", label, e, exc_info=True)
    if isinstance(e, (ValueError, HTTPException)):
        raise e
    raise HTTPException(status_code=502, detail=f"{label} failed: {e}")


# ─────────────────────────────────────────────────────────────────
#  FASTAPI APPLICATION
# ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Mamla.AI — High Court Case Search",
    description=(
        "Live scraper for hcservices.ecourts.gov.in — all 25 Indian High Courts.\n\n"
        "Uses the portal's internal JSON API (`cases_qry/`) directly. "
        "No Playwright required for case searches — only a CAPTCHA solve per request.\n\n"
        "**Search modes:** CNR · Party Name · Case Number · Advocate Name · "
        "Bar Code · Filing Number · FIR Number · Act Type · Case Type\n\n"
        "**Also:** Case Detail (full history) · Court Orders (PDF URLs) · Cause List\n\n"
        "Built by Neveon AI Technologies Pvt. Ltd. — neveon.ai@gmail.com"
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────
#  INFO / REFERENCE ENDPOINTS
# ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
async def root():
    return {
        "service":  "Mamla.AI — High Court Case Search",
        "version":  "2.0.0",
        "source":   "hcservices.ecourts.gov.in",
        "docs":     "/docs",
        "courts":   "/courts",
        "health":   "/health",
        "endpoints": {
            "cnr_search":      "/case/cnr/{cino}",
            "party_search":    "/case/party?hc=&bench=&name=&year=&status=",
            "case_no_search":  "/case/number?hc=&bench=&case_type=&case_number=&year=",
            "advocate_search": "/case/advocate?hc=&bench=&query=&status=",
            "bar_code_search": "/case/bar-code?hc=&bench=&bar_code=&status=",
            "filing_search":   "/case/filing?hc=&bench=&filing_number=&year=",
            "fir_search":      "/case/fir?hc=&bench=&police_station=<code>&status=Pending&fir_number=&year=",
            "act_search":      "/case/act?hc=&bench=&act_code=&section=&status=",
            "case_type_search":"/case/type?hc=&bench=&case_type=&year=&status=",
            "case_detail":     "/case/detail/{cino}",
            "orders":          "/orders/{cino}?hc=&bench=",
            "cause_list":      "/causelist?hc=&bench=&date=",
        },
    }


@app.get("/courts", tags=["Info"], summary="All supported High Courts and bench keys")
async def list_courts():
    return {
        hc_key: {
            "name":       meta["name"],
            "state_code": meta["state_code"],
            "nat_code":   meta["nat_code"],
            "benches": {
                b_key: b_meta["label"]
                for b_key, b_meta in meta["benches"].items()
            },
        }
        for hc_key, meta in HIGH_COURTS.items()
    }


@app.get("/health", tags=["Info"], summary="Portal reachability check")
async def health():
    return await _hc.health_check()


# ─────────────────────────────────────────────────────────────────
#  SEARCH ENDPOINTS
# ─────────────────────────────────────────────────────────────────

@app.get(
    "/case/cnr/{cino}",
    response_model=HCCaseDetail,
    tags=["Case Search"],
    summary="Search by CNR — full case detail, no HC/bench needed",
    description=(
        "Pass only the 16-character CNR (Case Number Record). "
        "HC and bench are auto-detected from the CNR prefix.\n\n"
        "**Format:** `{nat_code}{bench_code_2digit}{sequence}{year}`\n\n"
        "**Examples:**\n"
        "- `UPHC010551112017` → Allahabad HC, Principal Bench\n"
        "- `UPHC020551112017` → Allahabad HC, Lucknow Bench\n"
        "- `DLHC010551112017` → Delhi HC\n"
        "- `MHHC010551112017` → Bombay HC, Bombay Bench\n\n"
        "Returns: case details, parties, advocates, hearing history."
    ),
)
async def search_cnr(cino: str):
    try:
        return await _hc.search_cnr(cino)
    except HTTPException:
        raise
    except Exception as e:
        _err(e, "CNR search")


@app.get(
    "/case/party",
    response_model=SearchResponse,
    tags=["Case Search"],
    summary="Search by Petitioner / Respondent name (partial OK, min 3 chars)",
    description=(
        "Matches against both petitioner and respondent fields. "
        "Partial names work — `pankaj` returns all cases with 'pankaj' in any party name. "
        "Filter by year and pending/disposed status."
    ),
)
async def search_party(
    hc:     str          = Query(..., example="allahabad"),
    bench:  str          = Query(..., example="allahabad"),
    name:   str          = Query(..., min_length=3, description="Partial or full party name", example="pankaj"),
    year:   str          = Query(..., description="4-digit registration year", example="2017"),
    status: SearchStatus = Query(SearchStatus.BOTH, description="Pending | Disposed | Both"),
):
    hc, bench = _resolve(hc, bench)
    try:
        results = await _hc.search_party(hc, bench, name, year, status)
        return _wrap(results, hc, bench, "party_name")
    except Exception as e:
        _err(e, "Party name search")


@app.get(
    "/case/number",
    response_model=SearchResponse,
    tags=["Case Search"],
    summary="Search by Case Type + Registration Number + Year",
    description=(
        "case_type is the numeric code or abbreviation used by the HC. "
        "Examples: `1`=FAPL, `2`=SAPL, `13`=CRLA, `17`=A482, `20`=WRIA, `92`=WPIL.\n\n"
        "Use GET /case-types/{hc}/{bench} to get valid case type codes for a specific HC."
    ),
)
async def search_case_number(
    hc:          str = Query(..., example="allahabad"),
    bench:       str = Query(..., example="allahabad"),
    case_type:   str = Query(..., description="Numeric code or abbreviation e.g. 92 or WPIL", example="92"),
    case_number: str = Query(..., description="Registration number e.g. 588952", example="588952"),
    year:        str = Query(..., example="2017"),
):
    hc, bench = _resolve(hc, bench)
    try:
        results = await _hc.search_case_number(hc, bench, case_type, case_number, year)
        return _wrap(results, hc, bench, "case_number")
    except Exception as e:
        _err(e, "Case number search")


@app.get(
    "/case/advocate",
    response_model=SearchResponse,
    tags=["Case Search"],
    summary="Search by Advocate Name (min 3 chars)",
    description="Returns all cases linked to the advocate. Partial name search supported.",
)
async def search_advocate(
    hc:     str          = Query(..., example="allahabad"),
    bench:  str          = Query(..., example="allahabad"),
    query:  str          = Query(..., min_length=3, description="Advocate's name (min 3 chars)", example="sharma"),
    status: SearchStatus = Query(SearchStatus.BOTH),
):
    hc, bench = _resolve(hc, bench)
    try:
        results = await _hc.search_advocate_name(hc, bench, query, status)
        return _wrap(results, hc, bench, "advocate_name")
    except Exception as e:
        _err(e, "Advocate name search")


@app.get(
    "/case/bar-code",
    response_model=SearchResponse,
    tags=["Case Search"],
    summary="Search by Advocate Bar Registration Number",
    description=(
        "Exact match on bar registration number. "
        "Format varies by state e.g. `MH/1234/2005` or `DL/0001/1998` or `UP1234`."
    ),
)
async def search_bar_code(
    hc:       str          = Query(..., example="allahabad"),
    bench:    str          = Query(..., example="allahabad"),
    bar_code: str          = Query(..., description="Bar registration number", example="UP12345"),
    status:   SearchStatus = Query(SearchStatus.BOTH),
):
    hc, bench = _resolve(hc, bench)
    try:
        results = await _hc.search_bar_code(hc, bench, bar_code, status)
        return _wrap(results, hc, bench, "bar_code")
    except Exception as e:
        _err(e, "Bar code search")


@app.get(
    "/case/filing",
    response_model=SearchResponse,
    tags=["Case Search"],
    summary="Search by Filing / Diary Number",
    description="Pre-registration filing reference assigned when a case is filed before formal registration.",
)
async def search_filing(
    hc:             str = Query(..., example="allahabad"),
    bench:          str = Query(..., example="allahabad"),
    filing_number:  str = Query(..., description="Filing number e.g. 32226", example="32226"),
    year:           str = Query(..., example="2017"),
    case_type:      str = Query("", description="Case type code or abbreviation (optional)"),
):
    hc, bench = _resolve(hc, bench)
    try:
        results = await _hc.search_filing_number(hc, bench, filing_number, year, case_type)
        return _wrap(results, hc, bench, "filing_number")
    except Exception as e:
        _err(e, "Filing number search")


@app.get(
    "/case/fir",
    response_model=SearchResponse,
    tags=["Case Search"],
    summary="Search criminal cases by FIR Number",
    description="For criminal matters. Provide FIR number, year, and optionally police station name.",
)
async def search_fir(
    hc:              str          = Query(..., example="allahabad"),
    bench:           str          = Query(..., example="allahabad"),
    police_station:  str          = Query(..., description="Police station code — get from /meta/police_stations", example="4890602"),
    status:          SearchStatus = Query(..., description="Case status — Pending, Disposed, or Both"),
    fir_number:      str          = Query("",  description="FIR number (optional)"),
    year:            str          = Query("",  description="FIR year (optional)"),
):
    hc, bench = _resolve(hc, bench)
    try:
        results = await _hc.search_fir(hc, bench, police_station, status, fir_number, year)
        return _wrap(results, hc, bench, "fir_number")
    except Exception as e:
        _err(e, "FIR search")


@app.get(
    "/case/act",
    response_model=SearchResponse,
    tags=["Case Search"],
    summary="Search by Act Type code and optional section",
    description=(
        "act_code is the numeric code from the portal's Act dropdown. "
        "e.g. IPC=1, CrPC=2, NI Act=3. Use GET /acts/{hc}/{bench} to discover codes."
    ),
)
async def search_act(
    hc:       str          = Query(..., example="allahabad"),
    bench:    str          = Query(..., example="allahabad"),
    act_code: str          = Query(..., description="Numeric act code from portal", example="3"),
    section:  str          = Query("",  description="Section e.g. 138 (optional)"),
    status:   SearchStatus = Query(SearchStatus.PENDING),
):
    hc, bench = _resolve(hc, bench)
    try:
        results = await _hc.search_act(hc, bench, act_code, section, status)
        return _wrap(results, hc, bench, "act_type")
    except Exception as e:
        _err(e, "Act search")


@app.get(
    "/case/type",
    response_model=SearchResponse,
    tags=["Case Search"],
    summary="All cases of a Case Type in a year (can be large)",
    description=(
        "Returns all registered cases matching the case type and year. "
        "Results can be very large (thousands of cases for busy HCs). "
        "Use status filter to limit."
    ),
)
async def search_case_type(
    hc:        str          = Query(..., example="allahabad"),
    bench:     str          = Query(..., example="allahabad"),
    case_type: str          = Query(..., description="Case type code or abbreviation", example="92"),
    year:      str          = Query(..., example="2024"),
    status:    SearchStatus = Query(SearchStatus.PENDING),
):
    hc, bench = _resolve(hc, bench)
    try:
        results = await _hc.search_case_type(hc, bench, case_type, year, status)
        return _wrap(results, hc, bench, "case_type")
    except Exception as e:
        _err(e, "Case type search")


@app.get(
    "/case/advocate",
    response_model=SearchResponse,
    tags=["Case Search"],
    summary="Search by Advocate name or Bar registration code",
    description=(
        "Pass an advocate name (e.g. 'sharma') or a bar registration code "
        "(e.g. 'A/H0267/2014'). The endpoint auto-detects which mode to use: "
        "bar-code mode is triggered when the query contains '/'. "
        "\n\n- **By name**: `search_type=1`, field `advocate_name` "
        "\n- **By bar code**: `search_type=2`, field `adv_bar_state`"
    ),
)
async def search_advocate(
    hc:     str          = Query(..., example="allahabad"),
    bench:  str          = Query(..., example="allahabad"),
    query:  str          = Query(..., description="Advocate name OR bar registration code (e.g. A/H0267/2014)", example="sharma"),
    status: SearchStatus = Query(SearchStatus.PENDING),
):
    hc, bench = _resolve(hc, bench)
    try:
        results = await _hc.search_advocate(hc, bench, query, status)
        return _wrap(results, hc, bench, "advocate")
    except Exception as e:
        _err(e, "Advocate search")


# ─────────────────────────────────────────────────────────────────
#  CASE DETAIL
# ─────────────────────────────────────────────────────────────────

@app.get(
    "/case/detail/{cino}",
    response_model=HCCaseDetail,
    tags=["Case Detail"],
    summary="Full case history by CNR — hearing dates, orders, advocates",
    description=(
        "Pass the 16-character CNR. HC and bench are auto-detected from the CNR prefix "
        "(same behaviour as `/case/cnr/{cino}`). "
        "Returns hearing history, court orders, advocate names, acts, and subject."
    ),
)
async def get_case_detail(cino: str):
    try:
        return await _hc.get_case_detail(cino)
    except HTTPException:
        raise
    except Exception as e:
        _err(e, "Case detail")


# ─────────────────────────────────────────────────────────────────
#  COURT ORDERS
# ─────────────────────────────────────────────────────────────────

@app.get(
    "/orders/search",
    response_model=OrderSearchResponse,
    tags=["Court Orders"],
    summary="Search court orders/judgements by party name — returns PDF URLs",
    description=(
        "Searches orders using the COpartyName search type. "
        "Each result has a `pdf_url` (direct link to the order PDF) and "
        "a `detail_url` to fetch the full case history. "
        "The `year` parameter filters by registration year and is optional."
    ),
)
async def search_orders_by_party(
    hc:    str            = Query(..., example="allahabad"),
    bench: str            = Query(..., example="allahabad"),
    name:  str            = Query(..., description="Party name (petitioner or respondent)", example="ramesh"),
    year:  Optional[str]  = Query(None, description="Registration year (optional)", example="2020"),
):
    hc, bench = _resolve(hc, bench)
    try:
        items = await _hc.search_orders_by_party(hc, bench, name, year)
        hc_meta, bench_meta = _hc._get_meta(hc, bench)
        return OrderSearchResponse(
            query_type="orders_party_name",
            high_court=hc_meta["name"],
            bench=bench_meta["label"],
            total=len(items),
            orders=items,
        )
    except Exception as e:
        _err(e, "Orders search")


@app.get(
    "/orders/by-court",
    response_model=OrderSearchResponse,
    tags=["Court Orders"],
    summary="Search court orders by court/judge number and date range",
    description=(
        "Use `GET /meta/court_numbers` first to get the `court_code`, `date_from`, "
        "and `date_to` for a judge. Pass them here to retrieve all orders issued by "
        "that court in the date range. Each result has a `pdf_url` for the document."
    ),
)
async def search_orders_by_court(
    hc:         str = Query(..., example="allahabad"),
    bench:      str = Query(..., example="allahabad"),
    judge_code: str = Query(..., description="Court code from /meta/court_numbers", example="1007"),
    date_from:  str = Query(..., description="Start date YYYY-MM-DD", example="2019-03-14"),
    date_to:    str = Query(..., description="End date YYYY-MM-DD",   example="2021-04-11"),
):
    hc, bench = _resolve(hc, bench)
    try:
        items = await _hc.search_orders_by_court(hc, bench, judge_code, date_from, date_to)
        hc_meta, bench_meta = _hc._get_meta(hc, bench)
        return OrderSearchResponse(
            query_type="orders_court_number",
            high_court=hc_meta["name"],
            bench=bench_meta["label"],
            total=len(items),
            orders=items,
        )
    except Exception as e:
        _err(e, "Orders by court")


@app.get(
    "/orders/by-date",
    response_model=OrderSearchResponse,
    tags=["Court Orders"],
    summary="Search court orders by order date range — returns PDF URLs",
    description=(
        "Fetches all orders issued between `date_from` and `date_to` (inclusive).\n\n"
        "Dates must be in **DD-MM-YYYY** format (e.g. `02-04-2026`). "
        "Each result has a `pdf_url` for the document and a `detail_url` for the full case."
    ),
)
async def search_orders_by_date(
    hc:        str = Query(..., example="allahabad"),
    bench:     str = Query(..., example="allahabad"),
    date_from: str = Query(..., description="Start date DD-MM-YYYY", example="02-04-2026"),
    date_to:   str = Query(..., description="End date DD-MM-YYYY",   example="02-04-2026"),
):
    hc, bench = _resolve(hc, bench)
    try:
        items = await _hc.search_orders_by_date(hc, bench, date_from, date_to)
        hc_meta, bench_meta = _hc._get_meta(hc, bench)
        return OrderSearchResponse(
            query_type="orders_date_range",
            high_court=hc_meta["name"],
            bench=bench_meta["label"],
            total=len(items),
            orders=items,
        )
    except Exception as e:
        _err(e, "Orders by date")


@app.get(
    "/orders/{cino}",
    response_model=list[CaseDetailOrder],
    tags=["Court Orders"],
    summary="Fetch orders and judgements for a case — returns PDF URLs",
    description=(
        "Returns a list of orders/judgements with downloadable PDF URLs. "
        "The `document_url` field in each item is a direct link to the PDF."
    ),
)
async def get_orders(
    cino:  str,
    hc:    str = Query(..., example="allahabad"),
    bench: str = Query(..., example="allahabad"),
):
    hc, bench = _resolve(hc, bench)
    try:
        return await _hc.get_orders(hc, bench, cino)
    except Exception as e:
        _err(e, "Orders fetch")

@app.get(
    "/causelist",
    response_model=CauseListResponse,
    tags=["Cause List"],
    summary="Daily bench cause list",
    description=(
        "Returns the cause list for the specified HC and date. "
        "Date format: `DD-MM-YYYY` (as used on the portal). Defaults to today."
    ),
)
async def get_cause_list(
    hc:        str           = Query(..., example="allahabad"),
    bench:     str           = Query(..., example="allahabad"),
    list_date: Optional[str] = Query(None, description="DD-MM-YYYY. Defaults to today.", example="02-04-2026"),
):
    if not list_date:
        list_date = date.today().strftime("%d-%m-%Y")
    hc, bench = _resolve(hc, bench)
    try:
        return await _hc.get_cause_list(hc, bench, list_date)
    except Exception as e:
        _err(e, "Cause list")


# ─────────────────────────────────────────────────────────────────
#  METADATA ENDPOINTS
# ─────────────────────────────────────────────────────────────────

@app.get(
    "/meta/police_stations",
    response_model=list[PoliceStation],
    tags=["Metadata"],
    summary="Police stations list for FIR search",
    description=(
        "Returns all police station codes and names for the given HC bench.\n\n"
        "Use the `code` value as the `police_station` parameter in `/case/fir`. "
        "No captcha required — this is a lightweight metadata call."
    ),
)
async def get_police_stations(
    hc:    str = Query(..., example="allahabad"),
    bench: str = Query(..., example="allahabad"),
):
    hc, bench = _resolve(hc, bench)
    try:
        return await _hc.get_police_stations(hc, bench)
    except Exception as e:
        _err(e, "Police stations")


@app.get(
    "/meta/court_numbers",
    response_model=list[CourtJudge],
    tags=["Metadata"],
    summary="Court/judge list for court-orders search",
    description=(
        "Returns all court codes and judge names for the given HC bench.\n\n"
        "Use the `court_code` + `date_from` + `date_to` values as parameters in "
        "`/orders/by-court`. No captcha required."
    ),
)
async def get_court_numbers(
    hc:    str = Query(..., example="allahabad"),
    bench: str = Query(..., example="allahabad"),
):
    hc, bench = _resolve(hc, bench)
    try:
        return await _hc.get_court_numbers(hc, bench)
    except Exception as e:
        _err(e, "Court numbers")


# ─────────────────────────────────────────────────────────────────
#  DEBUG ENDPOINTS
# ─────────────────────────────────────────────────────────────────

@app.get(
    "/debug/captcha",
    tags=["Debug"],
    summary="Inspect captcha solving — create a real session and return image + solution",
    description=(
        "Creates a live session with the portal, fetches the CAPTCHA image, "
        "solves it via Capsolver/Tesseract, and returns all diagnostics.\n\n"
        "Use this to verify whether Capsolver is solving the securimage correctly before "
        "attributing failures to network/session issues."
    ),
)
async def debug_captcha(
    hc:    str = Query(..., example="allahabad"),
    bench: str = Query(..., example="allahabad"),
):
    hc_key, bench_key = _resolve(hc, bench)
    hc_meta    = HIGH_COURTS[hc_key]
    bench_meta = hc_meta["benches"][bench_key]
    session = await HCSession.create(hc_meta["state_code"], bench_meta["dist_code"])
    await session.close()
    phpsessid = session.client.cookies.get("PHPSESSID", "<not-set>")
    img_b64 = base64.b64encode(session.captcha_image).decode() if session.captcha_image else ""
    return {
        "phpsessid":        phpsessid,
        "captcha_solved":   session.captcha,
        "captcha_image_b64": img_b64,
        "image_bytes":      len(session.captcha_image),
        "note": (
            "Paste captcha_image_b64 into https://base64.guru/converter/decode/image "
            "to view the image and compare with captcha_solved."
        ),
    }


# ─────────────────────────────────────────────────────────────────
#  PDF PROXY
# ─────────────────────────────────────────────────────────────────

@app.get(
    "/order-pdf",
    tags=["Court Orders"],
    summary="Proxy an HC order PDF through a fresh portal session",
    description=(
        "The HC portal requires a valid PHPSESSID cookie to serve PDFs via "
        "`display_pdf.php`. This endpoint creates a bare session (no CAPTCHA) "
        "and fetches the PDF with that cookie, returning raw binary.\n\n"
        "Pass the full `document_url` from a case or orders response as `pdf_url`. "
        "`state_code` and `court_code` are parsed from the PDF URL automatically."
    ),
)
async def proxy_order_pdf(
    pdf_url: str = Query(..., description="Full display_pdf.php URL as returned in document_url"),
):
    from urllib.parse import urlparse as _ulp, parse_qs as _pqs
    from fastapi.responses import Response as _Resp

    # SSRF guard
    parsed = _ulp(pdf_url)
    if parsed.hostname not in ("hcservices.ecourts.gov.in",):
        raise HTTPException(status_code=400, detail="pdf_url must be from hcservices.ecourts.gov.in")

    # Derive state_code + court_code from the URL params — no hc/bench slugs needed
    qs = _pqs(parsed.query)
    state_code = qs.get("state_code", ["16"])[0]
    court_code = qs.get("court_code", qs.get("cCode", ["1"]))[0]

    cino = qs.get("cino", [""])[0].strip()

    # For causelist PDFs the filename token is tied to the session that fetched
    # the cause list HTML. Reuse that cached session if still fresh.
    # For order PDFs a fresh full session (CAPTCHA) is needed.
    is_causelist = "display_causelist_pdf.php" in pdf_url
    owns_session = True

    if is_causelist:
        cache_key = f"{state_code}:{court_code}"
        async with _causelist_session_lock:
            cached = _causelist_sessions.get(cache_key)
            if cached:
                cached_sess, cached_ts = cached
                if time.time() - cached_ts < CAUSELIST_SESSION_TTL:
                    session = cached_sess
                    owns_session = False
                    log.info("proxy_order_pdf: reusing causelist session key=%s", cache_key)
                else:
                    # expired — close it and fall through to create a new one
                    asyncio.create_task(cached_sess.close())
                    del _causelist_sessions[cache_key]
                    session = await HCSession.create(state_code, court_code)
            else:
                log.warning("proxy_order_pdf: no cached causelist session for %s — creating new", cache_key)
                session = await HCSession.create(state_code, court_code)
    else:
        session = await HCSession.create(state_code, court_code)
    try:
        # For order PDFs: also warm up with the case history page so the portal
        # sees a valid navigation context (non-fatal if this fails).
        if cino:
            try:
                await session.client.get(
                    API_CASE_QUERY,
                    params={
                        "state_code":           state_code,
                        "dist_code":            court_code,
                        "court_code":           court_code,
                        "caseStatusSearchType": "CNRNumber",
                        "cino":                 cino,
                        "national_court_code":  cino[:6] if len(cino) >= 6 else cino,
                    },
                    headers={**DEFAULT_HEADERS, "Accept": "text/html,*/*"},
                    timeout=20.0,
                )
            except Exception as warm_err:
                log.warning("proxy_order_pdf warm-up GET failed (non-fatal): %s", warm_err)

        log.info("proxy_order_pdf state=%s court=%s cino=%s url=%s", state_code, court_code, cino, pdf_url[:80])
        resp = await session.client.get(
            pdf_url,
            headers={**DEFAULT_HEADERS, "Accept": "application/pdf,*/*"},
            timeout=30.0,
        )
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "application/pdf")
        if "text/html" in content_type or "text/plain" in content_type:
            sample = resp.text[:300]
            log.warning("proxy_order_pdf: portal returned HTML — %s", sample)
            raise HTTPException(status_code=502, detail=f"Portal returned non-PDF response: {sample[:150]}")
        return _Resp(
            content=resp.content,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline; filename=\"order.pdf\""},
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error("proxy_order_pdf error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"PDF fetch failed: {e}")
    finally:
        if owns_session:
            await session.close()


# ─────────────────────────────────────────────────────────────────
#  ENTRYPOINT
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("hcecourt_fastapi_complete_scrapper:app", host="0.0.0.0", port=8001, reload=True, log_level="info")
