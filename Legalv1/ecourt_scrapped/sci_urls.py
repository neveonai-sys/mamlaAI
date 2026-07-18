from django.urls import path

from ecourt_scrapped import sci_views as views

urlpatterns = [
    # Health / Metadata
    path('health/',                views.sci_health),
    path('case-types/',            views.sci_case_types),

    # Case Status
    path('case/by-number/',        views.sci_case_by_number),
    path('case/by-diary/',         views.sci_case_by_diary),
    path('case/by-party/',         views.sci_case_by_party),
    path('case/by-aor/',           views.sci_case_by_aor),

    # Cause List
    path('causelist/today/',       views.sci_causelist_today),
    path('causelist/tomorrow/',    views.sci_causelist_tomorrow),
    path('causelist/by-date/',     views.sci_causelist_by_date),

    # Daily Orders
    path('orders/by-case/',        views.sci_orders_by_case),
    path('orders/by-diary/',       views.sci_orders_by_diary),

    # Judgments
    path('judgments/by-case/',     views.sci_judgments_by_case),
    path('judgments/by-party/',    views.sci_judgments_by_party),
    path('judgments/by-date/',     views.sci_judgments_by_date),

    # Office Reports
    path('office-report/by-case/', views.sci_office_report_by_case),
    path('office-report/by-diary/', views.sci_office_report_by_diary),

    # Document / PDF
    path('document/pdf/',          views.sci_document_pdf),
]
