from django.urls import path

from ecourt_scrapped import sci_views as views

urlpatterns = [
    # Health / Metadata
    path('health/',                views.sci_health),
    path('case-types/',            views.sci_case_types),
    path('judges/',                views.sci_judges),

    # Case Status
    path('case/by-number/',        views.sci_case_by_number),
    path('case/by-diary/',         views.sci_case_by_diary),
    path('case/by-party/',         views.sci_case_by_party),
    path('case/by-aor/',           views.sci_case_by_aor),
    path('case/by-cnr/',           views.sci_case_by_cnr),
    path('case-status-court/states/',      views.sci_case_status_court_states),
    path('case-status-court/benches/',     views.sci_case_status_court_benches),
    path('case-status-court/case-types/',  views.sci_case_status_court_case_types),
    path('case/by-court/',         views.sci_case_by_court),

    # Cause List
    path('causelist/today/',       views.sci_causelist_today),
    path('causelist/tomorrow/',    views.sci_causelist_tomorrow),
    path('causelist/by-date/',     views.sci_causelist_by_date),
    path('causelist/search/',      views.sci_causelist_search),

    # Daily Orders
    path('orders/by-case/',        views.sci_orders_by_case),
    path('orders/by-diary/',       views.sci_orders_by_diary),
    path('orders/by-rop-date/',    views.sci_orders_by_rop_date),
    path('orders/free-text/',      views.sci_orders_free_text),

    # Judgments
    path('judgments/by-case/',     views.sci_judgments_by_case),
    path('judgments/by-party/',    views.sci_judgments_by_party),
    path('judgments/by-date/',     views.sci_judgments_by_date),
    path('judgments/by-diary/',    views.sci_judgments_by_diary),
    path('judgments/by-judge/',    views.sci_judgments_by_judge),
    path('judgments/free-text/',   views.sci_judgments_free_text),

    # Office Reports
    path('office-report/by-case/', views.sci_office_report_by_case),
    path('office-report/by-diary/', views.sci_office_report_by_diary),

    # Case Details
    path('case/details/', views.sci_case_details),

    # Document / PDF
    path('document/pdf/',          views.sci_document_pdf),
]
