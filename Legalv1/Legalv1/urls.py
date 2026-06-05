"""
URL configuration for Legalv1 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from core.views import health, schema_view, swagger_ui_view, dashboard_home

urlpatterns = [
    path('api/health/', health),
    path('api/dashboard/home/', dashboard_home),
    path('api/schema/', schema_view, name='schema'),
    path('api/schema/swagger-ui/', swagger_ui_view, name='swagger-ui'),
    path('api/analytics/', include('analytics.urls')),
    path('api/users/', include('users.urls')),
    path('', include('calendersetup.urls')),
    path('api/drafts/', include('create_drafts.urls')),
    path('api/aidrafts/', include('ai_draft.urls')),
    path('api/aidraft/', include('ai_draft.urls')),   # alias without 's'
    path('api/calendar/', include('calendar_management.urls')),
    path('api/utils/', include('utilities.urls')),
    path('api/search/', include('search_facility.urls')),
    path('api/webhook/', include('whatsapp_module.urls')),
    path('api/todaysupdates/', include('todaysupdates.urls')),
    path('api/talkdoc/', include('talkdoc.urls')),
    path('api/brain/', include('mamla_brain.urls')),
    # Cases — internal case registry
    path('api/cases/', include('cases.urls')),
    # Mamla agents — AI lifecycle agents
    path('api/agents/', include('agents.urls')),
    # Live eCourts runtime is now scraper-first and uses local CAPTCHA solving.
    # path('api/ecourts/', include('ecourts_scraper.urls')),
    # New eCourts integration: FastAPI scraper proxy with MongoDB caching.
    path('api/ecourts/v2/', include('ecourt_scrapped.urls')),
    # Deprecated reference only: third-party partner API path retired from runtime.
    # path('api/ecourts/', include('ecourts_api.urls')),
]
