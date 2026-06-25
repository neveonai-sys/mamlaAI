"""
Analytics API routes.
"""
from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("usage/summary/", views.usage_summary, name="usage_summary"),
    path("usage/by-user/", views.usage_by_user, name="usage_by_user"),
    path("usage/by-feature/", views.usage_by_feature, name="usage_by_feature"),
    path("owner/dashboard/", views.owner_dashboard, name="owner_dashboard"),
]
