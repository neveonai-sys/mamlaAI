from django.urls import path
from calendar_management import views

urlpatterns = [
    path('add-event/', views.create_event),
    path('get-all-events', views.fetch_event),
    path('delete-event/', views.delete_event),
    path('update-event/', views.update_event)
]