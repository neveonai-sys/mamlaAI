from django.urls import path

from ecourt_scrapped import cat_views as views

urlpatterns = [
    # Health / Metadata
    path('health/',              views.cat_health),
    path('benches/',              views.cat_benches),
    path('case-types/',          views.cat_case_types),
    path('judges/',               views.cat_judges),

    # Case Status
    path('case/by-number/',      views.cat_case_by_number),
    path('case/by-diary/',       views.cat_case_by_diary),
    path('case/by-party/',       views.cat_case_by_party),
    path('case/by-advocate/',    views.cat_case_by_advocate),
    path('case/detail/',         views.cat_case_detail),

    # Cause List
    path('causelist/',           views.cat_causelist),

    # Orders — Daily
    path('orders/daily/by-case/',    views.cat_orders_daily_by_case),
    path('orders/daily/by-diary/',   views.cat_orders_daily_by_diary),
    path('orders/daily/by-party/',   views.cat_orders_daily_by_party),
    path('orders/daily/by-date/',    views.cat_orders_daily_by_date),
    path('orders/daily/by-judge/',   views.cat_orders_daily_by_judge),

    # Orders — Final / Oral
    path('orders/final/by-case/',    views.cat_orders_final_by_case),
    path('orders/final/by-diary/',   views.cat_orders_final_by_diary),
    path('orders/final/by-date/',    views.cat_orders_final_by_date),
    path('orders/final/by-judge/',   views.cat_orders_final_by_judge),

    # Judgments
    path('judgments/search/',    views.cat_judgments_search),
]
