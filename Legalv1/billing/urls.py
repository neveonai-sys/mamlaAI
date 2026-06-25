from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('create-order/', views.create_order, name='create_order'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('webhook/', views.webhook, name='webhook'),
    path('cancel/', views.cancel_subscription, name='cancel'),
    path('invoice/<str:invoice_id>/', views.get_invoice, name='invoice'),
]
