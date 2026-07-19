from django.urls import path
from utilities import views

urlpatterns = [
    path('send-simple-mail/', views.send_mail_page),
    path('send-email/', views.send_email),
    path('contact/', views.contact_inquiry),
    path('state-district-court/', views.state_district_courtlist),
]