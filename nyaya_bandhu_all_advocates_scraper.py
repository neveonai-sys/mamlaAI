#!/usr/bin/env python3
"""
nyaya_bandhu_full_scraper.py  (pagination-aware)

Scrapes every State/UT Bar Council from Nyaya Bandhu into
advocates_all_states.csv.  Add --split for per-state files and
--verbose for page-level prints.

pip install requests beautifulsoup4 tqdm
"""

import argparse, csv, sys, time
from pathlib import Path
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_URL = "https://probono-doj.in/list-of-advocates.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br",
}
ROWS_PER_PAGE = 50            # 50 is the largest value consistently honoured by server :contentReference[oaicite:2]{index=2}
SLEEP = 0.1
TIMEOUT = (3.05, 30)
RETRY = 2
MASTER_CSV = Path("advocates_all_states.csv")


# ───────────────────────────────────────── helpers ──────────────────────────────────────────

def discover_councils(sess) -> Dict[str, str]:
    """Return {council_id: 'State Name'} parsed from the dropdown."""
    soup = BeautifulSoup(sess.get(BASE_URL, timeout=TIMEOUT).text, "html.parser")
    return {opt["value"]: opt.text.strip()
            for opt in soup.select('select[name="AdvocateSearch[bar_council]"] option')
            if opt["value"].isdigit()}


def get_last_page(sess, cid: str) -> int:
    """Read the '»' pagination link on page 1 to know the final page index."""
    params = {"AdvocateSearch[bar_council]": cid,
              "per-page": ROWS_PER_PAGE,
              "page": 1}
    soup = BeautifulSoup(sess.get(BASE_URL, params=params, timeout=TIMEOUT).text,
                         "html.parser")
    last_link = soup.select_one("ul.pagination li.last a")
    if last_link and last_link.get("data-page", "").isdigit():
        return int(last_link["data-page"])
    return 1


def fetch_page(sess, cid, page):
    params = {"AdvocateSearch[bar_council]": cid,
              "per-page": ROWS_PER_PAGE,
              "page": page}
    for attempt in range(RETRY + 1):
        try:
            resp = sess.get(BASE_URL, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except Exception:
            if attempt == RETRY:
                raise
            time.sleep(2 * (attempt + 1))


def parse(html: str) -> List[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="table")
    if not table:
        return []
    # Each row: serial, name, reg-number, status, … (keep first 3 cols)
    return [{"Registration Number": tds[2], "Name": tds[1]}
            for tr in table.select("tr")[1:]
            if len((tds := [td.get_text(strip=True) for td in tr.find_all("td")])) >= 3]


def scrape_state(sess, cid, state, verbose=False):
    """Loop deterministically from page 1 to last_page inclusive."""
    last = get_last_page(sess, cid)
    if verbose:
        print(f"→ {state} (ID {cid}) – {last} pages expected")

    all_rows = []
    for page in range(1, last + 1):
        html = fetch_page(sess, cid, page)
        rows = parse(html)
        for r in rows:
            r.update({"Practicing Court": f"{state} Courts", "State": state})
        all_rows.extend(rows)

        if verbose and (page == 1 or page % 5 == 0 or page == last):
            print(f"   page {page}/{last} … {len(rows)} rows")

        if SLEEP:
            time.sleep(SLEEP)

    if verbose:
        print(f"← {state} done: {len(all_rows)} rows total")
    return all_rows


def write_csv(path: Path, data: List[dict]):
    if not data:
        return
    path.parent.mkdir(exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=data[0].keys()).writerows(data)


# ─────────────────────────────────────────── main ───────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", action="store_true",
                    help="write advocates_<state>.csv for each state")
    ap.add_argument("--verbose", action="store_true",
                    help="print detailed progress")
    args = ap.parse_args()

    master = []
    try:
        with requests.Session() as sess:
            sess.headers.update(HEADERS)
            councils = discover_councils(sess)
            print(f"Discovered {len(councils)} State/UT Bar Councils.")  # e.g., 24 :contentReference[oaicite:3]{index=3}

            for cid, state in tqdm(councils.items(), desc="States"):
                state_csv = Path(f"advocates_{state.replace(' ', '_')}.csv")
                if args.split and state_csv.exists() and state_csv.stat().st_size > 100:
                    if args.verbose:
                        print(f"⇢ {state} already scraped, skipping.")
                    continue

                rows = scrape_state(sess, cid, state, args.verbose)
                master.extend(rows)
                if args.split:
                    write_csv(state_csv, rows)

    except KeyboardInterrupt:
        print("⏹ Interrupted — writing what’s collected so far…", file=sys.stderr)
    finally:
        write_csv(MASTER_CSV, master)
        print(f"Saved {len(master)} advocates → {MASTER_CSV}")


if __name__ == "__main__":
    main()

