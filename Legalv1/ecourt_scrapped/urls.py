from django.urls import include, path

from ecourt_scrapped import views
from ecourt_scrapped import citation_views

urlpatterns = [
    # Health
    path('health/', views.scraper_health),

    # ── Dropdown / Master Data (cached in MongoDB) ────────────────────────────
    path('states/', views.get_states),
    path('districts/', views.get_districts),
    path('complexes/', views.get_complexes),
    path('establishments/', views.get_establishments),
    path('courts/', views.get_courts),
    path('police-stations/', views.get_police_stations),
    path('order-case-types/', views.get_order_case_types),
    path('order-court-numbers/', views.get_order_court_numbers),

    # ── Flow A: Direct Case Lookup ────────────────────────────────────────────
    path('cnr/search/', views.cnr_search),
    path('case/by-cino/', views.case_by_cino),

    # ── Shared Resolvers ──────────────────────────────────────────────────────
    path('case/from-url/', views.case_from_url),
    path('case/history/', views.case_history),
    path('case/detail/', views.case_detail),
    path('case/order-pdf/', views.order_pdf),

    # ── Flow B: Cause List ────────────────────────────────────────────────────
    path('causelist/fetch/', views.causelist_fetch),

    # ── Flow C: Case Status Search ────────────────────────────────────────────
    path('casestatus/by-party/', views.casestatus_by_party),
    path('casestatus/by-filing/', views.casestatus_by_filing),
    path('casestatus/by-advocate/', views.casestatus_by_advocate),
    path('casestatus/by-fir/', views.casestatus_by_fir),

    # ── Flow D: Court Orders Search ───────────────────────────────────────────
    path('courtorder/by-party/', views.courtorder_by_party),
    path('courtorder/by-case-number/', views.courtorder_by_case_number),
    path('courtorder/by-court-number/', views.courtorder_by_court_number),
    path('courtorder/by-order-date/', views.courtorder_by_order_date),

    # ── Seed / Admin ──────────────────────────────────────────────────────────
    path('seed/', views.seed_hierarchy),
    path('crawl/status/', views.crawl_status),

    # ── Data Read (serve from pre-crawled MongoDB collections) ────────────────
    path('data/states/', views.data_states),
    path('data/districts/', views.data_districts),
    path('data/complexes/', views.data_complexes),
    path('data/establishments/', views.data_establishments),
    path('data/courts/', views.data_courts),
    path('data/police-stations/', views.data_police_stations),
    path('data/case-types/', views.data_case_types),

    # ── High Court (HC scraper on port 8001) ─────────────────────────────────
    path('hc/', include('ecourt_scrapped.hc_urls')),

    # ── Supreme Court citation lookup (e-SCR scraper, mounted at /sc) ────────
    path('citations/health/', citation_views.citation_health),
    path('citations/lookup/', citation_views.citation_lookup),
    path('citations/case-search/search/', citation_views.citation_case_search),
    path('citations/case-search/page/', citation_views.citation_case_search_page),
    path('citations/case-search/resolve/', citation_views.citation_case_search_resolve),
]
