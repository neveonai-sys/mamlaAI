from django.urls import path
from ecourts_api import views

urlpatterns = [
    # Case endpoints
    path("case/<str:cnr>/", views.get_case_by_cnr, name="ecourts_api_case"),
    path("case/<str:cnr>/refresh/", views.refresh_case, name="ecourts_api_case_refresh"),
    path("case/<str:cnr>/orders/", views.get_case_orders, name="ecourts_api_case_orders"),
    path(
        "case/<str:cnr>/orders/<int:order_index>/download/",
        views.download_order,
        name="ecourts_api_order_download",
    ),

    # Search
    path("search/", views.search_cases, name="ecourts_api_search"),

    # Cause list
    path("causelist/", views.get_cause_list, name="ecourts_api_causelist"),
    path("causelist/dates/", views.get_cause_list_dates, name="ecourts_api_causelist_dates"),

    # Court structure (FREE endpoints)
    path("court-structure/", views.get_court_structure, name="ecourts_api_court_structure"),
    path("court-structure/states/", views.get_states, name="ecourts_api_states"),
    path(
        "court-structure/states/<str:state_code>/districts/",
        views.get_districts,
        name="ecourts_api_districts",
    ),
    path(
        "court-structure/states/<str:state_code>/districts/<str:district_code>/complexes/",
        views.get_complexes,
        name="ecourts_api_complexes",
    ),
    path(
        "court-structure/states/<str:state_code>/districts/<str:district_code>/complexes/<str:complex_code>/courts/",
        views.get_courts,
        name="ecourts_api_courts",
    ),
    path("court-structure/high-courts/", views.get_high_courts, name="ecourts_api_high_courts"),

    # Pre-populated defaults (populated by Celery Beat tasks)
    path("defaults/<str:section>/", views.get_defaults, name="ecourts_api_defaults"),

    # Kept for scraper compat — returns empty
    path("jobs/<str:job_id>/", views.get_job_status, name="ecourts_api_job_status"),
]
