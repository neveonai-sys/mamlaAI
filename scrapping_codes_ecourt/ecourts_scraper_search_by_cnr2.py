"""
eCourts India - CNR Number Scraper
curl_cffi (Chrome TLS) + CapSolver ImageToTextTask

Extracts all sections matching the website UI:
  - Case Details
  - Case Status
  - Petitioner & Advocate
  - Respondent & Advocate
  - Acts (Under Act / Under Section)
  - FIR Details
  - Case History (with clickable order links)
  - Case Transfer Details
  - QR / Cause Title link

Install:
    pip install curl_cffi beautifulsoup4 requests

Usage:
    export CAPSOLVER_API_KEY=CAP-xxx
    python ecourts_scraper.py BRAU010000972020
"""

import os, sys, json, time, re, base64
import requests as std_requests
from curl_cffi import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
CAPSOLVER_API_KEY = os.environ.get("CAPSOLVER_API_KEY", "")
if not CAPSOLVER_API_KEY:
    raise ValueError("Set env var: export CAPSOLVER_API_KEY=CAP-xxx")

BASE_URL    = "https://services.ecourts.gov.in/ecourtindia_v6"
HOME_URL    = f"{BASE_URL}/?p=home/index"
SEARCH_URL  = f"{BASE_URL}/?p=cnr_status/searchByCNR/"
CAPTCHA_URL = f"{BASE_URL}/vendor/securimage/securimage_show.php"
IMPERSONATE = "chrome110"

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
    "Referer": HOME_URL,
    "Origin": "https://services.ecourts.gov.in",
}


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def abs_url(href: str) -> str:
    """Make relative hrefs absolute."""
    if not href:
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return f"https://services.ecourts.gov.in{href}"
    return f"{BASE_URL}/{href.lstrip('/')}"


def clean(el) -> str:
    return el.get_text(" ", strip=True) if el else ""


# ──────────────────────────────────────────────────────────────────────────────
# SESSION
# ──────────────────────────────────────────────────────────────────────────────
def build_session() -> requests.Session:
    session = requests.Session(impersonate=IMPERSONATE)
    print("[*] Loading home page...")
    resp = session.get(HOME_URL, headers=BASE_HEADERS, timeout=20)
    print(f"    Status  : {resp.status_code}")
    print(f"    Cookies : {dict(session.cookies)}")
    if resp.status_code != 200:
        raise Exception(f"Home page returned HTTP {resp.status_code}")
    print("[✓] Session ready.")
    return session


# ──────────────────────────────────────────────────────────────────────────────
# CAPTCHA
# ──────────────────────────────────────────────────────────────────────────────
def fetch_captcha_b64(session: requests.Session, src: str = "") -> str:
    if not src:
        src = CAPTCHA_URL
    if src.startswith("/"):
        src = f"https://services.ecourts.gov.in{src}"
    sep = "&" if "?" in src else "?"
    url = f"{src}{sep}cb={int(time.time())}"
    print(f"[*] Fetching CAPTCHA: {url}")
    r = session.get(url, headers=BASE_HEADERS, timeout=20)
    print(f"    {r.status_code}  {r.headers.get('Content-Type','?')}  {len(r.content)} bytes")
    if r.status_code != 200 or len(r.content) < 100:
        raise Exception(f"CAPTCHA fetch failed: {r.status_code}")
    return base64.b64encode(r.content).decode().replace("\n", "")


def extract_captcha_src(div_html: str) -> str:
    soup = BeautifulSoup(div_html, "html.parser")
    img = soup.find("img", id="captcha_image") or \
          soup.find("img", attrs={"src": re.compile(r"securimage_show", re.I)})
    return img["src"] if img and img.get("src") else ""


def solve_captcha(b64: str) -> str:
    print("[*] Sending to CapSolver...")
    r = std_requests.post(
        "https://api.capsolver.com/createTask",
        json={"clientKey": CAPSOLVER_API_KEY,
              "task": {"type": "ImageToTextTask", "websiteURL": HOME_URL,
                       "module": "common", "body": b64}},
        timeout=30,
    )
    if r.status_code != 200:
        raise Exception(f"CapSolver HTTP {r.status_code}: {r.text[:200]}")
    d = r.json()
    if d.get("errorId") != 0:
        raise Exception(f"CapSolver {d.get('errorCode')}: {d.get('errorDescription')}")
    text = d.get("solution", {}).get("text", "").strip()
    if not text:
        raise Exception("CapSolver empty solution")
    print(f"[CapSolver] Solved: '{text}'")
    return text


# ──────────────────────────────────────────────────────────────────────────────
# POST
# ──────────────────────────────────────────────────────────────────────────────
def post_cnr(session: requests.Session, cnr: str, captcha: str, token: str = "") -> dict:
    payload = {"cino": cnr.upper(), "fcaptcha_code": captcha,
               "ajax_req": "true", "app_token": token}
    print(f"[*] POST → {SEARCH_URL}")
    r = session.post(SEARCH_URL, data=payload, headers=AJAX_HEADERS, timeout=30)
    print(f"    Status : {r.status_code}  |  preview: {r.text[:120].strip()!r}")
    if r.status_code != 200:
        return {}
    try:
        return r.json()
    except Exception:
        return {"_raw": r.text}


def is_captcha_bad(resp: dict) -> bool:
    msg = resp.get("errormsg", "")
    return bool(msg and re.search(r"captcha|invalid", msg, re.I)) or resp.get("status") == 0


# ──────────────────────────────────────────────────────────────────────────────
# PARSER  — mirrors the website's section layout exactly
# ──────────────────────────────────────────────────────────────────────────────
def parse_case_html(html: str, cnr: str) -> dict:
    """
    Parse every section of the case detail page into a structured dict.
    Matches the visual layout:
      Court Name / Case Details / Case Status /
      Petitioner & Advocate / Respondent & Advocate /
      Acts / FIR Details / Case History / Case Transfer Details
    """
    soup = BeautifulSoup(html, "html.parser")
    out: dict = {"cnr_number": cnr}

    body_text = soup.get_text(" ", strip=True).lower()
    if any(k in body_text for k in ["no record", "does not exist", "case not found"]):
        out["error"] = "No case found for this CNR number."
        return out

    # ── Court heading ─────────────────────────────────────────────────────────
    h2 = soup.find("h2")
    if h2:
        out["court_name"] = clean(h2)

    # ── Case Details table (blue rows) ────────────────────────────────────────
    details_table = soup.find("table", class_=re.compile(r"case_details_table", re.I))
    if details_table:
        case_details: dict = {}
        for row in details_table.find_all("tr"):
            cells = row.find_all("td")
            # Standard 2-column row
            if len(cells) == 2:
                k = clean(cells[0]).rstrip(":")
                v = clean(cells[1])
                if k:
                    case_details[k] = v
            # 4-column row (Filing Number | value | Filing Date | value)
            elif len(cells) == 4:
                k1 = clean(cells[0]).rstrip(":")
                v1 = clean(cells[1])
                k2 = clean(cells[2]).rstrip(":")
                v2 = clean(cells[3])
                if k1: case_details[k1] = v1
                if k2: case_details[k2] = v2

        # QR / Cause Title link
        qr_link = details_table.find("a", string=re.compile(r"QR|Cause Title", re.I))
        if qr_link:
            case_details["qr_cause_title_url"] = abs_url(qr_link.get("href", ""))

        # CNR number clean (strip the annotation text)
        cnr_td = details_table.find("td", string=re.compile(r"CNR Number", re.I))
        if cnr_td:
            next_td = cnr_td.find_next_sibling("td")
            if next_td:
                # grab just the bold/strong text (the actual CNR)
                strong = next_td.find(["strong", "b", "span"])
                case_details["CNR Number"] = (clean(strong) if strong
                                              else clean(next_td).split("(")[0].strip())

        out["case_details"] = case_details

    # ── Case Status table (yellow rows) ──────────────────────────────────────
    status_heading = soup.find(string=re.compile(r"^Case Status$", re.I))
    if status_heading:
        status_table = status_heading.find_parent().find_next("table")
        if status_table:
            case_status: dict = {}
            for row in status_table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    k = clean(cells[0]).rstrip(":")
                    v = clean(cells[1])
                    if k:
                        case_status[k] = v
            out["case_status"] = case_status

    # ── Petitioner & Advocate ─────────────────────────────────────────────────
    for section_name, pattern in [
        ("petitioner_and_advocate", r"Petitioner.*Advocate"),
        ("respondent_and_advocate", r"Respondent.*Advocate"),
    ]:
        heading = soup.find(string=re.compile(pattern, re.I))
        if heading:
            parent = heading.find_parent()
            # Collect all text items from the next sibling table or div
            container = parent.find_next_sibling() or parent.find_next("table")
            if container:
                items = [li.get_text(" ", strip=True)
                         for li in container.find_all(["li", "p", "div", "td"])
                         if li.get_text(strip=True)]
                if items:
                    out[section_name] = items

    # ── Acts ─────────────────────────────────────────────────────────────────
    acts_heading = soup.find(string=re.compile(r"^Acts$", re.I))
    if acts_heading:
        acts_table = acts_heading.find_parent().find_next("table")
        if acts_table:
            acts = []
            rows = acts_table.find_all("tr")
            if rows:
                headers = [clean(th) for th in rows[0].find_all(["th", "td"])]
                for row in rows[1:]:
                    cells = row.find_all("td")
                    if cells:
                        entry = dict(zip(headers,
                                        [clean(c) for c in cells]))
                        acts.append(entry)
            out["acts"] = acts

    # ── FIR Details ───────────────────────────────────────────────────────────
    fir_heading = soup.find(string=re.compile(r"FIR Details", re.I))
    if fir_heading:
        fir_table = fir_heading.find_parent().find_next("table")
        if fir_table:
            fir: dict = {}
            for row in fir_table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    k = clean(cells[0]).rstrip(":")
                    v = clean(cells[1])
                    if k and k.lower() not in ("field", "details"):
                        fir[k] = v
            out["fir_details"] = fir

    # ── Case History (hearing history with order links) ───────────────────────
    history_heading = soup.find(string=re.compile(r"^Case History$", re.I))
    if history_heading:
        history_table = history_heading.find_parent().find_next("table")
        if history_table:
            rows = history_table.find_all("tr")
            if rows:
                # Header row
                headers = [clean(th) for th in rows[0].find_all(["th", "td"])]
                hearings = []
                for row in rows[1:]:
                    cells = row.find_all("td")
                    if not cells:
                        continue
                    entry: dict = {}
                    for i, cell in enumerate(cells):
                        col = headers[i] if i < len(headers) else f"col_{i}"
                        entry[col] = clean(cell)
                        # Capture order link (clickable dates → order PDFs)
                        link = cell.find("a", href=True)
                        if link:
                            entry[f"{col}_url"] = abs_url(link["href"])
                    hearings.append(entry)
                out["case_history"] = hearings

    # ── Case Transfer Details ─────────────────────────────────────────────────
    transfer_heading = soup.find(string=re.compile(r"Case Transfer Details", re.I))
    if transfer_heading:
        transfer_table = transfer_heading.find_parent().find_next("table")
        if transfer_table:
            rows = transfer_table.find_all("tr")
            if rows:
                headers = [clean(th) for th in rows[0].find_all(["th", "td"])]
                transfers = []
                for row in rows[1:]:
                    cells = row.find_all("td")
                    if cells:
                        transfers.append(dict(zip(headers,
                                                   [clean(c) for c in cells])))
                out["case_transfer_details"] = transfers

    # ── Order / Judgment links (standalone) ───────────────────────────────────
    order_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"order|judgment|pdf|cino_order", href, re.I):
            order_links.append({
                "text": clean(a),
                "url":  abs_url(href)
            })
    if order_links:
        out["order_links"] = order_links

    out["success"] = True
    return out


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def fetch_case_status(cnr_number: str) -> dict:
    try:
        session = build_session()
    except Exception as e:
        return {"success": False, "error": str(e), "cnr_number": cnr_number}

    token       = ""
    captcha_src = ""

    for attempt in range(1, 6):
        print(f"\n[*] Attempt {attempt}...")
        try:
            b64     = fetch_captcha_b64(session, captcha_src)
            captcha = solve_captcha(b64)
        except Exception as e:
            return {"success": False, "error": str(e), "cnr_number": cnr_number}

        resp = post_cnr(session, cnr_number, captcha, token)

        if is_captcha_bad(resp):
            print("[!] Wrong captcha — fetching fresh one from response...")
            new_src = extract_captcha_src(resp.get("div_captcha", ""))
            if new_src:
                captcha_src = new_src
            if resp.get("app_token"):
                token = resp["app_token"]
            continue

        html = resp.get("casetype_list", "") or resp.get("_raw", "")
        if not html:
            return {"success": False, "error": "Empty response from server.",
                    "cnr_number": cnr_number}

        result = parse_case_html(html, cnr_number)
        if resp.get("app_token"):
            token = resp["app_token"]
        return result

    return {"success": False,
            "error": "CAPTCHA rejected 5 times — check CapSolver balance.",
            "cnr_number": cnr_number}


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:   python ecourts_scraper.py <CNR_NUMBER>")
        print("Example: python ecourts_scraper.py BRAU010000972020")
        sys.exit(1)

    cnr = sys.argv[1].strip().upper()
    print(f"\n{'='*52}\n  eCourts CNR Lookup: {cnr}\n{'='*52}\n")

    result = fetch_case_status(cnr)
    print("\n── RESULT ──────────────────────────────────────────")
    print(json.dumps(result, indent=2, ensure_ascii=False))
