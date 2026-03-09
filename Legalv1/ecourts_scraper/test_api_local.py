"""
Run eCourts API view tests locally (no HTTP server).
Uses Django test client with bypass_supabase_auth so no real Supabase token needed.
Usage from Legalv1/:
  DEBUG=1 python manage.py shell -c "exec(open('ecourts_scraper/test_api_local.py').read()); run_checks()"
"""
import os
import json
import sys

# Allow running as script
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Legalv1.settings")
    import django
    django.setup()

from django.test import RequestFactory

# Fake user for bypass
def _req(method="GET", path="/", **kwargs):
    rf = RequestFactory()
    if method == "GET":
        req = rf.get(path, **kwargs)
    else:
        req = rf.generic(method, path, **kwargs)
    req.bypass_supabase_auth = True
    req.supabase_user = {"user_id": "dev-test", "email": "dev@local"}
    return req


def _run_checks_main():
    from ecourts_scraper.views import (
        get_court_structure,
        get_high_courts,
        get_district_states,
        get_district_by_state,
        get_courts_by_district,
        get_case_by_cnr,
        get_case_orders,
        get_available_cause_list_dates,
        get_cause_list,
        get_job_status,
        refresh_case,
        search_cases,
        download_order_pdf,
    )

    ok, fail = 0, 0

    # Court structure (no scrape)
    r = get_court_structure(_req())
    if r.status_code == 200:
        d = json.loads(r.content)
        hc = len(d.get("data", {}).get("high_courts", []))
        states = len(d.get("data", {}).get("district_courts", {}).get("states", []))
        print(f"  GET court-structure/ 200  high_courts={hc} district_states={states}")
        ok += 1
    else:
        print(f"  GET court-structure/ {r.status_code} {r.content[:80]}")
        fail += 1

    r = get_high_courts(_req())
    if r.status_code == 200:
        print(f"  GET court-structure/high-courts/ 200  count={len(json.loads(r.content).get('data', []))}")
        ok += 1
    else:
        print(f"  GET high-courts/ {r.status_code}"); fail += 1

    r = get_district_states(_req())
    if r.status_code == 200:
        n = len(json.loads(r.content).get("data", []))
        print(f"  GET court-structure/district/states/ 200  count={n}")
        ok += 1
    else:
        print(f"  GET district/states/ {r.status_code}"); fail += 1

    # One state -> districts -> courts
    r = get_district_states(_req())
    if r.status_code == 200 and json.loads(r.content).get("data"):
        state_name = json.loads(r.content)["data"][0]["name"]
        r2 = get_district_by_state(_req(), state_name)
        if r2.status_code == 200 and json.loads(r2.content).get("data"):
            dist_name = json.loads(r2.content)["data"][0]["name"]
            r3 = get_courts_by_district(_req(), state_name, dist_name)
            if r3.status_code == 200:
                nc = len(json.loads(r3.content).get("data", []))
                print(f"  GET .../districts/ and .../courts/ 200  courts={nc}")
                ok += 1
            else: print(f"  GET courts/ {r3.status_code}"); fail += 1
        else: print(f"  GET districts/ {r2.status_code}"); fail += 1
    else: print("  GET districts (skip no states)"); fail += 1

    # Case by CNR (expect 202 or 200)
    r = get_case_by_cnr(_req(), "DLHC010000012015")
    if r.status_code in (200, 202):
        d = json.loads(r.content)
        print(f"  GET case/<cnr>/ {r.status_code}  job_id={d.get('job_id', 'cached')}")
        ok += 1
    else:
        print(f"  GET case/<cnr>/ {r.status_code} {r.content[:60]}"); fail += 1

    # Orders without cache -> 404
    r = get_case_orders(_req(), "DLHC010000012015")
    if r.status_code == 404:
        print(f"  GET case/<cnr>/orders/ 404 (expected when not cached)")
        ok += 1
    else:
        print(f"  GET case/<cnr>/orders/ {r.status_code}"); fail += 1

    # Causelist dates
    req = _req()
    req.GET = req.GET.copy()
    req.GET["high_court_id"], req.GET["bench_code"] = "5", "1"
    r = get_available_cause_list_dates(req)
    if r.status_code == 200:
        print(f"  GET causelist/dates/ 200  dates={len(json.loads(r.content).get('dates', []))}")
        ok += 1
    else:
        print(f"  GET causelist/dates/ {r.status_code}"); fail += 1

    # Cause list missing params -> 400
    r = get_cause_list(_req())
    if r.status_code == 400:
        print(f"  GET causelist/ no params 400 (expected)")
        ok += 1
    else:
        print(f"  GET causelist/ {r.status_code}"); fail += 1

    # Search -> 202 or 200
    req = RequestFactory().post(
        "/api/ecourts/search/",
        data=json.dumps({"query": "Test", "court_type": "high_court", "high_court_id": "5", "bench_code": "1"}),
        content_type="application/json",
    )
    req.bypass_supabase_auth = True
    req.supabase_user = {"user_id": "dev", "email": "dev@local"}
    r = search_cases(req)
    if r.status_code in (200, 202):
        print(f"  POST search/ {r.status_code}")
        ok += 1
    else:
        print(f"  POST search/ {r.status_code}"); fail += 1

    # Invalid CNR -> 400
    r = get_case_by_cnr(_req(), "x")
    if r.status_code == 400:
        print(f"  GET case/invalid/ 400 (expected)")
        ok += 1
    else:
        print(f"  GET case/invalid/ {r.status_code}"); fail += 1

    # Real check: cache -> API returns correct shape (proves scraper response path)
    ok2, fail2 = _run_cache_response_check()
    ok, fail = ok + ok2, fail + fail2

    print(f"\nResult: {ok} passed, {fail} failed")
    return fail == 0


def _run_cache_response_check():
    """Insert mock scraped data into cache, then verify API returns it with correct shape."""
    from ecourts_scraper.cache.cache_manager import EcourtsCacheManager
    from ecourts_scraper.views import get_case_by_cnr, get_case_orders

    ok, fail = 0, 0
    test_cnr = "TESTCACHE1234567890"
    cache = EcourtsCacheManager()

    mock_case = {
        "case_details_raw": [["CNR Number", test_cnr], ["Case Type", "Civil"]],
        "case_title": "Test Petitioner vs Test Respondent",
        "hearing_history": [],
        "orders": [
            {"Order Date": "01/01/2024", "Description": "Test order", "Link": "#"},
        ],
    }

    try:
        cache.set("hc:case:" + test_cnr, "case_detail", mock_case, "hcservices.ecourts.gov.in")
        r = get_case_by_cnr(_req(), test_cnr)
        if r.status_code != 200:
            print(f"  [cache check] GET case/ after cache  {r.status_code} (expected 200)")
            fail += 1
        else:
            d = json.loads(r.content)
            data = d.get("data", {})
            if data.get("case_title") != mock_case["case_title"] or "orders" not in data:
                print(f"  [cache check] GET case/ data shape wrong")
                fail += 1
            else:
                print(f"  [cache check] GET case/ 200  data from cache (case_title, orders present)")
                ok += 1

        r = get_case_orders(_req(), test_cnr)
        if r.status_code != 200:
            print(f"  [cache check] GET case/orders/ {r.status_code} (expected 200)")
            fail += 1
        else:
            d = json.loads(r.content)
            orders = d.get("orders", [])
            if len(orders) != 1:
                print(f"  [cache check] GET case/orders/ wrong count {len(orders)}")
                fail += 1
            else:
                print(f"  [cache check] GET case/orders/ 200  orders={len(orders)}")
                ok += 1

        cache.invalidate("hc:case:" + test_cnr)
    except Exception as e:
        print(f"  [cache check] error: {e}")
        fail += 2

    return ok, fail


def run_checks():
    return _run_checks_main()


if __name__ == "__main__":
    print("eCourts API local checks (bypass auth)\n")
    success = run_checks()
    sys.exit(0 if success else 1)
