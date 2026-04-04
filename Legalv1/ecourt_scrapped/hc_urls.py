from django.urls import path

from ecourt_scrapped import hc_views as views

urlpatterns = [
    # Health / Info
    path('health/',                       views.hc_health),
    path('courts/',                       views.hc_courts),

    # Metadata
    path('meta/police-stations/',         views.hc_meta_police_stations),
    path('meta/court-numbers/',           views.hc_meta_court_numbers),

    # Case Lookup
    path('case/cnr/<str:cino>/',          views.hc_cnr_search),

    # Case Status Searches
    path('case/party/',                   views.hc_case_party),
    path('case/advocate/',                views.hc_case_advocate),
    path('case/bar-code/',                views.hc_case_bar_code),
    path('case/filing/',                  views.hc_case_filing),
    path('case/fir/',                     views.hc_case_fir),

    # Court Orders
    path('orders/search/',                views.hc_orders_search),
    path('orders/by-court/',              views.hc_orders_by_court),
    path('orders/by-date/',               views.hc_orders_by_date),

    # Cause List
    path('causelist/',                    views.hc_causelist),

    # PDF Proxy
    path('order-pdf/',                    views.hc_order_pdf),
    path('causelist-pdf/',                views.hc_causelist_pdf),
]
