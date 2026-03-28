"""
eCourts India - CNR Number Scraper
curl_cffi (Chrome TLS) + CapSolver ImageToTextTask

Response rejection pattern (from live traffic):
  {"errormsg":"Invalid Captcha... ","div_captcha":"<img id='captcha_image' src='...'>"}
  → no 'status' field on rejection, use 'errormsg' check instead
  → new captcha src is embedded in div_captcha HTML

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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
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
    "Connection": "keep-alive",
}


# ──────────────────────────────────────────────────────────────────────────────
# STEP 1 — Session
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
# STEP 2 — Fetch CAPTCHA image → base64
# Can take either a direct URL or extract src from div_captcha HTML
# ──────────────────────────────────────────────────────────────────────────────
def fetch_captcha_b64(session: requests.Session, captcha_src: str = "") -> str:
    if not captcha_src:
        captcha_src = f"{CAPTCHA_URL}?{int(time.time())}"

    # Make absolute if relative
    if captcha_src.startswith("/"):
        captcha_src = f"https://services.ecourts.gov.in{captcha_src}"
    elif not captcha_src.startswith("http"):
        captcha_src = f"{BASE_URL}/{captcha_src.lstrip('/')}"

    # Always add cache-buster
    sep = "&" if "?" in captcha_src else "?"
    url = f"{captcha_src}{sep}cb={int(time.time())}"

    print(f"[*] Fetching CAPTCHA: {url}")
    r = session.get(url, headers=BASE_HEADERS, timeout=20)
    print(f"    {r.status_code}  {r.headers.get('Content-Type','?')}  {len(r.content)} bytes")
    if r.status_code != 200 or len(r.content) < 100:
        raise Exception(f"CAPTCHA fetch failed: {r.status_code}")
    return base64.b64encode(r.content).decode("utf-8").replace("\n", "")


def extract_captcha_src_from_div(div_captcha_html: str) -> str:
    """Pull the captcha img src out of the div_captcha response field."""
    soup = BeautifulSoup(div_captcha_html, "html.parser")
    img = (
        soup.find("img", id="captcha_image") or
        soup.find("img", attrs={"src": re.compile(r"securimage_show", re.I)})
    )
    if img and img.get("src"):
        return img["src"]
    return ""


# ──────────────────────────────────────────────────────────────────────────────
# STEP 3 — Solve CAPTCHA via CapSolver
# ──────────────────────────────────────────────────────────────────────────────
def solve_captcha(image_b64: str) -> str:
    print("[*] Sending to CapSolver...")
    resp = std_requests.post(
        "https://api.capsolver.com/createTask",
        json={
            "clientKey": CAPSOLVER_API_KEY,
            "task": {
                "type": "ImageToTextTask",
                "websiteURL": HOME_URL,
                "module": "common",
                "body": image_b64,
            }
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise Exception(f"CapSolver HTTP {resp.status_code}: {resp.text[:300]}")
    d = resp.json()
    if d.get("errorId") != 0:
        raise Exception(f"CapSolver {d.get('errorCode')}: {d.get('errorDescription')}")
    text = d.get("solution", {}).get("text", "").strip()
    if not text:
        raise Exception(f"CapSolver empty solution: {d}")
    print(f"[CapSolver] Solved: '{text}'")
    return text


# ──────────────────────────────────────────────────────────────────────────────
# STEP 4 — POST
# ──────────────────────────────────────────────────────────────────────────────
def post_cnr(session: requests.Session, cnr: str,
             captcha_text: str, app_token: str = "") -> dict:
    payload = {
        "cino":          cnr.upper(),
        "fcaptcha_code": captcha_text,
        "ajax_req":      "true",
        "app_token":     app_token,
    }
    print(f"[*] POST → {SEARCH_URL}")
    print(f"    cino={cnr}  captcha={captcha_text}  app_token='{app_token[:20]}...' " if len(app_token) > 20 else f"    cino={cnr}  captcha={captcha_text}  app_token='{app_token}'")

    r = session.post(SEARCH_URL, data=payload, headers=AJAX_HEADERS, timeout=30)
    print(f"    Status  : {r.status_code}")
    print(f"    Preview : {r.text[:250].strip()!r}")

    if r.status_code != 200:
        return {"_error": f"HTTP {r.status_code}"}

    try:
        return r.json()
    except Exception:
        return {"_raw_html": r.text}


# ──────────────────────────────────────────────────────────────────────────────
# STEP 5 — Parse response
# ──────────────────────────────────────────────────────────────────────────────
def is_captcha_rejected(resp: dict) -> bool:
    """
    Server signals bad captcha via:
      {"errormsg": "Invalid Captcha... ", "div_captcha": "..."}
    There is NO 'status' field on rejection.
    """
    errormsg = resp.get("errormsg", "")
    if errormsg and re.search(r"captcha|invalid", errormsg, re.I):
        print(f"    [!] Captcha rejected: {errormsg.strip()}")
        return True
    # Also check status==0 as secondary signal
    if resp.get("status") == 0:
        print("    [!] Captcha rejected: status=0")
        return True
    return False


def parse_result(resp: dict, cnr: str) -> dict:
    result: dict = {"success": False, "cnr_number": cnr}

    if not resp:
        result["error"] = "No response."
        return result

    # Update app_token if present in response
    if resp.get("app_token"):
        result["_app_token"] = resp["app_token"]

    html = resp.get("casetype_list", "") or resp.get("_raw_html", "")
    if not html:
        result["error"] = "Empty casetype_list — case may not exist."
        return result

    soup = BeautifulSoup(html, "html.parser")
    body_text = soup.get_text(" ", strip=True).lower()

    if any(kw in body_text for kw in ["no record", "case not found",
                                       "does not exist", "invalid cnr",
                                       "this case code does not"]):
        result["error"] = "No case found for this CNR number."
        return result

    # ── Key-value tables ──────────────────────────────────────────────────────
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                key   = cells[0].get_text(" ", strip=True).rstrip(":").strip()
                value = cells[1].get_text(" ", strip=True)
                if key and len(key) < 80 and key not in result:
                    result[key] = value

    # ── Hearing history ───────────────────────────────────────────────────────
    htable = (
        soup.find("table", id=re.compile(r"history", re.I)) or
        soup.find("table", class_=re.compile(r"history", re.I))
    )
    if htable:
        rows = htable.find_all("tr")
        if len(rows) > 1:
            headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
            hearings = [
                dict(zip(headers, [td.get_text(strip=True) for td in row.find_all("td")]))
                for row in rows[1:] if row.find_all("td")
            ]
            if hearings:
                result["Hearing History"] = hearings

    # ── Order links ───────────────────────────────────────────────────────────
    links = list({
        a["href"] for a in soup.find_all("a", href=True)
        if re.search(r"order|judgment|pdf", a["href"], re.I)
    })
    if links:
        result["Order Links"] = links

    result["success"] = True
    result["_raw_html"] = html
    return result


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def fetch_case_status(cnr_number: str) -> dict:
    try:
        session = build_session()
    except Exception as e:
        return {"success": False, "error": str(e), "cnr_number": cnr_number}

    app_token    = ""
    captcha_src  = ""   # will update from div_captcha on each retry

    for attempt in range(1, 6):   # up to 5 captcha attempts
        print(f"\n[*] Attempt {attempt}...")
        try:
            b64          = fetch_captcha_b64(session, captcha_src)
            captcha_text = solve_captcha(b64)
        except Exception as e:
            return {"success": False, "error": str(e), "cnr_number": cnr_number}

        resp = post_cnr(session, cnr_number, captcha_text, app_token)

        if is_captcha_rejected(resp):
            # Extract fresh captcha src from server's div_captcha response
            div_html = resp.get("div_captcha", "")
            if div_html:
                new_src = extract_captcha_src_from_div(div_html)
                if new_src:
                    captcha_src = new_src
                    print(f"    [*] Got fresh captcha src from response: {captcha_src}")
            # Update token if provided
            if resp.get("app_token"):
                app_token = resp["app_token"]
            print("[!] Retrying with fresh captcha...")
            continue

        result = parse_result(resp, cnr_number)
        # Carry forward app_token for potential follow-up calls
        if result.get("_app_token"):
            app_token = result["_app_token"]
        return result

    return {"success": False,
            "error": "CAPTCHA rejected 5 times — CapSolver accuracy issue or securimage changed.",
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

    display = {k: v for k, v in result.items() if not k.startswith("_")}
    print("\n── RESULT ──────────────────────────────────────────")
    print(json.dumps(display, indent=2, ensure_ascii=False))

    if result.get("_raw_html"):
        print(f"\n[_raw_html: {len(result['_raw_html'])} chars]")
