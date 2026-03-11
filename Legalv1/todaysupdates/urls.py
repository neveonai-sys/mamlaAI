# File: todaysupdates/urls.py
from django.urls import path
from todaysupdates import views

urlpatterns = [
    path('updates/', views.updates_list),  # REST alias for new frontend
    path('get-subscriptions/', views.get_subscriptions),
    path('subscribe-court/', views.subscribe_court),
    path('unsubscribe-court/', views.unsubscribe_court),
    path('fetch-updates/', views.fetch_updates),
    path('get-paralegal-subscriptions/', views.get_paralegal_subscription),
    path('paralegal-subscribe-court/', views.paralegal_subscribe_court),
    path('paralegal-unsubscribe-court/', views.paralegal_unsubscribe_court),
    path('fetch-paralegal-updates/', views.fetch_my_updates),
]
