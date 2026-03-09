from django.urls import path
from .views import GoogleCalendarInitView, GoogleCalendarRedirectView, GoogleCalendarEventsView

urlpatterns = [
    path('api/v1/calendar/init/', GoogleCalendarInitView.as_view(), name='calendar_init'),
    path('api/v1/calendar/redirect/', GoogleCalendarRedirectView.as_view(), name='calendar_redirect'),
    path('api/v1/calendar/events/', GoogleCalendarEventsView.as_view(), name='calendar_events'),
]