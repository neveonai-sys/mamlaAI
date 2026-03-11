from django.urls import path
from calendar_management import views

urlpatterns = [
    # REST-compatible aliases (used by new frontend)
    path('events/', views.events_rest),
    path('events/<str:event_id>/', views.event_detail_rest),
    path('conflicts/check/', views.conflict_check_rest),
    path('conflicts/resolve/', views.conflict_resolution_rest),

    path('add-event/', views.create_event),
    path('get-all-events', views.fetch_event),
    path('delete-event/', views.delete_event),
    path('update-event/', views.update_event)
]