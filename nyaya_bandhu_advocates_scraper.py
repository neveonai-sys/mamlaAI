#!/usr/bin/env python3
"""
nyaya_bandhu_full_scraper.py
============================

Scrape **all advocates listed on Nyaya Bandhu (Pro‑Bono Services)** across every
State/UT Bar Council and produce a single CSV.

Key features
------------
✔ Auto‑discovers every Bar Council ID from the dropdown  
✔ Uses a *single* persistent HTTP session for speed (keep‑alive)  
✔ Fetches 500 rows/page (server supports it) → ~80% fewer requests  
✔ Optional per‑state CSVs via `--split`  
✔ Graceful resume – skips states already scraped (file exists)  
✔ KeyboardInterrupt handling – always writes master CSV before exit  

Output
------
* `advocates_all_states.csv` (master)  
* `advocates_<State_Name>.csv` (if `--split` given)

Dependencies
------------
    pip install requests beautifulsoup4 tqdm

Usage
-----
    python nyaya_bandhu_full_scraper.py
    python nyaya_bandhu_full_scraper.py --split
"""

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ---------- Config ----------
BASE_URL = "https://probono-doj.in/list-of-advocates.html"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Encoding": "gzip, deflate, br",
}
ROWS_PER_PAGE = 500         # Server happily serves 500-row pages
DELAY_BETWEEN_PAGES = 0.1   # Seconds; keep load civil
RETRY_LIMIT = 2             # Retry fetches twice on error
TIMEOUT = (3.05, 30)        # (connect, read) seconds
OUTPUT_MASTER = Path("advocates_all_states.csv")
# -----------------------------


def discover_bar_councils(sess: requests.Session) -> Dict[str, str]:
    """Parse the dropdown to get {id: 'State Name'} mapping."""
    r = sess.get(BASE_URL, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    select = soup.find("select", attrs={"name": "AdvocateSearch[bar_council]"})
    if not select:
        raise RuntimeError("Bar council dropdown not found; site markup changed.")
    mapping = {}
    for opt in select.find_all("option"):
        val, label = opt.get("value", "").strip(), opt.text.strip()
        if val.isdigit() and label:
            mapping[val] = label
    return mapping


def fetch_page(sess: requests.Session, council_id: str, page: int) -> str:
    """Fetch HTML for a single page, with retries."""
    params = {
        "AdvocateSearch[bar_council]": council_id,
        "per-page": ROWS_PER_PAGE,
        "page": page,
    }
    for attempt in range(RETRY_LIMIT + 1):
        try:
            resp = sess.get(BASE_URL, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            if attempt == RETRY_LIMIT:
                raise
            time.sleep(1.5 * (attempt + 1))


def parse_rows(html: str) -> List[dict]:
    """Return list of advocate dicts from HTML table."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="table")
    if not table:
        return []
    records = []
    for tr in table.select("tr")[1:]:  # skip header
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(tds) >= 3:
            records.append(
                {
                    "Registration Number": tds[2],
                    "Name": tds[1],
                }
            )
    return records


def scrape_state(sess: requests.Session, council_id: str, state: str) -> List[dict]:
    """Scrape *all* pages for one state."""
    records, page = [], 1
    while True:
        html = fetch_page(sess, council_id, page)
        rows = parse_rows(html)
        if not rows:
            break
        for rec in rows:
            rec["Practicing Court"] = f"{state} Courts"
            rec["State"] = state
        records.extend(rows)
        page += 1
        if DELAY_BETWEEN_PAGES:
            time.sleep(DELAY_BETWEEN_PAGES)
    return records


def write_csv(path: Path, rows: List[dict]):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description="Scrape Nyaya Bandhu advocate directory")
    ap.add_argument("--split", action="store_true", help="write separate CSV per state")
    args = ap.parse_args()

    master_rows = []
    try:
        with requests.Session() as sess:
            sess.headers.update(HEADERS)
            state_map = discover_bar_councils(sess)
            print(f"Discovered {len(state_map)} State/UT Bar Councils.")

            for cid, state in tqdm(state_map.items(), desc="States"):
                state_file = Path(f"advocates_{state.replace(' ', '_')}.csv")
                # Resume: skip if file already exists & non‑empty
                if args.split and state_file.exists() and state_file.stat().st_size > 100:
                    print(f"  {state}: already scraped, skipping.")
                    continue
                rows = scrape_state(sess, cid, state)
                print(f"  {state}: {len(rows)} advocates")
                master_rows.extend(rows)
                if args.split:
                    write_csv(state_file, rows)

    except KeyboardInterrupt:
        print("\nInterrupted by user – writing partial CSV…", file=sys.stderr)
    finally:
        if master_rows:
            write_csv(OUTPUT_MASTER, master_rows)
            print(f"Saved {len(master_rows)} total advocates → {OUTPUT_MASTER}")
        else:
            print("No data scraped – nothing to write.", file=sys.stderr)


if __name__ == "__main__":
    main()

