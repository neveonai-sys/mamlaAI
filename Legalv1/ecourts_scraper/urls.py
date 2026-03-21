from django.urls import path
from ecourts_scraper import views

urlpatterns = [
    # Case lookup
    path('case/<str:cnr>/', views.get_case_by_cnr),
    path('case/<str:cnr>/refresh/', views.refresh_case),
    path('case/<str:cnr>/orders/', views.get_case_orders),
    path('case/<str:cnr>/orders/<int:order_index>/download/', views.download_order_pdf),

    # Search
    path('search/', views.search_cases),

    # Job polling
    path('jobs/<str:job_id>/', views.get_job_status),

    # Cause list
    path('causelist/', views.get_cause_list),
    path('causelist/dates/', views.get_available_cause_list_dates),

    # Reference data for stitched terminal flows
    path('reference/<str:section>/', views.get_reference_section),

    # Court structure (tree)
    path('court-structure/', views.get_court_structure),
    path('court-structure/high-courts/', views.get_high_courts),
    path('court-structure/district/states/', views.get_district_states),
    path(
        'court-structure/district/states/<str:state_name>/districts/',
        views.get_district_by_state,
    ),
    path(
        'court-structure/district/states/<str:state_name>/districts/<str:district_name>/complexes/',
        views.get_complexes_by_district,
    ),
    path(
        'court-structure/district/states/<str:state_name>/districts/<str:district_name>/courts/',
        views.get_courts_by_district,
    ),
    path(
        'court-structure/district/states/<str:state_name>/districts/<str:district_name>/complexes/<str:complex_code>/courts/',
        views.get_courts_by_complex,
    ),
]
