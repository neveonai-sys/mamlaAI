from django.urls import path

from ecourt_scrapped import cat_views as views

urlpatterns = [
    # Health / Metadata
    path('health/',              views.cat_health),
    path('benches/',              views.cat_benches),
    path('case-types/',          views.cat_case_types),

    # Case Status
    path('case/by-number/',      views.cat_case_by_number),
    path('case/by-diary/',       views.cat_case_by_diary),
    path('case/by-party/',       views.cat_case_by_party),
    path('case/by-advocate/',    views.cat_case_by_advocate),

    # Cause List
    path('causelist/',           views.cat_causelist),

    # Orders
    path('orders/daily/',        views.cat_orders_daily),
    path('orders/final/',        views.cat_orders_final),

    # Judgments
    path('judgments/search/',    views.cat_judgments_search),
]
