"""
One-off conversion script: turns the raw 2026 High Court holiday dataset
(highcourt_holidays_2026.json, court-grouped) into the per-state JSON files
the calendar app actually reads from ../states/<StateName>.json.

Not imported by the Django app or the FastAPI scraper — run manually:
    python3 convert_highcourt_holidays.py

State-name and bench-routing assumptions are explicit below (COURT_ROUTES)
rather than inferred, since a silent mismatch against the signup state
dropdown's exact string values would mean a state's file is generated but
never picked up. These names were not cross-checked against a live
`state_district_court_data` Mongo query (no DB access in this environment)
— verify against GET /api/users/get-states/ before treating as final,
especially for UTs (Ladakh, Lakshadweep, Chandigarh, Dadra and Nagar Haveli
and Daman and Diu) which may not appear in that collection at all if no
court complexes there are catalogued.
"""

import json
import os
from collections import defaultdict

RAW_DIR = os.path.dirname(__file__)
STATES_DIR = os.path.join(RAW_DIR, "..", "states")
RAW_FILE = os.path.join(RAW_DIR, "highcourt_holidays_2026.json")


# Each court maps to one or more (state_name, bench_filter) targets.
# bench_filter=None means "include every bench's entries for this court
# under this one state" (single-state courts, or a UT with no dedicated
# bench data — reuse the court's full/Principal-Seat list as-is).
# bench_filter=set(...) means "only include entries whose bench is one of
# these" — used where the data unambiguously ties specific benches to
# specific states/UTs within one multi-state court.
COURT_ROUTES = {
    "Allahabad High Court": [("Uttar Pradesh", None)],
    "Andhra Pradesh High Court": [("Andhra Pradesh", None)],
    "Bombay High Court": [
        # The combined bench label literally covers Goa too ("...and Goa"),
        # so Goa needs both its own bench's extra local holidays AND the
        # combined bench's common ones (Republic Day, Independence Day,
        # etc.) — excluding it would leave Goa with only its 3-4 local
        # additions and none of the shared holidays.
        ("Goa", {"Goa Bench", "Principal Seat, Nagpur, Aurangabad, Kolhapur Circuit Bench and Goa"}),
        ("Maharashtra", {
            "Principal Seat, Nagpur, Aurangabad, Kolhapur Circuit Bench and Goa",
            "Nagpur Bench", "Aurangabad Bench", "Kolhapur Circuit Bench",
        }),
        # No dedicated bench for this UT in the dataset — reuse the
        # combined Principal Seat list as the best available fallback.
        ("Dadra and Nagar Haveli and Daman and Diu", {
            "Principal Seat, Nagpur, Aurangabad, Kolhapur Circuit Bench and Goa",
        }),
    ],
    "Calcutta High Court": [
        ("West Bengal", None),
        # No dedicated Port Blair/A&N bench in the dataset — Principal
        # Seat fallback.
        ("Andaman and Nicobar Islands", None),
    ],
    "Chhattisgarh High Court": [("Chhattisgarh", None)],
    "Delhi High Court": [("Delhi", None)],
    "Gauhati High Court": [
        ("Assam", {"Principal Seat"}),
        ("Mizoram", {"Aizawl Bench"}),
        ("Arunachal Pradesh", {"Itanagar Bench"}),
        ("Nagaland", {"Kohima Bench"}),
    ],
    "Gujarat High Court": [("Gujarat", None)],
    "Himachal Pradesh High Court": [("Himachal Pradesh", None)],
    "High Court of Jammu & Kashmir and Ladakh": [
        ("Ladakh", {"Ladakh", "All Wings"}),
        ("Jammu and Kashmir", {"Jammu Wing", "Srinagar Wing", "All Wings"}),
    ],
    "Jharkhand High Court": [("Jharkhand", None)],
    "Karnataka High Court": [("Karnataka", None)],
    "Kerala High Court": [
        ("Kerala", None),
        ("Lakshadweep", None),  # Principal Seat fallback, no dedicated bench
    ],
    "Madhya Pradesh High Court": [("Madhya Pradesh", None)],
    "Madras High Court": [],  # holiday_count: 0, "Data Not Readily Available"
    "Manipur High Court": [("Manipur", None)],
    "Meghalaya High Court": [("Meghalaya", None)],
    "Orissa High Court": [("Odisha", None)],
    "Patna High Court": [("Bihar", None)],
    "Punjab and Haryana High Court": [
        ("Punjab", None),
        ("Haryana", None),
        ("Chandigarh", None),  # Principal Seat fallback, no dedicated bench
    ],
    "Rajasthan High Court": [("Rajasthan", None)],
    "Sikkim High Court": [("Sikkim", None)],
    "Telangana High Court": [("Telangana", None)],
    "Tripura High Court": [("Tripura", None)],
    "Uttarakhand High Court": [("Uttarakhand", None)],
}


def convert_entry(raw):
    return {
        "date": raw["date"],
        "name": raw["holiday"],
        "holiday_type": raw.get("holiday_type"),
        "bench": raw.get("bench"),
        "source_url": raw.get("source_document_url"),
    }


def main():
    with open(RAW_FILE) as f:
        data = json.load(f)

    state_entries = defaultdict(list)

    for court in data["court_calendars"]:
        court_name = court["court"]
        routes = COURT_ROUTES.get(court_name)
        if routes is None:
            raise SystemExit(f"No route defined for court: {court_name!r} — add it to COURT_ROUTES")
        for state_name, bench_filter in routes:
            for h in court["holidays"]:
                if bench_filter is not None and h.get("bench") not in bench_filter:
                    continue
                state_entries[state_name].append(convert_entry(h))

    os.makedirs(STATES_DIR, exist_ok=True)
    for state_name, entries in sorted(state_entries.items()):
        entries.sort(key=lambda e: (e["date"], e["name"]))
        out_path = os.path.join(STATES_DIR, f"{state_name}.json")
        with open(out_path, "w") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"wrote {len(entries):4d} entries -> {out_path}")


if __name__ == "__main__":
    main()
