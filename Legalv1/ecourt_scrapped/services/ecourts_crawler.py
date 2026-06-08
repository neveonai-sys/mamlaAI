"""
eCourts India — Direct Scraper for Master/Location Data
========================================================
Scrapes the complete location hierarchy directly from eCourts AJAX endpoints
using curl_cffi (TLS fingerprint impersonation) + BeautifulSoup.

No dependency on the FastAPI scraper — this talks to eCourts itself.

Data scraped:
    • States              (hardcoded — never changes)
    • Districts           (per state)
    • Court Complexes     (per district)
    • Establishments      (per complex)
    • Courts / Benches    (per establishment)
    • Police Stations     (per complex+establishment)
    • Case Types          (per complex+establishment)
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
BASE_URL    = "https://services.ecourts.gov.in/ecourtindia_v6"
CL_HOME_URL = f"{BASE_URL}/?p=cause_list/index"
CS_HOME_URL = f"{BASE_URL}/?p=casestatus/index"
CO_HOME_URL = f"{BASE_URL}/?p=courtorder/index"
IMPERSONATE = "chrome110"

REQUEST_DELAY_SEC       = 0.4
COMPLEX_BATCH_DELAY_SEC = 1.0
DISTRICT_BATCH_DELAY    = 2.0

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

# ──────────────────────────────────────────────────────────────────────────────
# HARDCODED STATES (confirmed from live eCourts HTML)
# ──────────────────────────────────────────────────────────────────────────────
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
# SESSION POOL — keeps cookies / TLS session alive across calls
# ──────────────────────────────────────────────────────────────────────────────
_sessions: dict[str, cffi_requests.Session] = {}


def get_session(home_url: str) -> cffi_requests.Session:
    if home_url not in _sessions:
        s = cffi_requests.Session(impersonate=IMPERSONATE)
        resp = s.get(home_url, headers=BASE_HEADERS, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"Could not reach eCourts: HTTP {resp.status_code}")
        _sessions[home_url] = s
        log.info(f"[ecourts_crawler] New session for {home_url}")
    return _sessions[home_url]


def reset_session(home_url: str):
    _sessions.pop(home_url, None)


def ajax_post(home_url: str, endpoint: str, payload: dict,
              retries: int = 3) -> dict:
    headers = {**AJAX_HEADERS, "Referer": home_url}
    for attempt in range(1, retries + 1):
        try:
            session = get_session(home_url)
            r = session.post(
                f"{BASE_URL}/?p={endpoint}",
                data=payload,
                headers=headers,
                timeout=30,
            )
            if r.status_code == 429:
                wait = 10 * attempt
                log.warning(f"[ajax] 429 rate limit — sleeping {wait}s")
                time.sleep(wait)
                reset_session(home_url)
                continue
            if r.status_code != 200:
                return {"_error": f"HTTP {r.status_code}"}
            if not r.text.strip():
                reset_session(home_url)
                return {"_raw": ""}
            try:
                return r.json()
            except Exception:
                return {"_raw": r.text}
        except Exception as e:
            log.warning(f"[ajax] Attempt {attempt} failed: {e}")
            reset_session(home_url)
            if attempt == retries:
                return {"_error": str(e)}
            time.sleep(2 * attempt)
    return {"_error": "all retries exhausted"}


# ──────────────────────────────────────────────────────────────────────────────
# PARSING HELPERS
# ──────────────────────────────────────────────────────────────────────────────
SKIP_VALUES = {"0", "-1", "", "D"}
SKIP_NAMES  = {
    "select district", "select court complex", "select establishment",
    "select court", "select court name", "select case type",
    "select police station", "",
}


def parse_options(html: str) -> list[dict]:
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for o in soup.find_all("option"):
        code = (o.get("value") or "").strip()
        name = o.get_text(strip=True)
        if (code not in SKIP_VALUES
                and name.lower() not in SKIP_NAMES
                and len(code) > 0):
            results.append({"code": code, "name": name})
    return results


def bare_complex(code: str) -> str:
    """Strip @est@flag suffix from court_complex_code."""
    return (code or "").split("@")[0]


def extract_html(resp: dict, *keys: str) -> str:
    for k in keys:
        v = resp.get(k)
        if v and isinstance(v, str) and len(v) > 10:
            return v
    return resp.get("_raw", "")


# ──────────────────────────────────────────────────────────────────────────────
# INDIVIDUAL SCRAPE FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────

def scrape_districts(state_code: str) -> list[dict]:
    resp = ajax_post(
        CL_HOME_URL,
        "casestatus/fillDistrict",
        {"state_code": state_code, "ajax_req": "true", "app_token": ""},
    )
    html = extract_html(resp, "dist_list")
    items = parse_options(html)
    log.info(f"  [districts] state={state_code} → {len(items)} districts")
    return items


def scrape_complexes(state_code: str, dist_code: str) -> list[dict]:
    resp = ajax_post(
        CL_HOME_URL,
        "casestatus/fillcomplex",
        {"state_code": state_code, "dist_code": dist_code,
         "ajax_req": "true", "app_token": ""},
    )
    html = extract_html(resp, "complex_list")
    items = parse_options(html)
    log.info(f"    [complexes] dist={dist_code} → {len(items)} complexes")
    return items


def scrape_establishments(state_code: str, dist_code: str,
                          complex_code_bare: str) -> list[dict]:
    resp = ajax_post(
        CL_HOME_URL,
        "casestatus/fillCourtEstablishment",
        {"state_code": state_code, "dist_code": dist_code,
         "court_complex_code": complex_code_bare,
         "ajax_req": "true", "app_token": ""},
    )
    html = extract_html(resp, "establishment_list")
    items = parse_options(html)
    log.info(f"      [establishments] complex={complex_code_bare} → {len(items)}")
    return items


def scrape_courts(state_code: str, dist_code: str,
                  complex_code_bare: str, est_code: str) -> list[dict]:
    resp = ajax_post(
        CL_HOME_URL,
        "cause_list/fillCauseList",
        {"state_code": state_code, "dist_code": dist_code,
         "court_complex_code": complex_code_bare, "est_code": est_code,
         "ajax_req": "true", "app_token": ""},
    )
    html = extract_html(resp, "courtnumber_list", "cause_list")
    items = parse_options(html)
    log.info(f"        [courts] est={est_code} → {len(items)} courts")
    return items


def scrape_police_stations(state_code: str, dist_code: str,
                           complex_code_bare: str, est_code: str) -> list[dict]:
    resp = ajax_post(
        CS_HOME_URL,
        "casestatus/fillPoliceStation",
        {"state_code": state_code, "dist_code": dist_code,
         "court_complex_code": complex_code_bare, "est_code": est_code,
         "ajax_req": "true", "app_token": ""},
    )
    html = extract_html(resp, "police_data", "police_station_list",
                        "policestation_list", "police_list")
    raw_items = parse_options(html)

    enriched = []
    for item in raw_items:
        parts = item["code"].split("-", 1)
        enriched.append({
            "code":            item["code"],
            "name":            item["name"],
            "ps_state_code":   parts[0] if len(parts) >= 2 else item["code"],
            "ps_uniform_code": parts[1] if len(parts) >= 2 else "",
        })
    log.info(f"        [police_stations] complex={complex_code_bare} "
             f"est={est_code} → {len(enriched)}")
    return enriched


def scrape_case_types(state_code: str, dist_code: str,
                      complex_code_bare: str, est_code: str) -> list[dict]:
    resp = ajax_post(
        CO_HOME_URL,
        "casestatus/fillCaseType",
        {"state_code": state_code, "dist_code": dist_code,
         "court_complex_code": complex_code_bare, "est_code": est_code,
         "search_type": "c_no",
         "ajax_req": "true", "app_token": ""},
    )
    html = extract_html(resp, "casetype_list", "case_type_list")
    items = parse_options(html)
    log.info(f"        [case_types] complex={complex_code_bare} "
             f"est={est_code} → {len(items)}")
    return items


# ──────────────────────────────────────────────────────────────────────────────
# MONGODB HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _db():
    from core.init_clients import get_mongo_client, get_mongo_db
    return get_mongo_db()


def ensure_indexes():
    db = _db()
    db.ecourts_states.create_index([("code", 1)], unique=True)
    db.ecourts_districts.create_index(
        [("state_code", 1), ("code", 1)], unique=True)
    db.ecourts_complexes.create_index(
        [("state_code", 1), ("dist_code", 1), ("code", 1)], unique=True)
    db.ecourts_establishments.create_index(
        [("state_code", 1), ("dist_code", 1),
         ("complex_code", 1), ("code", 1)], unique=True)
    db.ecourts_courts.create_index(
        [("state_code", 1), ("dist_code", 1),
         ("complex_code", 1), ("est_code", 1), ("code", 1)], unique=True)
    db.ecourts_police_stations.create_index(
        [("state_code", 1), ("dist_code", 1),
         ("complex_code", 1), ("est_code", 1), ("code", 1)], unique=True)
    db.ecourts_case_types.create_index(
        [("state_code", 1), ("dist_code", 1),
         ("complex_code", 1), ("est_code", 1), ("code", 1)], unique=True)
    log.info("[ecourts_crawler] MongoDB indexes ensured")


# ── Upsert functions ─────────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc)


def upsert_state(doc: dict):
    _db().ecourts_states.update_one(
        {"code": doc["code"]},
        {"$set": {**doc, "updated_at": _now()}},
        upsert=True,
    )


def upsert_district(state_code: str, item: dict):
    _db().ecourts_districts.update_one(
        {"state_code": state_code, "code": item["code"]},
        {"$set": {
            "state_code": state_code,
            "code": item["code"], "name": item["name"],
            "updated_at": _now(),
        }},
        upsert=True,
    )


def upsert_complex(state_code: str, dist_code: str, item: dict):
    full_code = item["code"]
    _db().ecourts_complexes.update_one(
        {"state_code": state_code, "dist_code": dist_code, "code": full_code},
        {"$set": {
            "state_code": state_code, "dist_code": dist_code,
            "code": full_code, "bare_code": bare_complex(full_code),
            "name": item["name"], "updated_at": _now(),
        }},
        upsert=True,
    )


def upsert_establishment(state_code: str, dist_code: str,
                         complex_code_full: str, item: dict):
    _db().ecourts_establishments.update_one(
        {"state_code": state_code, "dist_code": dist_code,
         "complex_code": complex_code_full, "code": item["code"]},
        {"$set": {
            "state_code": state_code, "dist_code": dist_code,
            "complex_code": complex_code_full,
            "bare_complex": bare_complex(complex_code_full),
            "code": item["code"], "name": item["name"],
            "updated_at": _now(),
        }},
        upsert=True,
    )


def upsert_court(state_code: str, dist_code: str,
                 complex_code_full: str, est_code: str, item: dict):
    _db().ecourts_courts.update_one(
        {"state_code": state_code, "dist_code": dist_code,
         "complex_code": complex_code_full,
         "est_code": est_code, "code": item["code"]},
        {"$set": {
            "state_code": state_code, "dist_code": dist_code,
            "complex_code": complex_code_full,
            "bare_complex": bare_complex(complex_code_full),
            "est_code": est_code,
            "code": item["code"], "name": item["name"],
            "updated_at": _now(),
        }},
        upsert=True,
    )


def upsert_police_station(state_code: str, dist_code: str,
                          complex_code_full: str, est_code: str, item: dict):
    _db().ecourts_police_stations.update_one(
        {"state_code": state_code, "dist_code": dist_code,
         "complex_code": complex_code_full,
         "est_code": est_code, "code": item["code"]},
        {"$set": {
            "state_code": state_code, "dist_code": dist_code,
            "complex_code": complex_code_full,
            "bare_complex": bare_complex(complex_code_full),
            "est_code": est_code,
            "code": item["code"], "name": item["name"],
            "ps_state_code": item.get("ps_state_code", ""),
            "ps_uniform_code": item.get("ps_uniform_code", ""),
            "updated_at": _now(),
        }},
        upsert=True,
    )


def upsert_case_type(state_code: str, dist_code: str,
                     complex_code_full: str, est_code: str, item: dict):
    _db().ecourts_case_types.update_one(
        {"state_code": state_code, "dist_code": dist_code,
         "complex_code": complex_code_full,
         "est_code": est_code, "code": item["code"]},
        {"$set": {
            "state_code": state_code, "dist_code": dist_code,
            "complex_code": complex_code_full,
            "bare_complex": bare_complex(complex_code_full),
            "est_code": est_code,
            "code": item["code"], "name": item["name"],
            "updated_at": _now(),
        }},
        upsert=True,
    )


# ── Crawl log ────────────────────────────────────────────────────────────────

def log_crawl_start(run_id: str, scope: str, params: dict):
    _db().ecourts_crawl_log.insert_one({
        "_id": run_id,
        "scope": scope,
        "params": params,
        "status": "running",
        "started_at": _now(),
        "counts": {},
        "errors": [],
    })


def log_crawl_update(run_id: str, counts: dict, errors: list):
    _db().ecourts_crawl_log.update_one(
        {"_id": run_id},
        {"$set": {"counts": counts, "errors": errors[-50:], "updated_at": _now()}},
    )


def log_crawl_finish(run_id: str, counts: dict, errors: list,
                     status: str = "complete"):
    _db().ecourts_crawl_log.update_one(
        {"_id": run_id},
        {"$set": {
            "status": status, "counts": counts,
            "errors": errors[-50:], "finished_at": _now(),
        }},
    )
    log.info(f"[crawl:{run_id}] Finished — status={status} counts={counts} "
             f"errors={len(errors)}")


# ──────────────────────────────────────────────────────────────────────────────
# CRAWL ORCHESTRATION
# ──────────────────────────────────────────────────────────────────────────────

class CrawlState:
    def __init__(self):
        self.run_id = str(uuid.uuid4())[:8]
        self.counts = {
            "states": 0, "districts": 0, "complexes": 0,
            "establishments": 0, "courts": 0,
            "police_stations": 0, "case_types": 0,
        }
        self.errors: list[dict] = []
        self.running = False

    def inc(self, key: str, n: int = 1):
        self.counts[key] = self.counts.get(key, 0) + n

    def error(self, msg: str, **ctx):
        entry = {"msg": msg, "ts": _now().isoformat(), **ctx}
        self.errors.append(entry)
        log.warning(f"[crawl error] {msg} | {ctx}")


_current_crawl: Optional[CrawlState] = None


def crawl_establishment_leaf(cs: CrawlState, state_code: str, dist_code: str,
                             complex_full: str, est: dict):
    est_code = est["code"]
    bare = bare_complex(complex_full)

    # Courts
    try:
        courts = scrape_courts(state_code, dist_code, bare, est_code)
        for c in courts:
            upsert_court(state_code, dist_code, complex_full, est_code, c)
        cs.inc("courts", len(courts))
        time.sleep(REQUEST_DELAY_SEC)
    except Exception as e:
        cs.error("courts", state=state_code, dist=dist_code,
                 complex=complex_full, est=est_code, err=str(e))

    # Police Stations
    try:
        pss = scrape_police_stations(state_code, dist_code, bare, est_code)
        for ps in pss:
            upsert_police_station(state_code, dist_code, complex_full, est_code, ps)
        cs.inc("police_stations", len(pss))
        time.sleep(REQUEST_DELAY_SEC)
    except Exception as e:
        cs.error("police_stations", state=state_code, dist=dist_code,
                 complex=complex_full, est=est_code, err=str(e))

    # Case Types
    try:
        cts = scrape_case_types(state_code, dist_code, bare, est_code)
        for ct in cts:
            upsert_case_type(state_code, dist_code, complex_full, est_code, ct)
        cs.inc("case_types", len(cts))
        time.sleep(REQUEST_DELAY_SEC)
    except Exception as e:
        cs.error("case_types", state=state_code, dist=dist_code,
                 complex=complex_full, est=est_code, err=str(e))


def crawl_complex(cs: CrawlState, state_code: str, dist_code: str,
                  complex_item: dict):
    complex_full = complex_item["code"]
    bare = bare_complex(complex_full)

    try:
        ests = scrape_establishments(state_code, dist_code, bare)
        for est in ests:
            upsert_establishment(state_code, dist_code, complex_full, est)
        cs.inc("establishments", len(ests))
        time.sleep(REQUEST_DELAY_SEC)
    except Exception as e:
        cs.error("establishments", state=state_code, dist=dist_code,
                 complex=complex_full, err=str(e))
        return

    if not ests:
        log.warning(f"      [!] No establishments for complex={complex_full}")
        return

    for est in ests:
        crawl_establishment_leaf(cs, state_code, dist_code, complex_full, est)

    time.sleep(COMPLEX_BATCH_DELAY_SEC)


def crawl_district(cs: CrawlState, state_code: str, dist_item: dict):
    dist_code = dist_item["code"]

    try:
        complexes = scrape_complexes(state_code, dist_code)
        for cx in complexes:
            upsert_complex(state_code, dist_code, cx)
        cs.inc("complexes", len(complexes))
        time.sleep(REQUEST_DELAY_SEC)
    except Exception as e:
        cs.error("complexes", state=state_code, dist=dist_code, err=str(e))
        return

    if not complexes:
        log.warning(f"    [!] No complexes for dist={dist_code}")
        return

    for cx in complexes:
        crawl_complex(cs, state_code, dist_code, cx)

    time.sleep(DISTRICT_BATCH_DELAY)


def crawl_state(cs: CrawlState, state_item: dict):
    state_code = state_item["code"]
    log.info(f"[crawl] STATE {state_item['name']} ({state_code})")

    upsert_state(state_item)
    cs.inc("states")

    try:
        districts = scrape_districts(state_code)
        for d in districts:
            upsert_district(state_code, d)
        cs.inc("districts", len(districts))
        time.sleep(REQUEST_DELAY_SEC)
    except Exception as e:
        cs.error("districts", state=state_code, err=str(e))
        return

    if not districts:
        log.warning(f"  [!] No districts for state={state_code}")
        return

    for dist in districts:
        crawl_district(cs, state_code, dist)


def run_full_crawl(state_codes: list[str] | None = None,
                   dist_codes: list[str] | None = None) -> CrawlState:
    global _current_crawl
    if _current_crawl and _current_crawl.running:
        raise RuntimeError("A crawl is already running")

    cs = CrawlState()
    _current_crawl = cs
    cs.running = True

    targets = [s for s in STATES
               if (not state_codes or s["code"] in state_codes)]

    ensure_indexes()
    log_crawl_start(
        cs.run_id,
        "full" if not state_codes else "partial",
        {"state_codes": state_codes, "dist_codes": dist_codes},
    )

    try:
        for state_item in targets:
            if dist_codes:
                state_code = state_item["code"]
                upsert_state(state_item)
                cs.inc("states")
                all_dists = scrape_districts(state_code)
                target_dists = [d for d in all_dists if d["code"] in dist_codes]
                for d in target_dists:
                    upsert_district(state_code, d)
                    crawl_district(cs, state_code, d)
            else:
                crawl_state(cs, state_item)

            log_crawl_update(cs.run_id, cs.counts, cs.errors)

        log_crawl_finish(cs.run_id, cs.counts, cs.errors, "complete")
    except Exception as e:
        cs.error("fatal", err=str(e))
        log_crawl_finish(cs.run_id, cs.counts, cs.errors, "failed")
        log.exception(f"[crawl] Fatal error: {e}")
    finally:
        cs.running = False

    return cs


def get_current_crawl() -> Optional[CrawlState]:
    return _current_crawl


# ──────────────────────────────────────────────────────────────────────────────
# DATA READ HELPERS — serve from MongoDB
# ──────────────────────────────────────────────────────────────────────────────

def read_states() -> list[dict]:
    return list(_db().ecourts_states.find(
        {}, {"_id": 0, "updated_at": 0}
    ).sort("name", 1))


def read_districts(state_code: str) -> list[dict]:
    return list(_db().ecourts_districts.find(
        {"state_code": state_code}, {"_id": 0, "updated_at": 0}
    ).sort("name", 1))


def read_complexes(state_code: str, dist_code: str) -> list[dict]:
    return list(_db().ecourts_complexes.find(
        {"state_code": state_code, "dist_code": dist_code},
        {"_id": 0, "updated_at": 0}
    ).sort("name", 1))


def read_establishments(state_code: str, dist_code: str,
                        complex_code: str) -> list[dict]:
    return list(_db().ecourts_establishments.find(
        {"state_code": state_code, "dist_code": dist_code,
         "$or": [{"complex_code": complex_code},
                 {"bare_complex": complex_code}]},
        {"_id": 0, "updated_at": 0}
    ).sort("name", 1))


def read_courts(state_code: str, dist_code: str,
                complex_code: str, est_code: str) -> list[dict]:
    return list(_db().ecourts_courts.find(
        {"state_code": state_code, "dist_code": dist_code,
         "$or": [{"complex_code": complex_code},
                 {"bare_complex": complex_code}],
         "est_code": est_code},
        {"_id": 0, "updated_at": 0}
    ).sort("name", 1))


def read_police_stations(state_code: str, dist_code: str,
                         complex_code: str, est_code: str) -> list[dict]:
    return list(_db().ecourts_police_stations.find(
        {"state_code": state_code, "dist_code": dist_code,
         "$or": [{"complex_code": complex_code},
                 {"bare_complex": complex_code}],
         "est_code": est_code},
        {"_id": 0, "updated_at": 0}
    ).sort("name", 1))


def read_case_types(state_code: str, dist_code: str,
                    complex_code: str, est_code: str) -> list[dict]:
    return list(_db().ecourts_case_types.find(
        {"state_code": state_code, "dist_code": dist_code,
         "$or": [{"complex_code": complex_code},
                 {"bare_complex": complex_code}],
         "est_code": est_code},
        {"_id": 0, "updated_at": 0}
    ).sort("name", 1))


def read_stats() -> dict:
    db = _db()
    last = db.ecourts_crawl_log.find_one(sort=[("started_at", -1)])
    if last:
        for k in ("started_at", "finished_at", "updated_at"):
            if last.get(k):
                last[k] = last[k].isoformat()
        last.pop("_id", None)
    return {
        "collections": {
            "states":          db.ecourts_states.count_documents({}),
            "districts":       db.ecourts_districts.count_documents({}),
            "complexes":       db.ecourts_complexes.count_documents({}),
            "establishments":  db.ecourts_establishments.count_documents({}),
            "courts":          db.ecourts_courts.count_documents({}),
            "police_stations": db.ecourts_police_stations.count_documents({}),
            "case_types":      db.ecourts_case_types.count_documents({}),
        },
        "last_crawl": last or {},
    }
