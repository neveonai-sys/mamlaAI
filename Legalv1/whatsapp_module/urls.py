from django.urls import path
from whatsapp_module import views

urlpatterns = [
    # Meta verification endpoint (if needed)
    path('verify/', views.whatsapp_webhook),
    # Main webhook
    path('', views.whatsapp_webhook),
]
